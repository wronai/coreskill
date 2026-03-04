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
    load_state, save_state, get_models_from_config, get_config_value, get_system_config,
)
from .utils import litellm, mprint, HAS_RICH, clean_code, clean_json, _clean, _clean_json
from .logger import Logger
from .llm_client import LLMClient, _detect_ollama_models, discover_models
from .intent_engine import IntentEngine
from .skill_manager import SkillManager, _load_bootstrap_skill
from .evo_engine import EvoEngine, FailureTracker
from .pipeline_manager import PipelineManager
from .supervisor import Supervisor
from .resource_monitor import ResourceMonitor
from .provider_selector import ProviderSelector, ProviderChain
from .system_identity import SystemIdentity, SkillStatus
from .preflight import SkillPreflight, EvolutionGuard, PreflightResult
from .skill_logger import init_nfo, inject_logging, get_skill_logger
from .user_memory import UserMemory
from .smart_intent import SmartIntentClassifier as _SIC_compat

# New intent package exports (preferred)
from .intent import (
    SmartIntentClassifier,
    IntentResult,
    create_smart_classifier,
    EmbeddingEngine,
    LocalLLMClassifier,
    DEFAULT_TRAINING,
)
from .garbage_collector import EvolutionGarbageCollector
from .evo_journal import EvolutionJournal
from .auto_repair import AutoRepair, RepairTask
from .session_config import SessionConfig, ConfigChange
from .config_generator import ConfigGenerator, get_config_generator
from .voice_loop import _extract_stt_text, _speak_tts, _run_stt_cycle, _run_voice_loop, _run_stt_autotest
from .stt_autotest import STTAutoTestPipeline, TestContext, TestResult, run_stt_autotest
from .self_reflection import SelfReflection, ReflectionEvent, DiagnosisReport
from .repair_journal import RepairJournal, RepairAttempt, KnownFix
from .stable_snapshot import StableSnapshot, SnapshotInfo
from .fuzzy_router import FuzzyCommandRouter
