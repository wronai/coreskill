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
from .provider_selector import ProviderSelector, ProviderChain
from .system_identity import SystemIdentity
from .skill_logger import init_nfo
from .user_memory import UserMemory
from .garbage_collector import EvolutionGarbageCollector
from .auto_repair import AutoRepair
from .session_config import SessionConfig, ConfigChange
from .config_generator import ConfigGenerator, get_config_generator
from .voice_loop import (_extract_stt_text, _speak_tts, _run_stt_cycle,
                        _run_voice_loop, _run_file_input_loop)
from .fuzzy_router import FuzzyCommandRouter
from .event_bus import EventBus
from .adaptive_monitor import AdaptiveResourceMonitor
from .proactive_scheduler import ProactiveScheduler, setup_default_tasks
from .bandit_selector import UCB1BanditSelector


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
    # Code-only models unsuitable for Polish chat — reject if persisted in state
    _CODE_ONLY = ("deepseek-coder", "starcoder", "codellama", "codegemma",
                  "stable-code", "codestral", "codeqwen")
    models = get_models_from_config(state)
    mdl = os.environ.get("EVO_MODEL") or state.get("model") or (models[0] if models else DEFAULT_MODEL)
    mdl_lower = str(mdl).lower()
    # NOTE: 'llm' is an internal placeholder used in logs/UI; it is NOT a real LiteLLM model.
    # If it gets persisted in state, LiteLLM will throw: "LLM Provider NOT provided".
    if (not mdl) or mdl_lower in ("llm", "auto") or "stepfun" in mdl_lower or any(c in mdl_lower for c in _CODE_ONLY):
        old = mdl
        mdl = models[0] if models else DEFAULT_MODEL
        state["model"] = mdl
        save_state(state)
        if old and old != mdl:
            cpr(C.YELLOW, f"[MODEL] Odrzucono '{old}' (code-only) → {mdl}")
    return mdl, models

def _init_components(ak, mdl, models, logger, state):
    llm = LLMClient(ak, mdl, logger, models=models)
    resource_mon = ResourceMonitor()
    provider_sel = ProviderSelector(SKILLS_DIR, resource_mon)
    sm = SkillManager(llm, logger, provider_selector=provider_sel)
    pm = PipelineManager(sm, llm, logger)
    bandit = UCB1BanditSelector()
    chain = ProviderChain(provider_sel, bandit=bandit)
    evo = EvoEngine(sm, llm, logger, provider_chain=chain)
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
        
        # Handle skill creation suggestion (e.g., from web_search empty results for local network)
        suggestion = outcome.get("suggestion")
        if suggestion:
            skill_name = suggestion.get("skill_name", "?")
            desc = suggestion.get("description", "")
            reason = suggestion.get("reason", "")
            cpr(C.CYAN, f"\n💡 SUGESTIA: Brak odpowiedniego skillu!")
            cpr(C.YELLOW, f"   Powód: {reason}")
            cpr(C.GREEN, f"   Proponowany skill: '{skill_name}'")
            cpr(C.DIM, f"   Opis: {desc[:80]}")
            cpr(C.CYAN, f"   Powiedz: 'stwórz {skill_name}' aby go zbudować.")
            # Add to conversation context
            conv.append({"role": "system", "content": 
                f"System sugeruje stworzenie nowego skillu '{skill_name}' "
                f"ponieważ: {reason}. Użytkownik może powiedzieć 'stwórz {skill_name}' aby zbudować."})
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

