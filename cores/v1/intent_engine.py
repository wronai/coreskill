#!/usr/bin/env python3
"""
evo-engine IntentEngine v2 — ML-based intent detection.

Replaces hardcoded _KW_* tuples with SmartIntentClassifier:
  Tier 1: Embedding similarity (~5ms)
  Tier 2: Local LLM Qwen 3B (~100ms)
  Tier 3: Remote LLM (~300ms)

Training data is learnable — grows from corrections and successful executions.
"""
import json
import re
from datetime import datetime, timezone

from .config import SKILLS_DIR, save_state, get_config_value
from .utils import clean_json
from .smart_intent import SmartIntentClassifier
from .i18n import (
    ALL_CONFIGURE_KEYWORDS, ALL_CREATE_KW_FLAT, ALL_EVOLVE_KEYWORDS,
    ALL_SHELL_KEYWORDS, ALL_SEARCH_KEYWORDS, match_any_keyword,
)


# Load topic map from system configuration
_TOPIC_MAP = get_config_value("topic_map", {
    "stt": "voice", "tts": "voice",
    "web_search": "web",
    "git_ops": "git",
    "shell": "dev",
    "network_info": "system",
})


class IntentEngine:
    """
    Context-aware intent detection with ML-based classification.
    
    Stages:
      0. Trivial filter (very short / greetings)
      1. ML classification (embedding → local LLM → remote LLM)
      2. Context inference (topic-based disambiguation)
      3. Gap recording for proactive skill suggestions
    
    No hardcoded keywords. Everything is learned.
    """

    # Only trivial words are kept as a quick filter (stage 0).
    # These are NOT intent classifiers — just "skip" words.
    # Multilingual: greetings, yes/no, farewells across all European languages.
    from .i18n import ALL_TRIVIAL_WORDS
    _TRIVIAL = ALL_TRIVIAL_WORDS

    def __init__(self, llm, logger, state):
        self.llm = llm
        self.log = logger
        self.state = state
        self._p = state.setdefault("user_profile", {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        })

        # ML classifier — replaces all _KW_* tuples
        state_dir = SKILLS_DIR.parent  # ~/.evo-engine or project root
        self._classifier = SmartIntentClassifier(
            state_dir=state_dir,
            llm_client=llm,
        )

    @property
    def classifier(self) -> SmartIntentClassifier:
        """Expose classifier for /stats, /info commands."""
        return self._classifier

    def save(self):
        self.state["user_profile"] = self._p
        save_state(self.state)

    # ── Topic tracking (kept — useful for context) ────────────────────
    # Topics are now detected from ML classification results,
    # not from hardcoded keyword tuples.

    def _update_topics_from_result(self, result):
        """Update topic tracking from classification result."""
        skill = result.get("skill", "")
        topic = _TOPIC_MAP.get(skill)
        if topic:
            topics = self._p.get("topics", [])
            self._p["topics"] = ([topic] + topics)[:30]

    def _recent_topic(self, n=10):
        topics = self._p.get("topics", [])[:n]
        if not topics:
            return None
        from collections import Counter
        return Counter(topics).most_common(1)[0][0]

    # ── Context building ──────────────────────────────────────────────
    def _build_context(self, conv):
        parts = []
        topic = self._recent_topic()
        if topic:
            parts.append(f"Active topic: {topic}")
        prefs = self._p.get("preferences", {})
        if prefs:
            parts.append(f"Preferences: {json.dumps(prefs, ensure_ascii=False)}")
        corrections = self._p.get("corrections", [])[-3:]
        if corrections:
            parts.append("Past corrections:\n" +
                "\n".join(f"  '{c['msg'][:50]}' → {c['correct']} (not {c['wrong']})"
                          for c in corrections))
        recent = conv[-6:] if conv else []
        if recent:
            parts.append("Recent:\n" +
                "\n".join(f"  {m['role']}: {m['content'][:80]}" for m in recent))
        return "\n".join(parts) if parts else ""

    # ── Recording ─────────────────────────────────────────────────────
    def record_skill_use(self, skill):
        u = self._p.setdefault("skill_usage", {})
        u[skill] = u.get(skill, 0) + 1

    def record_correction(self, msg, wrong, correct):
        """Record correction AND teach the classifier."""
        c = self._p.setdefault("corrections", [])
        c.append({"msg": msg[:200], "wrong": wrong, "correct": correct,
                  "ts": datetime.now(timezone.utc).isoformat()})
        self._p["corrections"] = c[-50:]
        self.save()
        self.log.core("intent_correction", {"wrong": wrong, "correct": correct})

        # Teach ML classifier
        self._classifier.learn_from_correction(msg, wrong, correct, correct_skill=correct)

    def record_success(self, msg, action, skill):
        """Auto-learn from successful execution."""
        self._classifier.learn_from_success(msg, action, skill)

    def record_unhandled(self, msg):
        u = self._p.setdefault("unhandled", [])
        u.append({"msg": msg[:200], "ts": datetime.now(timezone.utc).isoformat()})
        self._p["unhandled"] = u[-30:]

    # ── Stage handlers ──────────────────────────────────────────────

    def _is_trivial(self, user_msg: str) -> bool:
        """Stage 0: Check if message is trivial (very short / greetings)."""
        stripped = user_msg.strip()
        words = stripped.split()
        return len(stripped) < 4 or (len(words) == 1
                and words[0].lower().rstrip("?!.,") in self._TRIVIAL)

    def _check_deterministic_config(self, user_msg: str) -> dict | None:
        """Stage 0b: Check for deterministic configuration patterns."""
        ul = user_msg.lower()
        if match_any_keyword(ul, ALL_CONFIGURE_KEYWORDS) and any(k in ul for k in (" llm", "model", "mózg", "mozg")):
            return {
                "action": "configure",
                "category": "llm",
                "target": self._extract_config_target(user_msg, "llm"),
                "original_msg": user_msg,
                "_conf": 0.95,
                "_tier": "rule_config_llm",
            }
        return None

    def _check_utility_queries(self, user_msg: str, skills: dict | list) -> dict | None:
        """Stage 0c: Check for time/weather utility queries."""
        skills_list = list(skills.keys()) if isinstance(skills, dict) else list(skills)
        _ul = user_msg.lower()

        if "time" in skills_list:
            _time_q = (
                "która jest godzina", "ktora jest godzina", "jaka jest godzina",
                "godzina", "czas",
                "jaka data", "jaka jest data", "podaj dat", "dzisiejsza data",
                "dzisiaj jest", "dzis jest",
            )
            if any(q in _ul for q in _time_q):
                return {
                    "action": "use",
                    "skill": "time",
                    "input": {"text": user_msg},
                    "goal": "current_time_date",
                    "_conf": 0.95,
                    "_tier": "rule_time",
                }

        if "weather" in skills_list:
            _weather_q = ("pogoda", "jaka pogoda", "jaka jest pogoda", "weather")
            if any(q in _ul for q in _weather_q):
                return {
                    "action": "use",
                    "skill": "weather",
                    "input": {"text": user_msg},
                    "goal": "weather_query",
                    "_conf": 0.95,
                    "_tier": "rule_weather",
                }
        return None

    def _needs_ml_reset(self, result, topic_now: str | None, user_msg: str) -> bool:
        """Check if ML result should be reset for context-based reprocessing."""
        if not result or result.action != "configure":
            return False
        if result.skill not in ("tts", "voice"):
            return False
        if topic_now == "voice":
            return False
        ul = user_msg.lower()
        _voice_words = ("głos", "glos", "mowa", "voice", "tts", "speech", "syntez")
        return any(w in ul for w in _voice_words)

    def _process_ml_result(self, result, user_msg: str, skills: list, conv: list) -> dict | None:
        """Process successful ML classification result and build analysis."""
        has_conv = bool(conv)

        if has_conv:
            self._update_topics_from_result(result.to_analysis())
        self.log.core("intent_ml", {
            "action": result.action,
            "skill": result.skill,
            "conf": result.confidence,
            "tier": result.tier,
        })

        # Handle CONFIGURE intent - session configuration changes
        if result.action == "configure":
            return {
                "action": "configure",
                "category": result.skill,  # llm, tts, stt, voice
                "target": self._extract_config_target(user_msg, result.skill),
                "original_msg": user_msg,
                "_conf": result.confidence,
            }

        analysis = result.to_analysis()

        # Shell: extract actual command if not already set
        if result.skill == "shell":
            cmd = self._extract_shell_command(user_msg, conv)
            if cmd:
                analysis.setdefault("input", {})["command"] = cmd

        # STT: add default input params
        if result.skill == "stt" and not analysis.get("input"):
            analysis["input"] = {"duration_s": 5, "lang": "pl"}

        # TTS: add message as text
        if result.skill == "tts":
            analysis.setdefault("input", {})["text"] = user_msg

        # Create: extract skill name from message
        if result.action == "create" and not analysis.get("name"):
            name = self._extract_skill_name(user_msg)
            if name:
                analysis["name"] = name
                analysis["description"] = user_msg

        # Evolve: try to detect target skill
        if result.action == "evolve" and not result.skill:
            target = self._detect_evolve_target(user_msg, skills)
            if target:
                analysis["skill"] = target

        return analysis

    def _check_voice_context_inference(self, user_msg: str, skills: list, topic: str | None) -> dict | None:
        """Stage 2: Context inference for voice topic."""
        if topic != "voice":
            return None

        ul = user_msg.lower()

        # STT intent detection
        _listen = ("słysz", "slysz", "mikrofon", "nagr", "nasłuch", "nasluch")
        if any(w in ul for w in _listen) and "stt" in skills:
            return {"action": "use", "skill": "stt",
                    "input": {"duration_s": 4, "lang": "pl"}, "goal": "listen"}

        # Voice configuration quality words
        _quality_words = ("lepszy", "lepsza", "gorszy", "gorsza", "szybszy", "szybsza",
                       "better", "worse", "faster", "slower", "quality", "jakość")
        if any(w in ul for w in _quality_words):
            _llm_indicators = ("model", "gemini", "gpt", "claude", "llama", "qwen",
                              "llm", "nai", "mozgo", "mózgo")
            if not any(m in ul for m in _llm_indicators):
                return {
                    "action": "configure",
                    "category": "tts",
                    "target": self._extract_config_target(user_msg, "tts"),
                    "original_msg": user_msg,
                    "_conf": 0.75,
                }
        return None

    def _check_quality_config_fallback(self, user_msg: str) -> dict | None:
        """Check for quality-related configuration (fallback when not in voice context)."""
        ul = user_msg.lower()

        _quality_words = ("lepszy", "lepsza", "gorszy", "gorsza", "szybszy", "szybsza",
                       "better", "worse", "faster", "slower", "quality", "jakość",
                       "przełącz", "zmień", "używaj", "switch", "change", "use")
        if not any(w in ul for w in _quality_words):
            return None

        _llm_indicators = ("model", "gemini", "gpt", "claude", "llama", "qwen",
                          "llm", "nai", "mozgo", "mózgo")
        _voice_indicators = ("głos", "głosik", "mowa", "mówić", "voice", "tts",
                           "speech", "syntezator", "speak", "rozpoznawanie", "stt")

        if any(m in ul for m in _llm_indicators):
            return {
                "action": "configure",
                "category": "llm",
                "target": self._extract_config_target(user_msg, "llm"),
                "original_msg": user_msg,
                "_conf": 0.70,
            }
        elif not any(v in ul for v in _voice_indicators):
            # No voice indicators - FALLBACK to LLM as default
            return {
                "action": "configure",
                "category": "llm",
                "target": self._extract_config_target(user_msg, "llm"),
                "original_msg": user_msg,
                "_conf": 0.65,
                "_fallback": True,
            }
        return None

    # ── Main entry ────────────────────────────────────────────────────
    def analyze(self, user_msg, skills, conv=None):
        """
        ML-based intent detection.

        Flow:
          Stage 0: Trivial filter
          Stage 1: SmartIntentClassifier (embedding → local LLM → remote LLM)
          Stage 2: Context inference
          Stage 3: Gap recording
        """
        conv = conv or []
        has_conv = bool(conv)

        # Stage 0: Very short / trivial → chat
        if self._is_trivial(user_msg):
            return {"action": "chat"}

        # Stage 0b: Deterministic configuration patterns
        result = self._check_deterministic_config(user_msg)
        if result:
            return result

        # Stage 0c: Deterministic utility queries
        result = self._check_utility_queries(user_msg, skills)
        if result:
            return result

        # Stage 1: ML classification
        skills_list = list(skills.keys()) if isinstance(skills, dict) else list(skills)
        if isinstance(skills, dict):
            skills_dict = skills
        else:
            skills_dict = {name: {} for name in skills_list}
        context = self._build_context(conv) if has_conv else ""

        result = self._classifier.classify(
            user_msg,
            skills=skills_dict,
            context=context,
            conv=conv,
        )

        # Guard: without voice-topic context, treat configure-tts/voice as uncertain
        topic_now = self._recent_topic() if has_conv else None
        if self._needs_ml_reset(result, topic_now, user_msg):
            result = None

        if result and result.action != "chat" and result.confidence >= 0.40:
            analysis = self._process_ml_result(result, user_msg, skills_list, conv)
            if analysis:
                return analysis

        # Stage 1b: Skill name matching — catch references to existing skills
        matched = self._match_existing_skill(user_msg, skills_list)
        if matched:
            self.log.core("intent_skill_match", {
                "skill": matched, "msg": user_msg[:60]})
            return {"action": "use", "skill": matched,
                    "input": {"text": user_msg}, "goal": user_msg,
                    "_conf": 0.70, "_tier": "skill_name_match"}

        # Stage 2: Context inference
        result = self._check_voice_context_inference(user_msg, skills_list, topic_now)
        if result:
            return result

        # FALLBACK: Not in voice context, but quality words present
        result = self._check_quality_config_fallback(user_msg)
        if result:
            return result

        # Stage 3: Unhandled
        self.record_unhandled(user_msg)
        return {"action": "chat"}

    # ── Extraction helpers ────────────────────────────────────────────
    # These are NOT intent classifiers — they extract parameters
    # AFTER the ML classifier has decided the intent.

    _CMD_PREFIXES = ("uruchom ", "wykonaj ", "odpal ", "run ", "exec ")
    _CMD_STARTS = ("sudo", "apt", "pip", "ls", "cat", "grep", "find",
                   "echo", "cd", "mkdir", "cp", "mv", "chmod", "systemctl",
                   "docker", "git", "curl", "wget", "npm", "yarn")

    @staticmethod
    def _extract_cmd_from_conversation(conv, cmd_starts):
        """Extract shell command from recent conversation backticks or $ lines."""
        for m in reversed(conv[-6:]):
            content = m.get("content", "")
            for c in re.findall(r'`([^`]+)`', content):
                c = c.strip()
                if any(c.startswith(p) for p in cmd_starts):
                    return c
            for line in content.split("\n"):
                line = line.strip()
                if line.startswith("$ "):
                    return line[2:]
        return None

    def _extract_shell_command(self, msg, conv=None):
        """Extract actual shell command from message or context."""
        ul = msg.lower()

        for prefix in self._CMD_PREFIXES:
            if prefix in ul:
                cmd = msg[ul.index(prefix) + len(prefix):].strip().strip('"').strip("'")
                if cmd:
                    return cmd

        if any(w in ul for w in ("zaktualizuj", "aktualizuj")):
            if "system" in ul or "pakiet" in ul:
                return "sudo apt update && sudo apt upgrade -y"
            if "pip" in ul:
                return "pip list --outdated"

        first_word = ul.split()[0] if ul.split() else ""
        if first_word in self._CMD_STARTS:
            return msg.strip()

        if conv:
            return self._extract_cmd_from_conversation(conv, self._CMD_STARTS)

        return None

    def _extract_skill_name(self, msg):
        """Extract skill name from 'create' intent message."""
        ul = msg.lower()
        _skip = {"skill", "mi", "nowy", "nowa", "do", "sie", "się",
                 "postaci", "jako", "obslugi", "obsługi", "nowe", "nowego",
                 "stwórz", "stworz", "zrob", "zrób", "napisz", "zbuduj",
                 "create", "build", "write", "make"}
        words = ul.split()
        for w in words:
            clean = w.strip(".,!?'\"")
            if clean and clean not in _skip and len(clean) > 2:
                # Return first meaningful word as skill name
                return re.sub(r'[^a-z0-9_]', '_', clean)
        return None

    _SKILL_HINTS = {
        "kalkulator": ("policz", "oblicz", "kalkulat", "ile wynosi", "calculate", "math"),
        "password_generator": ("hasło", "haslo", "password", "wygeneruj has"),
        "text_processor": ("policz słow", "policz slow", "zlicz", "word count",
                           "count word", "ile słów", "ile slow"),
        "echo": ("echo ",),
        "shell": ("uruchom", "wykonaj", "odpal", "run ", "exec ",
                  "sudo ", "apt ", "pip ", "systemctl ", "docker "),
        "time": ("godzina", "czas", "time", "data", "zegar"),
        "weather": ("pogoda", "weather", "temperatura"),
        "network_info": ("sieć", "siec", "network", "ip ", "ping"),
        "system_info": ("system", "info o system", "cpu", "ram", "dysk"),
        "web_search": ("szukaj", "wyszukaj", "search", "google", "znajdź", "znajdz"),
        "json_validator": ("json", "waliduj", "validate"),
    }

    def _match_by_hints(self, ul, skills):
        """Match message against skill keyword hints. Returns skill name or None."""
        for sk_name, keywords in self._SKILL_HINTS.items():
            if sk_name in skills and any(kw in ul for kw in keywords):
                return sk_name
        # Match by trailing underscore variant
        for sk in skills:
            base = sk.rstrip("_")
            if base != sk and len(base) >= 4:
                hints = self._SKILL_HINTS.get(base, ())
                if hints and any(kw in ul for kw in hints):
                    return sk
        return None

    def _match_existing_skill(self, msg, skills):
        """Match user message to an existing skill by name or keyword hints.
        Returns skill name or None. Used as fallback when ML classifier is uncertain."""
        if not skills:
            return None
        ul = msg.lower()

        # Skip when message contains create/evolve intent keywords (multilingual)
        if match_any_keyword(ul, ALL_CREATE_KW_FLAT) or match_any_keyword(ul, ALL_EVOLVE_KEYWORDS):
            return None

        # 1. Direct skill name match (e.g., "kalkulator", "echo", "shell")
        for sk in skills:
            if len(sk) < 3:
                continue
            sk_lower = sk.lower().replace("_", " ")
            if sk_lower in ul or sk.lower() in ul:
                return sk

        # 2. Action-keyword hints
        return self._match_by_hints(ul, skills)

    def _detect_evolve_target(self, msg, skills):
        """Detect which skill to evolve from message."""
        ul = msg.lower()
        for sk in skills:
            if sk in ul:
                return sk
        return None

    _QUALITY_MODIFIERS = (
        ("better", ("lepszy", "lepsza", "better", "najlepszy", "best", "premium", "pro", "jakość")),
        ("worse",  ("gorszy", "gorsza", "worse", "simpler", "prostszy", "gorszej")),
        ("faster", ("szybszy", "szybsza", "szybciej", "faster", "fast", "speed")),
        ("free",   ("darmowy", "free", "tańszy", "cheap")),
        ("local",  ("lokalny", "local", "offline")),
    )
    _VOICE_ON_KW = ("włącz", "enable", "on", "aktywuj")
    _VOICE_OFF_KW = ("wyłącz", "wyłacz", "disable", "off", "dezaktywuj", "mute")
    _LLM_PATTERNS = (
        r'(gemini[-]?[a-z0-9.]*)', r'(gpt[-]?[0-9.]*)', r'(claude[-]?[a-z0-9.]*)',
        r'(llama[-]?[a-z0-9._]*)', r'(qwen[-]?[0-9.]*)',
    )
    _AUDIO_PROVIDERS = ("coqui", "piper", "espeak", "pyttsx3", "whisper", "vosk", "faster-whisper")

    def _extract_config_target(self, msg: str, category: str) -> str:
        """Extract configuration target from message.
        
        Returns: 'better', 'worse', 'faster', specific name, or ''
        """
        import re
        ul = msg.lower()
        
        # Quality modifiers (table-driven)
        for result, keywords in self._QUALITY_MODIFIERS:
            if any(w in ul for w in keywords):
                return result
        
        # Voice on/off
        if category == "voice":
            if any(w in ul for w in self._VOICE_ON_KW):
                return "on"
            if any(w in ul for w in self._VOICE_OFF_KW):
                return "off"
        
        # LLM model extraction
        if category == "llm":
            m = re.search(r'(?:openrouter/)?([a-z0-9_.-]+/[a-z0-9_.:-]+)', ul)
            if m:
                return m.group(1)
            for p in self._LLM_PATTERNS:
                m = re.search(p, ul)
                if m:
                    return m.group(1)
        
        # TTS/STT provider names
        if category in ("tts", "stt"):
            for p in self._AUDIO_PROVIDERS:
                if p in ul:
                    return p
        
        return ""

    # ── Proactive gap detection ───────────────────────────────────────
    def suggest_skills(self):
        """Analyze unhandled intents → suggest new skills."""
        unhandled = self._p.get("unhandled", [])
        if len(unhandled) < 3:
            return []
        msgs = [u["msg"] for u in unhandled[-10:]]
        prompt = ("User messages that no skill handled:\n" +
                  "\n".join(f"- {m}" for m in msgs) +
                  "\n\nSuggest 1-3 Python skills. Return JSON: "
                  '[{"name":"snake_case","description":"what it does"}]')
        raw = self.llm.chat(
            [{"role": "system", "content": "Suggest skills. Return ONLY JSON array."},
             {"role": "user", "content": prompt}], 0.3, 500)
        try:
            r = json.loads(clean_json(raw))
            if isinstance(r, list):
                return r[:3]
            if isinstance(r, dict) and "name" in r:
                return [r]
        except Exception:
            pass
        return []
