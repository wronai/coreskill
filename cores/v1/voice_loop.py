"""Voice loop module - STT/TTS voice conversation handling."""
import json as _json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from .config import C, cpr
from .utils import mprint


def _extract_stt_text(outcome: dict) -> str:
    """Extract transcribed text from STT outcome.
    
    Checks multiple possible keys where STT might store the text.
    """
    if not outcome:
        return ""

    # EvoEngine typically returns: outcome = {type, skill, result: {success, result: {...}}}
    # Some skills may return different nesting, so we normalize defensively.
    result = outcome.get("result", {})
    inner = result.get("result", {}) if isinstance(result, dict) else {}
    if not isinstance(inner, dict):
        inner = {}

    # Try various possible keys (prefer inner first)
    for obj in (inner, result, outcome):
        if not isinstance(obj, dict):
            continue
        for key in ["spoken", "text", "transcript", "recognized", "value"]:
            val = obj.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()

    # Check nested structure
    for obj in (inner, result):
        if not isinstance(obj, dict):
            continue
        output = obj.get("output")
        if isinstance(output, dict):
            for key in ["spoken", "text", "transcript"]:
                val = output.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    
    return ""


def _clean_for_tts(text: str) -> str:
    """Strip markdown formatting and emojis for clean TTS output."""
    if not text:
        return ""
    # Remove code blocks
    text = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code backticks
    text = re.sub(r'`([^`]*)`', r'\1', text)
    # Remove markdown headings
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    # Remove bold/italic markers
    text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
    # Remove markdown links [text](url)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    # Remove common emojis that espeak reads literally
    text = re.sub(r'[\U0001F300-\U0001F9FF\u2600-\u27BF\u2300-\u23FF'
                  r'\u2B50\u2705\u274C\u26A0\u2728\u2757\u2753'
                  r'\u25B6\u25C0\u27A1\u2B05\u2B06\u2B07'
                  r'\u2139\u2049\u203C\u2934\u2935]', '', text)
    # Remove arrow → and bullet markers
    text = re.sub(r'[→←↑↓⇒⇐•●○■□▸▹]', ' ', text)
    # Remove stray markdown list markers at line start
    text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
    # Clean up whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r'  +', ' ', text)
    return text.strip()


def _speak_tts(sm, evo, text: str) -> None:
    """Speak text using TTS skill (with markdown cleanup)."""
    clean = _clean_for_tts(text)
    if not clean:
        return

    def _chunks(s: str, max_chars: int = 260, max_parts: int = 6):
        if len(s) <= max_chars:
            return [s]
        parts = re.split(r'(?<=[.!?])\s+', s)
        out = []
        buf = ""
        for p in parts:
            if not p:
                continue
            cand = (buf + " " + p).strip() if buf else p.strip()
            if len(cand) <= max_chars:
                buf = cand
                continue
            if buf:
                out.append(buf)
                buf = ""
                if len(out) >= max_parts:
                    break
            if len(p) > max_chars:
                out.append(p[:max_chars].strip())
            else:
                buf = p.strip()
            if len(out) >= max_parts:
                break
        if buf and len(out) < max_parts:
            out.append(buf)
        return out

    sk = sm.list_skills()
    for part in _chunks(clean):
        evo.handle_request(
            part, sk,
            analysis={"action": "use", "skill": "tts",
                      "provider": "piper",  # Force Piper TTS
                      "input": {"text": part, "lang": "pl"},
                      "goal": "voice_response"}
        )


