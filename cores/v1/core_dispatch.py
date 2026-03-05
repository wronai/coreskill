#!/usr/bin/env python3
"""core_dispatch.py — Command handlers and chat processing.

Extracted from core.py to reduce CC.
Handles: COMMANDS dict, _cmd_*, _handle_chat, _handle_outcome, _handle_*_intent.
"""
import os
import json
from datetime import datetime

from .config import C, cpr, save_state, TIER_FREE, TIER_LOCAL, TIER_PAID
from .utils import mprint
from .llm_client import discover_models, _detect_ollama_models
from .voice_loop import _extract_stt_text, _speak_tts, _run_voice_loop


# ─── Help ────────────────────────────────────────────────────────────
HELP = """
  Skróty klawiaturowe:
  Ctrl+A            Tryb audio (voice)
  Ctrl+T            Tryb tekstowy
  Ctrl+\\            Wyjście z programu

  /skills            List skills         /create <n>     Create skill
  /run <n> [v]       Run skill           /evolve <n>     Improve skill
  /test <n>          Test skill           /rollback <n>   Rollback skill
  /diagnose <n>      Diagnose skill       /scan           System capabilities
  /pipeline list|create|run <n>          /compose        Docker compose
  /model <n>         Switch model        /models         Available models
  /models refresh    Auto-discover       /core           A/B status
  /switch            Switch core         /log [skill]    Recent logs
  /learn [skill]     Show learnings      /state          System state
  /autotune [goal] [profile] [--static]  Benchmark z LIVE testami API (domyślnie)
                       Profile: fastest, best_quality, ignore_cost, free_only, balanced
                       --static = szybki ale mniej dokładny (bez wywołań API)
                       Przykład: /autotune coding fastest
  /config            Show session config /config <cat> <set> <val>  Change setting
  /correct <wrong> <right>  Correct last intent (teaches the system)
  /profile           Show learned user profile & preferences
  /suggest           Suggest new skills based on unhandled requests
  /topic             Show current conversation topic
  /providers         Show capability/provider summary
  /resources         Show system resources snapshot
  /help              This help           /quit           Exit

  Chat naturally - evo auto-detects needs with context-aware IntentEngine,
  builds+tests skills, and validates goals. Learns from your corrections.
  
  Configuration via chat: say "używaj lepszego TTS", "przełącz na gemini", etc.
"""


QUICK_HELP = """
  Najważniejsze skróty:
  Ctrl+A  audio (voice) | Ctrl+T  tekst | Ctrl+\\  wyjście

  Najważniejsze komendy:
  /voice        tryb głosowy (on/off)
  /help         wszystkie komendy
  /providers    status providerów (TTS/STT)
  /health       zdrowie skill-i
  /models       modele LLM
  /memories     pamięć użytkownika
"""


# ─── Command Handlers ────────────────────────────────────────────────
def _cmd_help(**ctx):
    print(HELP)


def _cmd_quit(**ctx):
    return "QUIT"


def _cmd_skills(**ctx):
    for n, vs in ctx["sm"].list_skills().items():
        cpr(C.CYAN, f"  {n}: {', '.join(vs)}")


