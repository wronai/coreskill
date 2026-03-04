#!/usr/bin/env python3
"""
evo-engine Core v1 — modular package.
Exports main() for bootstrap compatibility.
"""
from .config import (
    ROOT, SKILLS_DIR, PIPELINES_DIR, LOGS_DIR, STATE_FILE,
    MAX_EVO_ITERATIONS, C, cpr,
    TIER_FREE, TIER_LOCAL, TIER_PAID,
    FREE_MODELS, LOCAL_PREFERRED, PAID_MODELS, MODELS, DEFAULT_MODEL,
    COOLDOWN_RATE_LIMIT, COOLDOWN_TIMEOUT, COOLDOWN_SERVER_ERR,
    load_state, save_state, get_models_from_config,
)
from .utils import litellm, mprint, HAS_RICH, clean_code, clean_json, _clean, _clean_json
from .logger import Logger
from .llm_client import LLMClient, _detect_ollama_models, discover_models
from .intent_engine import IntentEngine
from .skill_manager import SkillManager, _load_bootstrap_skill
from .evo_engine import EvoEngine
from .pipeline_manager import PipelineManager
from .supervisor import Supervisor
from .resource_monitor import ResourceMonitor
from .provider_selector import ProviderSelector, ProviderChain
from .system_identity import SystemIdentity, SkillStatus
from .preflight import SkillPreflight, EvolutionGuard, PreflightResult
from .skill_logger import init_nfo, inject_logging, get_skill_logger
from .user_memory import UserMemory
from .smart_intent import SmartIntentClassifier
from .garbage_collector import EvolutionGarbageCollector
from .auto_repair import AutoRepair, RepairTask
