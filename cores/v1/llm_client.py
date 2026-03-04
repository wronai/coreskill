#!/usr/bin/env python3
"""
evo-engine LLMClient — Tiered LLM routing: free → local (ollama) → paid.
"""
import os
import json
import subprocess
import time
import re

from .config import (
    TIER_FREE, TIER_LOCAL, TIER_PAID,
    FREE_MODELS, LOCAL_PREFERRED, PAID_MODELS, SKILLS_DIR,
    COOLDOWN_RATE_LIMIT, COOLDOWN_TIMEOUT, COOLDOWN_SERVER_ERR,
    load_state, save_state, cpr, C,
    DISABLE_LOCAL_MODELS,
)
from .utils import litellm, clean_code, clean_json


def _detect_ollama_models():
    """Auto-detect available ollama models. Returns list of 'ollama/<name>' strings."""
    from cores.v1.config import get_code_model_patterns
    CODE_MODELS = set(get_code_model_patterns())
    
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return []
        found = []
        for line in r.stdout.strip().split("\n")[1:]:
            if not line.strip():
                continue
            name = line.split()[0]
            # Skip code-only models for chat
            model_base = name.split(":")[0].lower()
            if any(code in model_base for code in CODE_MODELS):
                continue
            found.append(f"ollama/{name}")
        # Sort: preferred first, then rest
        preferred = [m for m in LOCAL_PREFERRED if m in found]
        rest = [m for m in found if m not in preferred]
        return preferred + rest
    except Exception:
        return []


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
        local_models = [] if DISABLE_LOCAL_MODELS else _detect_ollama_models()
        self._tiers = {
            TIER_FREE: models or FREE_MODELS,
            TIER_LOCAL: local_models,
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
        # Verbose logging
        if os.environ.get("EVO_VERBOSE") == "1":
            model_short = self.model.split('/')[-1] if '/' in self.model else self.model
            print(f"\n[VERBOSE] LLM Call: {model_short} (tier: {self.active_tier})")
            print(f"[VERBOSE] Temperature: {temperature}, Max tokens: {max_tokens}")
            print(f"[VERBOSE] Messages:")
            for i, msg in enumerate(messages):
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                # Truncate long content
                display = content[:200] + "..." if len(content) > 200 else content
                display = display.replace('\n', ' ')
                print(f"  [{i}] {role}: {display}")
        
        # 1. Try current model (with retry on rate limit)
        if self._is_available(self.model):
            result = self._try_model(self.model, messages, temperature, max_tokens, is_primary=True)
            if result is not None:
                if os.environ.get("EVO_VERBOSE") == "1":
                    print(f"[VERBOSE] Response length: {len(result)} chars")
                return result

        # 2. Tiered fallback — free → paid (if API key) → local
        # This ensures paid models are tried before falling back to local
        has_api_key = bool(self.api_key and len(self.api_key) > 10)
        
        if not has_api_key and self.active_tier == TIER_FREE:
            cpr(C.YELLOW, "⚠ Brak klucza API dla OpenRouter — płatne modele niedostępne.")
            cpr(C.DIM, "   Użyj /apikey <twój-klucz> aby włączyć szybsze naprawy.")
        
        # Determine fallback order based on API key availability
        if has_api_key:
            tier_order = (TIER_FREE, TIER_PAID, TIER_LOCAL)  # Try paid before local
        else:
            tier_order = (TIER_FREE, TIER_LOCAL)  # Skip paid if no API key
        
        for tier in tier_order:
            # Skip PAID tier if no API key
            if tier == TIER_PAID and not has_api_key:
                if os.environ.get("EVO_VERBOSE") == "1":
                    print(f"[VERBOSE] Skipping PAID tier — no API key")
                continue
            
            for model in self._tiers[tier]:
                if model == self.model or not self._is_available(model):
                    continue
                result = self._try_model(model, messages, temperature, max_tokens)
                if result is not None:
                    if os.environ.get("EVO_VERBOSE") == "1":
                        print(f"[VERBOSE] Fallback to: {model.split('/')[-1]} (tier: {tier})")
                        print(f"[VERBOSE] Response length: {len(result)} chars")
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

    def _try_model(self, model, messages, temperature, max_tokens, is_primary=False):
        is_local = model.startswith("ollama/")
        kw = dict(model=model, messages=messages,
                  temperature=temperature, max_tokens=max_tokens,
                  timeout=30 if is_local else 15)
        if not is_local:
            kw["api_key"] = self.api_key

        retries = 2 if is_primary else 1  # only retry on primary model
        for attempt in range(retries):
            try:
                r = litellm.completion(**kw)
                self._report_ok(model)
                return r.choices[0].message.content
            except Exception as e:
                err = str(e)
                if self.logger:
                    self.logger.core("llm_error", {"model": model, "error": err[:200]})
                # Rate limit on primary → wait and retry once
                if is_primary and ("RateLimitError" in err or "rate limit" in err.lower()) and attempt == 0:
                    time.sleep(3)
                    continue
                self._report_fail(model, err)
                return None
        self._report_fail(model, "max_retries")
        return None

    def _get_unavailable_reason(self, model: str) -> str:
        """Get human-readable reason why model is unavailable."""
        if model in self._dead:
            return "permanently blacklisted (404/auth error)"
        cd = self._cooldowns.get(model)
        if cd:
            remaining = int(cd[0] - time.time())
            return f"in cooldown ({remaining}s left, reason: {cd[1]})"
        return "not in tier lists"

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
             "8. Start IMMEDIATELY with imports, no comments before code.\n"
             "9. MUST include module-level functions: get_info() -> dict and health_check() -> dict.\n"
             "   get_info() returns {'name': '...', 'version': 'v1', 'description': '...'}.\n"
             "   health_check() returns {'status': 'ok'} or {'status': 'error', 'message': '...'}.\n"
             "10. MUST include module-level execute(params) function that creates class instance and calls .execute(params).")
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
        if any(w in ul for w in _evolve_kw):
            for sk_name in skills:
                if sk_name in ul:
                    return {"action":"evolve","skill":sk_name,"feedback":user_msg,"goal":"improve skill"}
            if any(w in ul for w in _tts_kw):
                return {"action":"evolve","skill":"tts","feedback":user_msg,"goal":"improve tts"}

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

        if any(w in ul for w in _speak_kw):
            return {"action":"use","skill":"tts","input":{"text":user_msg},"goal":"produce_audio"}

        if any(w in ul for w in _stt_kw):
            if "stt" in skills:
                return {"action":"use","skill":"stt","input":{"duration_s": 4, "lang": "pl"},"goal":"transcribe_audio"}
            return {"action":"create","name":"stt","description":"STT: nagrywanie z mikrofonu i transkrypcja po polsku, stdlib+subprocess only.","goal":"enable_stt"}

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
            parsed = json.loads(clean_json(raw))
            if parsed.get("action"):
                return parsed
        except:
            pass
        return {"action": "chat"}