def _cmd_create(a1, a2, **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /create <name> [description]")
        return
    if a2:
        d = a2
    else:
        cpr(C.CYAN, f"Describe '{a1}':")
        d = input(f"{C.GREEN}> {C.R}").strip()
    if d:
        ok, msg = ctx["evo"].evolve_skill(a1, d)
        cpr(C.GREEN if ok else C.RED, msg)


def _cmd_test(a1, **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /test <name>")
        return
    ok, out = ctx["sm"].test_skill(a1)
    cpr(C.GREEN if ok else C.RED, f"Test {'OK' if ok else 'FAILED'}: {out[:300]}")


def _cmd_run(a1, a2, **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /run <name>")
        return
    print(json.dumps(ctx["sm"].exec_skill(a1, inp=a2 or None), indent=2, default=str))


def _cmd_evolve(a1, a2="", **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /evolve <name> [feedback]")
        return
    if a2:
        fb = a2
    else:
        cpr(C.CYAN, "Feedback:")
        fb = input(f"{C.GREEN}> {C.R}").strip()
    if fb:
        sm = ctx["sm"]
        ok, msg = sm.evolve(a1, fb)
        cpr(C.GREEN if ok else C.RED, msg)
        if ok:
            cpr(C.DIM, "Testing new version...")
            tok, tout = sm.test_skill(a1)
            cpr(C.GREEN if tok else C.YELLOW,
                f"Test {'OK' if tok else 'FAILED'}: {tout[:200]}")


def _cmd_rollback(a1, **ctx):
    if a1:
        ok, msg = ctx["sm"].rollback(a1)
        cpr(C.GREEN if ok else C.RED, msg)


def _cmd_pipeline(a1, a2, **ctx):
    pm = ctx["pm"]
    if a1 == "list":
        for p2 in pm.list_p():
            cpr(C.CYAN, f"  {p2}")
    elif a1 == "create":
        n = input(f"{C.CYAN}Name: {C.R}").strip()
        d = input(f"{C.CYAN}Describe: {C.R}").strip()
        if n and d:
            ok, msg = pm.create_p(n, d)
            cpr(C.GREEN if ok else C.RED, msg)
    elif a1 == "run" and a2:
        print(json.dumps(pm.run_p(a2), indent=2, default=str))


def _cmd_compose(**ctx):
    from .core_boot import gen_compose
    cpr(C.GREEN, f"Generated: {gen_compose(ctx['sm'].list_skills(), ctx['state'])}")


def _cmd_model(a1, **ctx):
    llm = ctx["llm"]
    state = ctx["state"]
    if not a1:
        cpr(C.DIM, f"Current: {llm.model}")
        return
    nm = a1 if a1.startswith("openrouter/") else f"openrouter/{a1}"
    state["model"] = nm
    save_state(state)
    llm.model = nm
    cpr(C.GREEN, f"Model -> {nm}")


def _cmd_models(a1, **ctx):
    import time
    llm = ctx["llm"]
    state = ctx["state"]
    if a1 == "refresh":
        cpr(C.DIM, "[DISCOVER] Fetching available free models from OpenRouter...")
        discovered = discover_models()
        if discovered:
            state["models"] = ",".join(discovered)
            save_state(state)
            llm._tiers[TIER_FREE] = discovered
            llm.models = discovered
            cpr(C.GREEN, f"[DISCOVER] Found {len(discovered)} free models")
        else:
            cpr(C.YELLOW, "[DISCOVER] Could not fetch. Using current list.")
        # Also refresh local
        local = _detect_ollama_models()
        llm._tiers[TIER_LOCAL] = local
        cpr(C.DIM, f"Local (ollama): {len(local)} models")
        cpr(C.GREEN, f"Tiers: {llm.tier_info()}")
    else:
        cpr(C.CYAN, f"  Active: {llm.model} [{llm.active_tier}]")
        cpr(C.CYAN, f"  Tiers:  {llm.tier_info()}")
        for tier in (TIER_FREE, TIER_LOCAL, TIER_PAID):
            ms = llm._tiers[tier]
            if not ms:
                continue
            cpr(C.DIM, f"  [{tier}]")
            for m2 in ms[:8]:
                cur = " ← active" if m2 == llm.model else ""
                if m2 in llm._dead:
                    st = " ✗ dead"
                elif m2 in llm._cooldowns:
                    cd_t, cd_r = llm._cooldowns[m2]
                    secs = int(cd_t - time.time())
                    st = f" ⏳ {cd_r} ({secs}s)" if secs > 0 else ""
                else:
                    st = ""
                short = m2.split("/")[-1] if "/" in m2 else m2
                cpr(C.DIM, f"    {short}{cur}{st}")
            if len(ms) > 8:
                cpr(C.DIM, f"    ... +{len(ms)-8} more")


def _cmd_core(a1, **ctx):
    sv = ctx["sv"]
    if a1 == "rollback":
        ok, msg = sv.rollback_core()
        cpr(C.GREEN if ok else C.RED, msg)
        if ok:
            cpr(C.YELLOW, "Restart needed: python3 main.py")
    elif a1 == "list":
        for cv in sv.list_cores():
            active = " <-ACTIVE" if cv == f"v{sv.active_version()}" else ""
            cpr(C.CYAN, f"  {cv}{active}")
    else:
        a = sv.active()
        v = sv.active_version()
        cpr(C.CYAN, f"  Core {a}, version v{v}")
        cpr(C.DIM, f"  Available: {', '.join(sv.list_cores())}")
        cpr(C.DIM, "  /core list | /core rollback")


def _cmd_switch(**ctx):
    cpr(C.GREEN, f"Switched to {ctx['sv'].switch()}")


def _cmd_log(a1, **ctx):
    logger = ctx["logger"]
    if a1:
        logs = logger.read_skill_log(a1, 15)
    else:
        logs = logger.read_core_log(15)
    for entry in logs:
        cpr(C.DIM, f"  [{entry.get('ts','')}] {entry.get('event','')} {json.dumps(entry.get('data',{}))[:100]}")


def _cmd_learn(a1, **ctx):
    s = ctx["logger"].learn_summary(a1 if a1 else None)
    cpr(C.CYAN, f"Learnings: {s}")


def _cmd_diagnose(a1, **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /diagnose <skill>")
        return
    diag = ctx["sm"].diagnose_skill(a1)
    cpr(C.CYAN, f"Diagnosis for '{a1}':")
    for k, v in diag.items():
        cpr(C.DIM, f"  {k}: {json.dumps(v, default=str)[:200]}")


def _cmd_scan(**ctx):
    sm = ctx["sm"]
    if sm._deps:
        scan = sm._deps.scan_system()
        for cat, tools in scan.get("capabilities", {}).items():
            avail = [t for t, ok in tools.items() if ok]
            cpr(C.CYAN, f"  {cat}: {', '.join(avail) if avail else 'none'}")
    else:
        cpr(C.RED, "deps skill not loaded")


def _cmd_state(**ctx):
    print(json.dumps(ctx["state"], indent=2))


def _cmd_correct(a1, a2, **ctx):
    if not a1 or not a2:
        cpr(C.YELLOW, "Usage: /correct <wrong_action> <correct_action>")
        cpr(C.DIM, "  Example: /correct tts stt  (last msg should have used stt, not tts)")
    else:
        conv = ctx["conv"]
        intent = ctx["intent"]
        last_msg = conv[-2]["content"] if len(conv) >= 2 else "unknown"
        intent.record_correction(last_msg, a1, a2)
        cpr(C.GREEN, f"[LEARN] Zapamiętano: '{last_msg[:50]}' → {a2} (nie {a1})")


def _cmd_profile(**ctx):
    intent = ctx["intent"]
    p = intent._p
    topic = intent._recent_topic()
    cpr(C.CYAN, f"  Active topic: {topic or 'none'}")
    cpr(C.CYAN, f"  Topics history: {p.get('topics', [])[:10]}")
    cpr(C.CYAN, f"  Skill usage: {json.dumps(p.get('skill_usage', {}))}")
    cpr(C.CYAN, f"  Corrections: {len(p.get('corrections', []))}")
    cpr(C.CYAN, f"  Unhandled: {len(p.get('unhandled', []))}")
    prefs = p.get("preferences", {})
    if prefs:
        cpr(C.CYAN, f"  Preferences: {json.dumps(prefs, ensure_ascii=False)}")


def _cmd_suggest(**ctx):
    intent = ctx["intent"]
    cpr(C.DIM, "[LEARN] Analyzing unhandled intents...")
    suggestions = intent.suggest_skills()
    if suggestions:
        cpr(C.CYAN, "[LEARN] Proponowane nowe skills:")
        for sg in suggestions:
            cpr(C.GREEN, f"  → {sg.get('name','?')}: {sg.get('description','')[:80]}")
        cpr(C.DIM, "  Użyj /create <name> aby zbudować.")
    else:
        cpr(C.DIM, "[LEARN] Za mało danych (potrzeba min. 3 nieobsłużone intencje).")


def _cmd_topic(**ctx):
    intent = ctx["intent"]
    topic = intent._recent_topic()
    topics = intent._p.get("topics", [])[:10]
    cpr(C.CYAN, f"  Current topic: {topic or 'none'}")
    cpr(C.DIM, f"  Recent: {topics}")


def _cmd_providers(**ctx):
    ps = ctx.get("provider_selector")
    if ps:
        cpr(C.CYAN, "Capability/Provider summary:")
        cpr(C.DIM, ps.summary())
    else:
        cpr(C.YELLOW, "ProviderSelector not initialized")


def _cmd_chain(**ctx):
    evo = ctx.get("evo")
    if not evo or not evo.provider_chain:
        cpr(C.YELLOW, "ProviderChain not initialized")
        return
    chain = evo.provider_chain
    ps = ctx.get("provider_selector")
    if not ps:
        return
    cpr(C.CYAN, "Provider fallback chains:")
    for cap in ps.list_capabilities():
        cpr(C.DIM, f"  {chain.chain_summary(cap)}")


def _cmd_gc(**ctx):
    from .garbage_collector import EvolutionGarbageCollector
    a1 = ctx.get("a1", "")
    dry = a1 == "dry"
    gc = EvolutionGarbageCollector()
    reports = gc.cleanup_all(migrate=True, dry_run=dry)
    cpr(C.CYAN, gc.summary(reports))


def _cmd_resources(**ctx):
    rm = ctx.get("resource_monitor")
    if rm:
        snap = rm.snapshot()
        snap_display = dict(snap)
        pkgs = snap_display.pop("python_packages", {})
        snap_display["python_packages"] = f"({len(pkgs)} packages)"
        cpr(C.CYAN, "System resources:")
        for k, v in snap_display.items():
            cpr(C.DIM, f"  {k}: {json.dumps(v, default=str)}")
    else:
        cpr(C.YELLOW, "ResourceMonitor not initialized")


def _cmd_stt(a1, **ctx):
    """Direct STT command: /stt [duration_seconds]"""
    sm = ctx["sm"]
    evo = ctx["evo"]
    intent = ctx["intent"]
    llm = ctx["llm"]
    conv = ctx["conv"]
    identity = ctx.get("identity")

    # Parse duration
    duration = 4
    if a1 and a1.isdigit():
        duration = int(a1)

    cpr(C.CYAN, f"\n🎤 Nagrywam... (mów teraz, {duration}s)")

    # Execute STT skill directly
    outcome = evo.handle_request(
        f"[stt command]",
        sm.list_skills(),
        analysis={"action": "use", "skill": "stt", "input": {"duration_s": duration, "lang": "pl"}, "goal": "transcribe_audio"}
    )

    # Handle outcome like main loop
    if outcome and outcome.get("skill") == "stt":
        stt_text = _extract_stt_text(outcome)
        intent.record_skill_use("stt")
        if stt_text:
            cpr(C.GREEN, f"[STT] Usłyszałem: \"{stt_text}\"")
            mprint(f"### 🎤 Usłyszałem: *{stt_text}*")
            conv.append({"role": "user", "content": f"[głosowo] {stt_text}"})
            _handle_chat(llm, sm, ctx["logger"], conv, identity=identity, memory=ctx.get("memory"))
        else:
            cpr(C.YELLOW, "[STT] Nie usłyszałem nic. Spróbuj mówić głośniej lub bliżej mikrofonu.")
            mprint("### 🎤 Nie usłyszałem nic\nSpróbuj powiedzieć coś głośniej.")
            conv.append({"role": "assistant", "content": "Nie usłyszałem nic. Spróbuj ponownie."})


def _cmd_tts(a1, **ctx):
    """TTS command: /tts [provider] - Test or switch TTS provider"""
    sm = ctx["sm"]
    ps = ctx.get("provider_selector")
    
    if not a1:
        # Show current TTS providers
        if ps:
            providers = ps.list_providers("tts")
            cpr(C.CYAN, "Dostępni TTS providerzy:")
            for prov in providers:
                cpr(C.DIM, f"  - {prov}")
            cpr(C.DIM, "Użycie: /tts <provider> aby przetestować")
        else:
            cpr(C.YELLOW, "ProviderSelector nie jest dostępny")
        return
    
    # Test TTS with specified provider
    provider = a1.strip().lower()
    cpr(C.CYAN, f"🔊 Testuję TTS z providerem: {provider}")
    
    result = sm.exec_skill("tts", inp={"text": "To jest test syntezy mowy.", "lang": "pl"}, provider=provider)
    
    if result.get("success"):
        method = result.get("result", {}).get("method", "unknown")
        cpr(C.GREEN, f"✓ TTS działa! Method: {method}")
        # Save as preferred provider in session config
        session_cfg = ctx.get("session_config")
        if session_cfg:
            session_cfg.set("tts", "provider", provider)
            cpr(C.CYAN, f"💾 Ustawiono {provider} jako domyślny provider TTS dla tej sesji")
    else:
        cpr(C.RED, f"✗ TTS nie działa: {result.get('error', 'unknown error')}")
        cpr(C.DIM, "Sprawdź /providers aby zobaczyć dostępnych providerów")


def _cmd_fix(a1, **ctx):
    """Autonomous repair: /fix [skill_name]"""
    sm = ctx["sm"]
    evo = ctx["evo"]
    skill_name = a1 or "stt"
    
    cpr(C.CYAN, f"\n[AUTO] Naprawa skill: {skill_name}")
    
    # Test the skill first
    test_result = sm.exec_skill(skill_name, inp={"duration_s": 3, "lang": "pl"} if skill_name == "stt" else {})
    
    # Run autonomous repair
    fixed, msg, new_result = evo._autonomous_stt_repair(skill_name, test_result, f"/fix {skill_name}")
    
    if fixed:
        cpr(C.GREEN, f"✓ Naprawione: {msg[:100]}")
        # Extract and show result for STT
        if skill_name == "stt":
            text = new_result.get("result", {}).get("spoken") or new_result.get("result", {}).get("text", "")
            if text:
                cpr(C.GREEN, f"🎤 Usłyszałem: \"{text}\"")
    else:
        cpr(C.YELLOW, f"✗ Nie udało się naprawić: {msg}")
        cpr(C.DIM, "Spróbuj użyć innego providera lub sprawdź /diagnose")


def _print_skill_health(name, report):
    """Print health report for a single skill."""
    ok = report.get("ok", True)
    cpr(C.GREEN if ok else C.YELLOW, f"\n[{name}] {'✓ OK' if ok else '⚠ PROBLEM'}")
    deps = report.get("deps", {})
    if deps:
        dep_str = "  ".join(f"{k}={'✓' if v else '✗'}" for k, v in deps.items())
        cpr(C.DIM, f"  deps:  {dep_str}")
    for hw_k, hw_v in report.get("hardware", {}).items():
        if isinstance(hw_v, bool):
            cpr(C.DIM if hw_v else C.YELLOW, f"  hw:    {hw_k}={'✓' if hw_v else '✗'}")
        elif hw_v:
            cpr(C.DIM, f"  hw:    {hw_k}: {hw_v}")
    for res_k, res_v in report.get("resources", {}).items():
        cpr(C.DIM if res_v else C.YELLOW, f"  res:   {res_k}: {res_v or 'MISSING'}")
    for issue in report.get("issues", []):
        cpr(C.YELLOW, f"  ⚠  {issue}")


def _cmd_health(a1, **ctx):
    """Show skill readiness/health status: /health [skill_name]"""
    sm = ctx["sm"]
    skills_to_check = [a1] if a1 else sorted(sm.list_skills().keys())
    for name in skills_to_check:
        _print_skill_health(name, sm.readiness_check(name))


def _cmd_voice(a1, **ctx):
    """Voice mode: /voice (start), /voice off (disable), /voice file (file fallback)"""
    memory = ctx.get("memory")
    subcmd = a1.strip().lower() if a1 else ""

    if subcmd in ("off", "stop", "wyłącz", "wylacz"):
        if memory:
            memory.set_voice_mode(False)
            cpr(C.CYAN, "🔇 Tryb głosowy wyłączony na stałe.")
        else:
            cpr(C.YELLOW, "Brak modułu pamięci.")
        return

    if subcmd in ("file", "plik", "fallback"):
        from .voice_loop import _run_file_input_loop
        cpr(C.CYAN, "📁 Tryb plikowy — TTS→WAV→STT (bez mikrofonu)")
        _run_file_input_loop(
            ctx["sm"], ctx["evo"], ctx["llm"], ctx["intent"],
            ctx["logger"], ctx["conv"], ctx.get("identity"), memory=memory
        )
        return

    # Enable persistent voice mode (auto-save, don't ask)
    if memory and not memory.voice_mode:
        memory.set_voice_mode(True)
        cpr(C.CYAN, "🔊 Zapamiętano: tryb głosowy włączony na stałe. "
                    "Wyłącz: /voice off lub powiedz 'wyłącz tryb głosowy'.")

    _run_voice_loop(
        ctx["sm"], ctx["evo"], ctx["llm"], ctx["intent"],
        ctx["logger"], ctx["conv"], ctx.get("identity"), memory=memory
    )


# ─── COMMANDS Dispatch Table ─────────────────────────────────────────
def get_commands():
    """Return the COMMANDS dispatch table."""
    return {
        "/help": _cmd_help,
        "/quit": _cmd_quit,
        "/skills": _cmd_skills,
        "/create": _cmd_create,
        "/test": _cmd_test,
        "/run": _cmd_run,
        "/evolve": _cmd_evolve,
        "/rollback": _cmd_rollback,
        "/pipeline": _cmd_pipeline,
        "/compose": _cmd_compose,
        "/model": _cmd_model,
        "/models": _cmd_models,
        "/core": _cmd_core,
        "/switch": _cmd_switch,
        "/log": _cmd_log,
        "/learn": _cmd_learn,
        "/diagnose": _cmd_diagnose,
        "/scan": _cmd_scan,
        "/state": _cmd_state,
        "/correct": _cmd_correct,
        "/profile": _cmd_profile,
        "/suggest": _cmd_suggest,
        "/topic": _cmd_topic,
        "/providers": _cmd_providers,
        "/chain": _cmd_chain,
        "/gc": _cmd_gc,
        "/resources": _cmd_resources,
        "/stt": _cmd_stt,
        "/tts": _cmd_tts,
        "/fix": _cmd_fix,
        "/health": _cmd_health,
        "/voice": _cmd_voice,
    }


# ─── Chat Handling ───────────────────────────────────────────────────
def _build_env_context():
    """Build masked environment context for LLM."""
    import os as _os
    _env_ctx = []
    _key_env = ['HOME', 'USER', 'PATH', 'PWD', 'SHELL', 'TERM', 'EVO_TEXT_ONLY',
                'OPENROUTER_API_KEY', 'OLLAMA_HOST', 'DISPLAY', 'XDG_SESSION_TYPE',
                'XDG_CURRENT_DESKTOP', 'LANG', 'LC_ALL']
    for _k in _key_env:
        _v = _os.environ.get(_k)
        if _v:
            if 'KEY' in _k or 'TOKEN' in _k or 'SECRET' in _k:
                _v = _v[:8] + "..." if len(_v) > 12 else "***"
            _env_ctx.append(f"  {_k}={_v}")
    return _env_ctx


def _build_skills_info(sm):
    """Build skills descriptions for system prompt."""
    _skills_info = []
    for _name, _skill in sm.list_skills().items():
        try:
            if hasattr(_skill, 'get_info'):
                _info = _skill.get_info()
                _desc = _info.get('description', 'brak opisu')
                _caps = _info.get('capabilities', [])
                _caps_str = ', '.join(_caps[:3]) if _caps else ''
                _skills_info.append(f"  {_name}: {_desc[:60]}{'...' if len(_desc) > 60 else ''}" + (f" [{_caps_str}]" if _caps_str else ""))
            else:
                _skills_info.append(f"  {_name}: (skill bez opisu)")
        except Exception:
            _skills_info.append(f"  {_name}: (błąd odczytu info)")
    return _skills_info


def _build_fallback_system_prompt(sm, identity=None):
    """Build fallback system prompt when identity not available."""
    from datetime import datetime as _dt
    import os
    import json
    
    _now = _dt.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
    _skills = list(sm.list_skills().keys())
    _env_candidates = [
        "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY",
        "GOOGLE_API_KEY", "MOONSHOT_API_KEY", "OLLAMA_HOST",
        "EVO_MODEL", "EVO_TEXT_ONLY",
    ]
    _env_lines = []
    for k in _env_candidates:
        _env_lines.append(f"- {k}: {'SET' if os.environ.get(k) else 'UNSET'}")

    sp = (
        f"AKTUALNY CZAS SYSTEMOWY: {_now}\n"
        "NIGDY nie wymyślaj daty/godziny — używaj WYŁĄCZNIE powyższego czasu.\n\n"
        "Jesteś evo-engine, ewolucyjny asystent AI połączony z systemem skills.\n"
        "Nigdy nie mów, że nie umiesz — używaj skill-i.\n\n"
        f"DOSTĘPNE SKILLS: {json.dumps(_skills, ensure_ascii=False)}\n\n"
        "DOSTĘPNE ZMIENNE ŚRODOWISKOWE (tylko nazwy, bez wartości):\n"
        + "\n".join(_env_lines)
    )
    return sp


def _sanitize_chat_response(text, sm, logger):
    """Detect and flag when LLM hallucinates skill execution in its text response."""
    import re as _re
    if not text:
        return text
    skill_names = set(sm.list_skills().keys()) if sm else set()
    _fake_patterns = []
    for sn in skill_names:
        _fake_patterns.append(
            _re.compile(r'✅\s*`?' + _re.escape(sn) + r'`?\s*→[^\n]*', _re.IGNORECASE))
        _fake_patterns.append(
            _re.compile(r'➡️\s*`?' + _re.escape(sn) + r'`?\s*→[^\n]*', _re.IGNORECASE))
    
    found_fake = False
    cleaned = text
    for pat in _fake_patterns:
        if pat.search(cleaned):
            found_fake = True
            cleaned = pat.sub('', cleaned)
    
    if found_fake:
        logger.core("hallucination_detected", {"original_len": len(text), "cleaned_len": len(cleaned)})
        cpr(C.YELLOW, "[VALIDATE] LLM halucynował wykonanie skilla — usunięto fałszywe dane")
        cleaned = _re.sub(r'\n{3,}', '\n\n', cleaned).strip()
        if not cleaned or len(cleaned) < 10:
            cleaned = "Nie mam aktualnych danych. System uruchomi odpowiedni skill automatycznie."
    return cleaned


def _check_proactive_learning(intent):
    unhandled = intent._p.get("unhandled", [])
    if len(unhandled) >= 5 and len(unhandled) % 5 == 0:
        suggestions = intent.suggest_skills()
        if suggestions:
            cpr(C.CYAN, "\n[LEARN] Wykryłem powtarzające się potrzeby. Proponuję nowe skills:")
            for sg in suggestions:
                cpr(C.GREEN, f"  → {sg.get('name','?')}: {sg.get('description','')[:80]}")
            cpr(C.DIM, "  Napisz 'stwórz <name>' lub /create <name> aby zbudować.")


def _append_truncated(sp, header, lines, limit=20):
    """Append up to `limit` lines with a header to system prompt."""
    if not lines:
        return sp
    sp += f"\n\n{header}:\n" + "\n".join(lines[:limit])
    if len(lines) > limit:
        sp += f"\n  ... i {len(lines) - limit} innych"
    return sp


def _build_full_system_prompt(sm, llm, identity=None, memory=None):
    """Assemble complete system prompt with env, skills, memory, and model info."""
    sp = identity.build_system_prompt() if identity else _build_fallback_system_prompt(sm)
    sp = _append_truncated(sp, "ZMIENNE ŚRODOWISKOWE (maskowane)", _build_env_context())
    sp = _append_truncated(sp, "SKILLS (skrót)", _build_skills_info(sm))
    if memory:
        mem_ctx = memory.build_system_context()
        if mem_ctx:
            sp = mem_ctx + "\n\n" + sp
    model_short = llm.model.split('/')[-1] if '/' in llm.model else llm.model
    sp += f"\n\n[Aktywny model: {model_short} ({llm.active_tier})]"
    return sp, model_short


def _handle_chat(llm, sm, logger, conv, identity=None, memory=None):
    """Generate LLM response. Returns response text (or None on error)."""
    sp, model_short = _build_full_system_prompt(sm, llm, identity, memory)
    cpr(C.DIM, f"Thinking... [{model_short}]")
    r = llm.chat([{"role": "system", "content": sp}] + conv[-20:])
    if r and "[ERROR]" in r:
        logger.core("chat_error", {"error": r[:200]})
        cpr(C.RED, f"evo> {r}")
        return None
    if r:
        r = _sanitize_chat_response(r, sm, logger)
    conv.append({"role": "assistant", "content": r})
    mprint(f"**evo>** {r}\n")
    logger.core("chat_response", {"length": len(r) if r else 0})
    return r


def _display_shell_result(res_data, conv):
    """Display shell command outcome and append to conversation."""
    cmd = res_data.get("command", "?")
    exit_code = res_data.get("exit_code", "?")
    stdout = res_data.get("stdout", "").strip()
    stderr = res_data.get("stderr", "").strip()
    ok = res_data.get("success", True)
    icon = "✅" if ok else "⚠️"
    md = f"### {icon} `$ {cmd}` (exit: {exit_code})\n"
    if stdout:
        md += f"```\n{stdout[:3000]}\n```\n"
    if stderr and not ok:
        md += f"**stderr:** `{stderr[:500]}`\n"
    mprint(md)
    conv.append({"role": "assistant", "content":
        f"Wykonałem: `{cmd}` → exit {exit_code}\n{stdout[:500]}"})


def _display_generic_result(skill, res_data, conv):
    """Display generic skill outcome and append to conversation."""
    md = f"### ✅ `{skill}` — done\n"
    _skip = ("success", "available_backends", "raw", "audio_path",
             "exit_code", "stderr", "command")
    if isinstance(res_data, dict):
        for k, v in res_data.items():
            if k not in _skip and v:
                md += f"- **{k}**: {v}\n"
    mprint(md)
    conv.append({"role": "assistant", "content": f"Executed {skill} successfully."})


def _handle_suggestion(outcome, conv):
    """Display and record skill creation suggestion if present."""
    suggestion = outcome.get("suggestion")
    if not suggestion:
        return
    skill_name = suggestion.get("skill_name", "?")
    desc = suggestion.get("description", "")
    reason = suggestion.get("reason", "")
    cpr(C.CYAN, f"\n💡 SUGESTIA: Brak odpowiedniego skillu!")
    cpr(C.YELLOW, f"   Powód: {reason}")
    cpr(C.GREEN, f"   Proponowany skill: '{skill_name}'")
    cpr(C.DIM, f"   Opis: {desc[:80]}")
    cpr(C.CYAN, f"   Powiedz: 'stwórz {skill_name}' aby go zbudować.")
    conv.append({"role": "system", "content":
        f"System sugeruje stworzenie nowego skillu '{skill_name}' "
        f"ponieważ: {reason}. Użytkownik może powiedzieć 'stwórz {skill_name}' aby zbudować."})


def _handle_outcome(outcome, intent, conv, identity=None):
    """Process EvoEngine outcome. Returns True if handled (skip chat), False to fall through."""
    if not outcome:
        return False
    otype = outcome.get("type")
    skill = outcome.get("skill", "?")
    if otype == "success":
        r = outcome.get("result", {})
        intent.record_skill_use(skill)
        res_data = r.get("result", {}) if isinstance(r, dict) else r
        if skill == "shell" and isinstance(res_data, dict):
            _display_shell_result(res_data, conv)
        else:
            _display_generic_result(skill, res_data, conv)
        _handle_suggestion(outcome, conv)
        return True
    elif otype == "evo_failed":
        mprint(f"### ❌ Build failed\n{outcome.get('message', '')}")
        conv.append({"role": "assistant", "content": outcome.get("message", "")})
        return True
    elif otype == "failed":
        if identity:
            msg = identity.build_fallback_message(skill, outcome.get("goal", ""))
            mprint(f"### ❌ {msg}")
            conv.append({"role": "system", "content":
                f"Skill '{skill}' jest tymczasowo uszkodzony. "
                f"NIE mów że nie umiesz. Powiedz że naprawiasz skill."})
        else:
            mprint(f"### ❌ Nie udało się: {outcome.get('goal', '?')}\nSpróbuję odpowiedzieć tekstowo.")
    return False
