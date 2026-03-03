#!/usr/bin/env python3
"""
evo-engine Core v1 - Evolutionary Chat Engine
Dual-core (A/B) with self-healing, evolutionary skill building,
per-skill/core logging, learning from logs, auto-proposals.
"""
import os, sys, json, subprocess, hashlib, traceback, shutil, threading, time, warnings, re
import importlib.util
from pathlib import Path
from datetime import datetime, timezone, timedelta

# ─── Suppress ALL noisy output BEFORE any imports ───────────────────
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*[Pp]ydantic.*")
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["LITELLM_SUPPRESS_DEBUG_INFO"] = "1"

# Monkey-patch print() BEFORE litellm import (litellm captures ref at import)
import builtins
_real_print = builtins.print
_SPAM = ("Provider List", "Give Feedback", "LiteLLM.Info", "litellm._turn_on_debug",
         "LiteLLM completion()", "litellm.completion")
def _quiet_print(*a, **kw):
    msg = " ".join(str(x) for x in a)
    if any(s in msg for s in _SPAM):
        return
    _real_print(*a, **kw)
builtins.print = _quiet_print

# Suppress pydantic warnings (they go through warnings.warn → stderr)
_orig_showwarning = warnings.showwarning
def _quiet_warning(msg, cat, *a, **kw):
    s = str(msg)
    if "pydantic" in s.lower() or "Pydantic" in s or "serializer" in s.lower():
        return
    _orig_showwarning(msg, cat, *a, **kw)
warnings.showwarning = _quiet_warning

import logging
for _ln in ("LiteLLM", "LiteLLM Proxy", "LiteLLM Router", "litellm",
            "httpx", "httpcore", "openai", "urllib3"):
    logging.getLogger(_ln).setLevel(logging.CRITICAL)

def _setup_litellm():
    import litellm
    litellm.drop_params = True
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    try: litellm._logging._disable_debugging()
    except: pass
    return litellm

try:
    litellm = _setup_litellm()
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm", "-q",
                           "--break-system-packages"])
    litellm = _setup_litellm()

# ─── Rich Markdown terminal rendering ────────────────────────────────
try:
    from rich.console import Console
    from rich.markdown import Markdown as RichMarkdown
    from rich.theme import Theme
    _rich_theme = Theme({"info": "dim cyan", "warning": "yellow", "error": "bold red"})
    _console = Console(theme=_rich_theme, highlight=False)
    def mprint(text, style=None):
        """Print rich-rendered markdown to terminal."""
        if not text: return
        try:
            _console.print(RichMarkdown(text), style=style)
        except:
            print(text)
    HAS_RICH = True
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q",
                               "--break-system-packages"])
        from rich.console import Console
        from rich.markdown import Markdown as RichMarkdown
        _console = Console(highlight=False)
        def mprint(text, style=None):
            if not text: return
            try: _console.print(RichMarkdown(text), style=style)
            except: print(text)
        HAS_RICH = True
    except:
        def mprint(text, style=None): print(text)
        HAS_RICH = False

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


def _detect_ollama_models():
    """Auto-detect available ollama models. Returns list of 'ollama/<name>' strings."""
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return []
        found = []
        for line in r.stdout.strip().split("\n")[1:]:
            if not line.strip():
                continue
            name = line.split()[0]
            found.append(f"ollama/{name}")
        # Sort: preferred first, then rest
        preferred = [m for m in LOCAL_PREFERRED if m in found]
        rest = [m for m in found if m not in preferred]
        return preferred + rest
    except Exception:
        return []


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

# ─── State ───────────────────────────────────────────────────────────
def load_state():
    if STATE_FILE.exists():
        try: return json.loads(STATE_FILE.read_text())
        except: pass
    return {}

