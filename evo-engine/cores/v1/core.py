#!/usr/bin/env python3
"""
evo-engine Core v1 - Evolutionary Chat Engine
Dual-core (A/B) with self-healing, evolutionary skill building,
per-skill/core logging, learning from logs, auto-proposals.

Refactored: thin main() with dispatch table. All logic in submodules.
"""
import os
import sys
import json
import time
from datetime import datetime, timezone, timedelta

from .config import (
    ROOT, SKILLS_DIR, C, cpr,
    TIER_FREE, TIER_LOCAL, TIER_PAID,
    DEFAULT_MODEL,
    load_state, save_state, get_models_from_config,
)
from .utils import mprint
from .logger import Logger
from .llm_client import LLMClient, _detect_ollama_models, discover_models
from .intent_engine import IntentEngine
from .skill_manager import SkillManager
from .evo_engine import EvoEngine
from .pipeline_manager import PipelineManager
from .supervisor import Supervisor
from .resource_monitor import ResourceMonitor
from .provider_selector import ProviderSelector
from .system_identity import SystemIdentity
from .skill_logger import init_nfo


# ─── Docker Compose Generator ────────────────────────────────────────
def gen_compose(skills, state):
    svc = {}
    for side in ["a", "b"]:
        svc[f"core-{side}"] = {
            "build": {"context": ".", "dockerfile": "Dockerfile.core"},
            "container_name": f"evo-core-{side}",
            "environment": {
                "CORE_ID": side.upper(),
                "CORE_VERSION": str(state.get(f"core_{side}_version", 1)),
                "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
                "MODEL": state.get("model", "")},
            "volumes": ["./cores:/app/cores:ro", "./skills:/app/skills",
                        "./logs:/app/logs", "./pipelines:/app/pipelines"],
            "restart": "unless-stopped"}
    for sn, vs in skills.items():
        svc[f"skill-{sn}"] = {
            "build": {"context": f"./skills/{sn}/{vs[-1]}"},
            "container_name": f"evo-skill-{sn}",
            "restart": "unless-stopped"}
    out = ROOT / "docker-compose.yml"
    out.write_text(json.dumps({"version": "3.8", "services": svc}, indent=2))
    return str(out)


# ─── Help ────────────────────────────────────────────────────────────
HELP = """
  /skills            List skills         /create <n>     Create skill
  /run <n> [v]       Run skill           /evolve <n>     Improve skill
  /test <n>          Test skill           /rollback <n>   Rollback skill
  /diagnose <n>      Diagnose skill       /scan           System capabilities
  /pipeline list|create|run <n>          /compose        Docker compose
  /model <n>         Switch model        /models         Available models
  /models refresh    Auto-discover       /core           A/B status
  /switch            Switch core         /log [skill]    Recent logs
  /learn [skill]     Show learnings      /state          System state
  /correct <wrong> <right>  Correct last intent (teaches the system)
  /profile           Show learned user profile & preferences
  /suggest           Suggest new skills based on unhandled requests
  /topic             Show current conversation topic
  /providers         Show capability/provider summary
  /resources         Show system resources snapshot
  /help              This help           /quit           Exit

  Chat naturally - evo auto-detects needs with context-aware IntentEngine,
  builds+tests skills, and validates goals. Learns from your corrections.
"""


# ─── Command Dispatch Table ──────────────────────────────────────────
def _cmd_help(**ctx):
    print(HELP)

def _cmd_quit(**ctx):
    return "QUIT"

def _cmd_skills(**ctx):
    for n, vs in ctx["sm"].list_skills().items():
        cpr(C.CYAN, f"  {n}: {', '.join(vs)}")

