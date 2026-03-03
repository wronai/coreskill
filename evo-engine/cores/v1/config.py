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
MAX_EVO_ITERATIONS = 5

# ─── Colors ──────────────────────────────────────────────────────────
class C:
    R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"; GREEN="\033[32m"
    YELLOW="\033[33m"; BLUE="\033[34m"; MAGENTA="\033[35m"; CYAN="\033[36m"; RED="\033[31m"

def cpr(c, m): print(f"{c}{m}{C.R}", flush=True)

# ─── Model Tiers ─────────────────────────────────────────────────────
TIER_FREE  = "free"       # OpenRouter free models (rate-limited)
TIER_LOCAL = "local"      # Ollama local models (always available)
TIER_PAID  = "paid"       # OpenRouter paid models (last resort)

FREE_MODELS = [
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/google/gemma-3-27b-it:free",
    "openrouter/mistralai/mistral-small-3.1-24b-instruct:free",
    "openrouter/google/gemma-3-12b-it:free",
    "openrouter/google/gemma-3-4b-it:free",
]

# Preferred local models (sorted by quality for code gen + Polish)
LOCAL_PREFERRED = [
    "ollama/qwen2.5-coder:14b",
    "ollama/mistral:7b-instruct",
    "ollama/qwen2.5-coder:7b-instruct",
    "ollama/llama3.2:latest",
    "ollama/qwen2.5:3b",
]

PAID_MODELS = [
    "openrouter/google/gemini-2.0-flash-001",
    "openrouter/anthropic/claude-3.5-haiku",
]

# Backward compat
MODELS = FREE_MODELS
DEFAULT_MODEL = FREE_MODELS[0]

# Cooldown durations (seconds)
COOLDOWN_RATE_LIMIT = 60
COOLDOWN_TIMEOUT    = 30
COOLDOWN_SERVER_ERR = 20

# ─── State ───────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {}

def save_state(s):
    s["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(s, indent=2))


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
