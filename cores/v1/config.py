#!/usr/bin/env python3
"""
evo-engine config — state management, constants, paths.
"""
import os
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent.parent
SKILLS_DIR = ROOT / "skills"
PIPELINES_DIR = ROOT / "pipelines"
LOGS_DIR = ROOT / "logs"
STATE_FILE = ROOT / ".evo_state.json"
CONFIG_FILE = ROOT / "config" / "models.json"
SYSTEM_CONFIG_FILE = ROOT / "config" / "system.json"

# Load system configuration
_SYSTEM_CONFIG = None

def _load_system_config():
    """Load system-wide configuration from config/system.json"""
    global _SYSTEM_CONFIG
    if _SYSTEM_CONFIG is not None:
        return _SYSTEM_CONFIG
        
    if SYSTEM_CONFIG_FILE.exists():
        try:
            with open(SYSTEM_CONFIG_FILE, 'r') as f:
                _SYSTEM_CONFIG = json.load(f)
                return _SYSTEM_CONFIG
        except Exception as e:
            print(f"[Config] Error loading {SYSTEM_CONFIG_FILE}: {e}")
    
    # Fallback defaults
    _SYSTEM_CONFIG = {
        "limits": {"max_evo_iterations": 5},
        "cooldowns": {"rate_limit": 60, "demotion": 300},
        "llm": {
            "default_temperature": 0.7,
            "default_max_tokens": 4096,
            "intent_temperature": 0.3
        },
        "filters": {
            "code_model_patterns": [
                "deepseek-coder", "starcoder", "codellama", 
                "codegemma", "qwen2.5-coder"
            ]
        }
    }
    return _SYSTEM_CONFIG

def reload_system_config():
    """Force reload system configuration from disk (for hot-reload)."""
    global _SYSTEM_CONFIG
    _SYSTEM_CONFIG = None
    return _load_system_config()

# Getters for system config
def get_system_config():
    """Get full system configuration"""
    return _load_system_config()

def get_config_value(key_path, default=None):
    """Get config value by dot-path (e.g., 'limits.max_evo_iterations')"""
    config = _load_system_config()
    keys = key_path.split('.')
    value = config
    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return default
    return value

def get_code_model_patterns():
    """Get patterns for code-only models that should be excluded from chat"""
    models_config = _load_model_config()
    # First check models.json
    if "code_models" in models_config and "patterns" in models_config["code_models"]:
        return models_config["code_models"]["patterns"]
    # Fallback to system.json
    return get_config_value("filters.code_model_patterns", [])

# Legacy constant for backward compatibility
MAX_EVO_ITERATIONS = get_config_value("limits.max_evo_iterations", 5)

