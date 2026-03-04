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


def _run_stt_autotest(sm, logger) -> dict:
    """Run STT hardware/audio auto-test with auto-repair at each stage.
    
    Flow per stage: DETECT → AUTO-FIX → RE-TEST → VERIFY
    Never just reports — always tries to fix first.
    Returns diagnostic dict with fix results.
    """
    import shutil, subprocess, tempfile, os
    from pathlib import Path
    
    cpr(C.CYAN, "\n[REFLECT] === Autotest STT (detect → fix → verify) ===")
    
    diagnostics = {
        "microphone": {"ok": False},
        "audio_level": {"ok": False},
        "transcription": {"ok": False},
        "fixes_applied": [],
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

    # ── Helper: test vosk transcription ─────────────────────────────
    def _test_vosk(wav_path):
        if not shutil.which("vosk-transcriber"):
            return False, "vosk-transcriber not found"
        fd2, out_path = tempfile.mkstemp(suffix=".txt", prefix="stt_autotest_out_")
        os.close(fd2)
        try:
            tr = subprocess.run(
                ["vosk-transcriber", "--input", wav_path,
                 "--output", out_path, "--output-type", "txt"],
                capture_output=True, text=True, timeout=30)
            return tr.returncode == 0, (tr.stderr or "")[:200]
        except Exception as e:
            return False, str(e)
        finally:
            try: Path(out_path).unlink(missing_ok=True)
            except: pass

    # ═══════════════════════════════════════════════════════════════
    # STAGE 1: MICROPHONE HARDWARE
    # ═══════════════════════════════════════════════════════════════
    cpr(C.DIM, "  [1/3] Sprawdzam mikrofon...")
    if not shutil.which("arecord"):
        cpr(C.YELLOW, "  ✗ arecord brak — próbuję zainstalować alsa-utils...")
        try:
            subprocess.run(["sudo", "apt-get", "install", "-y", "alsa-utils"],
                           capture_output=True, timeout=30)
            if shutil.which("arecord"):
                cpr(C.GREEN, "  ✓ alsa-utils zainstalowane!")
                diagnostics["fixes_applied"].append("installed alsa-utils")
            else:
                cpr(C.RED, "  ✗ Nie udało się zainstalować alsa-utils")
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
        # Can't proceed without mic
        cpr(C.RED, "[REFLECT] Brak mikrofonu — nie mogę naprawić sprzętowego problemu")
        logger.core("stt_autotest", diagnostics)
        return diagnostics

    # ═══════════════════════════════════════════════════════════════
    # STAGE 2: AUDIO LEVEL — detect silence → try amixer fixes → re-test
    # ═══════════════════════════════════════════════════════════════
    cpr(C.DIM, "  [2/3] Testuję poziom audio...")
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
                cpr(C.CYAN, "  [AUTOFIX] Próbuję naprawić ustawienia audio...")
                
                # ── AUTO-FIX: Try multiple amixer strategies ────────
                amixer_fixes = [
                    # Generic capture unmute + max volume
                    (["amixer", "set", "Capture", "unmute"], "Capture unmute"),
                    (["amixer", "set", "Capture", "100%"], "Capture 100%"),
                    # Try specific card 0
                    (["amixer", "-c", "0", "set", "Capture", "unmute"], "Card0 Capture unmute"),
                    (["amixer", "-c", "0", "set", "Capture", "100%"], "Card0 Capture 100%"),
                    # Try Mic control (some cards use 'Mic' instead of 'Capture')
                    (["amixer", "set", "Mic", "unmute"], "Mic unmute"),
                    (["amixer", "set", "Mic", "100%"], "Mic 100%"),
                    # Try 'Input Source' and other common names
                    (["amixer", "set", "Capture", "cap"], "Capture cap"),
                    (["amixer", "-c", "0", "set", "Capture", "cap"], "Card0 Capture cap"),
                    # Try card 1 (USB mics often on card 1)
                    (["amixer", "-c", "1", "set", "Capture", "unmute"], "Card1 Capture unmute"),
                    (["amixer", "-c", "1", "set", "Capture", "100%"], "Card1 Capture 100%"),
                ]
                
                fixes_tried = []
                for cmd, desc in amixer_fixes:
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
                    
                    # ── RE-TEST after fixes ─────────────────────────
                    time.sleep(0.5)
                    fd2, test_wav2 = tempfile.mkstemp(suffix=".wav", prefix="stt_retest_")
                    os.close(fd2)
                    try:
                        if _record_test(test_wav2):
                            has_sound2, db_level2 = _measure_db(test_wav2)
                            if has_sound2:
                                cpr(C.GREEN, f"  ✓ NAPRAWIONE! Audio level: {db_level2:.1f}dB (było {db_level:.1f}dB)")
                                diagnostics["audio_level"] = {"ok": True, "db": db_level2,
                                                              "fixed_from": db_level}
                            else:
                                cpr(C.YELLOW, f"  ✗ Nadal cisza ({db_level2:.1f}dB) po amixer fix")
                                diagnostics["audio_level"] = {"ok": False, "db": db_level2,
                                                              "attempted_fixes": fixes_tried}
                                # ── Try pulseaudio as last resort ───
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
                    cpr(C.YELLOW, "  ✗ Żaden amixer fix nie zadziałał")
                    diagnostics["audio_level"] = {"ok": False, "db": db_level,
                                                  "error": "no amixer fixes worked"}
    finally:
        try: Path(test_wav).unlink(missing_ok=True)
        except: pass

    # ═══════════════════════════════════════════════════════════════
    # STAGE 3: VOSK TRANSCRIPTION — test → fix model → re-test
    # ═══════════════════════════════════════════════════════════════
    cpr(C.DIM, "  [3/3] Testuję transkrypcję vosk...")
    
    if not shutil.which("vosk-transcriber"):
        cpr(C.YELLOW, "  ✗ vosk-transcriber brak — próbuję zainstalować...")
        try:
            subprocess.run([sys.executable, "-m", "pip", "install", "vosk"],
                           capture_output=True, timeout=60)
            if shutil.which("vosk-transcriber"):
                cpr(C.GREEN, "  ✓ vosk zainstalowany!")
                diagnostics["fixes_applied"].append("pip install vosk")
        except Exception:
            pass
    
    if shutil.which("vosk-transcriber"):
        # Record fresh audio for transcription test
        fd3, test_wav3 = tempfile.mkstemp(suffix=".wav", prefix="stt_vosk_test_")
        os.close(fd3)
        try:
            if _record_test(test_wav3, duration=2):
                vosk_ok, vosk_err = _test_vosk(test_wav3)
                if vosk_ok:
                    cpr(C.GREEN, "  ✓ vosk-transcriber: działa")
                    diagnostics["transcription"] = {"ok": True}
                else:
                    cpr(C.YELLOW, f"  ✗ vosk-transcriber błąd: {vosk_err[:80]}")
                    
                    # ── AUTO-FIX: check/download vosk model ─────────
                    cpr(C.CYAN, "  [AUTOFIX] Sprawdzam model vosk...")
                    model_paths = [
                        Path.home() / ".cache" / "vosk",
                        Path.home() / ".local" / "share" / "vosk",
                    ]
                    model_found = False
                    for mp in model_paths:
                        if mp.exists():
                            models = [d for d in mp.iterdir() if d.is_dir() 
                                      and "model" in d.name.lower()]
                            if models:
                                cpr(C.DIM, f"    Model znaleziony: {models[0].name}")
                                model_found = True
                                break
                    
                    if not model_found:
                        cpr(C.CYAN, "  [AUTOFIX] Pobieram model vosk-model-small-pl-0.22...")
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
                                cpr(C.GREEN, "  ✓ Model pobrany!")
                                diagnostics["fixes_applied"].append("downloaded vosk-model-small-pl-0.22")
                            else:
                                cpr(C.YELLOW, f"  ✗ Pobieranie modelu: exit {r.returncode}")
                        except Exception as e:
                            cpr(C.YELLOW, f"  ✗ Pobieranie modelu: {e}")
                    
                    # ── RE-TEST vosk after fix ──────────────────────
                    cpr(C.DIM, "  [AUTOFIX] Ponowny test vosk...")
                    vosk_ok2, vosk_err2 = _test_vosk(test_wav3)
                    if vosk_ok2:
                        cpr(C.GREEN, "  ✓ NAPRAWIONE! vosk-transcriber działa")
                        diagnostics["transcription"] = {"ok": True, "fixed": True}
                    else:
                        cpr(C.YELLOW, f"  ✗ vosk nadal nie działa: {vosk_err2[:80]}")
                        diagnostics["transcription"] = {"ok": False, "error": vosk_err2[:200]}
        finally:
            try: Path(test_wav3).unlink(missing_ok=True)
            except: pass
    else:
        diagnostics["transcription"] = {"ok": False, "error": "vosk-transcriber unavailable"}

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
    
    cpr(C.CYAN, "[REFLECT] === Koniec autotestu ===\n")
    logger.core("stt_autotest", diagnostics)
    return diagnostics


def _try_pulseaudio_fix(diagnostics: dict):
    """Last resort: try PulseAudio source adjustments."""
    import subprocess, shutil
    if not shutil.which("pactl"):
        return
    try:
        # List sources
        r = subprocess.run(["pactl", "list", "sources", "short"],
                           capture_output=True, text=True, timeout=5)
        sources = [l.split('\t') for l in r.stdout.strip().split('\n') if l.strip()]
        for parts in sources:
            if len(parts) >= 2:
                src_name = parts[1]
                # Unmute and set volume to 100%
                subprocess.run(["pactl", "set-source-mute", src_name, "0"],
                               capture_output=True, timeout=3)
                subprocess.run(["pactl", "set-source-volume", src_name, "100%"],
                               capture_output=True, timeout=3)
                cpr(C.DIM, f"    PulseAudio: unmute + 100% → {src_name}")
                diagnostics.setdefault("fixes_applied", []).append(f"pactl unmute {src_name}")
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
                diag = _run_stt_autotest(sm, logger)
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