def save_state(s):
    s["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE_FILE.write_text(json.dumps(s, indent=2))


# ─── Logger ──────────────────────────────────────────────────────────
class Logger:
    """Per-skill, per-core structured logging with learning."""

    def __init__(self, core_id="A"):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.core_id = core_id

    def _write(self, path, entry):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _entry(self, event, data=None):
        return {"ts": datetime.now(timezone.utc).isoformat(),
                "core": self.core_id, "event": event, "data": data or {}}

    def core(self, event, data=None):
        e = self._entry(event, data)
        self._write(LOGS_DIR / f"core_{self.core_id}.log", e)
        self._write(LOGS_DIR / "core.log", e)

    def skill(self, skill_name, event, data=None):
        e = self._entry(event, data)
        self._write(LOGS_DIR / "skills" / f"{skill_name}.log", e)
        self._write(LOGS_DIR / "core.log", e)

    def read_skill_log(self, skill_name, last_n=20):
        p = LOGS_DIR / "skills" / f"{skill_name}.log"
        if not p.exists(): return []
        lines = p.read_text().strip().split("\n")[-last_n:]
        return [json.loads(l) for l in lines if l.strip()]

    def read_core_log(self, last_n=30):
        p = LOGS_DIR / f"core_{self.core_id}.log"
        if not p.exists(): return []
        lines = p.read_text().strip().split("\n")[-last_n:]
        return [json.loads(l) for l in lines if l.strip()]

    def learn_summary(self, skill_name=None):
        """Build a summary of past errors and successes for learning."""
        logs = self.read_skill_log(skill_name, 50) if skill_name else self.read_core_log(50)
        errors = [l for l in logs if "error" in l.get("event","")]
        successes = [l for l in logs if "success" in l.get("event","") or "created" in l.get("event","")]
        summary = []
        if errors:
            summary.append(f"Past errors ({len(errors)}): " +
                           "; ".join(set(str(e.get("data",{}).get("error",""))[:80] for e in errors[-5:])))
        if successes:
            summary.append(f"Successes: {len(successes)}")
        return " | ".join(summary) if summary else "No history"


# ─── LLM Client with tiered model routing ────────────────────────────
class LLMClient:
    """
    Tiered LLM routing: free remote → local (ollama) → paid remote.
    - Rate-limited models get cooldown (not permanent blacklist)
    - 404/auth errors permanently blacklist the model
    - Auto-detects ollama on first init
    - Silent fallback (no noisy output)
    """

    def __init__(self, api_key, model, logger=None, models=None):
        self.api_key = api_key
        self.model = model
        self.logger = logger
        self.active_tier = TIER_FREE

        # Build tier lists
        self._tiers = {
            TIER_FREE: models or FREE_MODELS,
            TIER_LOCAL: _detect_ollama_models(),
            TIER_PAID: PAID_MODELS if api_key else [],
        }
        # Backward compat
        self.models = self._tiers[TIER_FREE]

        # Health tracking
        self._dead = set()        # permanently failed (404, auth)
        self._cooldowns = {}      # model -> (available_after_ts, reason)
        self._last_errors = {}
        self._stats = {}          # model -> {ok: int, fail: int}

        os.environ["OPENROUTER_API_KEY"] = api_key

        # Classify current model into a tier
        for tier, ms in self._tiers.items():
            if model in ms:
                self.active_tier = tier
                break

        if logger:
            local_n = len(self._tiers[TIER_LOCAL])
            logger.core("llm_init", {
                "model": model, "tier": self.active_tier,
                "free": len(self._tiers[TIER_FREE]),
                "local": local_n, "paid": len(self._tiers[TIER_PAID]),
            })

    # ── Public info ──
    def tier_info(self):
        """Return human-readable tier status."""
        parts = []
        for tier in (TIER_FREE, TIER_LOCAL, TIER_PAID):
            n = len(self._tiers[tier])
            avail = sum(1 for m in self._tiers[tier] if self._is_available(m))
            if n > 0:
                parts.append(f"{tier}:{avail}/{n}")
        return " | ".join(parts)

    # ── Availability checks ──
    def _is_available(self, model):
        if model in self._dead:
            return False
        cd = self._cooldowns.get(model)
        if cd:
            if time.time() < cd[0]:
                return False
            del self._cooldowns[model]
        return True

    def _report_ok(self, model):
        s = self._stats.setdefault(model, {"ok": 0, "fail": 0})
        s["ok"] += 1
        self._cooldowns.pop(model, None)

    def _report_fail(self, model, err):
        s = self._stats.setdefault(model, {"ok": 0, "fail": 0})
        s["fail"] += 1
        self._last_errors[model] = err
        el = err.lower()
        if "notfound" in el or "404" in err or "no endpoints" in el:
            self._dead.add(model)
        elif "401" in err or "authentication" in el or "unauthorized" in el:
            self._dead.add(model)
        elif "ratelimit" in el or "rate limit" in el or "429" in err:
            self._cooldowns[model] = (time.time() + COOLDOWN_RATE_LIMIT, "rate_limit")
        elif "timeout" in el or "timed out" in el:
            self._cooldowns[model] = (time.time() + COOLDOWN_TIMEOUT, "timeout")
        elif "500" in err or "502" in err or "503" in err:
            self._cooldowns[model] = (time.time() + COOLDOWN_SERVER_ERR, "server_error")
        else:
            self._cooldowns[model] = (time.time() + COOLDOWN_SERVER_ERR, "unknown")

    # ── Core chat with tiered fallback ──
    def chat(self, messages, temperature=0.7, max_tokens=4096):
        # 1. Try current model
        if self._is_available(self.model):
            result = self._try_model(self.model, messages, temperature, max_tokens)
            if result is not None:
                return result

        # 2. Tiered fallback — free → local → paid
        for tier in (TIER_FREE, TIER_LOCAL, TIER_PAID):
            for model in self._tiers[tier]:
                if model == self.model or not self._is_available(model):
                    continue
                result = self._try_model(model, messages, temperature, max_tokens)
                if result is not None:
                    old_model, old_tier = self.model, self.active_tier
                    self.model = model
                    self.active_tier = tier
                    state = load_state()
                    state["model"] = model
                    state["model_tier"] = tier
                    save_state(state)
                    if self.logger:
                        self.logger.core("model_switch", {
                            "from": old_model, "to": model,
                            "from_tier": old_tier, "to_tier": tier,
                        })
                    if tier != old_tier:
                        cpr(C.DIM, f"[LLM] {old_tier}→{tier}: {model.split('/')[-1]}")
                    return result

        # 3. All failed
        if self.logger:
            self.logger.core("all_models_failed", {"tiers": self.tier_info()})
        return self._build_error_msg()

    def _build_error_msg(self):
        errs = list(self._last_errors.values())[-8:]
        joined = " | ".join(e[:120].replace("\n", " ") for e in errs if e)[:300]
        lower = joined.lower()
        has_local = bool(self._tiers[TIER_LOCAL])
        if "ratelimit" in lower or "rate limit" in lower or "429" in joined:
            if has_local:
                return "[ERROR] Remote rate-limited, local models also failed. Spróbuj za chwilę."
            return "[ERROR] Rate limit. Zainstaluj ollama dla lokalnych modeli: curl -fsSL https://ollama.com/install.sh | sh"
        if "401" in joined or "authentication" in lower:
            if has_local:
                return "[ERROR] API key invalid, but local models also failed. Check key + ollama status."
            return "[ERROR] API key invalid. Check: https://openrouter.ai/keys"
        if "notfound" in lower or "404" in joined:
            if has_local:
                return "[ERROR] Remote models unavailable, local also failed. Try: ollama pull qwen2.5:3b"
            return "[ERROR] Models unavailable. Install ollama or change models."
        return f"[ERROR] All models failed ({self.tier_info()}). Last: {joined[:100]}"

    def _try_model(self, model, messages, temperature, max_tokens):
        is_local = model.startswith("ollama/")
        kw = dict(model=model, messages=messages,
                  temperature=temperature, max_tokens=max_tokens)
        if not is_local:
            kw["api_key"] = self.api_key

        for attempt in range(2):
            try:
                r = litellm.completion(**kw)
                self._report_ok(model)
                return r.choices[0].message.content
            except Exception as e:
                err = str(e)
                if self.logger:
                    self.logger.core("llm_error", {"model": model, "error": err[:200]})
                # Rate limit on first attempt → wait and retry
                if ("RateLimitError" in err or "rate limit" in err.lower()) and attempt == 0:
                    time.sleep(4)
                    continue
                self._report_fail(model, err)
                return None
        self._report_fail(model, "max_retries")
        return None

    def gen_code(self, prompt, ctx="", learning=""):
        s = ("You are an expert Python developer generating skills for evo-engine.\n"
             "STRICT RULES:\n"
             "1. Return ONLY valid Python code. No markdown fences (```), no explanations.\n"
             "2. Use ONLY stdlib + subprocess for system commands. NO pip packages.\n"
             "3. Must have a class with execute(self, params: dict) -> dict method.\n"
             "4. execute() MUST return {'success': True/False, ...} with result data.\n"
             "5. Include proper error handling with try/except.\n"
             "6. For TTS: use subprocess.run(['espeak', ...]) not pyttsx3/gtts.\n"
             "7. For HTTP: use urllib.request, not requests.\n"
             "8. Start IMMEDIATELY with imports, no comments before code.")
        if ctx: s += f"\nContext:\n{ctx}"
        if learning: s += f"\nLearnings from past attempts:\n{learning}"
        return self.chat([{"role":"system","content":s},
                          {"role":"user","content":prompt}], 0.3)

    def gen_pipeline(self, prompt, skills):
        s = ('Return ONLY JSON: {"name":"...","steps":[{"skill":"...","version":"v1",'
             '"input":{},"output_key":"step_1"}]}\nSkills: ' + json.dumps(skills))
        return self.chat([{"role":"system","content":s},
                          {"role":"user","content":prompt}], 0.2)

    def analyze_need(self, user_msg, skills):
        """Analyze user request. Keywords FIRST (fast+reliable), LLM only for ambiguous."""
        ul = user_msg.lower()
        _evolve_kw = ("zmien", "zmień", "napraw", "popraw", "lepszy", "lepsza",
                       "ulepszy", "fix", "improve", "change")
        _create_kw = ("stworz", "stwórz", "zainstaluj", "zrob", "zrób",
                       "create", "install", "build", "wgraj", "dodaj", "napisz",
                       "zbuduj", "chcialbym", "chciałbym", "potrzebuje", "potrzebuję",
                       "zaimplementuj", "implement", "deploy", "aplikacj", "program")
        _tts_kw = ("glos", "głos", "voice", "tts", "mow", "mów", "glosowo")
        _speak_kw = ("powiedz", "przywitaj", "say", "speak", "mow ze", "mów ze",
                     "mow do", "mów do", "pogadac", "pogadaj")
        _stt_kw = ("slyszysz", "słyszysz", "slychac", "słychać", "mikrofon",
                   "co mowie", "co mówię", "transkrybuj", "transkrypcja", "stt",
                   "rozpozn", "nasłuch", "nasluch", "dyktuj", "dictate")

        # ── PHASE 1: Fast keyword detection (no LLM call needed) ──
        # 1. Evolve check FIRST - "zmien glos" = evolve, not use
        if any(w in ul for w in _evolve_kw):
            for sk_name in skills:
                if sk_name in ul:
                    return {"action":"evolve","skill":sk_name,"feedback":user_msg,"goal":"improve skill"}
            if any(w in ul for w in _tts_kw):
                return {"action":"evolve","skill":"tts","feedback":user_msg,"goal":"improve tts"}

        # 2. Create check ("chcialbym stworzyc aplikacje APK", "napisz program")
        if any(w in ul for w in _create_kw):
            words = ul.split()
            name = "new_skill"
            skip = set(_create_kw) | {"skill", "mi", "nowy", "nowa", "do", "sie", "się",
                                       "postaci", "jako", "moze", "może", "chce", "chcę",
                                       "obslugi", "obsługi", "dokumentow", "dokumentów"}
            for w in reversed(words):
                clean = re.sub(r'[^a-z0-9_]', '', w)
                if clean and clean not in skip and len(clean) > 2:
                    name = clean
                    break
            return {"action":"create","name":name,"description":user_msg,"goal":"fulfill request"}

        # 3. Direct speak commands ("powiedz cos", "przywitaj sie glosowo")
        if any(w in ul for w in _speak_kw):
            return {"action":"use","skill":"tts","input":{"text":user_msg},"goal":"produce_audio"}

        # 4. STT (listen/transcribe)
        if any(w in ul for w in _stt_kw):
            if "stt" in skills:
                return {"action":"use","skill":"stt","input":{"duration_s": 4, "lang": "pl"},"goal":"transcribe_audio"}
            return {"action":"create","name":"stt","description":"STT: nagrywanie z mikrofonu i transkrypcja po polsku, stdlib+subprocess only.","goal":"enable_stt"}

        # 5. Voice/TTS mentions
        if any(w in ul for w in _tts_kw):
            return {"action":"use","skill":"tts","input":{"text":user_msg},"goal":"produce_audio"}

        # ── PHASE 2: LLM for ambiguous cases (no keyword match) ──
        skill_list = json.dumps(skills)
        s = f"""Action classifier. Skills: {skill_list}
Return ONLY JSON. Rules:
1. If user wants something DONE (not just talk) → create skill or use existing.
2. "tak"/"ok"/"dawaj" = confirm previous → {{"action":"create","name":"<from_context>","description":"<from_context>","goal":"confirm"}}
3. Pure small-talk only → {{"action":"chat"}}
PREFER action over chat. When in doubt → create."""
        raw = self.chat([{"role":"system","content":s},
                         {"role":"user","content":user_msg}], 0.2, 500)
        try:
            parsed = json.loads(_clean_json(raw))
            if parsed.get("action"):
                return parsed
        except:
            pass
        return {"action": "chat"}


def _clean(code):
    """Remove markdown fences from code."""
    if not code: return ""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        code = "\n".join(lines[1:end])
    return code

def _clean_json(text):
    """Extract JSON from potential markdown wrapping."""
    if not text: return "{}"
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]
    return text