def _run_stt_cycle(sm, evo, llm, intent, logger, conv, identity, duration=5, memory=None):
    """Single STT→Intent→Skill/LLM→TTS cycle.
    
    Routes transcribed text through IntentEngine so voice commands like
    'jaka jest pogoda' actually use the weather skill instead of just chatting.
    Returns ('got_text', text) or ('silence', '') or ('error', msg).
    """
    from .core import _handle_chat
    
    sk = sm.list_skills()
    # Step 1: Record audio via STT
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
    
    # Step 2: Analyze intent — should we use a skill or just chat?
    analysis = intent.analyze(stt_text, sk, conv)
    action = (analysis.get("action") or "chat") if analysis else "chat"
    skill_name = (analysis.get("skill") or "") if analysis else ""
    
    # Step 3: Execute skill if intent says so (skip stt/tts — voice loop handles those)
    if action in ("use", "create", "evolve") and skill_name and skill_name not in ("stt", "tts"):
        cpr(C.CYAN, f"[VOICE] Intent: {action} → {skill_name}")
        skill_outcome = evo.handle_request(stt_text, sk, analysis=analysis)
        
        if skill_outcome:
            otype = skill_outcome.get("type", "")
            if otype == "success":
                r = skill_outcome.get("result", {})
                res_data = r.get("result", {}) if isinstance(r, dict) else r
                summary = (_json.dumps(res_data, ensure_ascii=False, default=str)[:600]
                           if isinstance(res_data, dict) else str(res_data)[:600])
                conv.append({"role": "system", "content":
                    f"Skill '{skill_name}' wykonany pomyślnie. Wynik: {summary}\n"
                    f"Podsumuj wynik krótko po polsku (mówisz głosem, bądź zwięzły)."})
                intent.record_skill_use(skill_name)
            elif otype in ("failed", "evo_failed"):
                msg = skill_outcome.get("message", skill_outcome.get("goal", "?"))
                conv.append({"role": "system", "content":
                    f"Skill '{skill_name}' nie powiódł się: {str(msg)[:200]}\n"
                    f"Poinformuj użytkownika po polsku i zaproponuj alternatywę."})
    
    # Step 4: Generate natural language response (always — for spoken output)
    response = _handle_chat(llm, sm, logger, conv, identity=identity, memory=memory)
    if response:
        _speak_tts(sm, evo, response)
    intent.record_skill_use("stt")
    return "got_text", stt_text


def _run_stt_autotest(sm, logger, llm=None) -> dict:
    """Run STT hardware/audio auto-test with auto-repair at each stage.
    
    Delegates to STTAutoTestPipeline (Chain of Responsibility pattern).
    Returns diagnostic dict with fix results.
    """
    from .stt_autotest import run_stt_autotest
    return run_stt_autotest(sm, logger, llm)


def _try_pulseaudio_fix(diagnostics: dict):
    """Last resort: try PulseAudio source adjustments."""
    from .stt_autotest import try_pulseaudio_fix
    try_pulseaudio_fix(diagnostics)


def _generate_speech_file(text: str, lang: str = "pl") -> str:
    """Generate a WAV file from text using espeak-ng/espeak.
    Returns path to generated WAV or empty string on failure."""
    import shutil
    tts_bin = shutil.which("espeak-ng") or shutil.which("espeak")
    if not tts_bin:
        return ""
    fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="evo_speech_file_")
    os.close(fd)
    try:
        cmd = [tts_bin, "-v", lang, "-w", wav_path, text]
        r = subprocess.run(cmd, capture_output=True, timeout=15)
        if r.returncode == 0 and Path(wav_path).stat().st_size > 100:
            return wav_path
    except Exception:
        pass
    try:
        Path(wav_path).unlink(missing_ok=True)
    except Exception:
        pass
    return ""


def _run_stt_from_file(sm, evo, wav_path: str, lang: str = "pl") -> dict:
    """Run STT on a WAV file instead of live microphone.
    Returns the same outcome dict as evo.handle_request for STT."""
    sk = sm.list_skills()
    return evo.handle_request(
        "[file_input]", sk,
        analysis={"action": "use", "skill": "stt",
                  "input": {"audio_path": wav_path, "lang": lang},
                  "goal": "file_transcription"}
    )


