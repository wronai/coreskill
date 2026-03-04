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
from .voice_loop import (_extract_stt_text, _speak_tts, _run_stt_cycle,
                        _run_voice_loop, _run_file_input_loop, _run_stt_autotest)
from .stt_autotest import STTAutoTestPipeline, TestContext, TestResult, run_stt_autotest
from .self_reflection import SelfReflection, ReflectionEvent, DiagnosisReport
from .repair_journal import RepairJournal, RepairAttempt, KnownFix
from .stable_snapshot import StableSnapshot, SnapshotInfo
from .fuzzy_router import FuzzyCommandRouter
from .event_bus import EventBus
from .adaptive_monitor import AdaptiveResourceMonitor
from .proactive_scheduler import ProactiveScheduler
from .learned_repair import LearnedRepairStrategy, TieredRepair
from .autonomy_loop import AutonomyLoop, LoopCycleResult
from .bandit_selector import UCB1BanditSelector
from .resilience import retry_llm, retry_skill, retry_io, with_retry, get_struct_logger
from .quality_gate import SkillQualityGate, QualityReport
from .skill_validator import SkillValidator, ValidationResult
from .base_skill import BaseSkill, SkillManifest, generate_scaffold, generate_manifest_yaml, InputField
from .skill_forge import SkillForge, ErrorBudget, SkillMatch, is_conversational
from .i18n import (
    EUROPEAN_LANGUAGES, normalize_diacritics, detect_language, match_any_keyword,
    ALL_TTS_KEYWORDS, ALL_STT_KEYWORDS, ALL_SEARCH_KEYWORDS, ALL_SHELL_KEYWORDS,
    ALL_CREATE_KEYWORDS, ALL_EVOLVE_KEYWORDS, ALL_CONFIGURE_KEYWORDS,
    ALL_TRIVIAL_WORDS, ALL_ACTION_VERBS,
)
from .skill_schema import (
    SKILL_MANIFEST_SCHEMA,
    SKILL_OUTPUT_SCHEMA,
    SKILL_INTERFACE_SCHEMA,
    ValidationResult as SchemaValidationResult,
    SkillSchemaValidator,
    BlueprintRegistry,
    validate_manifest_file,
    generate_skill_manifest,
    get_schema_validation_stats,
)
from .metrics_collector import (
    MetricsCollector,
    SkillMetric,
    OperationMetric,
    SystemHealthSnapshot,
    get_collector,
    record_skill_execution,
    record_operation,
    get_skill_health,
    get_system_health_summary,
    compute_and_save_system_health,
)
from .reflection_engine import (
    ReflectionRuleEngine,
    ProactiveReflection,
    SystemState,
    RuleMatch,
    get_rule_engine,
    evaluate_reflection_rules,
    run_reflection_cycle,
)
from .drift_detector import (
    DriftDetector,
    DriftReport,
    detect_drift,
    detect_all_drift,
    get_drift_summary,
)