# ─── Model Discovery ─────────────────────────────────────────────────
def discover_models():
    """Fetch available free models from OpenRouter API."""
    import urllib.request
    try:
        req = urllib.request.Request("https://openrouter.ai/api/v1/models",
                                     headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        free = [m["id"] for m in data.get("data", []) if ":free" in m.get("id", "")]
        pref = ["nvidia/", "meta-llama/", "google/", "qwen/", "mistralai/", "openai/"]
        scored = []
        for m in free:
            score = sum(6 - i for i, p in enumerate(pref) if p in m)
            scored.append((score, m))
        scored.sort(reverse=True)
        return [f"openrouter/{m}" for _, m in scored[:12]]
    except Exception:
        return []


# ─── Intent Engine: context-aware multi-stage intent detection ────────
class IntentEngine:
    """
    Multi-stage intent detection with conversation context and learning.
    Stages:
      1. Topic tracking (voice/web/files/git context)
      2. High-confidence keyword patterns
      3. LLM classification with full context
      4. Low-confidence keyword fallback
      5. Context inference (topic-based disambiguation)
      6. Gap recording for proactive skill suggestions
    """

    _TOPIC_KW = {
        "voice": ("glos", "głos", "voice", "mow", "mów", "tts", "stt",
                  "slysz", "słysz", "mowi", "mówi", "nagr", "audio",
                  "glosow", "głosow", "powiedz", "speak", "rozm"),
        "web":   ("web", "http", "url", "stron", "internet", "search", "szukaj"),
        "files": ("plik", "file", "folder", "katalog", "dir", "zapis", "odczyt"),
        "git":   ("git", "commit", "push", "branch", "repo"),
        "dev":   ("kod", "code", "program", "skrypt", "script", "debug"),
    }

    def __init__(self, llm, logger, state):
        self.llm = llm
        self.log = logger
        self.state = state
        self._p = state.setdefault("user_profile", {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        })

    def save(self):
        self.state["user_profile"] = self._p
        save_state(self.state)

    # ── Topic tracking ──
    def _detect_topics(self, msg):
        ul = msg.lower()
        return [t for t, kws in self._TOPIC_KW.items() if any(w in ul for w in kws)]

    def _update_topics(self, msg):
        new = self._detect_topics(msg)
        if new:
            self._p["topics"] = (new + self._p.get("topics", []))[:30]

    def _recent_topic(self, n=10):
        topics = self._p.get("topics", [])[:n]
        if not topics: return None
        from collections import Counter
        return Counter(topics).most_common(1)[0][0]

    # ── Context building ──
    def _build_context(self, conv):
        parts = []
        topic = self._recent_topic()
        if topic: parts.append(f"Active conversation topic: {topic}")
        prefs = self._p.get("preferences", {})
        if prefs: parts.append(f"User preferences: {json.dumps(prefs, ensure_ascii=False)}")
        corrections = self._p.get("corrections", [])[-3:]
        if corrections:
            parts.append("Past intent corrections (user corrected me):\n" +
                "\n".join(f"  '{c['msg'][:50]}' was wrongly '{c['wrong']}', should be '{c['correct']}'"
                          for c in corrections))
        recent = conv[-6:] if conv else []
        if recent:
            parts.append("Recent conversation:\n" +
                "\n".join(f"  {m['role']}: {m['content'][:80]}" for m in recent))
        return "\n".join(parts) if parts else "No prior context."

    # ── Recording ──
    def record_skill_use(self, skill):
        u = self._p.setdefault("skill_usage", {})
        u[skill] = u.get(skill, 0) + 1

    def record_correction(self, msg, wrong, correct):
        c = self._p.setdefault("corrections", [])
        c.append({"msg": msg[:200], "wrong": wrong, "correct": correct,
                  "ts": datetime.now(timezone.utc).isoformat()})
        self._p["corrections"] = c[-50:]
        self.save()
        self.log.core("intent_correction", {"wrong": wrong, "correct": correct})

    def record_unhandled(self, msg):
        u = self._p.setdefault("unhandled", [])
        u.append({"msg": msg[:200], "ts": datetime.now(timezone.utc).isoformat()})
        self._p["unhandled"] = u[-30:]

    # ── Main entry ──
    def analyze(self, user_msg, skills, conv=None):
        """Multi-stage intent detection with full conversation context."""
        self._update_topics(user_msg)
        conv = conv or []
        topic = self._recent_topic()
        context = self._build_context(conv)

        # Stage 1: High-confidence keywords
        kw = self._kw_classify(user_msg, skills, topic)
        if kw and kw.pop("_conf", 0) >= 0.9:
            self.log.core("intent_kw_hi", {"action": kw.get("action"), "skill": kw.get("skill","")})
            return kw

        # Stage 2: LLM with context
        llm_r = self._llm_classify(user_msg, skills, context, topic)
        if llm_r and llm_r.get("action") != "chat":
            self.log.core("intent_llm", {"action": llm_r.get("action"), "skill": llm_r.get("skill","")})
            return llm_r

        # Stage 3: Low-confidence keyword fallback
        if kw and kw.get("action") != "chat":
            kw.pop("_conf", None)
            self.log.core("intent_kw_lo", {"action": kw.get("action")})
            return kw

        # Stage 4: Context inference
        ctx = self._ctx_infer(user_msg, skills, topic, conv)
        if ctx:
            self.log.core("intent_ctx", {"action": ctx.get("action")})
            return ctx

        self.record_unhandled(user_msg)
        return {"action": "chat"}

    # ── Stage 1: Keywords with confidence ──
    def _kw_classify(self, msg, skills, topic):
        ul = msg.lower()
        _evolve = ("zmien", "zmień", "napraw", "popraw", "lepszy", "lepsza",
                   "ulepszy", "fix", "improve", "change")
        _create = ("stworz", "stwórz", "zainstaluj", "zrob", "zrób",
                   "create", "install", "build", "wgraj", "dodaj", "napisz",
                   "zbuduj", "chcialbym", "chciałbym", "potrzebuje", "potrzebuję",
                   "zaimplementuj", "implement", "deploy", "aplikacj", "program")
        _tts = ("powiedz", "przywitaj", "przeczytaj", "speak", "say",
                "mow ze", "mów ze", "mow do", "mów do", "read aloud")
        _stt = ("slyszysz", "słyszysz", "slychac", "słychać", "mikrofon",
                "co mowie", "co mówię", "transkrybuj", "transkrypcja", "stt",
                "nagraj", "nagrywaj", "record", "listen",
                "rozpoznaj mow", "rozpoznaj mów", "posluchaj", "posłuchaj",
                "dyktuj", "dictate", "nasłuch", "nasluch")
        _voice = ("glos", "głos", "voice", "tts", "glosow", "głosow")
        _conv  = ("pogad", "rozmaw", "rozmow", "rozmawiać", "porozmaw",
                  "gadaj", "gadac", "gadać")

        # 1. Evolve FIRST
        if any(w in ul for w in _evolve):
            for sk in skills:
                if sk in ul:
                    return {"action":"evolve","skill":sk,"feedback":msg,"goal":"improve skill","_conf":0.95}
            if any(w in ul for w in _voice):
                return {"action":"evolve","skill":"tts","feedback":msg,"goal":"improve tts","_conf":0.9}

        # 2. Create (broad)
        if any(w in ul for w in _create):
            words = ul.split()
            name = "new_skill"
            skip = set(_create) | {"skill", "mi", "nowy", "nowa", "do", "sie", "się",
                                    "postaci", "jako", "obslugi", "obsługi"}
            for w in reversed(words):
                c = re.sub(r'[^a-z0-9_]', '', w)
                if c and c not in skip and len(c) > 2: name = c; break
            return {"action":"create","name":name,"description":msg,"goal":"fulfill request","_conf":0.95}

        # 3. TTS commands (speak/say/greet) — BEFORE STT and voice!
        if any(w in ul for w in _tts):
            return {"action":"use","skill":"tts","input":{"text":msg},
                    "goal":"produce_audio","_conf":0.95}

        # 4. STT (listen/transcribe)
        if any(w in ul for w in _stt):
            if "stt" in skills:
                return {"action":"use","skill":"stt","input":{"duration_s":4,"lang":"pl"},
                        "goal":"transcribe_audio","_conf":0.95}
            return {"action":"create","name":"stt",
                    "description":"STT: stdlib+subprocess only, record mic + transcribe po polsku.",
                    "goal":"enable_stt","_conf":0.9}

        # 5. Voice conversation ("pogadać głosowo") → STT first
        if any(w in ul for w in _conv) and any(w in ul for w in _voice):
            if "stt" in skills:
                return {"action":"use","skill":"stt","input":{"duration_s":5,"lang":"pl"},
                        "goal":"voice_conversation","_conf":0.9}
            return {"action":"create","name":"stt",
                    "description":"STT for voice conversation: stdlib only, record mic + transcribe",
                    "goal":"enable_voice","_conf":0.9}

        # 6. Ambiguous voice keywords → default to TTS (speak), NOT STT
        if any(w in ul for w in _voice):
            return {"action":"use","skill":"tts","input":{"text":msg},
                    "goal":"produce_audio","_conf":0.7}

        return {"action":"chat","_conf":0.5}

    # ── Stage 2: LLM with conversation context ──
    def _llm_classify(self, msg, skills, context, topic):
        # Build skill descriptions from meta.json
        descs = {}
        for sk in skills:
            vs = skills[sk]
            mp = SKILLS_DIR / sk / (vs[-1] if vs else "v1") / "meta.json"
            if mp.exists():
                try: descs[sk] = json.loads(mp.read_text()).get("description", sk)
                except: descs[sk] = sk
            else: descs[sk] = sk

        s = f"""Intent classifier for evo-engine. Skills: {json.dumps(descs, ensure_ascii=False)}
Context: {context}

RULES:
1. "powiedz"/"przywitaj"/"mów coś"/"głosowo" (user wants system to SPEAK) → use tts
2. "czy mnie słyszysz"/"nagraj"/"posłuchaj"/"mikrofon" (user wants system to LISTEN) → use stt
3. "zmień"/"napraw"/"lepszy" → evolve existing skill
4. "stwórz"/"zrób"/"napisz"/"chciałbym"/"aplikacja" → create new skill
5. "tak"/"ok"/"dawaj" = confirm previous → create/use from context
6. ONLY pure small-talk → chat

DEFAULT: "głosowo" without clear listen-intent = TTS (speak), NOT STT.
PREFER action over chat. When in doubt → create skill.
Return ONLY JSON: {{"action":"use|create|evolve|chat","skill":"name","input":{{}},"goal":"..."}}"""

        raw = self.llm.chat([{"role":"system","content":s},
                             {"role":"user","content":msg}], 0.2, 500)
        try:
            return json.loads(_clean_json(raw))
        except:
            return None

    # ── Stage 4: Context inference ──
    def _ctx_infer(self, msg, skills, topic, conv):
        """Infer intent from conversation context when other stages fail."""
        ul = msg.lower()
        if not topic:
            return None
        # In voice topic: only route to STT if explicitly about listening/microphone
        if topic == "voice":
            _listen = ("slysz", "słysz", "mikrofon", "nagr", "nasluch", "nasłuch")
            if any(w in ul for w in _listen) and "stt" in skills:
                return {"action":"use","skill":"stt",
                        "input":{"duration_s":4,"lang":"pl"},"goal":"listen"}
        return None

    # ── Proactive gap detection ──
    def suggest_skills(self):
        """Analyze unhandled intents → suggest new skills."""
        unhandled = self._p.get("unhandled", [])
        if len(unhandled) < 3:
            return []
        msgs = [u["msg"] for u in unhandled[-10:]]
        prompt = ("User messages that no skill handled:\n" +
                  "\n".join(f"- {m}" for m in msgs) +
                  "\n\nSuggest 1-3 Python skills to handle these."
                  " Return JSON: [{\"name\":\"snake_case\",\"description\":\"what it does\"}]")
        raw = self.llm.chat([{"role":"system","content":"Suggest skills. Return ONLY JSON array."},
                             {"role":"user","content":prompt}], 0.3, 500)
        try:
            r = json.loads(_clean_json(raw.replace("[", "{", 1).replace("]", "}", 1)) if "{" not in raw[:5] else raw)
            # Handle both array and object
            if isinstance(r, list): return r[:3]
            if isinstance(r, dict) and "name" in r: return [r]
        except:
            pass
        return []


# ─── Bootstrap skill loaders (no LLM needed) ────────────────────────
def _load_bootstrap_skill(name):
    """Load a bootstrap skill class directly. Returns instance or None."""
    p = SKILLS_DIR / name / "v1" / "skill.py"
    if not p.exists(): return None
    try:
        spec = importlib.util.spec_from_file_location(f"boot_{name}", str(p))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for attr in dir(mod):
            obj = getattr(mod, attr)
            if isinstance(obj, type) and hasattr(obj, "execute") and attr != "type":
                return obj()
        return None
    except Exception:
        return None


# ─── Skill Manager with bootstrap skill integration ──────────────────
class SkillManager:
    def __init__(self, llm, logger):
        self.llm = llm
        self.log = logger
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        # Load bootstrap skills for internal use
        self._devops = _load_bootstrap_skill("devops")
        self._deps = _load_bootstrap_skill("deps")
        self._git = _load_bootstrap_skill("git_ops")

    def list_skills(self):
        sk = {}
        if not SKILLS_DIR.exists(): return sk
        for d in sorted(SKILLS_DIR.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                vs = sorted([v.name for v in d.iterdir()
                             if v.is_dir() and v.name.startswith("v")
                             and not v.name.startswith("__")])
                if vs: sk[d.name] = vs
        return sk

    def latest_v(self, name):
        d = SKILLS_DIR / name
        if not d.exists(): return None
        vs = []
        for v in d.iterdir():
            if v.is_dir() and v.name.startswith("v") and v.name[1:].isdigit():
                vs.append(v.name)
        vs.sort(key=lambda x: int(x[1:]))
        return vs[-1] if vs else None

    def skill_path(self, name, version=None):
        if not version: version = self.latest_v(name)
        if not version: return None
        return SKILLS_DIR / name / version / "skill.py"

    def create_skill(self, name, desc):
        ev = self.latest_v(name)
        nv = f"v{int(ev[1:])+1}" if ev else "v1"
        sd = SKILLS_DIR / name / nv
        sd.mkdir(parents=True, exist_ok=True)

        # Gather system context from deps skill
        sys_ctx = ""
        if self._deps:
            scan = self._deps.scan_system()
            caps = scan.get("capabilities", {})
            sys_ctx = f"\nSystem capabilities: {json.dumps(caps)}"

        learning = self.log.learn_summary(name)
        prompt = (f"Create Python skill '{name}'. {desc}\n"
                  f"Requirements:\n"
                  f"- class with execute(input_data:dict)->dict\n"
                  f"- execute() MUST return dict with 'success':True/False key\n"
                  f"- get_info()->dict function\n"
                  f"- health_check()->bool function\n"
                  f"- if __name__=='__main__' test block\n"
                  f"- Use ONLY stdlib + available system commands. NO pip packages.\n"
                  f"- Version: {nv}"
                  f"{sys_ctx}")
        code = _clean(self.llm.gen_code(prompt, learning=learning))
        if not code or "[ERROR]" in code:
            self.log.skill(name, "create_failed", {"error": "LLM returned no code"})
            return False, "Failed to generate code"

        (sd / "skill.py").write_text(code)
        (sd / "Dockerfile").write_text(
            f"FROM python:3.12-slim\nWORKDIR /app\nCOPY skill.py .\n"
            f'CMD ["python","skill.py"]\n')
        meta = {"name": name, "version": nv, "description": desc,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "checksum": hashlib.md5(code.encode()).hexdigest()}
        (sd / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.skill(name, "skill_created", meta)

        # Git commit if available
        if self._git:
            self._git.commit_skill_version(name, nv, str(sd))

        return True, f"Skill '{name}' {nv} created"

    def diagnose_skill(self, name, version=None):
        """Use devops+deps to fully diagnose a skill. Returns diagnostic dict."""
        p = self.skill_path(name, version)
        if not p or not p.exists():
            return {"phase": "missing", "error": f"Skill '{name}' not found"}

        if not self._devops:
            # Fallback: raw subprocess test
            return self._raw_test(name, version)

        # Full diagnostic via devops skill
        result = self._devops.test_skill(str(p))
        phase = result.get("phase", "unknown")

        # Enrich with deps info if dependency problem
        if phase == "deps" and self._deps:
            missing = result.get("missing", [])
            alternatives = {}
            for mod in missing:
                alt = self._deps.suggest_alternatives(mod)
                if alt.get("success"):
                    alternatives[mod] = alt["alternative"]
            result["alternatives"] = alternatives

        self.log.skill(name, "diagnosis", result)
        return result

    def _raw_test(self, name, version=None):
        """Fallback test without devops skill."""
        p = self.skill_path(name, version)
        if not p: return {"phase": "missing", "error": "not found"}
        try:
            r = subprocess.run([sys.executable, str(p)],
                              capture_output=True, text=True, timeout=15,
                              cwd=str(p.parent))
            ok = r.returncode == 0
            return {"success": ok, "phase": "runtime",
                    "output": r.stdout[-500:],
                    "error": r.stderr[-500:] if not ok else None}
        except subprocess.TimeoutExpired:
            return {"success": False, "phase": "runtime", "error": "Timeout"}
        except Exception as e:
            return {"success": False, "phase": "runtime", "error": str(e)}

    def test_skill(self, name, version=None):
        """Test skill. Returns (success, output_or_error)."""
        diag = self.diagnose_skill(name, version)
        ok = diag.get("success", False)
        if ok:
            return True, diag.get("output", "OK")
        return False, diag.get("error", json.dumps(diag, default=str)[:300])

    def exec_skill(self, name, version=None, inp=None):
        """Execute skill, always using latest version."""
        if not version: version = self.latest_v(name)
        if not version: return {"success": False, "error": f"'{name}' not found"}
        # Skip rolled-back versions
        mp = SKILLS_DIR / name / version / "meta.json"
        if mp.exists():
            m = json.loads(mp.read_text())
            if m.get("rolled_back"):
                vs = sorted([v.name for v in (SKILLS_DIR / name).iterdir()
                             if v.is_dir() and v.name.startswith("v") and v.name != version])
                if vs: version = vs[-1]
        p = SKILLS_DIR / name / version / "skill.py"
        if not p.exists(): return {"success": False, "error": f"Not found: {p}"}
        try:
            spec = importlib.util.spec_from_file_location(
                f"sk_{name}_{version}_{id(self)}", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            info = mod.get_info() if hasattr(mod, "get_info") else {"name": name}
            for a in dir(mod):
                o = getattr(mod, a)
                if isinstance(o, type) and hasattr(o, "execute"):
                    result = o().execute(inp or {})
                    self.log.skill(name, "exec_success", {"version": version})
                    return {"success": True, "result": result, "info": info}
            if hasattr(mod, "execute"):
                result = mod.execute(inp or {})
                self.log.skill(name, "exec_success", {"version": version})
                return {"success": True, "result": result, "info": info}
            return {"success": True, "result": info}
        except Exception as e:
            self.log.skill(name, "exec_error", {"error": str(e), "version": version})
            return {"success": False, "error": str(e), "tb": traceback.format_exc()}

    def smart_evolve(self, name, feedback, user_msg=""):
        """Evolve skill using devops diagnosis + deps alternatives."""
        cv = self.latest_v(name)
        if not cv: return False, "Not found"
        p = self.skill_path(name, cv)
        old = p.read_text()

        # Get diagnosis from devops
        diag = self.diagnose_skill(name, cv)
        phase = diag.get("phase", "unknown")

        # Build smart prompt using devops.generate_fix_prompt
        if self._devops:
            prompt = self._devops.generate_fix_prompt(str(p), diag)
            if isinstance(prompt, dict):
                prompt = prompt.get("prompt", "")
        else:
            prompt = (f"Fix this Python skill:\n```python\n{old}\n```\n"
                      f"Error: {feedback}\n")

        # Add system capabilities context
        if self._deps:
            scan = self._deps.scan_system()
            prompt += f"\nAvailable system tools: {json.dumps(scan.get('capabilities', {}))}"

        # Add learning from logs
        learning = self.log.learn_summary(name)
        if learning != "No history":
            prompt += f"\nLearnings: {learning}"

        if user_msg:
            prompt += f"\nUser wanted: {user_msg}"

        prompt += ("\nReturn ONLY the complete fixed Python code."
                   "\nMUST use only stdlib + available system commands."
                   "\nexecute() MUST return dict with 'success' key.")

        code = _clean(self.llm.gen_code(prompt))
        if not code or "[ERROR]" in code:
            return False, "LLM failed to generate fix"

        nv = f"v{int(cv[1:]) + 1}"
        nd = SKILLS_DIR / name / nv
        nd.mkdir(parents=True, exist_ok=True)
        (nd / "skill.py").write_text(code)
        odf = SKILLS_DIR / name / cv / "Dockerfile"
        if odf.exists(): shutil.copy2(str(odf), str(nd / "Dockerfile"))
        meta = {"name": name, "version": nv, "parent": cv, "phase": phase,
                "created_at": datetime.now(timezone.utc).isoformat()}
        (nd / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.skill(name, "skill_evolved", meta)

        if self._git:
            self._git.commit_skill_version(name, nv, str(nd))

        return True, f"'{name}' evolved: {cv} -> {nv}"

    def evolve(self, name, feedback):
        """Backward-compatible evolve - delegates to smart_evolve."""
        return self.smart_evolve(name, feedback)

    def rollback(self, name):
        d = SKILLS_DIR / name
        if not d.exists(): return False, "Not found"
        vs = sorted([v.name for v in d.iterdir() if v.is_dir() and v.name.startswith("v")])
        if len(vs) < 2: return False, "No previous version"
        mp = d / vs[-1] / "meta.json"
        if mp.exists():
            m = json.loads(mp.read_text())
            m["rolled_back"] = True
            mp.write_text(json.dumps(m, indent=2))
        self.log.skill(name, "rollback", {"from": vs[-1], "to": vs[-2]})
        return True, f"Rolled back: {vs[-1]} -> {vs[-2]}"


# ─── Evolutionary Engine ─────────────────────────────────────────────
class EvoEngine:
    """
    Generic evolutionary algorithm:
    1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
       diagnose (devops) → find alternatives (deps) → evolve with smart prompt
    5. Loop until goal achieved or max iterations → 6. Report to user
    """
    def __init__(self, sm, llm, logger):
        self.sm = sm
        self.llm = llm
        self.log = logger

    def handle_request(self, user_msg, skills, analysis=None):
        """Full pipeline: analyze → execute/create/evolve → validate. No user prompts."""
        cpr(C.DIM, "[EVO] Analyzing...")
        if analysis is None:
            analysis = self.llm.analyze_need(user_msg, skills)
        action = analysis.get("action", "chat")
        goal = analysis.get("goal", "")
        inp = analysis.get("input", {})
        if not isinstance(inp, dict): inp = {}

        if action == "chat":
            return None

        if action == "use":
            skill_name = analysis.get("skill")
            if skill_name and skill_name in skills:
                return self._execute_with_validation(
                    skill_name, inp, goal, user_msg)
            # Skill not found - auto-create it
            if skill_name:
                cpr(C.CYAN, f"[EVO] Skill '{skill_name}' not found. Auto-creating...")
                ok, msg = self.evolve_skill(skill_name, analysis.get("description", user_msg))
                if ok:
                    return self._execute_with_validation(skill_name, inp, goal, user_msg)
                return {"type": "evo_failed", "message": msg}

        if action == "evolve":
            skill_name = analysis.get("skill", "")
            feedback = analysis.get("feedback", user_msg)
            if skill_name and skill_name in skills:
                cpr(C.CYAN, f"[EVO] Evolving '{skill_name}'...")
                ok, msg = self.sm.smart_evolve(skill_name, feedback, user_msg)
                if ok:
                    cpr(C.GREEN, f"[EVO] {msg}")
                    return self._execute_with_validation(skill_name, inp, goal, user_msg)
                return {"type": "evo_failed", "message": msg}

        if action == "create":
            name = analysis.get("name", "").replace(" ", "_").lower()
            desc = analysis.get("description", user_msg)
            if not name:
                return None
            cpr(C.CYAN, f"[EVO] Auto-creating skill '{name}'...")
            ok, msg = self.evolve_skill(name, desc)
            if ok:
                return self._execute_with_validation(name, inp, goal, user_msg)
            return {"type": "evo_failed", "message": msg}

        return None

    def _execute_with_validation(self, skill_name, inp, goal, user_msg):
        """Execute skill → validate → diagnose → evolve → retry loop."""
        for attempt in range(MAX_EVO_ITERATIONS):
            cpr(C.CYAN, f"[EVO] Running '{skill_name}' (attempt {attempt + 1}/{MAX_EVO_ITERATIONS})...")
            result = self.sm.exec_skill(skill_name, inp=inp)
            self.log.core("skill_exec", {
                "skill": skill_name, "attempt": attempt + 1,
                "success": result.get("success"), "goal": goal})

            if result.get("success"):
                validated = self._validate_goal(skill_name, result, goal)
                if validated:
                    cpr(C.GREEN, f"[EVO] ✓ Goal achieved: {goal or 'OK'}")
                    self.log.skill(skill_name, "goal_achieved", {"goal": goal})
                    return {"type": "success", "skill": skill_name,
                            "result": result, "goal": goal}
                error_info = (f"Goal '{goal}' not validated. "
                              f"Result: {json.dumps(result.get('result',{}), default=str)[:200]}")
                cpr(C.YELLOW, f"[EVO] Ran but goal not met. Fixing...")
            else:
                error_info = result.get("error", "unknown error")
                cpr(C.YELLOW, f"[EVO] ✗ Failed: {error_info[:100]}")

            if attempt >= MAX_EVO_ITERATIONS - 1:
                break

            # Diagnose → smart evolve
            cpr(C.DIM, f"[EVO] Diagnosing '{skill_name}'...")
            diag = self.sm.diagnose_skill(skill_name)
            phase = diag.get("phase", "?")
            missing = diag.get("missing", [])
            alts = diag.get("alternatives", {})

            if missing:
                cpr(C.YELLOW, f"[EVO] Missing deps: {', '.join(missing)}")
                for mod, alt in alts.items():
                    hint = alt.get("code_hint", alt.get("hint", ""))
                    if hint:
                        cpr(C.DIM, f"  {mod} → {hint}")

            cpr(C.DIM, f"[EVO] Evolving '{skill_name}' (phase: {phase})...")
            ok, msg = self.sm.smart_evolve(skill_name, error_info, user_msg)
            if ok:
                cpr(C.DIM, f"[EVO] {msg}")
                # Quick test before re-executing
                test_ok, test_out = self.sm.test_skill(skill_name)
                if not test_ok:
                    cpr(C.YELLOW, f"[EVO] Test failed: {test_out[:80]}")
                    continue
            else:
                cpr(C.RED, f"[EVO] Evolution failed: {msg}")
                break

        cpr(C.RED, f"[EVO] Could not achieve goal after {MAX_EVO_ITERATIONS} attempts")
        self.log.core("goal_failed", {"skill": skill_name, "goal": goal})
        return {"type": "failed", "skill": skill_name, "goal": goal}

    def _validate_goal(self, skill_name, result, goal):
        """Validate goal from result metadata."""
        r = result.get("result", {})
        if not isinstance(r, dict):
            return True
        if r.get("spoken") is True:
            return True
        if r.get("success") is False:
            return False
        if r.get("error"):
            return False
        if r.get("success") is True:
            return True
        return True

    def evolve_skill(self, name, desc):
        """Create + evolutionary test loop for new skills."""
        cpr(C.CYAN, f"\n[EVO] === Building '{name}' ===")
        self.log.core("evo_start", {"skill": name, "desc": desc})

        cpr(C.DIM, f"[EVO] 1/{MAX_EVO_ITERATIONS}: Generating...")
        ok, msg = self.sm.create_skill(name, desc)
        if not ok:
            cpr(C.RED, f"[EVO] Create failed: {msg}")
            return False, msg
        cpr(C.GREEN, f"[EVO] {msg}")

        for i in range(MAX_EVO_ITERATIONS):
            cpr(C.DIM, f"[EVO] Testing '{name}'...")
            test_ok, test_out = self.sm.test_skill(name)

            if test_ok:
                cpr(C.GREEN, f"[EVO] ✓ '{name}' works!")
                self.log.core("evo_success", {"skill": name, "iterations": i + 1})
                return True, f"Skill '{name}' ready ({i + 1} iter)"

            if i < MAX_EVO_ITERATIONS - 1:
                cpr(C.YELLOW, f"[EVO] ✗ iter {i+1}: {test_out[:100]}")
                cpr(C.DIM, f"[EVO] Diagnosing + evolving...")
                ok, msg = self.sm.smart_evolve(name, test_out[:300])
                if not ok:
                    cpr(C.RED, f"[EVO] Evolve failed: {msg}")
                    break
                cpr(C.DIM, f"[EVO] {msg}")
            else:
                cpr(C.RED, f"[EVO] Max iterations. Error: {test_out[:100]}")

        self.log.core("evo_failed", {"skill": name})
        self.sm.rollback(name)
        return False, f"Skill '{name}' failed after {MAX_EVO_ITERATIONS} iter"


# ─── Pipeline Manager ────────────────────────────────────────────────
class PipelineManager:
    def __init__(self, sm, llm, logger):
        self.sm = sm
        self.llm = llm
        self.log = logger
        PIPELINES_DIR.mkdir(parents=True, exist_ok=True)

    def list_p(self): return [f.stem for f in PIPELINES_DIR.glob("*.json")]

    def create_p(self, name, desc):
        raw = _clean(self.llm.gen_pipeline(desc, list(self.sm.list_skills().keys())))
        try:
            pd = json.loads(_clean_json(raw))
        except:
            return False, f"Invalid JSON: {raw[:200]}"
        pd["created_at"] = datetime.now(timezone.utc).isoformat()
        (PIPELINES_DIR / f"{name}.json").write_text(json.dumps(pd, indent=2))
        self.log.core("pipeline_created", {"name": name})
        return True, f"Pipeline '{name}' created"

    def run_p(self, name, ini=None):
        pf = PIPELINES_DIR / f"{name}.json"
        if not pf.exists(): return {"success": False, "error": "Not found"}
        pipe = json.loads(pf.read_text())
        res = {}; cur = ini or {}
        for i, st in enumerate(pipe.get("steps", [])):
            si = st.get("input", {})
            si.update(cur)
            cpr(C.DIM, f"  Step {i + 1}: {st.get('skill')}")
            r = self.sm.exec_skill(st.get("skill"), st.get("version"), si)
            res[st.get("output_key", f"step_{i + 1}")] = r
            if not r.get("success"):
                return {"success": False, "failed": i + 1, "results": res}
            if isinstance(r.get("result"), dict): cur.update(r["result"])
        return {"success": True, "results": res}


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


# ─── Supervisor ──────────────────────────────────────────────────────
class Supervisor:
    """Manages core versions: can create coreB/C/D, test, promote, rollback."""
    def __init__(self, st, logger):
        self.st = st
        self.log = logger

    def active(self): return self.st.get("active_core", "A")

    def active_version(self):
        return self.st.get(f"core_{self.active().lower()}_version", 1)

    def list_cores(self):
        """List all available core versions."""
        cores_dir = ROOT / "cores"
        if not cores_dir.exists(): return []
        return sorted([d.name for d in cores_dir.iterdir()
                       if d.is_dir() and d.name.startswith("v") and (d / "core.py").exists()])

    def switch(self):
        c = self.active()
        n = "B" if c == "A" else "A"
        self.st["active_core"] = n
        self.st["last_healthy_core"] = c
        save_state(self.st)
        self.log.core("core_switch", {"from": c, "to": n})
        return n

    def health(self, cid):
        v = self.st.get(f"core_{cid.lower()}_version", 1)
        return (ROOT / "cores" / f"v{v}" / "core.py").exists()

    def create_next_core(self, desc=""):
        """Create new core version by copying current."""
        cur_v = self.active_version()
        new_v = cur_v + 1
        src = ROOT / "cores" / f"v{cur_v}" / "core.py"
        dst_dir = ROOT / "cores" / f"v{new_v}"
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(src), str(dst_dir / "core.py"))
        meta = {"version": new_v, "parent": cur_v, "description": desc,
                "created_at": datetime.now(timezone.utc).isoformat()}
        (dst_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        self.log.core("core_created", meta)
        return new_v, str(dst_dir / "core.py")

    def promote_core(self, version):
        """Switch active core to use new version."""
        cid = self.active()
        self.st[f"core_{cid.lower()}_version"] = version
        save_state(self.st)
        self.log.core("core_promoted", {"core": cid, "version": version})
        return cid, version

    def rollback_core(self):
        """Rollback to previous core version."""
        cur_v = self.active_version()
        if cur_v <= 1: return False, "Already at v1"
        prev_v = cur_v - 1
        cid = self.active()
        self.st[f"core_{cid.lower()}_version"] = prev_v
        save_state(self.st)
        self.log.core("core_rollback", {"from": cur_v, "to": prev_v})
        return True, f"Core {cid}: v{cur_v} -> v{prev_v}"

    def recover(self):
        a = self.active()
        o = "B" if a == "A" else "A"
        if self.health(o): return self.switch()
        self.st.update({"core_a_version": 1, "core_b_version": 1, "active_core": "A"})
        save_state(self.st)
        return "A"


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
  /help              This help           /quit           Exit

  Chat naturally - evo auto-detects needs with context-aware IntentEngine,
  builds+tests skills, and validates goals. Learns from your corrections.
"""


# ─── Main ────────────────────────────────────────────────────────────
def main():
    state = load_state()

    # Restart loop detection
    if state.get("last_reset"):
        lr = datetime.fromisoformat(state["last_reset"])
        if datetime.now(timezone.utc) - lr < timedelta(minutes=5):
            cpr(C.RED, "\n=== RESTART LOOP DETECTED ===")
            cpr(C.YELLOW, "Check your API key: https://openrouter.ai/keys")
            cpr(C.RED, "Exiting. Fix the issue and run again.")
            sys.exit(1)

    logger = Logger(state.get("active_core", "A"))
    sv = Supervisor(state, logger)

    cpr(C.CYAN, "\n" + "=" * 56)
    cpr(C.CYAN, "  evo-engine | Evolutionary AI System v1.2")
    cpr(C.CYAN, "  Context-aware IntentEngine | Self-healing dual-core")
    cpr(C.CYAN, "  Auto skill builder | Learning from conversations")
    cpr(C.CYAN, "=" * 56)

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

    models = get_models_from_config(state)
    mdl = os.environ.get("EVO_MODEL") or state.get("model") or (models[0] if models else DEFAULT_MODEL)
    # Auto-fix stale model
    if (not mdl) or "stepfun" in str(mdl):
        mdl = models[0] if models else DEFAULT_MODEL
        state["model"] = mdl
        save_state(state)
    llm = LLMClient(ak, mdl, logger, models=models)
    sm = SkillManager(llm, logger)
    pm = PipelineManager(sm, llm, logger)
    evo = EvoEngine(sm, llm, logger)
    intent = IntentEngine(llm, logger, state)

    cpr(C.DIM, f"Model: {llm.model} | Core: {sv.active()} | Tiers: {llm.tier_info()}")
    sk = sm.list_skills()
    if sk:
        cpr(C.GREEN, f"Skills: {', '.join(sk.keys())}")
    else:
        cpr(C.YELLOW, "No skills yet. Chat or /create <n>")
    cpr(C.DIM, "/help for commands\n")
    logger.core("boot", {"model": llm.model, "tier": llm.active_tier,
                          "tiers": llm.tier_info(), "skills": list(sk.keys())})

    conv = []
    while True:
        try:
            ui = input(f"{C.GREEN}you> {C.R}").strip()
        except (EOFError, KeyboardInterrupt):
            cpr(C.DIM, "\nBye!")
            break
        if not ui:
            continue

        # ── Commands ──
        if ui.startswith("/"):
            p = ui.split(maxsplit=2)
            act = p[0].lower()
            a1 = p[1] if len(p) > 1 else ""
            a2 = p[2] if len(p) > 2 else ""

            if act == "/help":
                print(HELP)
            elif act in ("/quit", "/exit"):
                break
            elif act == "/skills":
                for n, vs in sm.list_skills().items():
                    cpr(C.CYAN, f"  {n}: {', '.join(vs)}")
            elif act == "/create":
                if not a1:
                    cpr(C.YELLOW, "Usage: /create <name>")
                    continue
                cpr(C.CYAN, f"Describe '{a1}':")
                d = input(f"{C.GREEN}> {C.R}").strip()
                if d:
                    ok, msg = evo.evolve_skill(a1, d)
                    cpr(C.GREEN if ok else C.RED, msg)
            elif act == "/test":
                if not a1:
                    cpr(C.YELLOW, "Usage: /test <name>")
                    continue
                ok, out = sm.test_skill(a1)
                cpr(C.GREEN if ok else C.RED, f"Test {'OK' if ok else 'FAILED'}: {out[:300]}")
            elif act == "/run":
                if not a1:
                    cpr(C.YELLOW, "Usage: /run <name>")
                    continue
                print(json.dumps(sm.exec_skill(a1, a2 or None), indent=2, default=str))
            elif act == "/evolve":
                if not a1:
                    cpr(C.YELLOW, "Usage: /evolve <name>")
                    continue
                cpr(C.CYAN, "Feedback:")
                fb = input(f"{C.GREEN}> {C.R}").strip()
                if fb:
                    ok, msg = sm.evolve(a1, fb)
                    cpr(C.GREEN if ok else C.RED, msg)
                    if ok:
                        cpr(C.DIM, "Testing new version...")
                        tok, tout = sm.test_skill(a1)
                        cpr(C.GREEN if tok else C.YELLOW,
                            f"Test {'OK' if tok else 'FAILED'}: {tout[:200]}")
            elif act == "/rollback":
                if a1:
                    ok, msg = sm.rollback(a1)
                    cpr(C.GREEN if ok else C.RED, msg)
            elif act == "/pipeline":
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
            elif act == "/compose":
                cpr(C.GREEN, f"Generated: {gen_compose(sm.list_skills(), state)}")
            elif act == "/model":
                if not a1:
                    cpr(C.DIM, f"Current: {llm.model}")
                    continue
                nm = a1 if a1.startswith("openrouter/") else f"openrouter/{a1}"
                state["model"] = nm
                save_state(state)
                llm.model = nm
                cpr(C.GREEN, f"Model -> {nm}")
            elif act == "/models":
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
            elif act == "/core":
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
            elif act == "/switch":
                cpr(C.GREEN, f"Switched to {sv.switch()}")
            elif act == "/log":
                if a1:
                    logs = logger.read_skill_log(a1, 15)
                else:
                    logs = logger.read_core_log(15)
                for entry in logs:
                    cpr(C.DIM, f"  [{entry.get('ts','')}] {entry.get('event','')} {json.dumps(entry.get('data',{}))[:100]}")
            elif act == "/learn":
                s = logger.learn_summary(a1 if a1 else None)
                cpr(C.CYAN, f"Learnings: {s}")
            elif act == "/diagnose":
                if not a1:
                    cpr(C.YELLOW, "Usage: /diagnose <skill>")
                    continue
                diag = sm.diagnose_skill(a1)
                cpr(C.CYAN, f"Diagnosis for '{a1}':")
                for k, v in diag.items():
                    cpr(C.DIM, f"  {k}: {json.dumps(v, default=str)[:200]}")
            elif act == "/scan":
                if sm._deps:
                    scan = sm._deps.scan_system()
                    for cat, tools in scan.get("capabilities", {}).items():
                        avail = [t for t, ok in tools.items() if ok]
                        cpr(C.CYAN, f"  {cat}: {', '.join(avail) if avail else 'none'}")
                else:
                    cpr(C.RED, "deps skill not loaded")
            elif act == "/state":
                print(json.dumps(state, indent=2))
            elif act == "/correct":
                if not a1 or not a2:
                    cpr(C.YELLOW, "Usage: /correct <wrong_action> <correct_action>")
                    cpr(C.DIM, "  Example: /correct tts stt  (last msg should have used stt, not tts)")
                else:
                    last_msg = conv[-2]["content"] if len(conv) >= 2 else "unknown"
                    intent.record_correction(last_msg, a1, a2)
                    cpr(C.GREEN, f"[LEARN] Zapamiętano: '{last_msg[:50]}' → {a2} (nie {a1})")
            elif act == "/profile":
                p = intent._p
                topic = intent._recent_topic()
                cpr(C.CYAN, f"  Active topic: {topic or 'none'}")
                cpr(C.CYAN, f"  Topics history: {p.get('topics', [])[:10]}")
                cpr(C.CYAN, f"  Skill usage: {json.dumps(p.get('skill_usage', {}))}")
                cpr(C.CYAN, f"  Corrections: {len(p.get('corrections', []))}")
                cpr(C.CYAN, f"  Unhandled: {len(p.get('unhandled', []))}")
                prefs = p.get("preferences", {})
                if prefs: cpr(C.CYAN, f"  Preferences: {json.dumps(prefs, ensure_ascii=False)}")
            elif act == "/suggest":
                cpr(C.DIM, "[LEARN] Analyzing unhandled intents...")
                suggestions = intent.suggest_skills()
                if suggestions:
                    cpr(C.CYAN, "[LEARN] Proponowane nowe skills:")
                    for sg in suggestions:
                        cpr(C.GREEN, f"  → {sg.get('name','?')}: {sg.get('description','')[:80]}")
                    cpr(C.DIM, "  Użyj /create <name> aby zbudować.")
                else:
                    cpr(C.DIM, "[LEARN] Za mało danych (potrzeba min. 3 nieobsłużone intencje).")
            elif act == "/topic":
                topic = intent._recent_topic()
                topics = intent._p.get("topics", [])[:10]
                cpr(C.CYAN, f"  Current topic: {topic or 'none'}")
                cpr(C.DIM, f"  Recent: {topics}")
            else:
                cpr(C.YELLOW, f"Unknown: {act}. /help")
            continue

        # ── Chat with context-aware IntentEngine ──
        conv.append({"role": "user", "content": ui})
        logger.core("user_msg", {"msg": ui[:200]})

        # Step 1: IntentEngine analyzes with full conversation context
        sk = sm.list_skills()
        analysis = intent.analyze(ui, sk, conv)
        logger.core("intent_result", {
            "action": analysis.get("action"), "skill": analysis.get("skill",""),
            "goal": analysis.get("goal","")})

        # Step 2: Let EvoEngine handle the pre-computed analysis
        outcome = evo.handle_request(ui, sk, analysis=analysis)

        if outcome:
            otype = outcome.get("type")
            if otype == "success":
                r = outcome.get("result", {})
                skill = outcome.get("skill", "?")
                intent.record_skill_use(skill)
                res_data = r.get("result", {}) if isinstance(r, dict) else r
                md = f"### ✅ `{skill}` — done\n"
                if isinstance(res_data, dict):
                    for k, v in res_data.items():
                        if k not in ("success", "available_backends") and v:
                            md += f"- **{k}**: {v}\n"
                mprint(md)
                conv.append({"role": "assistant", "content": f"Executed {skill} successfully."})
                continue
            elif otype == "failed":
                mprint(f"### ❌ Nie udało się: {outcome.get('goal', '?')}\nSpróbuję odpowiedzieć tekstowo.")
                # Fall through to regular chat
            elif otype == "evo_failed":
                mprint(f"### ❌ Build failed\n{outcome.get('message', '')}")
                conv.append({"role": "assistant", "content": outcome.get("message", "")})
                continue

        # Step 2: Regular chat (strict: no questions, no code, just do it)
        sp = (f"Jesteś evo-engine, ewolucyjny asystent AI. Masz umiejętności (skills): {json.dumps(list(sm.list_skills().keys()))}.\n\n"
              f"BEZWZGLĘDNE ZASADY:\n"
              f"1. Odpowiadaj po polsku jeśli user mówi po polsku.\n"
              f"2. NIGDY nie wypisuj bloków kodu (```). Zamiast tego stwórz skill.\n"
              f"3. NIGDY nie pytaj o wybór technologii. Sam wybierz najtańszą/najszybszą opcję i ZRÓB TO.\n"
              f"4. NIGDY nie dawaj listy opcji do wyboru. Sam podejmij decyzję.\n"
              f"5. NIGDY nie pisz instrukcji 'jak zainstalować'. Sam to zainstaluj.\n"
              f"6. Jeśli user mówi 'tak' - natychmiast działaj w kontekście poprzedniej rozmowy.\n"
              f"7. Bądź ULTRA zwięzły. Max 2-3 zdania. Używaj markdown.\n"
              f"8. Jeśli czegoś nie możesz zrobić - powiedz JEDNO zdanie i zaproponuj stworzenie skill.\n"
              f"9. Przy tworzeniu czegokolwiek - kalkuluj: co najtańsze, najszybsze, wymaga najmniej zasobów.\n")
        cpr(C.DIM, "Thinking...")
        r = llm.chat([{"role": "system", "content": sp}] + conv[-20:])

        if r and "[ERROR]" in r:
            logger.core("chat_error", {"error": r[:200]})
            cpr(C.RED, f"evo> {r}")
        else:
            conv.append({"role": "assistant", "content": r})
            mprint(f"**evo>** {r}\n")
        logger.core("chat_response", {"length": len(r) if r else 0})

        # Step 4: Proactive learning - suggest skills for recurring gaps
        unhandled = intent._p.get("unhandled", [])
        if len(unhandled) >= 5 and len(unhandled) % 5 == 0:
            suggestions = intent.suggest_skills()
            if suggestions:
                cpr(C.CYAN, "\n[LEARN] Wykryłem powtarzające się potrzeby. Proponuję nowe skills:")
                for sg in suggestions:
                    cpr(C.GREEN, f"  → {sg.get('name','?')}: {sg.get('description','')[:80]}")
                cpr(C.DIM, "  Napisz 'stwórz <name>' lub /create <name> aby zbudować.")
        intent.save()


if __name__ == "__main__":
    main()