def _run_file_input_loop(sm, evo, llm, intent, logger, conv, identity, memory=None):
    """File-based speech input: type text → TTS generates WAV → STT transcribes it.
    Used as fallback when microphone is broken. Tests the full TTS→STT pipeline."""
    from .core import _handle_chat

    cpr(C.CYAN, "\n📁 Tryb głosowy z pliku (fallback bez mikrofonu)")
    cpr(C.CYAN, "  Wpisz tekst → TTS wygeneruje mowę → STT ją rozpozna")
    cpr(C.CYAN, "  Komenda 'quit' lub Ctrl+C aby wyjść\n")

    while True:
        try:
            text_in = input(f"{C.CYAN}speech> {C.R}").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not text_in or text_in.lower() in ("quit", "exit", "koniec"):
            break

        # Step 1: Generate speech WAV from text
        cpr(C.DIM, f"  [TTS] Generuję mowę: \"{text_in[:60]}\"...")
        wav_path = _generate_speech_file(text_in)
        if not wav_path:
            cpr(C.RED, "  [TTS] Nie udało się wygenerować pliku WAV (brak espeak-ng?)")
            continue

        try:
            # Step 2: Feed WAV to STT
            cpr(C.DIM, f"  [STT] Transkrybuję plik: {Path(wav_path).name}")
            outcome = _run_stt_from_file(sm, evo, wav_path)

            if outcome and outcome.get("type") == "success":
                stt_text = _extract_stt_text(outcome)
                if stt_text:
                    cpr(C.GREEN, f"  [STT] Rozpoznano: \"{stt_text}\"")
                    mprint(f"### 🎤 *{stt_text}*")
                    conv.append({"role": "user", "content": f"[głosowo/plik] {stt_text}"})
                    # Route through intent engine (same as _run_stt_cycle)
                    sk = sm.list_skills()
                    analysis = intent.analyze(stt_text, sk, conv)
                    act = (analysis.get("action") or "chat") if analysis else "chat"
                    sk_name = (analysis.get("skill") or "") if analysis else ""
                    if act in ("use", "create", "evolve") and sk_name and sk_name not in ("stt", "tts"):
                        cpr(C.CYAN, f"  [FILE] Intent: {act} → {sk_name}")
                        sk_out = evo.handle_request(stt_text, sk, analysis=analysis)
                        if sk_out:
                            ot = sk_out.get("type", "")
                            if ot == "success":
                                r = sk_out.get("result", {})
                                rd = r.get("result", {}) if isinstance(r, dict) else r
                                s = (_json.dumps(rd, ensure_ascii=False, default=str)[:600]
                                     if isinstance(rd, dict) else str(rd)[:600])
                                conv.append({"role": "system", "content":
                                    f"Skill '{sk_name}' wykonany pomyślnie. Wynik: {s}\n"
                                    f"Podsumuj wynik krótko po polsku."})
                                intent.record_skill_use(sk_name)
                            elif ot in ("failed", "evo_failed"):
                                conv.append({"role": "system", "content":
                                    f"Skill '{sk_name}' nie powiódł się."})
                    response = _handle_chat(
                        llm, sm, logger, conv, identity=identity, memory=memory)
                    if response:
                        _speak_tts(sm, evo, response)
                    intent.record_skill_use("stt")
                else:
                    cpr(C.YELLOW, "  [STT] Cisza — STT nie rozpoznało tekstu z pliku")
            else:
                err = outcome.get("goal", "stt failed") if outcome else "stt failed"
                cpr(C.RED, f"  [STT] Błąd: {err}")
        finally:
            try:
                Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass

    cpr(C.DIM, "📁 Tryb plikowy zakończony.")


