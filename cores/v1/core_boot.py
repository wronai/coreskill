#!/usr/bin/env python3
"""core_boot.py — System initialization and boot sequence.

Extracted from core.py to reduce CC (74 → ~15 per module).
Handles: component initialization, health checks, auto-repair, scheduler setup.
"""
import os
import sys
import json
from datetime import datetime, timezone, timedelta

from .config import (
    ROOT, SKILLS_DIR, C, cpr,
    load_state, save_state, get_models_from_config,
)
from .utils import mprint
from .logger import Logger
from .llm_client import LLMClient, _detect_ollama_models, discover_models
from .skill_manager import SkillManager
from .pipeline_manager import PipelineManager
from .supervisor import Supervisor
from .resource_monitor import ResourceMonitor
from .provider_selector import ProviderSelector, ProviderChain
from .system_identity import SystemIdentity
from .user_memory import UserMemory
from .garbage_collector import EvolutionGarbageCollector
from .auto_repair import AutoRepair
from .session_config import SessionConfig
from .config_generator import get_config_generator
from .fuzzy_router import FuzzyCommandRouter
from .event_bus import EventBus
from .adaptive_monitor import AdaptiveResourceMonitor
from .proactive_scheduler import ProactiveScheduler, setup_default_tasks
from .bandit_selector import UCB1BanditSelector
from .metrics_collector import MetricsCollector
from .drift_detector import DriftDetector
from .autonomy_loop import AutonomyLoop


def _check_restart_loop(state):
    """Detect restart loops (crashing within 5 minutes)."""
    if state.get("last_reset"):
        lr = datetime.fromisoformat(state["last_reset"])
        if datetime.now(timezone.utc) - lr < timedelta(minutes=5):
            cpr(C.RED, "\n=== RESTART LOOP DETECTED ===")
            cpr(C.YELLOW, "Check your API key: https://openrouter.ai/keys")
            cpr(C.RED, "Exiting. Fix the issue and run again.")
            sys.exit(1)


def _ensure_api_key(state):
    """Ensure OpenRouter API key is available."""
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
    """Resolve model with validation (reject code-only models)."""
    _CODE_ONLY = ("deepseek-coder", "starcoder", "codellama", "codegemma",
                  "stable-code", "codestral", "codeqwen")
    models = get_models_from_config(state)
    mdl = os.environ.get("EVO_MODEL") or state.get("model") or (models[0] if models else "")
    mdl_lower = str(mdl).lower()
    # Reject invalid models
    if (not mdl) or mdl_lower in ("llm", "auto") or "stepfun" in mdl_lower or any(c in mdl_lower for c in _CODE_ONLY):
        old = mdl
        mdl = models[0] if models else "openrouter/meta-llama/llama-3.3-70b-instruct:free"
        state["model"] = mdl
        save_state(state)
        if old and old != mdl:
            cpr(C.YELLOW, f"[MODEL] Odrzucono '{old}' (code-only) → {mdl}")
    return mdl, models


def _init_components(ak, mdl, models, logger, state):
    """Initialize all system components."""
    from .llm_client import LLMClient
    from .resource_monitor import ResourceMonitor
    from .provider_selector import ProviderSelector, ProviderChain
    from .skill_manager import SkillManager
    from .pipeline_manager import PipelineManager
    from .bandit_selector import UCB1BanditSelector
    from .evo_engine import EvoEngine
    from .intent_engine import IntentEngine
    from .system_identity import SystemIdentity

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


