"""Voice loop module - STT/TTS voice conversation handling."""
import sys
import time

from .config import C, cpr
from .utils import mprint


def _extract_stt_text(outcome: dict) -> str:
    """Extract transcribed text from STT outcome.
    
    Checks multiple possible keys where STT might store the text.
    """
    if not outcome:
        return ""
    
    result = outcome.get("result", {})
    
    # Try various possible keys
    for key in ["spoken", "text", "transcript", "recognized", "value"]:
        if key in result and result[key]:
            return result[key]
    
    # Check nested structure
    if "output" in result:
        output = result["output"]
        for key in ["spoken", "text", "transcript"]:
            if key in output and output[key]:
                return output[key]
    
    return ""


def _speak_tts(sm, evo, text: str) -> None:
    """Speak text using TTS skill."""
    sk = sm.list_skills()
    evo.handle_request(
        text, sk,
        analysis={"action": "use", "skill": "tts",
                  "input": {"text": text, "lang": "pl"},
                  "goal": "voice_response"}
    )


def _run_stt_cycle(sm, evo, llm, intent, logger, conv, identity, duration=5, memory=None):
    """Single STT→LLM→TTS cycle. Returns ('got_text', text) or ('silence', '') or ('error', msg)."""
    # Import here to avoid circular dependency
    from .core import _handle_chat
    
    sk = sm.list_skills()
    outcome = evo.handle_request(
        "[voice]", sk,
        analysis={"action": "use", "skill": "stt",
                  "input": {"duration_s": duration, "lang": "pl"},
                  "goal": "voice_conversation"}
    )
    if not outcome or outcome.get("type") != "success":
        return "error", outcome.get("goal", "stt failed") if outcome else "stt failed"
    stt_text = _extract_stt_text(outcome)
    if not stt_text:
        return "silence", ""
    cpr(C.GREEN, f"[STT] Usłyszałem: \"{stt_text}\"")
    mprint(f"### 🎤 *{stt_text}*")
    conv.append({"role": "user", "content": f"[głosowo] {stt_text}"})
    response = _handle_chat(llm, sm, logger, conv, identity=identity, memory=memory)
    # Speak the response via TTS
    if response:
        _speak_tts(sm, evo, response)
    intent.record_skill_use("stt")
    return "got_text", stt_text