def _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=None):
    """Continuous voice conversation: record→transcribe→respond→repeat.
    Exits on: MAX_TOTAL_SILENCE consecutive silences, KeyboardInterrupt, or exit keyword.
    'wyłącz tryb głosowy' also disables the persistent preference.
    After REFLECT_THRESHOLD consecutive silences, runs STT auto-diagnostic (max 2 times)."""
    REFLECT_THRESHOLD = 3  # Trigger auto-reflection after this many silences
    MAX_AUTOTEST_RUNS = 2  # Max autotest cycles before giving up
    MAX_TOTAL_SILENCE = 10  # Hard limit — exit voice loop after this many total silences
    silence_count = 0
    total_silence_count = 0
    autotest_runs = 0
    last_reflect_time = 0
    REFLECT_COOLDOWN = 120  # Don't reflect more than once per 2 minutes
    _EXIT_KW = ("koniec", "stop", "wyjdź", "wyjedź", "quit", "exit", "zamknij", "zakończ", "zakończ program")
    _DISABLE_KW = ("wyłącz tryb", "wylacz tryb", "disable voice", "voice off")
    cpr(C.CYAN, "\n🎤 Tryb głosowy aktywny. Mów teraz! "
                "(Ctrl+C: tryb tekstowy | Ctrl+\\: wyjście | 'wyłącz tryb głosowy': zakończ)")
    while True:
        cpr(C.CYAN, f"\n🎤 Słucham... (5s)")
        try:
            status, text = _run_stt_cycle(sm, evo, llm, intent, logger, conv, identity, memory=memory)
        except KeyboardInterrupt:
            break
        except EOFError:
            # Terminal sent EOF (Ctrl+D or similar) - exit gracefully
            cpr(C.DIM, "[VOICE] Przerwano wejście (EOF). Wychodzę.")
            break
        except RuntimeError as e:
            # STT skill errors (interrupted recording, etc.)
            err_msg = str(e).lower()
            if "interrupted" in err_msg or "przerwano" in err_msg:
                cpr(C.DIM, f"[VOICE] Nagrywanie przerwane. Wznawiam...")
                continue
            cpr(C.RED, f"[VOICE] Błąd STT: {e}. Kończę.")
            break
        except Exception as e:
            # Catch-all for unexpected errors during STT
            cpr(C.RED, f"[VOICE] Nieoczekiwany błąd: {e}. Kończę.")
            break
        if status == "got_text":
            silence_count = 0
            total_silence_count = 0
            autotest_runs = 0  # Reset on successful speech
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
            cpr(C.YELLOW, f"[VOICE] Nie usłyszałem ({total_silence_count}/{MAX_TOTAL_SILENCE}). "
                          f"Mów głośniej lub Ctrl+C.")
            
            # Hard exit after too many total silences
            if total_silence_count >= MAX_TOTAL_SILENCE:
                cpr(C.RED, f"[VOICE] {MAX_TOTAL_SILENCE} ciszych z rzędu — "
                           "wychodzę z trybu głosowego. Sprawdź mikrofon.")
                _speak_tts(sm, evo, 
                    "Nie słyszę nic od dłuższego czasu. Wychodzę z trybu głosowego. "
                    "Sprawdź mikrofon i użyj /voice aby spróbować ponownie.")
                break
            
            # Trigger auto-reflection after REFLECT_THRESHOLD silences (limited runs)
            now = time.time()
            if (silence_count >= REFLECT_THRESHOLD 
                    and autotest_runs < MAX_AUTOTEST_RUNS
                    and (now - last_reflect_time) > REFLECT_COOLDOWN):
                autotest_runs += 1
                last_reflect_time = now
                cpr(C.YELLOW, f"[VOICE] {silence_count} ciszych z rzędu — "
                              f"uruchamiam autotest ({autotest_runs}/{MAX_AUTOTEST_RUNS})...")
                diag = _run_stt_autotest(sm, logger, llm=llm)
                fixes = diag.get("fixes_applied", [])
                
                # If hardware problem found — only truly unfixable = no mic at all
                if not diag.get("microphone", {}).get("ok"):
                    cpr(C.RED, "[VOICE] Brak mikrofonu — jedyny problem którego nie mogę naprawić.")
                    _speak_tts(sm, evo, "Brak mikrofonu. Podłącz mikrofon i spróbuj ponownie.")
                    break
                
                # Check what was fixed vs what still fails
                audio_ok = diag.get("audio_level", {}).get("ok", False)
                vosk_ok = diag.get("transcription", {}).get("ok", False)
                
                if fixes and (audio_ok or vosk_ok):
                    fix_msg = f"Naprawiłem {len(fixes)} problem(ów). Kontynuuję nasłuchiwanie."
                    cpr(C.GREEN, f"[VOICE] {fix_msg}")
                    _speak_tts(sm, evo, fix_msg)
                    silence_count = 0
                elif audio_ok and vosk_ok:
                    cpr(C.DIM, "[VOICE] Sprzęt OK — cisza w otoczeniu. Kontynuuję.")
                    _speak_tts(sm, evo, "Sprzęt działa poprawnie. Czekam na Twoją wypowiedź.")
                    silence_count = 0
                else:
                    if not audio_ok:
                        cpr(C.YELLOW, "[VOICE] Audio nadal cichy po naprawach.")
                    if not vosk_ok:
                        cpr(C.YELLOW, "[VOICE] Vosk nadal ma problemy.")
                    if autotest_runs >= MAX_AUTOTEST_RUNS:
                        cpr(C.YELLOW, "[VOICE] Wyczerpano próby autonaprawy. "
                                      "Dalej nasłuchuję, ale bez kolejnych autotestów.")
                    silence_count = 0
            
            continue
        else:
            cpr(C.RED, f"[VOICE] Błąd: {text}. Kończę tryb głosowy.")
            break
    cpr(C.DIM, "🎤 Tryb głosowy zakończony.")