def _cmd_create(a1, a2, **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /create <name>")
        return
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
    print(json.dumps(ctx["sm"].exec_skill(a1, a2 or None), indent=2, default=str))

def _cmd_evolve(a1, **ctx):
    if not a1:
        cpr(C.YELLOW, "Usage: /evolve <name>")
        return
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
    if prefs: cpr(C.CYAN, f"  Preferences: {json.dumps(prefs, ensure_ascii=False)}")

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
            _handle_chat(llm, sm, ctx["logger"], conv, identity=identity)
        else:
            cpr(C.YELLOW, "[STT] Nie usłyszałem nic. Spróbuj mówić głośniej lub bliżej mikrofonu.")
            mprint("### 🎤 Nie usłyszałem nic\nSpróbuj powiedzieć coś głośniej.")
            conv.append({"role": "assistant", "content": "Nie usłyszałem nic. Spróbuj ponownie."})

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


# Command dispatch table
COMMANDS = {
    "/help": _cmd_help,
    "/quit": _cmd_quit,
    "/exit": _cmd_quit,
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
    "/resources": _cmd_resources,
    "/stt": _cmd_stt,
    "/fix": _cmd_fix,
    "/voice": _cmd_voice,
}


# ─── Init helpers ─────────────────────────────────────────────────────
def _check_restart_loop(state):
    if state.get("last_reset"):
        lr = datetime.fromisoformat(state["last_reset"])
        if datetime.now(timezone.utc) - lr < timedelta(minutes=5):
            cpr(C.RED, "\n=== RESTART LOOP DETECTED ===")
            cpr(C.YELLOW, "Check your API key: https://openrouter.ai/keys")
            cpr(C.RED, "Exiting. Fix the issue and run again.")
            sys.exit(1)

def _ensure_api_key(state):
    ak = state.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")
    if not ak or not ak.strip():
        cpr(C.YELLOW, "\nPodaj API key OpenRouter:")
        cpr(C.DIM, "(https://openrouter.ai/keys)")
        ak = input(f"{C.GREEN}> {C.R}").strip()
        if not ak:
            cpr(C.RED, "Required.")
            sys.exit(1)
    state["openrouter_api_key"] = ak
    if not state.get("created_at"):
        state["created_at"] = datetime.now(timezone.utc).isoformat()
    save_state(state)
    return ak

def _resolve_model(state):
    models = get_models_from_config(state)
    mdl = os.environ.get("EVO_MODEL") or state.get("model") or (models[0] if models else DEFAULT_MODEL)
    if (not mdl) or "stepfun" in str(mdl):
        mdl = models[0] if models else DEFAULT_MODEL
        state["model"] = mdl
        save_state(state)
    return mdl, models

def _init_components(ak, mdl, models, logger, state):
    llm = LLMClient(ak, mdl, logger, models=models)
    resource_mon = ResourceMonitor()
    provider_sel = ProviderSelector(SKILLS_DIR, resource_mon)
    sm = SkillManager(llm, logger, provider_selector=provider_sel)
    pm = PipelineManager(sm, llm, logger)
    evo = EvoEngine(sm, llm, logger)
    intent = IntentEngine(llm, logger, state)
    identity = SystemIdentity(skill_manager=sm, resource_monitor=resource_mon)
    return llm, sm, pm, evo, intent, provider_sel, resource_mon, identity


# ─── Chat loop helpers ────────────────────────────────────────────────
def _extract_stt_text(outcome):
    """Extract transcribed text from STT result, if any."""
    if not outcome or outcome.get("type") != "success":
        return None
    if outcome.get("skill") != "stt":
        return None
    r = outcome.get("result", {})
    inner = r.get("result", {}) if isinstance(r, dict) else {}
    if not isinstance(inner, dict):
        return None
    text = inner.get("spoken") or inner.get("text") or inner.get("transcript") or ""
    if isinstance(text, str):
        text = text.strip()
    return text if text else None

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

        # Special shell output display
        if skill == "shell" and isinstance(res_data, dict):
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
        else:
            md = f"### ✅ `{skill}` — done\n"
            _skip = ("success", "available_backends", "raw", "audio_path",
                     "exit_code", "stderr", "command")
            if isinstance(res_data, dict):
                for k, v in res_data.items():
                    if k not in _skip and v:
                        md += f"- **{k}**: {v}\n"
            mprint(md)
            conv.append({"role": "assistant", "content": f"Executed {skill} successfully."})
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

def _handle_chat(llm, sm, logger, conv, identity=None):
    if identity:
        sp = identity.build_system_prompt()
    else:
        sp = ("Jesteś evo-engine, ewolucyjny asystent AI. "
              f"Masz umiejętności (skills): {json.dumps(list(sm.list_skills().keys()))}.")
    cpr(C.DIM, "Thinking...")
    r = llm.chat([{"role": "system", "content": sp}] + conv[-20:])
    if r and "[ERROR]" in r:
        logger.core("chat_error", {"error": r[:200]})
        cpr(C.RED, f"evo> {r}")
    else:
        conv.append({"role": "assistant", "content": r})
        mprint(f"**evo>** {r}\n")
    logger.core("chat_response", {"length": len(r) if r else 0})

def _check_proactive_learning(intent):
    unhandled = intent._p.get("unhandled", [])
    if len(unhandled) >= 5 and len(unhandled) % 5 == 0:
        suggestions = intent.suggest_skills()
        if suggestions:
            cpr(C.CYAN, "\n[LEARN] Wykryłem powtarzające się potrzeby. Proponuję nowe skills:")
            for sg in suggestions:
                cpr(C.GREEN, f"  → {sg.get('name','?')}: {sg.get('description','')[:80]}")
            cpr(C.DIM, "  Napisz 'stwórz <name>' lub /create <name> aby zbudować.")


def _run_stt_cycle(sm, evo, llm, intent, logger, conv, identity, duration=5):
    """Single STT→LLM cycle. Returns ('got_text', text) or ('silence', '') or ('error', msg)."""
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
    _handle_chat(llm, sm, logger, conv, identity=identity)
    intent.record_skill_use("stt")
    return "got_text", stt_text


def _run_voice_loop(sm, evo, llm, intent, logger, conv, identity):
    """Continuous voice conversation: record→transcribe→respond→repeat.
    Exits on: 3 consecutive silences, KeyboardInterrupt, or /quit spoken."""
    MAX_SILENCE = 3
    silence_count = 0
    cpr(C.CYAN, "\n🎤 Tryb głosowy aktywny. Mów teraz! (Ctrl+C aby zakończyć)")
    while True:
        cpr(C.CYAN, f"\n🎤 Słucham... (5s)")
        try:
            status, text = _run_stt_cycle(sm, evo, llm, intent, logger, conv, identity)
        except KeyboardInterrupt:
            break
        if status == "got_text":
            silence_count = 0
            # Check if user wants to exit voice mode
            if any(w in text.lower() for w in ("koniec", "stop", "wyjdź", "wyjedź", "quit", "exit", "zamknij")):
                cpr(C.DIM, "[VOICE] Wychodzę z trybu głosowego.")
                break
        elif status == "silence":
            silence_count += 1
            cpr(C.YELLOW, f"[VOICE] Nie usłyszałem ({silence_count}/{MAX_SILENCE}). Mów głośniej lub Ctrl+C.")
            if silence_count >= MAX_SILENCE:
                cpr(C.YELLOW, "[VOICE] Zbyt wiele ciszy — wychodzę z trybu głosowego.")
                break
        else:
            cpr(C.RED, f"[VOICE] Błąd: {text}. Kończę tryb głosowy.")
            break
    cpr(C.DIM, "🎤 Tryb głosowy zakończony. Możesz pisać normalnie.")


def _cmd_voice(a1, **ctx):
    """Start continuous voice conversation mode: /voice"""
    _run_voice_loop(
        ctx["sm"], ctx["evo"], ctx["llm"], ctx["intent"],
        ctx["logger"], ctx["conv"], ctx.get("identity")
    )


# ─── Main ────────────────────────────────────────────────────────────
def main():
    init_nfo()

    state = load_state()
    _check_restart_loop(state)

    logger = Logger(state.get("active_core", "A"))
    sv = Supervisor(state, logger)

    cpr(C.CYAN, "\n" + "=" * 56)
    cpr(C.CYAN, "  evo-engine | Evolutionary AI System v2.0")
    cpr(C.CYAN, "  Context-aware IntentEngine | Self-healing dual-core")
    cpr(C.CYAN, "  Auto skill builder | Capability/Provider architecture")
    cpr(C.CYAN, "=" * 56)

    ak = _ensure_api_key(state)
    mdl, models = _resolve_model(state)
    llm, sm, pm, evo, intent, provider_sel, resource_mon, identity = _init_components(
        ak, mdl, models, logger, state)

    # Startup health scan
    identity.refresh_statuses()
    report = identity.get_readiness_report()
    if report["broken"]:
        cpr(C.YELLOW, f"Uszkodzone skille: {', '.join(report['broken'])}")
        for broken_skill in report["broken"]:
            p = sm.skill_path(broken_skill)
            if p and p.exists():
                code = p.read_text()
                fixed = sm.preflight.auto_fix_imports(code)
                if fixed != code:
                    p.write_text(fixed)
                    cpr(C.GREEN, f"  Auto-fixed: {broken_skill}")
        identity.refresh_statuses()

    cpr(C.DIM, f"Model: {llm.model} | Core: {sv.active()} | Tiers: {llm.tier_info()}")
    sk = sm.list_skills()
    if sk:
        cpr(C.GREEN, f"Skills: {', '.join(sk.keys())}")
    else:
        cpr(C.YELLOW, "No skills yet. Chat or /create <n>")

    caps_with_providers = [c for c in provider_sel.list_capabilities()
                           if len(provider_sel.list_providers(c)) > 1]
    if caps_with_providers:
        cpr(C.DIM, f"Multi-provider skills: {', '.join(caps_with_providers)}")

    cpr(C.DIM, "/help for commands\n")
    logger.core("boot", {"model": llm.model, "tier": llm.active_tier,
                          "tiers": llm.tier_info(), "skills": list(sk.keys())})

    conv = []
    cmd_ctx = {
        "sm": sm, "llm": llm, "pm": pm, "evo": evo, "sv": sv,
        "intent": intent, "logger": logger, "state": state, "conv": conv,
        "provider_selector": provider_sel, "resource_monitor": resource_mon,
        "identity": identity,
    }

    while True:
        try:
            ui = input(f"{C.GREEN}you> {C.R}").strip()
        except (EOFError, KeyboardInterrupt):
            cpr(C.DIM, "\nBye!")
            break
        if not ui:
            continue

        # ── Commands via dispatch table ──
        if ui.startswith("/"):
            p = ui.split(maxsplit=2)
            act = p[0].lower()
            a1 = p[1] if len(p) > 1 else ""
            a2 = p[2] if len(p) > 2 else ""
            handler = COMMANDS.get(act)
            if handler:
                if handler(a1=a1, a2=a2, **cmd_ctx) == "QUIT":
                    break
            else:
                cpr(C.YELLOW, f"Unknown: {act}. /help")
            continue

        # ── Chat with context-aware IntentEngine ──
        conv.append({"role": "user", "content": ui})
        logger.core("user_msg", {"msg": ui[:200]})

        sk = sm.list_skills()
        analysis = intent.analyze(ui, sk, conv)
        logger.core("intent_result", {
            "action": analysis.get("action"), "skill": analysis.get("skill",""),
            "goal": analysis.get("goal","")})

        # Voice conversation mode: enter continuous listen loop
        if (analysis.get("action") == "use" and analysis.get("skill") == "stt"
                and analysis.get("goal") in ("voice_conversation", "enable_voice", "enable_stt")):
            _run_voice_loop(sm, evo, llm, intent, logger, conv, identity)
            _check_proactive_learning(intent)
            intent.save()
            continue

        # Show feedback before single-shot STT/TTS execution
        if analysis.get("action") == "use" and analysis.get("skill") == "stt":
            cpr(C.CYAN, "\n🎤 Nagrywam... (mów teraz)")

        outcome = evo.handle_request(ui, sk, analysis=analysis)

        # Special STT flow: feed transcription back into conversation
        if outcome and outcome.get("skill") == "stt" and outcome.get("type") == "success":
            stt_text = _extract_stt_text(outcome)
            intent.record_skill_use("stt")
            if stt_text:
                cpr(C.GREEN, f"[STT] Usłyszałem: \"{stt_text}\"")
                mprint(f"### 🎤 Usłyszałem: *{stt_text}*")
                conv.append({"role": "user", "content": f"[głosowo] {stt_text}"})
                _handle_chat(llm, sm, logger, conv, identity=identity)
            else:
                cpr(C.YELLOW, "[STT] Nie usłyszałem nic. Spróbuj mówić głośniej lub bliżej mikrofonu.")
                mprint("### 🎤 Nie usłyszałem nic\nSpróbuj powiedzieć coś głośniej lub użyj `/stt` ponownie.")
                conv.append({"role": "assistant", "content": "Nie usłyszałem nic. Spróbuj ponownie."})
        elif not _handle_outcome(outcome, intent, conv, identity=identity):
            _handle_chat(llm, sm, logger, conv, identity=identity)

        _check_proactive_learning(intent)
        intent.save()


if __name__ == "__main__":
    main()