def _handle_chat(llm, sm, logger, conv, identity=None, memory=None):
    """Generate LLM response. Returns response text (or None on error)."""
    import os as _os
    
    # Build enhanced system context with env vars and skills
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
    
    # Get skills with descriptions
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
    
    if identity:
        sp = identity.build_system_prompt()
    else:
        from datetime import datetime as _dt
        _now = _dt.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
        # Fallback prompt must still tell the LLM what integrations/skills are available.
        # IMPORTANT: never include secret VALUES, only names + whether present.
        _skills = list(sm.list_skills().keys())
        _env_candidates = [
            "OPENROUTER_API_KEY",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GOOGLE_API_KEY",
            "MOONSHOT_API_KEY",
            "OLLAMA_HOST",
            "EVO_MODEL",
            "EVO_TEXT_ONLY",
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

    # Always provide the LLM with a concise, safe snapshot of env+skills.
    # Values are masked; this is informational so the LLM knows what it can use.
    if _env_ctx:
        sp += "\n\nZMIENNE ŚRODOWISKOWE (maskowane):\n" + "\n".join(_env_ctx[:20])
        if len(_env_ctx) > 20:
            sp += f"\n  ... i {len(_env_ctx) - 20} innych"
    if _skills_info:
        sp += "\n\nSKILLS (skrót):\n" + "\n".join(_skills_info[:20])
        if len(_skills_info) > 20:
            sp += f"\n  ... i {len(_skills_info) - 20} innych"
    
    if memory:
        mem_ctx = memory.build_system_context()
        if mem_ctx:
            sp = mem_ctx + "\n\n" + sp
    
    # Add active model info to system prompt
    model_short = llm.model.split('/')[-1] if '/' in llm.model else llm.model
    sp += f"\n\n[Aktywny model: {model_short} ({llm.active_tier})]"
    
    cpr(C.DIM, f"Thinking... [{model_short}]")
    r = llm.chat([{"role": "system", "content": sp}] + conv[-20:])
    if r and "[ERROR]" in r:
        logger.core("chat_error", {"error": r[:200]})
        cpr(C.RED, f"evo> {r}")
        return None
    # Validate: detect hallucinated skill usage in LLM response
    if r:
        r = _sanitize_chat_response(r, sm, logger)
    conv.append({"role": "assistant", "content": r})
    mprint(f"**evo>** {r}\n")
    logger.core("chat_response", {"length": len(r) if r else 0})
    return r


def _sanitize_chat_response(text, sm, logger):
    """Detect and flag when LLM hallucinates skill execution in its text response.
    
    The LLM sometimes writes '✅ web_search → ...' pretending it ran a skill,
    then fabricates results. This strips those fake skill invocations and adds
    a warning so the user isn't misled.
    """
    import re as _re
    if not text:
        return text
    skill_names = set(sm.list_skills().keys()) if sm else set()
    # Pattern: ✅ skill_name → ... or skill_name → ... at line start
    # Also catches: ➡️ skill_name → ...
    _fake_patterns = []
    for sn in skill_names:
        # "✅ web_search → ..." or "✅ `web_search` → ..."
        _fake_patterns.append(
            _re.compile(r'✅\s*`?' + _re.escape(sn) + r'`?\s*→[^\n]*', _re.IGNORECASE))
        # "➡️ web_search → ..."  or  "➡️ `web_search` → ..."
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
        # Clean up leftover blank lines
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


def _cmd_health(a1, **ctx):
    """Show skill readiness/health status: /health [skill_name]"""
    sm = ctx["sm"]
    if a1:
        skills_to_check = [a1]
    else:
        skills_to_check = sorted(sm.list_skills().keys())
    for name in skills_to_check:
        r = sm.readiness_check(name)
        ok = r.get("ok", True)
        issues = r.get("issues", [])
        deps = r.get("deps", {})
        hw = r.get("hardware", {})
        res = r.get("resources", {})
        color = C.GREEN if ok else C.YELLOW
        status = "✓ OK" if ok else "⚠ PROBLEM"
        cpr(color, f"\n[{name}] {status}")
        if deps:
            dep_str = "  ".join(f"{k}={'✓' if v else '✗'}" for k, v in deps.items())
            cpr(C.DIM, f"  deps:  {dep_str}")
        for hw_k, hw_v in hw.items():
            if isinstance(hw_v, bool):
                cpr(C.DIM if hw_v else C.YELLOW, f"  hw:    {hw_k}={'✓' if hw_v else '✗'}")
            elif hw_v:
                cpr(C.DIM, f"  hw:    {hw_k}: {hw_v}")
        for res_k, res_v in res.items():
            cpr(C.DIM if res_v else C.YELLOW, f"  res:   {res_k}: {res_v or 'MISSING'}")
        for issue in issues:
            cpr(C.YELLOW, f"  ⚠  {issue}")


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


def _cmd_memories(**ctx):
    """List all persistent memory directives: /memories"""
    memory = ctx.get("memory")
    if not memory:
        cpr(C.YELLOW, "Memory not initialized.")
        return
    cpr(C.CYAN, "\n📋 Trwałe preferencje (pamięć długotrwała):")
    memory.display()
    cpr(C.DIM, "\n  /remember <tekst>  — dodaj dyrektywę")
    cpr(C.DIM, "  /forget <id>       — usuń dyrektywę")


def _cmd_remember(a1, a2, **ctx):
    """Save a directive to long-term memory: /remember <text>"""
    memory = ctx.get("memory")
    if not memory:
        cpr(C.YELLOW, "Memory not initialized.")
        return
    # a1 + a2 = full text (split by maxsplit=1 gives a1=first word, a2=rest)
    text = (a1 + (" " + a2 if a2 else "")).strip()
    if not text:
        cpr(C.YELLOW, "Użycie: /remember <tekst do zapamiętania>")
        return
    entry = memory.add(text)
    if entry:
        cpr(C.GREEN, f"✓ Zapamiętano [{entry['id']}]: {entry['text']}")
    else:
        cpr(C.DIM, "Już istnieje identyczna dyrektywa.")


def _cmd_forget(a1, **ctx):
    """Remove a directive from long-term memory: /forget <id>"""
    memory = ctx.get("memory")
    if not memory:
        cpr(C.YELLOW, "Memory not initialized.")
        return
    if not a1 or not a1.isdigit():
        cpr(C.YELLOW, "Użycie: /forget <id>  (id z /memories)")
        return
    if memory.remove(int(a1)):
        cpr(C.GREEN, f"✓ Usunięto dyrektywę #{a1}")
    else:
        cpr(C.YELLOW, f"Nie znaleziono dyrektywy #{a1}")


def _cmd_apikey(a1, a2, **ctx):
    """Set or show OpenRouter API key: /apikey [key]"""
    state = ctx["state"]
    llm = ctx["llm"]
    sm = ctx.get("sm")
    
    if not a1:
        # Show current status
        key = state.get("api_key", "")
        if key:
            masked = key[:8] + "..." + key[-4:] if len(key) > 12 else "***"
            cpr(C.GREEN, f"✓ API key ustawiony: {masked}")
            cpr(C.DIM, "   Płatne modele OpenRouter dostępne")
        else:
            cpr(C.YELLOW, "⚠ Brak API key dla OpenRouter")
            cpr(C.DIM, "   Użycie: /apikey <twój-klucz>")
            cpr(C.DIM, "   Lub ustaw zmienną: export OPENROUTER_API_KEY=...")
        return
    
    # Set new key
    key = (a1 + (" " + a2 if a2 else "")).strip()
    
    # Test API key immediately
    cpr(C.CYAN, "🔍 Testuję klucz API...")
    try:
        from skills.openrouter_api_test.v1.skill import OpenRouterAPITestSkill
        test_skill = OpenRouterAPITestSkill()
        result = test_skill.execute({"action": "test", "api_key": key})
        
        if result.get("success"):
            cpr(C.GREEN, f"✓ Klucz API poprawny! (response: {result.get('response_time_ms')}ms)")
        else:
            error_type = result.get("error_type", "unknown")
            error = result.get("error", "Unknown error")
            suggestion = result.get("suggestion", "")
            
            if error_type == "authentication":
                cpr(C.RED, f"❌ Klucz API niepoprawny: {error}")
            elif error_type == "rate_limit":
                cpr(C.YELLOW, f"⚠ Rate limit: {error}")
            elif error_type == "payment":
                cpr(C.YELLOW, f"⚠ Brak środków: {error}")
            else:
                cpr(C.YELLOW, f"⚠ Błąd API: {error}")
            
            if suggestion:
                cpr(C.DIM, f"   {suggestion}")
            
            # Ask if user wants to save anyway
            cpr(C.DIM, "   Klucz nie został zapisany. Sprawdź klucz i spróbuj ponownie.")
            return
            
    except Exception as e:
        cpr(C.YELLOW, f"⚠ Nie można przetestować klucza: {e}")
        cpr(C.DIM, "   Kontynuuję bez weryfikacji...")
    
    # Save key after successful validation
    state["api_key"] = key
    from cores.v1 import save_state
    save_state(state)
    
    # Update LLM client
    llm.api_key = key
    
    # Refresh available models in provider selector
    if sm:
        try:
            # Force refresh of model lists
            llm._tiers["paid"] = llm._load_paid_models()
            cpr(C.DIM, f"   Znaleziono {len(llm._tiers.get('paid', []))} płatnych modeli")
        except Exception as e:
            cpr(C.DIM, f"   Nie można odświeżyć listy modeli: {e}")
    
    cpr(C.GREEN, "✓ API key zapisany i zweryfikowany")
    cpr(C.DIM, "   Płatne modele OpenRouter są teraz dostępne")
    cpr(C.DIM, "   Użyj /autotune lub /models aby zobaczyć dostępne modele")


def _cmd_autotune(a1, **ctx):
    """Auto-tune: benchmark models with LIVE tests and select optimal: /autotune [goal] [profile] [--static]"""
    from skills.benchmark.v1.skill import execute as benchmark_execute

    llm = ctx["llm"]
    state = ctx["state"]
    logger = ctx["logger"]
    api_key = state.get("openrouter_api_key", "")

    # Parse args - support: /autotune [goal] [profile] [--static]
    args = (a1 or "").split()
    goal = "coding"
    profile = "balanced"
    use_static = False  # Default is LIVE benchmark
    
    valid_profiles = ["fastest", "best_quality", "ignore_cost", "free_only", "balanced", "large_context"]
    valid_goals = ["coding", "chat", "reasoning", "summarization", "creative", "general"]
    
    for arg in args:
        if arg.startswith("--"):
            if arg == "--static":
                use_static = True
        elif arg in valid_profiles:
            profile = arg
        elif arg in valid_goals:
            goal = arg
        elif arg:
            goal = arg

    cpr(C.CYAN, f"🔬 Auto-tune: LIVE benchmark dla celu '{goal}' [profile: {profile}]...")
    if use_static:
        cpr(C.DIM, "   (static mode - fast but less accurate)")
    else:
        cpr(C.DIM, "   (live mode - testing real latency/quality via API)")

    if use_static:
        # Static benchmark (fast, hardcoded scores)
        result = benchmark_execute({
            "action": "recommend",
            "goal": goal,
            "budget": "any",
            "profile": profile,
            "limit": 5
        })
    else:
        # LIVE benchmark with real API calls - the default
        # Check if API key is available
        if not api_key:
            cpr(C.YELLOW, "⚠️ Brak API key - używam statycznego benchmarku")
            result = benchmark_execute({
                "action": "recommend",
                "goal": goal,
                "budget": "any",
                "profile": profile,
                "limit": 5
            })
        else:
            result = benchmark_execute({
                "action": "recommend_live",
                "goal": goal,
                "budget": "any",
                "profile": profile,
                "limit": 5,
                "api_key": api_key,
            })

    if not result.get("success"):
        cpr(C.RED, f"❌ Benchmark nie powiódł się: {result.get('error', 'unknown')}")
        return

    # Show profile description if available
    profile_desc = result.get("profile_description", "")
    if profile_desc:
        cpr(C.DIM, f"   Profil: {profile_desc}")

    # Handle results (both live and static use same format now)
    recommendations = result.get("recommendations", [])
    if not recommendations:
        cpr(C.YELLOW, "⚠️ Brak rekomendacji z benchmark")
        return

    is_live = result.get("live_tested", False) or not use_static
    
    if is_live:
        cpr(C.GREEN, f"\n📊 LIVE benchmark dla '{goal}' (rzeczywiste testy API):")
    else:
        cpr(C.GREEN, f"\n📊 Statyczny benchmark dla '{goal}':")
    
    for r in recommendations[:3]:
        model_short = r['model_id'].split('/')[-1]
        tier = r['tier']
        marker = "★" if r['rank'] == 1 else " "
        lat_info = f", lat={r.get('avg_latency_ms', 'N/A'):.0f}ms" if 'avg_latency_ms' in r else ""
        cpr(C.DIM if r['rank'] > 1 else C.GREEN,
            f"{marker} {r['rank']}. {model_short} (score: {r['overall_score']}) [{tier}]{lat_info}")

    best = recommendations[0]
    best_model = best['model_id']

    cpr(C.CYAN, f"\n🏆 Najlepszy model: {best_model.split('/')[-1]}")

    # Check if different from current
    current = llm.model
    if best_model == current:
        cpr(C.GREEN, "✅ Aktualny model jest już optymalny")
        return

    # Auto-switch
    cpr(C.CYAN, f"\n🔄 Przełączam na {best_model.split('/')[-1]}...")

    # Determine tier
    best_tier = "paid"
    if ":free" in best_model:
        best_tier = "free"
    elif best_model.startswith("ollama/"):
        best_tier = "local"

    # Update LLM client
    llm.model = best_model
    llm.active_tier = best_tier

    # Update state
    state["model"] = best_model
    state["model_tier"] = best_tier
    save_state(state)

    logger.core("autotune_switch", {
        "from": current,
        "to": best_model,
        "goal": goal,
        "profile": profile,
        "score": best.get('overall_score'),
        "live_mode": not use_static
    })

    cpr(C.GREEN, f"✅ Model zmieniony na: {best_model.split('/')[-1]}")
    cpr(C.DIM, f"   Poprzedni: {current.split('/')[-1]}")


def _cmd_config(a1, **ctx):
    """Show or modify session configuration."""
    session_cfg = ctx.get("session_config")
    if not session_cfg:
        cpr(C.YELLOW, "SessionConfig not available")
        return
    
    if not a1:
        # Show current session config
        cpr(C.CYAN, session_cfg.get_session_summary())
        return
    
    # Parse config command: /config <category> <setting> <value>
    parts = a1.split(maxsplit=2)
    if len(parts) < 2:
        cpr(C.YELLOW, "Usage: /config <category> <setting> [value]  (e.g., /config tts provider coqui)")
        return
    
    category = parts[0]
    setting = parts[1]
    value = parts[2] if len(parts) > 2 else ""
    
    # Handle special values
    if value.lower() in ("true", "on", "enable", "włącz"):
        value = True
    elif value.lower() in ("false", "off", "disable", "wyłącz", "wyłacz"):
        value = False
    
    change = session_cfg.set(category, setting, value)
    feedback = session_cfg.format_change_feedback(change)
    cpr(C.CYAN, feedback)


def _cmd_reload_config(**ctx):
    """Reload system configuration from config/system.json without restart: /reload_config"""
    from .config import reload_system_config, get_config_value
    
    cpr(C.CYAN, "🔄 Przeładowuję konfigurację z config/system.json...")
    
    # Reload the config
    config = reload_system_config()
    
    # Show what changed - check defaults for TTS/STT
    tts_default = get_config_value("defaults.tts", "?")
    stt_default = get_config_value("defaults.stt", "?")
    
    cpr(C.GREEN, "✓ Konfiguracja przeładowana!")
    cpr(C.DIM, f"   defaults.tts: {tts_default}")
    cpr(C.DIM, f"   defaults.stt: {stt_default}")
    
    # Note: running system components may need restart to pick up all changes
    cpr(C.YELLOW, "\n⚠️  Uwaga: Niektóre komponenty mogą wymagać restartu systemu")
    cpr(C.DIM, "   aby w pełni zastosować zmiany (np. ProviderSelector cache)")
    
    ctx["logger"].core("config_reloaded", {
        "tts_default": tts_default,
        "stt_default": stt_default
    })


def _cmd_reflect(a1, **ctx):
    """Run self-reflection diagnostic: /reflect [skill_name]"""
    from .self_reflection import SelfReflection
    
    llm = ctx["llm"]
    sm = ctx["sm"]
    logger = ctx["logger"]
    state = ctx["state"]
    
    skill_name = a1 if a1 else ""
    
    cpr(C.CYAN, f"\n[REFLECT] Uruchamiam autorefleksję systemu...")
    if skill_name:
        cpr(C.DIM, f"[REFLECT] Fokus na skill: {skill_name}")
    
    # Create reflection instance
    reflection = SelfReflection(llm, sm, logger, state)
    
    # Run diagnostic
    report = reflection.run_diagnostic(skill_name, specific_error="")
    
    # Try auto-fix if possible and user wants it
    if report.auto_fixable:
        cpr(C.CYAN, "\n[REFLECT] Próbuję automatycznych napraw...")
        fixes = reflection.attempt_auto_fix(report)
        if fixes:
            cpr(C.GREEN, "\n[REFLECT] Wykonane naprawy:")
            for fix in fixes:
                cpr(C.GREEN, f"  ✓ {fix}")
        else:
            cpr(C.YELLOW, "[REFLECT] Nie udało się automatycznie naprawić")
    
    # Show summary
    cpr(C.DIM, f"\n[REFLECT] Podsumowanie: {reflection.get_summary()}")


def _cmd_hw(a1, **ctx):
    """Hardware diagnostics: /hw [full|audio_input|audio_output|audio_loop|devices|drivers|pulse|usb|skill_hw]"""
    from skills.hw_test.v1.skill import HWTestSkill
    import json as _json
    
    action = a1.strip().lower() if a1 else "full"
    cpr(C.CYAN, f"\n🔧 Diagnostyka sprzętowa [{action}]...")
    
    hw = HWTestSkill()
    result = hw.execute({"action": action})
    
    # Pretty-print results
    ok = result.get("ok", result.get("success", False))
    cpr(C.GREEN if ok else C.RED,
        f"\n{'✓' if ok else '✗'} Wynik: {'OK' if ok else 'PROBLEMY'}")
    
    # Show test results for full test
    tests = result.get("tests", {})
    if tests:
        for name, data in tests.items():
            tok = data.get("ok", False)
            cpr(C.GREEN if tok else C.YELLOW,
                f"  {'✓' if tok else '✗'} {name}")
            for issue in data.get("issues", []):
                cpr(C.YELLOW, f"      ⚠ {issue}")
            for rec in data.get("recommendations", []):
                cpr(C.DIM, f"      → {rec}")
    
    # Show issues for single tests
    issues = result.get("issues", [])
    for issue in issues:
        cpr(C.YELLOW, f"  ⚠ {issue}")
    recommendations = result.get("recommendations", [])
    for rec in recommendations:
        cpr(C.DIM, f"  → {rec}")
    
    # Show devices if present
    devices = result.get("devices", result.get("capture_devices", []))
    if devices:
        cpr(C.DIM, f"\n  Urządzenia ({len(devices)}):")
        for d in devices[:10]:
            dtype = d.get("type", "")
            dname = d.get("name", d.get("raw", "?"))
            direction = d.get("direction", "")
            if len(dname) > 80:
                dname = dname[:80] + "..."
            cpr(C.DIM, f"    [{dtype}] {dname} ({direction})")
    
    # Show summary
    summary = result.get("summary", {})
    if isinstance(summary, dict) and "passed" in summary:
        cpr(C.CYAN, f"\n  Podsumowanie: {summary['passed']} ✓ / {summary['failed']} ✗ / {summary.get('warnings', 0)} ⚠")
    
    # Log
    ctx["logger"].core("hw_test", {"action": action, "ok": ok})


def _cmd_repairs(a1, **ctx):
    """Show repair journal: /repairs [skill_name]"""
    from .repair_journal import RepairJournal
    journal = RepairJournal(llm_client=ctx["llm"])
    cpr(C.CYAN, journal.format_report(skill_name=a1 if a1 else ""))


def _cmd_snapshot(a1, a2, **ctx):
    """Manage stable snapshots: /snapshot [save|restore|branch|list|compare] [skill]"""
    from .stable_snapshot import StableSnapshot
    snap = StableSnapshot(skill_manager=ctx["sm"], logger=ctx["logger"])
    
    action = (a1 or "").lower()
    skill = a2 or ""
    
    if action == "save" and skill:
        snap.save_as_stable(skill)
    elif action == "restore" and skill:
        snap.restore_stable(skill)
    elif action == "branch" and skill:
        branch_type = "bugfix"  # default
        snap.create_branch(skill, branch_type=branch_type)
    elif action == "compare" and skill:
        result = snap.validate_against_stable(skill)
        cpr(C.CYAN, f"Porównanie {skill} vs stable:")
        for k, v in result.items():
            cpr(C.DIM, f"  {k}: {v}")
    elif action == "list" and skill:
        branches = snap.list_branches(skill)
        if branches:
            cpr(C.CYAN, f"Branching {skill}:")
            for b in branches:
                cpr(C.DIM, f"  {b['name']} ({b['type']}) — {b['health']}")
        else:
            cpr(C.DIM, f"Brak branchy dla {skill}")
    else:
        cpr(C.YELLOW, "Usage: /snapshot save|restore|branch|compare|list <skill_name>")


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
    "/chain": _cmd_chain,
    "/gc": _cmd_gc,
    "/resources": _cmd_resources,
    "/stt": _cmd_stt,
    "/fix": _cmd_fix,
    "/voice": _cmd_voice,
    "/health": _cmd_health,
    "/memories": _cmd_memories,
    "/remember": _cmd_remember,
    "/forget": _cmd_forget,
    "/apikey": _cmd_apikey,
    "/autotune": _cmd_autotune,
    "/benchmark": _cmd_autotune,
    "/journal": lambda **ctx: cpr(C.CYAN, ctx["evo"].journal.format_report()),
    "/config": _cmd_config,
    "/reload_config": _cmd_reload_config,
    "/reflect": _cmd_reflect,
    "/repairs": _cmd_repairs,
    "/snapshot": _cmd_snapshot,
    "/hw": _cmd_hw,
    "/hwtest": _cmd_hw,
}


