#!/usr/bin/env python3
"""core_loop.py — Main event loop and intent handlers.

Extracted from core.py to reduce CC.
Handles: main(), _process_chat_input, _handle_*_intent, voice loop integration.
"""
import os
import sys
import json
import signal

from .config import C, cpr, save_state
from .core_dispatch import _handle_chat, _handle_outcome, _check_proactive_learning, QUICK_HELP
from .voice_loop import _extract_stt_text, _speak_tts, _run_voice_loop, _run_file_input_loop


def _handle_configure_intent(analysis, session_cfg, conv, state, llm, sm, intent):
    """Handle CONFIGURE intent (session configuration changes). Returns True if handled."""
    if analysis.get("action") != "configure":
        return False

    if analysis.get("_fallback"):
        cpr(C.YELLOW, "[FALLBACK] Niejasna konfiguracja → domyślnie LLM (brak kontekstu głosowego)")

    from .session_config import ConfigChange
    change = session_cfg.handle_configure_intent(analysis)
    feedback = session_cfg.format_change_feedback(change)
    cpr(C.CYAN, feedback)
    conv.append({"role": "assistant", "content": feedback})

    # Apply overrides to components
    if change.category == "llm" and change.setting == "model" and change.new_value:
        state["model"] = change.new_value
        save_state(state)
        llm.model = change.new_value
        cpr(C.GREEN, f"Model zmieniony na: {change.new_value}")
    elif change.category in ("tts", "stt") and change.setting == "provider":
        cpr(C.GREEN, f"{change.category.upper()} provider: {change.old_value} → {change.new_value}")
        if hasattr(sm, 'provider_preferences'):
            sm.provider_preferences[change.category] = change.new_value

    _check_proactive_learning(intent)
    intent.save()
    return True


def _handle_voice_intent(analysis, sm, evo, llm, intent, logger, conv, identity, memory):
    """Handle voice conversation intent. Returns True if handled."""
    if not (analysis.get("action") == "use" and analysis.get("skill") == "stt"
            and analysis.get("goal") in ("voice_conversation", "enable_voice", "enable_stt")):
        return False

    if memory and not memory.voice_mode:
        memory.set_voice_mode(True)
        cpr(C.CYAN, "🔊 Zapamiętano: tryb głosowy włączony na stałe. "
                    "Wyłącz: /voice off lub powiedz 'wyłącz tryb głosowy'.")
    _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=memory)
    _check_proactive_learning(intent)
    intent.save()
    return True


def _handle_stt_outcome(outcome, ui, sk, analysis, evo, intent, llm, sm, logger, conv,
                        identity, memory):
    """Handle STT skill outcome: retry on silence, feed text to chat. Returns True if handled."""
    if not (outcome and outcome.get("skill") == "stt" and outcome.get("type") == "success"):
        return False

    stt_text = _extract_stt_text(outcome)
    intent.record_skill_use("stt")

    # Auto-retry once on silence before giving up
    if not stt_text:
        cpr(C.DIM, "[STT] Cisza — ponawiam automatycznie...")
        retry_outcome = evo.handle_request(ui, sk, analysis=analysis)
        if retry_outcome and retry_outcome.get("type") == "success":
            stt_text = _extract_stt_text(retry_outcome)

    if stt_text:
        cpr(C.GREEN, f"[STT] Usłyszałem: \"{stt_text}\"")
        from .utils import mprint
        mprint(f"### 🎤 Usłyszałem: *{stt_text}*")
        conv.append({"role": "user", "content": f"[głosowo] {stt_text}"})
        response = _handle_chat(llm, sm, logger, conv, identity=identity, memory=memory)
        if response:
            _speak_tts(sm, evo, response)
    else:
        cpr(C.YELLOW, "[STT] Nie usłyszałem nic po 2 próbach. Sprawdź mikrofon.")
        from .utils import mprint
        mprint("### 🎤 Nie usłyszałem nic\nSpróbuj powiedzieć coś głośniej lub użyj `/stt` ponownie.")
        conv.append({"role": "assistant", "content": "Nie usłyszałem nic po 2 próbach. Sprawdź mikrofon."})
    return True