def _load_model_config():
    """Load model configuration from config/models.json"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[Config] Error loading {CONFIG_FILE}: {e}")
    
    # Fallback defaults
    return {
        "tiers": {
            "free": {"models": [
                {"id": "openrouter/meta-llama/llama-3.3-70b-instruct:free"},
                {"id": "openrouter/google/gemma-3-27b-it:free"},
            ]},
            "local": {"models": [
                {"id": "ollama/qwen2.5-coder:14b", "preferred": True},
                {"id": "ollama/mistral:7b-instruct"},
            ]},
            "paid": {"models": []}
        },
        "provider_scores": {},
        "speed_tiers": {},
        "default": "openrouter/meta-llama/llama-3.3-70b-instruct:free"
    }

# Load configuration
_MODEL_CONFIG = _load_model_config()

def get_models_from_tier(tier_name, enabled_only=True):
    """Get model IDs from a specific tier in JSON config."""
    tier = _MODEL_CONFIG.get("tiers", {}).get(tier_name, {})
    models = tier.get("models", [])
    if enabled_only:
        models = [m for m in models if m.get("enabled", True)]
    return [m["id"] for m in models]

# Model lists loaded from JSON
FREE_MODELS = get_models_from_tier("free")
LOCAL_PREFERRED = [m["id"] for m in _MODEL_CONFIG["tiers"]["local"]["models"] if m.get("preferred")] or get_models_from_tier("local")
PAID_MODELS = get_models_from_tier("paid")
DEFAULT_MODEL = _MODEL_CONFIG.get("default", FREE_MODELS[0] if FREE_MODELS else "openrouter/meta-llama/llama-3.3-70b-instruct:free")

# Backward compat
MODELS = FREE_MODELS

# Disable local models via environment: EVO_DISABLE_LOCAL=1
DISABLE_LOCAL_MODELS = os.environ.get("EVO_DISABLE_LOCAL", "").lower() in ("1", "true", "yes")

# ─── Colors ──────────────────────────────────────────────────────────
class C:
    R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; GREEN="\033[32m"
    YELLOW="\033[33m"; BLUE="\033[34m"; MAGENTA="\033[35m"; CYAN="\033[36m"; RED="\033[31m"

def cpr(c, m): print(f"{c}{m}{C.R}", flush=True)

# ─── Model Tiers ─────────────────────────────────────────────────────
TIER_FREE  = "free"       # OpenRouter free models (rate-limited)
TIER_LOCAL = "local"      # Ollama local models (always available)
TIER_PAID  = "paid"       # OpenRouter paid models (last resort)

# Fast intent classification — prefer smallest local model
INTENT_MODEL_MAX_PARAMS = 3.0  # billions, prefer models ≤ this size

# Cooldown durations (seconds)
COOLDOWN_RATE_LIMIT = 60
COOLDOWN_TIMEOUT    = 30
COOLDOWN_SERVER_ERR = 20

# ─── State ───────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError) as e:
            print(f"[Config] Warning: Could not load state, using empty: {e}")
            return {}
    return {}

def save_state(s):
    """Save state by merging changes into existing file, only overwriting if file is unusable."""
    # First try to load existing state to preserve other values
    existing = {}
    if STATE_FILE.exists():
        try:
            existing = json.loads(STATE_FILE.read_text())
        except (json.JSONDecodeError, IOError):
            # File exists but is corrupted - will overwrite
            pass
    
    # Merge new values into existing state (shallow merge for nested dicts)
    merged = existing.copy()
    for key, value in s.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Deep merge for nested dicts like user_memory, model_cooldowns
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    
    merged["updated_at"] = datetime.now(timezone.utc).isoformat()
    
    try:
        STATE_FILE.write_text(json.dumps(merged, indent=2))
    except IOError as e:
        print(f"[Config] Warning: Could not save state: {e}")


def _parse_models_override(raw):
    if not raw:
        return None
    if isinstance(raw, list):
        items = [str(x).strip() for x in raw if str(x).strip()]
        return items or None
    if isinstance(raw, str):
        items = [x.strip() for x in raw.split(",") if x.strip()]
        return items or None
    return None


def get_models_from_config(state):
    env_models = _parse_models_override(os.environ.get("EVO_MODELS", ""))
    if env_models:
        return env_models
    st_models = _parse_models_override(state.get("models")) if isinstance(state, dict) else None
    if st_models:
        return st_models
    return FREE_MODELS


def get_categories():
    """Get configuration categories and their options."""
    return get_config_value("categories", {
        "llm": ["model", "temperature", "max_tokens"],
        "tts": ["provider", "speed", "voice", "quality"],
        "stt": ["provider", "duration", "sensitivity"],
        "voice": ["auto_mode", "wake_word", "mute_beep"],
    })


def get_provider_tiers():
    """Get provider quality tiers for 'better/worse' resolution."""
    return get_config_value("provider_tiers", {
        "tts": {
            "espeak": {"tier": "lite", "quality": 3, "speed": 10},
            "pyttsx3": {"tier": "standard", "quality": 5, "speed": 8},
            "coqui": {"tier": "premium", "quality": 9, "speed": 4},
            "piper": {"tier": "premium", "quality": 9, "speed": 5},
        },
        "stt": {
            "vosk": {"tier": "lite", "quality": 6, "speed": 9},
            "whisper": {"tier": "premium", "quality": 9, "speed": 5},
        },
    })


def get_blocked_commands():
    """Get blocked dangerous shell commands."""
    return get_config_value("blocking.blocked_commands", [
        "rm -rf /",
        "rm -rf /*",
        "mkfs",
        "dd if=/dev/zero",
        "format",
        "fdisk",
        ":(){ :|:& };:",
    ])