# ─── Boot sequence ────────────────────────────────────────────────────
def _boot():
    """Initialize all components. Returns (cmd_ctx, conv, memory) tuple."""
    # init_nfo()  # DISABLED: may interfere with stdout in subprocess

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

    # Ensure all config files exist (generate missing ones via LLM)
    cfg_gen = get_config_generator(llm_client=llm)
    cfg_gen.ensure_config_files()

    # Startup: auto-repair (GC + skill fixes + model validation)
    repairer = AutoRepair(skill_manager=sm, logger=logger, identity=identity)
    repair_report = repairer.run_boot_repair()

    # Refresh identity after repairs
    identity.refresh_statuses()
    report = identity.get_readiness_report()
    if report["broken"]:
        cpr(C.YELLOW, f"Nadal uszkodzone: {', '.join(report['broken'])}")

    # Multi-level readiness check (deps/hw/api/resources)
    # Skip in text-only mode (EVO_TEXT_ONLY=1)
    if not os.environ.get("EVO_TEXT_ONLY"):
        sm.boot_health_check()
    else:
        cpr(C.DIM, "[Text-only mode: skipping audio health checks]")

    # Long-term user memory
    memory = UserMemory(state)
    if memory.directives:
        cpr(C.CYAN, f"📋 Pamięć: {len(memory.directives)} dyrektywa(y) aktywna. /memories aby zobaczyć.")

    # Session configuration layer (user-facing, hot-swappable)
    session_cfg = SessionConfig(llm_client=llm, provider_selector=provider_sel)
    cpr(C.DIM, "SessionConfig: gotowy do zmian konfiguracji w locie")

    # Self-reflection system for auto-diagnosis on failures/stalls
    from .self_reflection import SelfReflection
    reflection = SelfReflection(llm, sm, logger, state)
    evo.set_reflection(reflection)

    # Event bus: decouple AutoRepair ↔ EvoEngine ↔ SelfReflection
    bus = EventBus()
    bus.wire(reflection=reflection, repairer=repairer, evo=evo, logger=logger)
    cpr(C.DIM, f"SelfReflection: aktywny | EventBus: {'wired' if bus.is_active else 'fallback'}")

    # Adaptive resource monitor (EWMA trend detection)
    adaptive_mon = AdaptiveResourceMonitor()
    adaptive_mon.start(interval=5.0)

    # Proactive scheduler (periodic GC, health checks, resource alerts)
    scheduler = ProactiveScheduler()
    gc = EvolutionGarbageCollector()
    setup_default_tasks(scheduler, adaptive_monitor=adaptive_mon, gc=gc,
                        skill_manager=sm, logger=logger)
    scheduler.start()
    cpr(C.DIM, f"AdaptiveMonitor: aktywny | Scheduler: {len(scheduler.status())} zadań")

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
    router = FuzzyCommandRouter(COMMANDS)
    cmd_ctx = {
        "sm": sm, "llm": llm, "pm": pm, "evo": evo, "sv": sv,
        "intent": intent, "logger": logger, "state": state, "conv": conv,
        "provider_selector": provider_sel, "resource_monitor": resource_mon,
        "identity": identity, "memory": memory, "session_config": session_cfg,
        "router": router, "adaptive_monitor": adaptive_mon, "scheduler": scheduler,
    }
    return cmd_ctx, conv, memory


