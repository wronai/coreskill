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
    
    Delegates to STTAutoTestPipeline (Chain of Responsibility pattern).
    Returns diagnostic dict with fix results.
    """
    from .stt_autotest import run_stt_autotest
    return run_stt_autotest(sm, logger, llm)


def _try_pulseaudio_fix(diagnostics: dict):
    """Last resort: try PulseAudio source adjustments."""
    from .stt_autotest import try_pulseaudio_fix
    try_pulseaudio_fix(diagnostics)


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