def _auto_save_preference(ui, memory):
    """Auto-detect and save user preference statements."""
    if not memory or not memory.looks_like_preference(ui):
        return
    suggestion = memory.suggest_save(ui)
    if not suggestion:
        return
    ul = ui.lower()
    if any(kw in ul for kw in ("głosowo", "glosowo", "voice", "głos")):
        if not memory.voice_mode:
            memory.set_voice_mode(True)
            cpr(C.CYAN, "🔊 Zapamiętano: tryb głosowy włączony na stałe. "
                        "Wyłącz: /voice off")
    else:
        memory.add(suggestion)
        cpr(C.CYAN, f"📋 Zapamiętano: {suggestion[:80]}")


def _flush_stdin():
    """Flush any pending input from stdin to prevent terminal prompt from being read as user input."""
    import sys
    import select
    
    try:
        if hasattr(select, 'select'):
            import time
            time.sleep(0.1)
            while select.select([sys.stdin], [], [], 0)[0]:
                char = sys.stdin.read(1)
                if not char:
                    break
    except Exception:
        pass


def _read_line_with_shortcuts(prompt: str) -> str:
    """Read a line from stdin with Ctrl+A / Ctrl+T shortcuts (TTY only)."""
    import sys
    if not sys.stdin.isatty():
        print(prompt, end='', flush=True)
        return sys.stdin.readline().rstrip("\n")

    import termios
    import tty

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    buf = []
    try:
        print(prompt, end='', flush=True)
        tty.setcbreak(fd)
        while True:
            ch = sys.stdin.read(1)
            if ch == "":
                raise EOFError

            # Ctrl+A
            if ch == "\x01":
                print("\n", end='', flush=True)
                return "__SWITCH_TO_VOICE__"

            # Ctrl+T
            if ch == "\x14":
                print("\n", end='', flush=True)
                return "__SWITCH_TO_TEXT__"

            # Enter
            if ch in ("\n", "\r"):
                print("\n", end='', flush=True)
                return "".join(buf).strip()

            # Backspace
            if ch in ("\x7f", "\b"):
                if buf:
                    buf.pop()
                    print("\b \b", end='', flush=True)
                continue

            # Ctrl+D (EOF)
            if ch == "\x04":
                if not buf:
                    raise EOFError
                continue

            # Ctrl+C
            if ch == "\x03":
                raise KeyboardInterrupt

            # Regular characters
            if ch.isprintable():
                buf.append(ch)
                print(ch, end='', flush=True)
    finally:
        try:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
        except Exception:
            pass


def _setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    _shutdown_requested = False
    
    def _signal_handler(signum, frame):
        nonlocal _shutdown_requested
        if not _shutdown_requested:
            _shutdown_requested = True
            cpr(C.DIM, f"\n[SIGNAL] Received {signal.Signals(signum).name}, shutting down gracefully...")
        raise SystemExit(0)
    
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGQUIT, _signal_handler)


def _try_auto_voice_mode(memory, cmd_ctx) -> bool:
    """Auto-enter voice mode if persistent preference is saved."""
    if not memory or not memory.voice_mode or os.environ.get("EVO_TEXT_ONLY"):
        return False
    
    sm = cmd_ctx["sm"]
    evo = cmd_ctx["evo"]
    llm = cmd_ctx["llm"]
    intent = cmd_ctx["intent"]
    logger = cmd_ctx["logger"]
    conv = cmd_ctx["conv"]
    identity = cmd_ctx["identity"]
    
    cpr(C.CYAN, "🔊 Tryb głosowy aktywny (zapamiętana preferencja). Wyłącz: /voice off")
    try:
        _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=memory)
    except KeyboardInterrupt:
        cpr(C.DIM, "\n[VOICE] Ctrl+C — przechodzę do trybu tekstowego (aplikacja działa dalej).")
    _flush_stdin()
    cpr(C.CYAN, "📝 Przechodzę do trybu tekstowego. Wpisz /voice aby wrócić do głosowego.")
    return True