def boot():
    """Initialize all components. Returns (cmd_ctx, conv, memory) tuple."""
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

    # Ensure all config files exist
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

    # Multi-level readiness check
    if not os.environ.get("EVO_TEXT_ONLY"):
        sm.boot_health_check()
    else:
        cpr(C.DIM, "[Text-only mode: skipping audio health checks]")

    # Long-term user memory
    memory = UserMemory(state)
    if memory.directives:
        cpr(C.CYAN, f"📋 Pamięć: {len(memory.directives)} dyrektywa(y) aktywna. /memories aby zobaczyć.")

    # Session configuration layer
    session_cfg = SessionConfig(llm_client=llm, provider_selector=provider_sel)
    cpr(C.DIM, "SessionConfig: gotowy do zmian konfiguracji w locie")

    # Self-reflection system for auto-diagnosis on failures/stalls
    from .self_reflection import SelfReflection
    reflection = SelfReflection(llm, sm, logger, state)
    evo.set_reflection(reflection)

    # Metrics collector
    metrics = MetricsCollector()

    # Event bus: decouple components
    bus = EventBus()
    bus.wire(
        reflection=reflection,
        repairer=repairer,
        evo=evo,
        metrics=metrics,
        quality_gate=sm.quality_gate,
        logger=logger,
    )
    cpr(C.DIM, f"SelfReflection: aktywny | EventBus: {bus.subscriber_count} subscribers")

    # Adaptive resource monitor (EWMA trend detection)
    adaptive_mon = AdaptiveResourceMonitor()
    adaptive_mon.start(interval=5.0)

    # Drift detector (manifest vs runtime state)
    drift = DriftDetector()

    # Proactive scheduler (periodic GC, health checks, resource alerts, drift, quality)
    scheduler = ProactiveScheduler()
    gc = EvolutionGarbageCollector()
    setup_default_tasks(scheduler, adaptive_monitor=adaptive_mon, gc=gc,
                        skill_manager=sm, logger=logger)

    # Additional autonomy tasks
    def _drift_scan():
        """Periodic drift detection across all capabilities."""
        try:
            caps = [d.name for d in SKILLS_DIR.iterdir()
                    if d.is_dir() and not d.name.startswith(".")]
            drifted = []
            for cap in caps:
                report = drift.detect(cap)
                if report.drift_detected:
                    drifted.append(cap)
            if drifted:
                cpr(C.YELLOW, f"[DRIFT] Wykryto drift w: {', '.join(drifted)}")
                if logger:
                    logger.core("scheduled_drift", {"drifted": drifted})
        except Exception:
            pass

    def _quality_regression_check():
        """Periodic quality regression scan on all skills."""
        try:
            regressions = []
            for name in list(sm.list_skills().keys()):
                p = sm.skill_path(name)
                if not p or not p.exists():
                    continue
                meta_file = p.parent / "meta.json"
                if meta_file.exists():
                    meta = json.loads(meta_file.read_text())
                    if meta.get("is_regression"):
                        regressions.append(name)
            if regressions:
                cpr(C.YELLOW, f"[QUALITY] Regresje: {', '.join(regressions)}")
                if logger:
                    logger.core("scheduled_quality_regression", {"skills": regressions})
        except Exception:
            pass

    scheduler.register("drift_scan", _drift_scan, interval_s=600)
    scheduler.register("quality_regression", _quality_regression_check, interval_s=1800)

    # Autonomy loop: closed-loop diagnostics → repair → metrics → events
    from .self_healing.diagnostics import DiagnosticEngine
    diag_engine = DiagnosticEngine(llm_client=llm, skill_manager=sm, logger=logger)
    autonomy = AutonomyLoop(
        diagnostics=diag_engine,
        repairer=repairer,
        metrics=metrics,
        event_bus=bus,
        logger=logger,
        skill_manager=sm,
    )
    scheduler.register("autonomy_cycle", autonomy.scheduled_cycle, interval_s=300)

    scheduler.start()
    cpr(C.DIM, f"AdaptiveMonitor: aktywny | Scheduler: {len(scheduler.status())} zadań | AutonomyLoop: aktywny")

    cpr(C.DIM, f"Model: {llm.model} | Core: {sv.active()} | Tiers: {llm.tier_info()}")
    sk = sm.list_skills()
    if sk:
        cpr(C.GREEN, f"Skills: {', '.join(sk.keys())}")
    else:
        cpr(C.YELLOW, "No skills yet. Chat or /create <n>")

    from .core_dispatch import QUICK_HELP
    cpr(C.DIM, QUICK_HELP.strip("\n"))

    caps_with_providers = [c for c in provider_sel.list_capabilities()
                           if len(provider_sel.list_providers(c)) > 1]
    if caps_with_providers:
        cpr(C.DIM, f"Multi-provider skills: {', '.join(caps_with_providers)}")

    cpr(C.DIM, "/help for commands\n")
    logger.core("boot", {"model": llm.model, "tier": llm.active_tier,
                          "tiers": llm.tier_info(), "skills": list(sk.keys())})

    conv = []
    from .core_dispatch import get_commands
    router = FuzzyCommandRouter(get_commands())
    cmd_ctx = {
        "sm": sm, "llm": llm, "pm": pm, "evo": evo, "sv": sv,
        "intent": intent, "logger": logger, "state": state, "conv": conv,
        "provider_selector": provider_sel, "resource_monitor": resource_mon,
        "identity": identity, "memory": memory, "session_config": session_cfg,
        "router": router, "adaptive_monitor": adaptive_mon, "scheduler": scheduler,
        "autonomy": autonomy,
    }
    return cmd_ctx, conv, memory
