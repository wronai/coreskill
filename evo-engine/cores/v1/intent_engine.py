#!/usr/bin/env python3
"""
evo-engine IntentEngine — context-aware multi-stage intent detection.
"""
import json
import re
from datetime import datetime, timezone

from .config import SKILLS_DIR, save_state
from .utils import clean_json


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

        # Stage 0: Very short / ambiguous → chat (don't waste LLM calls)
        stripped = user_msg.strip()
        words = stripped.split()
        _trivial = {"czy", "co", "jak", "no", "ok", "hej", "elo", "hm", "ee",
                     "nie", "tak", "aha", "wow", "ej", "hmm", "eee", "o",
                     "a", "i", "to", "jest", "kto", "ile", "cześć", "czesc",
                     "halo", "siema", "yo", "witam", "dzień", "dzien"}
        if len(stripped) < 4 or (len(words) == 1 and words[0].lower().rstrip("?!.,") in _trivial):
            return {"action": "chat"}

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
            return json.loads(clean_json(raw))
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
            r = json.loads(clean_json(raw.replace("[", "{", 1).replace("]", "}", 1)) if "{" not in raw[:5] else raw)
            # Handle both array and object
            if isinstance(r, list): return r[:3]
            if isinstance(r, dict) and "name" in r: return [r]
        except:
            pass
        return []
