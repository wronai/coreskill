"""Voice loop module - STT/TTS voice conversation handling."""
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


def _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=None):
    """Continuous voice conversation: record→transcribe→respond→repeat.
    Exits on: 3 consecutive silences, KeyboardInterrupt, or exit keyword spoken.
    'wyłącz tryb głosowy' also disables the persistent preference."""
    MAX_SILENCE = 3
    silence_count = 0
    _EXIT_KW = ("koniec", "stop", "wyjdź", "wyjedź", "quit", "exit", "zamknij")
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
            cpr(C.YELLOW, f"[VOICE] Nie usłyszałem ({silence_count}). Mów głośniej lub Ctrl+C.")
            # Don't exit on silence - just continue listening
            # Only exit if explicitly requested by user
            continue
        else:
            cpr(C.RED, f"[VOICE] Błąd: {text}. Kończę tryb głosowy.")
            break
    cpr(C.DIM, "🎤 Tryb głosowy zakończony.")