def _run_stt_autotest(sm, logger, llm=None) -> dict:
    """Run STT hardware/audio auto-test with auto-repair at each stage.
    
    Flow per stage: DETECT → AUTO-FIX → RE-TEST → VERIFY → JOURNAL
    - Records every attempt in RepairJournal (learns from past)
    - Checks known fixes before trying blind repairs
    - Consults LLM when local fixes fail
    - Never just reports — always tries to fix first.
    Returns diagnostic dict with fix results.
    """
    import shutil, subprocess, tempfile, os
    from pathlib import Path
    from .repair_journal import RepairJournal
    
    journal = RepairJournal(llm_client=llm)
    
    cpr(C.CYAN, "\n[REFLECT] === Autotest STT (detect → fix → verify → learn) ===")
    
    diagnostics = {
        "microphone": {"ok": False},
        "audio_level": {"ok": False},
        "transcription": {"ok": False},
        "fixes_applied": [],
        "llm_consulted": False,
    }

    # ── Helper: record test wav ─────────────────────────────────────
    def _record_test(path, duration=2):
        try:
            r = subprocess.run(
                ["arecord", "-q", "-d", str(duration), "-f", "S16_LE",
                 "-r", "16000", "-c", "1", path],
                capture_output=True, timeout=duration + 8)
            return r.returncode == 0
        except Exception:
            return False

    # ── Helper: measure audio level ─────────────────────────────────
    def _measure_db(path):
        """Returns (has_sound, db_level). Uses sox → ffmpeg → file size."""
        if shutil.which("sox"):
            try:
                sr = subprocess.run(
                    ["sox", path, "-n", "stat"],
                    capture_output=True, text=True, timeout=10)
                for line in sr.stderr.split('\n'):
                    if 'RMS amplitude' in line:
                        parts = line.split(':')
                        if len(parts) >= 2:
                            amp = float(parts[1].strip())
                            if amp > 0:
                                db = 20 * (amp ** 0.5) - 60
                                return db > -40.0, db
            except Exception:
                pass
        if shutil.which("ffmpeg"):
            try:
                sr = subprocess.run(
                    ["ffmpeg", "-i", path, "-af", "volumedetect",
                     "-f", "null", "-"],
                    capture_output=True, text=True, timeout=10)
                for line in sr.stderr.split('\n'):
                    if 'mean_volume' in line and 'dB' in line:
                        db = float(line.split(':')[1].split('dB')[0].strip())
                        return db > -40.0, db
            except Exception:
                pass
        try:
            sz = Path(path).stat().st_size
            return sz > 10000, -999.0 if sz <= 10000 else 0.0
        except Exception:
            return False, -999.0

    # ── Helper: test vosk with explicit model path ──────────────────
    def _test_vosk(wav_path, model_path=None):
        if not shutil.which("vosk-transcriber"):
            return False, "vosk-transcriber not found"
        fd2, out_path = tempfile.mkstemp(suffix=".txt", prefix="stt_autotest_out_")
        os.close(fd2)
        try:
            cmd = ["vosk-transcriber", "--input", wav_path,
                   "--output", out_path, "--output-type", "txt"]
            if model_path:
                cmd.extend(["--model", str(model_path)])
            tr = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return tr.returncode == 0, (tr.stderr or "")[:300]
        except Exception as e:
            return False, str(e)
        finally:
            try: Path(out_path).unlink(missing_ok=True)
            except: pass
    
    # ── Helper: find vosk model directories ─────────────────────────
    def _find_vosk_models():
        """Find all vosk model directories. Also clean stale files."""
        cache_dirs = [
            Path.home() / ".cache" / "vosk",
            Path.home() / ".local" / "share" / "vosk",
        ]
        models = []
        stale_files = []
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            for item in cache_dir.iterdir():
                if item.is_dir() and "model" in item.name.lower():
                    models.append(item)
                elif item.is_file() and item.suffix == ".zip":
                    stale_files.append(item)
        return models, stale_files

    # ═══════════════════════════════════════════════════════════════
    # STAGE 1: MICROPHONE HARDWARE
    # ═══════════════════════════════════════════════════════════════
    cpr(C.DIM, "  [1/4] Sprawdzam mikrofon...")
    if not shutil.which("arecord"):
        cpr(C.YELLOW, "  ✗ arecord brak — próbuję zainstalować alsa-utils...")
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "alsa-utils"],
                           capture_output=True, timeout=30)
            if shutil.which("arecord"):
                cpr(C.GREEN, "  ✓ alsa-utils zainstalowane!")
                diagnostics["fixes_applied"].append("installed alsa-utils")
                journal.record_attempt("stt", "arecord missing",
                    "apt_install", "sudo apt install alsa-utils", True)
            else:
                cpr(C.RED, "  ✗ Nie udało się zainstalować alsa-utils")
                journal.record_attempt("stt", "arecord missing",
                    "apt_install", "sudo apt install alsa-utils", False)
        except Exception:
            cpr(C.RED, "  ✗ Nie udało się zainstalować alsa-utils")
    
    if shutil.which("arecord"):
        try:
            r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().split('\n')
            devices = [l for l in lines if l.strip().startswith('card') and 'device' in l]
            if devices:
                cpr(C.GREEN, f"  ✓ Mikrofon: {len(devices)} urządzenie(a)")
                diagnostics["microphone"] = {"ok": True, "devices": len(devices),
                                             "device_list": [d.strip() for d in devices]}
            else:
                cpr(C.RED, "  ✗ Brak urządzeń capture — sprzętowy problem")
                diagnostics["microphone"] = {"ok": False, "error": "no capture devices"}
        except Exception as e:
            cpr(C.RED, f"  ✗ Mikrofon: {e}")
            diagnostics["microphone"] = {"ok": False, "error": str(e)}

    if not diagnostics["microphone"]["ok"]:
        cpr(C.RED, "[REFLECT] Brak mikrofonu — nie mogę naprawić sprzętowego problemu")
        logger.core("stt_autotest", diagnostics)
        return diagnostics

    # ═══════════════════════════════════════════════════════════════
    # STAGE 2: AUDIO LEVEL — detect silence → try amixer fixes → re-test
    # ═══════════════════════════════════════════════════════════════
    cpr(C.DIM, "  [2/4] Testuję poziom audio...")
    fd, test_wav = tempfile.mkstemp(suffix=".wav", prefix="stt_autotest_")
    os.close(fd)
    
    try:
        if not _record_test(test_wav):
            cpr(C.RED, "  ✗ Nagrywanie testowe nie powiodło się")
            diagnostics["audio_level"] = {"ok": False, "error": "arecord failed"}
        else:
            has_sound, db_level = _measure_db(test_wav)
            fsize = Path(test_wav).stat().st_size
            
            if has_sound:
                cpr(C.GREEN, f"  ✓ Audio level: {db_level:.1f}dB (OK)")
                diagnostics["audio_level"] = {"ok": True, "db": db_level}
            else:
                cpr(C.YELLOW, f"  ✗ Audio level: {db_level:.1f}dB (cisza, {fsize}b)")
                
                # Check journal for known fixes first
                known = journal.get_known_fix(f"audio silence {db_level}dB")
                if known and known.confidence >= 0.7:
                    cpr(C.CYAN, f"  [JOURNAL] Znany fix (conf={known.confidence:.0%}): {known.fix_type}")
                
                cpr(C.CYAN, "  [AUTOFIX] Próbuję naprawić ustawienia audio...")
                amixer_fixes = [
                    (["amixer", "set", "Capture", "unmute"], "Capture unmute"),
                    (["amixer", "set", "Capture", "100%"], "Capture 100%"),
                    (["amixer", "-c", "0", "set", "Capture", "unmute"], "Card0 Capture unmute"),
                    (["amixer", "-c", "0", "set", "Capture", "100%"], "Card0 Capture 100%"),
                    (["amixer", "set", "Mic", "unmute"], "Mic unmute"),
                    (["amixer", "set", "Mic", "100%"], "Mic 100%"),
                    (["amixer", "set", "Capture", "cap"], "Capture cap"),
                    (["amixer", "-c", "0", "set", "Capture", "cap"], "Card0 Capture cap"),
                    (["amixer", "-c", "1", "set", "Capture", "unmute"], "Card1 Capture unmute"),
                    (["amixer", "-c", "1", "set", "Capture", "100%"], "Card1 Capture 100%"),
                ]
                
                # Skip fixes that journal says always fail
                failed_types = journal.get_failed_fixes(f"audio silence")
                
                fixes_tried = []
                for cmd, desc in amixer_fixes:
                    if desc in failed_types:
                        continue
                    try:
                        r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                        if r.returncode == 0:
                            fixes_tried.append(desc)
                            cpr(C.DIM, f"    ✓ {desc}")
                    except Exception:
                        pass
                
                if fixes_tried:
                    diagnostics["fixes_applied"].extend(fixes_tried)
                    cpr(C.CYAN, f"  [AUTOFIX] Zastosowano {len(fixes_tried)} poprawek. Weryfikuję...")
                    
                    time.sleep(0.5)
                    fd2, test_wav2 = tempfile.mkstemp(suffix=".wav", prefix="stt_retest_")
                    os.close(fd2)
                    try:
                        if _record_test(test_wav2):
                            has_sound2, db_level2 = _measure_db(test_wav2)
                            if has_sound2:
                                cpr(C.GREEN, f"  ✓ NAPRAWIONE! Audio: {db_level2:.1f}dB (było {db_level:.1f}dB)")
                                diagnostics["audio_level"] = {"ok": True, "db": db_level2,
                                                              "fixed_from": db_level}
                                for ft in fixes_tried:
                                    journal.record_attempt("stt", f"audio silence {db_level}dB",
                                        ft, f"amixer {ft}", True, f"Naprawione: {db_level2:.1f}dB")
                            else:
                                cpr(C.YELLOW, f"  ✗ Nadal cisza ({db_level2:.1f}dB) po amixer fix")
                                diagnostics["audio_level"] = {"ok": False, "db": db_level2,
                                                              "attempted_fixes": fixes_tried}
                                for ft in fixes_tried:
                                    journal.record_attempt("stt", f"audio silence {db_level}dB",
                                        ft, f"amixer {ft}", False, f"Nadal cisza: {db_level2:.1f}dB")
                                if shutil.which("pactl"):
                                    cpr(C.DIM, "  [AUTOFIX] Próbuję PulseAudio...")
                                    _try_pulseaudio_fix(diagnostics)
                        else:
                            diagnostics["audio_level"] = {"ok": False, "db": db_level,
                                                          "error": "retest recording failed"}
                    finally:
                        try: Path(test_wav2).unlink(missing_ok=True)
                        except: pass
                else:
                    diagnostics["audio_level"] = {"ok": False, "db": db_level,
                                                  "error": "no amixer fixes worked"}
    finally:
        try: Path(test_wav).unlink(missing_ok=True)
        except: pass

    # ═══════════════════════════════════════════════════════════════
    # STAGE 3: VOSK TRANSCRIPTION — deep diagnosis with path fixing
    # ═══════════════════════════════════════════════════════════════
    cpr(C.DIM, "  [3/4] Testuję transkrypcję vosk...")
    
    if not shutil.which("vosk-transcriber"):
        cpr(C.YELLOW, "  ✗ vosk-transcriber brak — próbuję zainstalować...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "vosk"],
                           capture_output=True, timeout=60)
            if shutil.which("vosk-transcriber"):
                cpr(C.GREEN, "  ✓ vosk zainstalowany!")
                diagnostics["fixes_applied"].append("pip install vosk")
                journal.record_attempt("stt", "vosk-transcriber missing",
                    "pip_install", "pip install vosk", True)
        except Exception:
            pass
    
    if shutil.which("vosk-transcriber"):
        # Pre-detect model and clean stale zips BEFORE first test
        models, stale_zips = _find_vosk_models()
        if stale_zips:
            for zf in stale_zips:
                try:
                    zf.unlink()
                    cpr(C.DIM, f"    Usunięto stary zip: {zf.name}")
                    diagnostics["fixes_applied"].append(f"removed stale {zf.name}")
                except Exception:
                    pass
        
        # Find best model path for first test
        detected_model = None
        for m in models:
            if "pl" in m.name.lower():
                detected_model = m
                break
        if not detected_model and models:
            detected_model = models[0]
        if detected_model:
            cpr(C.DIM, f"    Model: {detected_model.name}")
        
        fd3, test_wav3 = tempfile.mkstemp(suffix=".wav", prefix="stt_vosk_test_")
        os.close(fd3)
        try:
            if _record_test(test_wav3, duration=2):
                vosk_ok, vosk_err = _test_vosk(test_wav3, model_path=detected_model)
                if vosk_ok:
                    cpr(C.GREEN, "  ✓ vosk-transcriber: działa")
                    diagnostics["transcription"] = {"ok": True}
                    journal.record_success("stt", "vosk transcription OK")
                else:
                    cpr(C.YELLOW, f"  ✗ vosk-transcriber błąd: {vosk_err[:100]}")
                    
                    # ── DEEP FIX: analyze vosk error precisely ──────
                    models, stale_zips = _find_vosk_models()
                    
                    # Fix 1: Remove stale zip files confusing vosk
                    if stale_zips:
                        for zf in stale_zips:
                            cpr(C.CYAN, f"  [AUTOFIX] Usuwam nierozpakowany zip: {zf.name}")
                            try:
                                zf.unlink()
                                diagnostics["fixes_applied"].append(f"removed stale {zf.name}")
                                journal.record_attempt("stt", vosk_err,
                                    "remove_stale_zip", f"rm {zf}", True,
                                    f"Usunięto plik myłący vosk: {zf.name}")
                            except Exception as e:
                                cpr(C.YELLOW, f"  ✗ Nie mogę usunąć: {e}")
                    
                    # Fix 2: Find correct PL model and test with explicit path
                    pl_model = None
                    for m in models:
                        if "pl" in m.name.lower():
                            pl_model = m
                            break
                    if not pl_model and models:
                        pl_model = models[0]
                    
                    if pl_model:
                        cpr(C.CYAN, f"  [AUTOFIX] Test z jawną ścieżką modelu: {pl_model.name}")
                        vosk_ok2, vosk_err2 = _test_vosk(test_wav3, model_path=pl_model)
                        if vosk_ok2:
                            cpr(C.GREEN, f"  ✓ NAPRAWIONE! vosk działa z --model {pl_model.name}")
                            diagnostics["transcription"] = {"ok": True, "fixed": True,
                                                            "model_path": str(pl_model)}
                            diagnostics["fixes_applied"].append(f"explicit model path: {pl_model.name}")
                            journal.record_attempt("stt", vosk_err,
                                "explicit_model_path", f"--model {pl_model}", True,
                                "vosk działa z jawną ścieżką modelu")
                        else:
                            cpr(C.YELLOW, f"  ✗ Nadal nie działa z jawnym modelem: {vosk_err2[:80]}")
                            journal.record_attempt("stt", vosk_err,
                                "explicit_model_path", f"--model {pl_model}", False,
                                vosk_err2[:100])
                            
                            # Fix 3: Re-test after stale zip removal (default path now clean)
                            if stale_zips:
                                cpr(C.DIM, "  [AUTOFIX] Ponowny test vosk (po czyszczeniu cache)...")
                                vosk_ok3, vosk_err3 = _test_vosk(test_wav3)
                                if vosk_ok3:
                                    cpr(C.GREEN, "  ✓ NAPRAWIONE! vosk działa po czyszczeniu cache")
                                    diagnostics["transcription"] = {"ok": True, "fixed": True}
                                    diagnostics["fixes_applied"].append("cleaned vosk cache")
                                    journal.record_attempt("stt", vosk_err,
                                        "clean_cache", "rm stale zips", True)
                                else:
                                    diagnostics["transcription"] = {"ok": False, 
                                                                    "error": vosk_err3[:200]}
                            else:
                                diagnostics["transcription"] = {"ok": False, 
                                                                "error": vosk_err2[:200]}
                    else:
                        # No model found at all — download
                        cpr(C.CYAN, "  [AUTOFIX] Brak modelu vosk — pobieram PL...")
                        try:
                            cache_dir = Path.home() / ".cache" / "vosk"
                            cache_dir.mkdir(parents=True, exist_ok=True)
                            dl_cmd = (
                                f"cd {cache_dir} && "
                                "curl -L -o model.zip "
                                "'https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip' && "
                                "unzip -q -o model.zip && rm -f model.zip"
                            )
                            r = subprocess.run(dl_cmd, shell=True,
                                               capture_output=True, timeout=120)
                            if r.returncode == 0:
                                cpr(C.GREEN, "  ✓ Model PL pobrany!")
                                diagnostics["fixes_applied"].append("downloaded vosk-model-small-pl-0.22")
                                journal.record_attempt("stt", "no vosk model",
                                    "download_model", dl_cmd[:80], True)
                                # Re-test
                                vosk_ok4, _ = _test_vosk(test_wav3)
                                diagnostics["transcription"] = {"ok": vosk_ok4, 
                                                                "fixed": vosk_ok4}
                            else:
                                cpr(C.YELLOW, f"  ✗ Pobieranie modelu: exit {r.returncode}")
                                journal.record_attempt("stt", "no vosk model",
                                    "download_model", dl_cmd[:80], False)
                                diagnostics["transcription"] = {"ok": False,
                                    "error": "model download failed"}
                        except Exception as e:
                            diagnostics["transcription"] = {"ok": False, "error": str(e)[:200]}
        finally:
            try: Path(test_wav3).unlink(missing_ok=True)
            except: pass
    else:
        diagnostics["transcription"] = {"ok": False, "error": "vosk-transcriber unavailable"}

    # ═══════════════════════════════════════════════════════════════
    # STAGE 4: LLM CONSULTATION — if local fixes didn't help
    # ═══════════════════════════════════════════════════════════════
    still_broken = [k for k in ("microphone", "audio_level", "transcription")
                    if not diagnostics[k].get("ok")]
    
    if still_broken and llm:
        cpr(C.CYAN, f"  [4/4] Konsultuję LLM o {', '.join(still_broken)}...")
        diagnostics["llm_consulted"] = True
        
        for problem_area in still_broken:
            err_detail = diagnostics[problem_area].get("error", "unknown")
            attempted = diagnostics.get("fixes_applied", [])
            
            sys_ctx = (f"Linux system. Microphone: {diagnostics['microphone']}. "
                       f"Audio: {diagnostics['audio_level']}. "
                       f"Transcription: {diagnostics['transcription']}")
            
            llm_result = journal.ask_llm_and_try(
                skill_name="stt",
                error=f"{problem_area}: {err_detail}",
                system_context=sys_ctx,
                attempted_fixes=attempted,
            )
            
            if llm_result.get("success"):
                diagnostics["fixes_applied"].append(f"llm_fix_{problem_area}")
                cpr(C.GREEN, f"  [LLM] ✓ {problem_area} naprawione przez LLM!")
                # Re-check this specific area
                if problem_area == "transcription":
                    fd_re, wav_re = tempfile.mkstemp(suffix=".wav", prefix="stt_llm_retest_")
                    os.close(fd_re)
                    try:
                        if _record_test(wav_re, 2):
                            ok_re, _ = _test_vosk(wav_re)
                            diagnostics["transcription"] = {"ok": ok_re, "fixed": ok_re,
                                                            "fix_source": "llm"}
                    finally:
                        try: Path(wav_re).unlink(missing_ok=True)
                        except: pass
            else:
                cpr(C.DIM, f"  [LLM] Nie udało się naprawić {problem_area}: "
                           f"{llm_result.get('diagnosis', '')[:80]}")
    elif still_broken:
        cpr(C.DIM, "  [4/4] Brak LLM — pomijam konsultację")

    # ═══════════════════════════════════════════════════════════════
    # SUMMARY
    # ═══════════════════════════════════════════════════════════════
    all_ok = all(diagnostics[k].get("ok") for k in ("microphone", "audio_level", "transcription"))
    fixes = diagnostics["fixes_applied"]
    
    if all_ok:
        if fixes:
            cpr(C.GREEN, f"[REFLECT] STT autotest: NAPRAWIONO ({len(fixes)} fix(ów)) ✓")
        else:
            cpr(C.GREEN, "[REFLECT] STT autotest: WSZYSTKO OK — problem w otoczeniu (cisza w pokoju)")
    else:
        failed = [k for k, v in diagnostics.items() 
                  if isinstance(v, dict) and not v.get("ok")]
        cpr(C.YELLOW, f"[REFLECT] STT autotest: nadal problemy — {', '.join(failed)}")
        if fixes:
            cpr(C.DIM, f"  Zastosowano {len(fixes)} fix(ów): {', '.join(fixes)}")
    
    # Show journal stats
    stats = journal.get_stats()
    if stats["total_attempts"] > 0:
        cpr(C.DIM, f"  [JOURNAL] Łączne próby: {stats['total_attempts']} "
                   f"(✓{stats['successes']}/✗{stats['fails']}), "
                   f"znane wzorce: {stats['known_fix_patterns']}")
    
    cpr(C.CYAN, "[REFLECT] === Koniec autotestu ===\n")
    logger.core("stt_autotest", diagnostics)
    return diagnostics


