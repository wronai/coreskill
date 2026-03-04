"""Voice loop module - STT/TTS voice conversation handling."""
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
    """Run quick STT hardware and audio auto-test. Returns diagnostic dict."""
    from .self_reflection import SelfReflection
    
    cpr(C.CYAN, "\n[REFLECT] === Autotest STT po 3 ciszach ===")
    
    diagnostics = {
        "microphone": {"ok": False},
        "audio_level": {"ok": False},
        "transcription": {"ok": False},
    }
    
    # 1. Check microphone hardware
    import shutil, subprocess
    if not shutil.which("arecord"):
        cpr(C.RED, "  ✗ arecord: nie zainstalowany")
        diagnostics["microphone"] = {"ok": False, "error": "arecord missing"}
    else:
        try:
            r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=5)
            lines = r.stdout.strip().split('\n')
            devices = [l for l in lines if l.strip().startswith('card') and 'device' in l]
            if devices:
                cpr(C.GREEN, f"  ✓ Mikrofon: {len(devices)} urządzenie(a)")
                diagnostics["microphone"] = {"ok": True, "devices": len(devices)}
            else:
                cpr(C.RED, "  ✗ Mikrofon: brak urządzeń capture")
                diagnostics["microphone"] = {"ok": False, "error": "no capture devices"}
        except Exception as e:
            cpr(C.RED, f"  ✗ Mikrofon: {e}")
            diagnostics["microphone"] = {"ok": False, "error": str(e)}
    
    # 2. Quick 2s recording + audio level test
    if diagnostics["microphone"]["ok"]:
        import tempfile, os
        fd, test_wav = tempfile.mkstemp(suffix=".wav", prefix="stt_autotest_")
        os.close(fd)
        try:
            cpr(C.DIM, "  Nagrywam 2s testu...")
            r = subprocess.run(
                ["arecord", "-q", "-d", "2", "-f", "S16_LE", "-r", "16000", "-c", "1", test_wav],
                capture_output=True, timeout=10
            )
            if r.returncode != 0:
                cpr(C.RED, f"  ✗ Nagrywanie: błąd (exit {r.returncode})")
                diagnostics["audio_level"] = {"ok": False, "error": f"arecord exit {r.returncode}"}
            else:
                from pathlib import Path
                fsize = Path(test_wav).stat().st_size
                
                # Check audio level with sox or ffmpeg
                db_level = -999.0
                has_sound = False
                
                if shutil.which("sox"):
                    try:
                        sr = subprocess.run(
                            ["sox", test_wav, "-n", "stat"],
                            capture_output=True, text=True, timeout=10
                        )
                        for line in sr.stderr.split('\n'):
                            if 'RMS amplitude' in line:
                                parts = line.split(':')
                                if len(parts) >= 2:
                                    amplitude = float(parts[1].strip())
                                    if amplitude > 0:
                                        db_level = 20 * (amplitude ** 0.5) - 60
                                        has_sound = db_level > -40.0
                    except Exception:
                        pass
                
                if has_sound:
                    cpr(C.GREEN, f"  ✓ Audio level: {db_level:.1f}dB (OK)")
                    diagnostics["audio_level"] = {"ok": True, "db": db_level}
                else:
                    cpr(C.YELLOW, f"  ✗ Audio level: {db_level:.1f}dB (cisza, file={fsize}b)")
                    diagnostics["audio_level"] = {"ok": False, "db": db_level, "file_size": fsize}
                    
                # 3. Quick transcription test
                if shutil.which("vosk-transcriber"):
                    fd2, out_path = tempfile.mkstemp(suffix=".txt", prefix="stt_autotest_out_")
                    os.close(fd2)
                    try:
                        tr = subprocess.run(
                            ["vosk-transcriber", "--input", test_wav, "--output", out_path, "--output-type", "txt"],
                            capture_output=True, text=True, timeout=15
                        )
                        if tr.returncode == 0:
                            cpr(C.GREEN, "  ✓ vosk-transcriber: działa")
                            diagnostics["transcription"] = {"ok": True}
                        else:
                            cpr(C.RED, f"  ✗ vosk-transcriber: exit {tr.returncode}")
                            diagnostics["transcription"] = {"ok": False, "error": tr.stderr[:100]}
                    except Exception as e:
                        cpr(C.RED, f"  ✗ vosk-transcriber: {e}")
                        diagnostics["transcription"] = {"ok": False, "error": str(e)}
                    finally:
                        try: Path(out_path).unlink(missing_ok=True)
                        except: pass
        except Exception as e:
            cpr(C.RED, f"  ✗ Test nagrywania: {e}")
            diagnostics["audio_level"] = {"ok": False, "error": str(e)}
        finally:
            try:
                from pathlib import Path
                Path(test_wav).unlink(missing_ok=True)
            except: pass
    
    # Summary
    all_ok = all(d.get("ok") for d in diagnostics.values())
    if all_ok:
        cpr(C.GREEN, "[REFLECT] STT autotest: WSZYSTKO OK — problem może być w otoczeniu (cisza w pokoju)")
    else:
        failed = [k for k, v in diagnostics.items() if not v.get("ok")]
        cpr(C.YELLOW, f"[REFLECT] STT autotest: PROBLEM — {', '.join(failed)}")
        
        # Recommendations
        if not diagnostics["microphone"]["ok"]:
            cpr(C.YELLOW, "  → Sprawdź podłączenie mikrofonu: arecord -l")
            cpr(C.YELLOW, "  → Sprawdź uprawnienia: groups | grep audio")
        elif not diagnostics["audio_level"]["ok"]:
            cpr(C.YELLOW, "  → Mikrofon działa, ale nagrywa ciszę")
            cpr(C.YELLOW, "  → Sprawdź: alsamixer (zwiększ capture)")
            cpr(C.YELLOW, "  → Sprawdź czy mikrofon nie jest wyciszony (mute)")
        elif not diagnostics["transcription"]["ok"]:
            cpr(C.YELLOW, "  → vosk-transcriber nie działa")
            cpr(C.YELLOW, "  → Sprawdź model: ls ~/.cache/vosk/")
    
    cpr(C.CYAN, "[REFLECT] === Koniec autotestu ===\n")
    
    logger.core("stt_autotest", diagnostics)
    return diagnostics


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
                cpr(C.YELLOW, f"[VOICE] {silence_count} ciszych z rzędu — uruchamiam autotest STT...")
                diag = _run_stt_autotest(sm, logger)
                
                # If hardware problem found, exit voice mode gracefully
                if not diag.get("microphone", {}).get("ok"):
                    cpr(C.RED, "[VOICE] Mikrofon niedostępny — kończę tryb głosowy.")
                    _speak_tts(sm, evo, "Mikrofon nie działa. Sprawdź podłączenie.")
                    break
                
                # If audio level issue, inform and continue (user might fix it)
                if not diag.get("audio_level", {}).get("ok"):
                    _speak_tts(sm, evo, "Mikrofon nagrywa ciszę. Sprawdź ustawienia alsamixer.")
                    # Reset counter — give user time to fix
                    silence_count = 0
                
                # If all ok, it's just environmental silence — keep listening
                if all(d.get("ok") for d in diag.values()):
                    cpr(C.DIM, "[VOICE] Sprzęt OK — kontynuuję nasłuchiwanie.")
                    silence_count = 0
            
            continue
        else:
            cpr(C.RED, f"[VOICE] Błąd: {text}. Kończę tryb głosowy.")
            break
    cpr(C.DIM, "🎤 Tryb głosowy zakończony.")