# ─── Chat loop intent handlers ───────────────────────────────────────
def _handle_configure_intent(analysis, session_cfg, conv, state, llm, sm, intent):
    """Handle CONFIGURE intent (session configuration changes). Returns True if handled."""
    if analysis.get("action") != "configure":
        return False

    if analysis.get("_fallback"):
        cpr(C.YELLOW, "[FALLBACK] Niejasna konfiguracja → domyślnie LLM (brak kontekstu głosowego)")

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
        mprint(f"### 🎤 Usłyszałem: *{stt_text}*")
        conv.append({"role": "user", "content": f"[głosowo] {stt_text}"})
        response = _handle_chat(llm, sm, logger, conv, identity=identity, memory=memory)
        if response:
            _speak_tts(sm, evo, response)
    else:
        cpr(C.YELLOW, "[STT] Nie usłyszałem nic po 2 próbach. Sprawdź mikrofon.")
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


# ─── Main ────────────────────────────────────────────────────────────
def main():
    # Setup signal handlers for graceful shutdown
    import signal
    _shutdown_requested = False
    _in_voice_mode = False
    
    def _signal_handler(signum, frame):
        nonlocal _shutdown_requested, _in_voice_mode
        if not _shutdown_requested:
            if _in_voice_mode:
                # In voice mode: just print message, don't exit - voice loop will handle KeyboardInterrupt
                cpr(C.DIM, f"\n[SIGNAL] {signal.Signals(signum).name} — wychodzę z trybu głosowego...")
                return  # Don't raise SystemExit, let voice loop catch KeyboardInterrupt
            _shutdown_requested = True
            cpr(C.DIM, f"\n[SIGNAL] Received {signal.Signals(signum).name}, shutting down gracefully...")
            # Save any pending state
            try:
                if 'intent' in dir():
                    intent.save()
                if 'logger' in dir():
                    logger.core("shutdown", {"reason": "signal", "signum": signum})
            except Exception:
                pass
        raise SystemExit(0)
    
    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)
    
    cmd_ctx, conv, memory = _boot()
    sm, llm, evo, intent, logger = (
        cmd_ctx["sm"], cmd_ctx["llm"], cmd_ctx["evo"],
        cmd_ctx["intent"], cmd_ctx["logger"])
    state = cmd_ctx["state"]
    identity = cmd_ctx["identity"]
    session_cfg = cmd_ctx["session_config"]

    # Auto-enter voice mode if persistent preference is saved (but not in text-only mode)
    if memory and memory.voice_mode and not os.environ.get("EVO_TEXT_ONLY"):
        cpr(C.CYAN, "🔊 Tryb głosowy aktywny (zapamiętana preferencja). "
                    "Wyłącz: /voice off")
        _in_voice_mode = True
        _run_voice_loop(sm, evo, llm, intent, logger, conv, identity, memory=memory)
        _in_voice_mode = False
        cpr(C.CYAN, "📝 Przechodzę do trybu tekstowego. Wpisz /voice aby wrócić do głosowego.")

    while True:
        try:
            # Explicitly print and flush prompt for non-tty stdout (pipes)
            print(f"{C.GREEN}you> {C.R}", end='', flush=True)
            ui = input().strip()
        except (EOFError, KeyboardInterrupt):
            cpr(C.DIM, "\nBye!")
            break
        if not ui:
            continue

        # ── Commands via fuzzy dispatch table ──
        if ui.startswith("/"):
            p = ui.split(maxsplit=2)
            act = p[0].lower()
            a1 = p[1] if len(p) > 1 else ""
            a2 = p[2] if len(p) > 2 else ""
            handler, _ = cmd_ctx["router"].resolve(act)
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

        if _handle_configure_intent(analysis, session_cfg, conv, state, llm, sm, intent):
            continue

        if _handle_voice_intent(analysis, sm, evo, llm, intent, logger, conv, identity, memory):
            continue

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


if __name__ == "__main__":
    main()