def _try_pulseaudio_fix(diagnostics: dict):
    """Last resort: try PulseAudio source adjustments.
    Prioritizes actual input sources over output monitors."""
    import subprocess, shutil
    if not shutil.which("pactl"):
        return
    try:
        r = subprocess.run(["pactl", "list", "sources", "short"],
                           capture_output=True, text=True, timeout=5)
        sources = [l.split('\t') for l in r.stdout.strip().split('\n') if l.strip()]
        
        # Separate real inputs from output monitors
        real_inputs = []
        monitors = []
        for parts in sources:
            if len(parts) >= 2:
                src_name = parts[1]
                if ".monitor" in src_name:
                    monitors.append(src_name)
                else:
                    real_inputs.append(src_name)
        
        # Process real inputs first (these are actual microphones)
        best_input = None
        for src_name in real_inputs:
            subprocess.run(["pactl", "set-source-mute", src_name, "0"],
                           capture_output=True, timeout=3)
            subprocess.run(["pactl", "set-source-volume", src_name, "100%"],
                           capture_output=True, timeout=3)
            cpr(C.DIM, f"    PulseAudio input: unmute + 100% → {src_name}")
            diagnostics.setdefault("fixes_applied", []).append(f"pactl unmute {src_name}")
            # Prefer USB audio inputs (typically external mics/headsets)
            if "usb" in src_name.lower() and best_input is None:
                best_input = src_name
        
        # Set the best input as default source
        if best_input:
            subprocess.run(["pactl", "set-default-source", best_input],
                           capture_output=True, timeout=3)
            cpr(C.CYAN, f"    PulseAudio: domyślne źródło → {best_input}")
            diagnostics.setdefault("fixes_applied", []).append(f"pactl default-source {best_input}")
        elif real_inputs:
            subprocess.run(["pactl", "set-default-source", real_inputs[0]],
                           capture_output=True, timeout=3)
            cpr(C.CYAN, f"    PulseAudio: domyślne źródło → {real_inputs[0]}")
        
        # Also unmute monitors (low priority, usually not needed for mic input)
        for src_name in monitors:
            subprocess.run(["pactl", "set-source-mute", src_name, "0"],
                           capture_output=True, timeout=3)
    except Exception:
        pass