def _dispatch_command(ui: str, cmd_ctx: dict) -> bool:
    """Dispatch slash command via fuzzy router. Returns True if QUIT command was issued."""
    p = ui.split(maxsplit=2)
    act = p[0].lower()
    a1 = p[1] if len(p) > 1 else ""
    a2 = p[2] if len(p) > 2 else ""
    
    handler, _ = cmd_ctx["router"].resolve(act)
    if handler:
        return handler(a1=a1, a2=a2, **cmd_ctx) == "QUIT"
    else:
        cpr(C.YELLOW, f"Unknown: {act}. /help")
    return False


def _process_chat_input(ui: str, cmd_ctx: dict) -> None:
    """Process chat input through IntentEngine and EvoEngine."""
    conv = cmd_ctx["conv"]
    logger = cmd_ctx["logger"]
    sm = cmd_ctx["sm"]
    intent = cmd_ctx["intent"]
    session_cfg = cmd_ctx["session_config"]
    state = cmd_ctx["state"]
    llm = cmd_ctx["llm"]
    evo = cmd_ctx["evo"]
    identity = cmd_ctx["identity"]
    memory = cmd_ctx.get("memory")
    
    conv.append({"role": "user", "content": ui})
    logger.core("user_msg", {"msg": ui[:200]})

    sk = sm.list_skills()
    analysis = intent.analyze(ui, sk, conv)
    logger.core("intent_result", {
        "action": analysis.get("action"), "skill": analysis.get("skill", ""),
        "goal": analysis.get("goal", "")})

    if _handle_configure_intent(analysis, session_cfg, conv, state, llm, sm, intent):
        return

    if _handle_voice_intent(analysis, sm, evo, llm, intent, logger, conv, identity, memory):
        return

    # Show feedback before single-shot STT execution
    if analysis.get("action") == "use" and analysis.get("skill") == "stt":
        cpr(C.CYAN, "\n🎤 Nagrywam... (mów teraz)")

    outcome = evo.handle_request(ui, sk, analysis=analysis)

    _auto_save_preference(ui, memory)

    if not _handle_stt_outcome(outcome, ui, sk, analysis, evo, intent, llm, sm,
                               logger, conv, identity, memory):
        if not _handle_outcome(outcome, intent, conv, identity=identity):
            _handle_chat(llm, sm, logger, conv, identity=identity, memory=memory)

    _check_proactive_learning(intent)
    intent.save()


def run_main_loop(cmd_ctx, conv, memory):
    """Run the main input loop."""
    # Auto-enter voice mode if persistent preference is saved
    _try_auto_voice_mode(memory, cmd_ctx)

    while True:
        try:
            ui = _read_line_with_shortcuts(f"{C.GREEN}you> {C.R}")
        except (EOFError, KeyboardInterrupt):
            cpr(C.DIM, "\nBye!")
            break

        if ui == "__SWITCH_TO_TEXT__":
            _flush_stdin()
            continue

        if ui == "__SWITCH_TO_VOICE__":
            if os.environ.get("EVO_TEXT_ONLY"):
                cpr(C.YELLOW, "Tryb tekstowy wymuszony przez EVO_TEXT_ONLY.")
                continue
            # Enter voice mode for this session
            sm = cmd_ctx["sm"]
            evo = cmd_ctx["evo"]
            llm = cmd_ctx["llm"]
            intent = cmd_ctx["intent"]
            logger = cmd_ctx["logger"]
            identity = cmd_ctx.get("identity")
            try:
                _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=memory)
            except KeyboardInterrupt:
                cpr(C.DIM, "\n[VOICE] Ctrl+C — przechodzę do trybu tekstowego (aplikacja działa dalej).")
            _flush_stdin()
            continue

        if not ui:
            continue

        # Commands via fuzzy dispatch table
        if ui.startswith("/"):
            if _dispatch_command(ui, cmd_ctx):
                break
            continue

        # Chat with context-aware IntentEngine
        _process_chat_input(ui, cmd_ctx)


def main():
    """Main entry point — thin wrapper that delegates to modular components."""
    _setup_signal_handlers()
    
    from .core_boot import boot
    cmd_ctx, conv, memory = boot()
    cmd_ctx["conv"] = conv
    if memory:
        cmd_ctx["memory"] = memory

    run_main_loop(cmd_ctx, conv, memory)