def _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=None):
    """Continuous voice conversation: record→transcribe→respond→repeat.
    Exits on: 3 consecutive silences, KeyboardInterrupt, or exit keyword spoken.
    'wyłącz tryb głosowy' also disables the persistent preference.
    After REFLECT_THRESHOLD consecutive silences, runs STT auto-diagnostic."""
    MAX_SILENCE = 3
    REFLECT_THRESHOLD = 3  # Trigger auto-reflection after this many silences
    silence_count = 0
    total_silence_count = 0
    last_reflect_time = 0
    REFLECT_COOLDOWN = 60  # Don't reflect more than once per minute
    _EXIT_KW = ("koniec", "stop", "wyjdź", "wyjedź", "quit", "exit", "zamknij", "zakończ", "zakończ program")
    _DISABLE_KW = ("wyłącz tryb", "wylacz tryb", "disable voice", "voice off")
    cpr(C.CYAN, "\n🎤 Tryb głosowy aktywny. Mów teraz! "
                "(Ctrl+C lub powiedz 'wyłącz tryb głosowy' aby zakończyć)")
    while True:
        cpr(C.CYAN, f"\n🎤 Słucham... (5s)")
        try:
            status, text = _run_stt_cycle(sm, evo, llm, intent, logger, conv, identity, memory=memory)
        except KeyboardInterrupt:
            break
        if status == "got_text":
            silence_count = 0
            tl = text.lower()
            # Check if user wants to DISABLE voice mode (persistent off)
            if any(kw in tl for kw in _DISABLE_KW):
                if memory:
                    memory.set_voice_mode(False)
                    cpr(C.CYAN, "🔇 Tryb głosowy wyłączony na stałe.")
                else:
                    cpr(C.DIM, "[VOICE] Wychodzę z trybu głosowego.")
                break
            # Check if user wants to just exit this session
            if any(w in tl for w in _EXIT_KW):
                cpr(C.DIM, "[VOICE] Wychodzę z trybu głosowego. "
                           "Tryb głosowy nadal zapamiętany — /voice off aby wyłączyć na stałe.")
                break
        elif status == "silence":
            silence_count += 1
            total_silence_count += 1
            cpr(C.YELLOW, f"[VOICE] Nie usłyszałem ({silence_count}). Mów głośniej lub Ctrl+C.")
            
            # Trigger auto-reflection after REFLECT_THRESHOLD consecutive silences
            now = time.time()
            if silence_count >= REFLECT_THRESHOLD and (now - last_reflect_time) > REFLECT_COOLDOWN:
                last_reflect_time = now
                cpr(C.YELLOW, f"[VOICE] {silence_count} ciszych z rzędu — uruchamiam autotest + autonaprawę STT...")
                diag = _run_stt_autotest(sm, logger, llm=llm)
                fixes = diag.get("fixes_applied", [])
                
                # If hardware problem found — only truly unfixable = no mic at all
                if not diag.get("microphone", {}).get("ok"):
                    cpr(C.RED, "[VOICE] Brak mikrofonu — jedyny problem którego nie mogę naprawić.")
                    _speak_tts(sm, evo, "Brak mikrofonu. Podłącz mikrofon i spróbuj ponownie.")
                    break
                
                # Check what was fixed vs what still fails
                mic_ok = diag.get("microphone", {}).get("ok", False)
                audio_ok = diag.get("audio_level", {}).get("ok", False)
                vosk_ok = diag.get("transcription", {}).get("ok", False)
                
                if fixes and (audio_ok or vosk_ok):
                    # Something was fixed! Inform and keep going
                    fix_msg = f"Naprawiłem {len(fixes)} problem(ów). Kontynuuję nasłuchiwanie."
                    cpr(C.GREEN, f"[VOICE] {fix_msg}")
                    _speak_tts(sm, evo, fix_msg)
                    silence_count = 0
                elif audio_ok and vosk_ok:
                    # All OK — environmental silence, keep listening
                    cpr(C.DIM, "[VOICE] Sprzęt OK — cisza w otoczeniu. Kontynuuję.")
                    _speak_tts(sm, evo, "Sprzęt działa poprawnie. Czekam na Twoją wypowiedź.")
                    silence_count = 0
                else:
                    # Fixes attempted but still not working — DON'T exit, keep trying
                    if not audio_ok:
                        cpr(C.YELLOW, "[VOICE] Audio nadal cichy po naprawach — "
                                      "kontynuuję nasłuchiwanie (może pomóc głośniejsze mówienie)")
                        _speak_tts(sm, evo, 
                            "Próbowałem naprawić mikrofon. Mów głośniej, a spróbuję ponownie.")
                    if not vosk_ok:
                        cpr(C.YELLOW, "[VOICE] Vosk nadal ma problemy — "
                                      "kontynuuję, spróbuję przy następnym cyklu")
                    silence_count = 0  # Reset — always continue
            
            continue
        else:
            cpr(C.RED, f"[VOICE] Błąd: {text}. Kończę tryb głosowy.")
            break
    cpr(C.DIM, "🎤 Tryb głosowy zakończony.")
