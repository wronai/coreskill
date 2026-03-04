#!/usr/bin/env python3
"""
evo-engine IntentEngine — context-aware multi-stage intent detection.

Primary: fast local LLM (smallest available ollama model, e.g. 1.5-3b)
Fallback: keyword matching (when ollama unavailable)
"""
import json
import re
from datetime import datetime, timezone

import nfo

from .config import SKILLS_DIR, INTENT_MODEL_MAX_PARAMS, save_state, cpr, C
from .utils import litellm, clean_json
from .llm_client import _detect_ollama_models


@nfo.logged
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
    _KW_EVOLVE = ("zmien", "zmień", "napraw", "popraw", "lepszy", "lepsza",
                  "ulepszy", "fix", "improve", "change")
    _KW_CREATE = ("stworz", "stwórz", "zainstaluj", "zrob", "zrób",
                  "create", "install", "build", "wgraj", "dodaj", "napisz",
                  "zbuduj", "chcialbym", "chciałbym", "potrzebuje", "potrzebuję",
                  "zaimplementuj", "implement", "deploy", "aplikacj", "program")
    _KW_TTS = ("powiedz", "przywitaj", "przeczytaj", "speak", "say",
               "mow ze", "mów ze", "mow do", "mów do", "read aloud")
    _KW_STT = ("slyszysz", "słyszysz", "slychac", "słychać", "mikrofon",
               "co mowie", "co mówię", "transkrybuj", "transkrypcja", "stt",
               "nagraj", "nagrywaj", "record", "listen",
               "rozpoznaj mow", "rozpoznaj mów", "posluchaj", "posłuchaj",
               "dyktuj", "dictate", "nasłuch", "nasluch")
    _KW_VOICE = ("glos", "głos", "voice", "tts", "glosow", "głosow")
    _KW_CONV = ("pogad", "rozmaw", "rozmow", "rozmawiać", "porozmaw",
                "gadaj", "gadac", "gadać",
                "mowmy", "mówmy", "porozm", "gloso", "glosow",
                "głoso", "głosow", "rozmawiajmy")
    _KW_SHELL = ("uruchom", "wykonaj", "odpal", "wlacz", "włącz",
                 "run ", "exec ", "shell", "komend", "command",
                 "sudo ", "apt ", "pip ", "systemctl", "bash",
                 "terminal", "konsol", "aktualizuj", "zaktualizuj", "update ")
    _CREATE_SKIP = {"skill", "mi", "nowy", "nowa", "do", "sie", "się",
                    "postaci", "jako", "obslugi", "obsługi"}

    def __init__(self, llm, logger, state):
        self.llm = llm
        self.log = logger
        self.state = state
        self._p = state.setdefault("user_profile", {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        })
        self._fast_model = self._detect_fast_model()
        if self._fast_model:
            cpr(C.DIM, f"[INTENT] Fast classifier: {self._fast_model}")

    # ── Fast model detection ──
    _CODE_MODELS = ("coder", "starcoder", "codellama", "deepseek-coder")
    _PREFERRED_FAMILIES = ("qwen2.5:", "qwen2.5-", "gemma", "llama3", "phi3", "phi:")
    _MIN_PARAMS = 2.0  # models < 2b often can't produce reliable JSON

    def _detect_fast_model(self):
        """Find the best small ollama model for intent classification.
        Priority: preferred families (qwen2.5, gemma, llama3) > other language > code.
        Size: ≥ 2b (reliable JSON) and ≤ INTENT_MODEL_MAX_PARAMS."""
        try:
            models = _detect_ollama_models()
        except Exception:
            return None
        if not models:
            return None

        preferred = []
        lang_models = []
        code_models = []
        for m in models:
            match = re.search(r'(\d+\.?\d*)b', m.lower())
            if not match:
                continue
            size = float(match.group(1))
            if size < self._MIN_PARAMS or size > INTENT_MODEL_MAX_PARAMS:
                continue
            ml = m.lower()
            is_code = any(c in ml for c in self._CODE_MODELS)
            is_preferred = any(f in ml for f in self._PREFERRED_FAMILIES)
            if is_preferred and not is_code:
                preferred.append((size, m))
            elif not is_code:
                lang_models.append((size, m))
            else:
                code_models.append((size, m))

        # Pick smallest from best available pool
        for pool in (preferred, lang_models, code_models):
            if pool:
                pool.sort()
                return pool[0][1]

        # Fallback: any model at all (relax size constraint)
        all_sized = []
        for m in models:
            match = re.search(r'(\d+\.?\d*)b', m.lower())
            if match:
                all_sized.append((float(match.group(1)), m))
        if all_sized:
            all_sized.sort()
            return all_sized[0][1]
        return models[0] if models else None

    # ── Dynamic intent prompt ──
    def _build_intent_prompt(self, skills):
        """Build intent classification prompt dynamically from skill metadata."""
        descs = {}
        for sk in skills:
            # Try manifest.json first (has interface info)
            manifest = SKILLS_DIR / sk / "manifest.json"
            if manifest.exists():
                try:
                    m = json.loads(manifest.read_text())
                    desc = m.get("description", sk)
                    iface = m.get("interface", {})
                    inp = iface.get("input", {})
                    if inp:
                        desc += f" input: {json.dumps(inp, ensure_ascii=False)}"
                    descs[sk] = desc
                    continue
                except Exception:
                    pass
            # Try meta.json in latest version
            vs = skills[sk]
            mp = SKILLS_DIR / sk / (vs[-1] if vs else "v1") / "meta.json"
            if mp.exists():
                try:
                    descs[sk] = json.loads(mp.read_text()).get("description", sk)
                    continue
                except Exception:
                    pass
            descs[sk] = sk

        skills_block = "\n".join(f"- {k}: {v}" for k, v in descs.items())
        return f"""Classify user intent. Reply ONLY valid JSON, no markdown.
Skills:
{skills_block}

Actions: use (run skill), evolve (improve skill), create (new skill), chat (conversation)

Key rules:
- tts = user wants system to SAY/SPEAK something aloud
- stt = user wants system to LISTEN/RECORD from microphone ("słyszysz","nagraj","posłuchaj","mikrofon")
- shell = user wants to RUN a system command ("uruchom","wykonaj","sudo","apt","pip")
- Questions like "jaka pogoda?" or "co to jest?" = chat (no skill needed)
- "zmień"/"napraw"/"popraw" existing skill = evolve
- "stwórz"/"zrób"/"napisz" new thing = create
- For shell: extract the actual command in input.command

JSON: {{"action":"use|evolve|create|chat","skill":"name","input":{{}},"goal":"brief"}}"""

    def _classify_fast(self, msg, skills, conv=None):
        """Use small local LLM for intent classification (primary method)."""
        if not self._fast_model:
            return None

        prompt = self._build_intent_prompt(skills)

        # Build messages with minimal conversation context
        messages = [{"role": "system", "content": prompt}]
        if conv:
            for m in conv[-3:]:
                messages.append({"role": m["role"],
                                 "content": m.get("content", "")[:100]})
        messages.append({"role": "user", "content": msg})

        try:
            r = litellm.completion(
                model=self._fast_model,
                messages=messages,
                temperature=0.1,
                max_tokens=200,
                timeout=30,  # first call needs model loading (gemma2:2b ~1.6GB)
            )
            raw = r.choices[0].message.content
            result = json.loads(clean_json(raw))

            # Normalize: small models sometimes return skill name as action
            action = result.get("action", "chat")
            skill = result.get("skill") or ""
            if skill in ("none", "null", "None", ""):
                skill = ""
                result["skill"] = ""

            # If action is a skill name, normalize to "use"
            if action in skills:
                result["skill"] = action
                result["action"] = "use"
                action = "use"
                skill = result["skill"]

            # Normalize action aliases
            _action_map = {"run": "use", "execute": "use", "fix": "evolve",
                           "improve": "evolve", "build": "create", "make": "create"}
            if action in _action_map:
                result["action"] = _action_map[action]
                action = result["action"]

            # Validate: skill must exist for "use" action
            if action == "use" and skill not in skills:
                return None

            # Ensure input is a dict
            if not isinstance(result.get("input"), dict):
                result["input"] = {}

            # Post-process: enrich shell commands from conversation context
            if skill == "shell":
                cmd = result.get("input", {}).get("command", "")
                if not cmd:
                    cmd = self._extract_shell_command(msg.lower(), msg, conv)
                    if cmd:
                        result["input"]["command"] = cmd

            # Add confidence for consistency with keyword classifier
            result["_conf"] = 0.85  # fast LLM is reasonably confident

            return result
        except Exception as e:
            self.log.core("intent_fast_err",
                          {"model": self._fast_model, "err": str(e)[:100]})
            return None

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
        """Multi-stage intent detection.
        Stage 0: Trivial filter
        Stage 1: Fast local LLM (primary — handles typos, Polish, synonyms)
        Stage 2: Keyword fallback (when fast LLM unavailable)
        Stage 3: Context inference
        """
        self._update_topics(user_msg)
        conv = conv or []
        topic = self._recent_topic()

        # Stage 0: Very short / ambiguous → chat (don't waste LLM calls)
        stripped = user_msg.strip()
        words = stripped.split()
        _trivial = {"czy", "co", "jak", "no", "ok", "hej", "elo", "hm", "ee",
                     "nie", "tak", "aha", "wow", "ej", "hmm", "eee", "o",
                     "a", "i", "to", "jest", "kto", "ile", "cześć", "czesc",
                     "halo", "siema", "yo", "witam", "dzień", "dzien"}
        if len(stripped) < 4 or (len(words) == 1 and words[0].lower().rstrip("?!.,") in _trivial):
            return {"action": "chat"}

        # Stage 1: Fast local LLM classification (primary)
        fast = self._classify_fast(user_msg, skills, conv)
        if fast and fast.get("action") != "chat":
            self.log.core("intent_fast", {
                "action": fast.get("action"), "skill": fast.get("skill", ""),
                "model": self._fast_model or "?"})
            return fast

        # Stage 2: Keyword fallback (when fast LLM unavailable or returned chat)
        kw = self._kw_classify(user_msg, skills, topic, conv)
        if kw and kw.pop("_conf", 0) >= 0.7:
            self.log.core("intent_kw", {"action": kw.get("action"), "skill": kw.get("skill", "")})
            return kw

        # Stage 3: Context inference
        ctx = self._ctx_infer(user_msg, skills, topic, conv)
        if ctx:
            self.log.core("intent_ctx", {"action": ctx.get("action")})
            return ctx

        self.record_unhandled(user_msg)
        # If fast LLM said chat, trust it
        return fast if fast else {"action": "chat"}

    # ── Stage 1: Keywords with confidence ──
    def _match(self, ul, kws):
        return any(w in ul for w in kws)

    def _kw_evolve(self, ul, msg, skills):
        if not self._match(ul, self._KW_EVOLVE): return None
        for sk in skills:
            if sk in ul:
                return {"action":"evolve","skill":sk,"feedback":msg,"goal":"improve skill","_conf":0.95}
        if self._match(ul, self._KW_VOICE):
            return {"action":"evolve","skill":"tts","feedback":msg,"goal":"improve tts","_conf":0.9}
        return None

    def _kw_create(self, ul, msg):
        if not self._match(ul, self._KW_CREATE): return None
        words = ul.split()
        name = "new_skill"
        skip = set(self._KW_CREATE) | self._CREATE_SKIP
        for w in reversed(words):
            c = re.sub(r'[^a-z0-9_]', '', w)
            if c and c not in skip and len(c) > 2: name = c; break
        return {"action":"create","name":name,"description":msg,"goal":"fulfill request","_conf":0.95}

    def _kw_shell(self, ul, msg, skills, conv=None):
        if not self._match(ul, self._KW_SHELL): return None
        if "shell" not in skills: return None
        # Extract command from message or recent conversation
        cmd = self._extract_shell_command(ul, msg, conv)
        if cmd:
            return {"action":"use","skill":"shell",
                    "input":{"command":cmd},"goal":f"run: {cmd[:60]}","_conf":0.95}
        return {"action":"use","skill":"shell",
                "input":{"command":""},"goal":"run_command","_conf":0.8}

    def _extract_shell_command(self, ul, msg, conv=None):
        """Try to extract a shell command from user message or recent conversation."""
        import re
        # Direct command patterns: "uruchom ls -la" or "wykonaj apt update"
        for prefix in ("uruchom ", "wykonaj ", "odpal ", "run ", "exec "):
            if prefix in ul:
                idx = ul.index(prefix) + len(prefix)
                cmd = msg[idx:].strip().strip('"').strip("'")
                if cmd:
                    return cmd

        # Common system operation patterns (Polish)
        if any(w in ul for w in ("zaktualizuj", "aktualizuj", "update ")):
            if "system" in ul or "systemu" in ul or "pakiet" in ul:
                return "sudo apt update && sudo apt upgrade -y"
            if "pip" in ul or "python" in ul:
                return "pip list --outdated"

        # Package installation patterns
        if any(w in ul for w in ("zainstaluj", "zainstalować", "install ")):
            # Try to extract package name after common install words
            words = ul.split()
            for i, w in enumerate(words):
                if w in ("zainstaluj", "install", "apt", "pip") and i + 1 < len(words):
                    pkg = words[i + 1].strip('"').strip("'").rstrip(".,!?")
                    if pkg and pkg not in ("mi", "mnie", "to", "ten", "ta"):
                        if "pip" in ul or pkg.startswith("python-"):
                            return f"pip install {pkg}"
                        return f"sudo apt install -y {pkg}"

        # Check for backtick or code-block commands in recent conversation
        if conv:
            for m in reversed(conv[-6:]):
                content = m.get("content", "")
                # Match code blocks
                code_match = re.findall(r'`([^`]+)`', content)
                for c in code_match:
                    c = c.strip()
                    if any(c.startswith(p) for p in ("sudo", "apt", "pip", "systemctl",
                                                      "ls", "cat", "grep", "find", "echo",
                                                      "cd", "mkdir", "cp", "mv", "chmod")):
                        return c
                # Match plain command lines
                for line in content.split("\n"):
                    line = line.strip()
                    if line.startswith("$ "):
                        return line[2:]
                    if line.startswith("sudo ") or line.startswith("apt "):
                        return line
        return None

    def _kw_tts(self, ul, msg):
        if not self._match(ul, self._KW_TTS): return None
        return {"action":"use","skill":"tts","input":{"text":msg},"goal":"produce_audio","_conf":0.95}

    def _kw_stt(self, ul, msg, skills):
        if not self._match(ul, self._KW_STT): return None
        if "stt" in skills:
            return {"action":"use","skill":"stt","input":{"duration_s":4,"lang":"pl"},
                    "goal":"transcribe_audio","_conf":0.95}
        return {"action":"create","name":"stt",
                "description":"STT: stdlib+subprocess only, record mic + transcribe po polsku.",
                "goal":"enable_stt","_conf":0.9}

    def _kw_voice_conv(self, ul, msg, skills):
        if not (self._match(ul, self._KW_CONV) and self._match(ul, self._KW_VOICE)): return None
        if "stt" in skills:
            return {"action":"use","skill":"stt","input":{"duration_s":5,"lang":"pl"},
                    "goal":"voice_conversation","_conf":0.9}
        return {"action":"create","name":"stt",
                "description":"STT for voice conversation: stdlib only, record mic + transcribe",
                "goal":"enable_voice","_conf":0.9}

    def _kw_voice_ambiguous(self, ul, msg):
        if not self._match(ul, self._KW_VOICE): return None
        return {"action":"use","skill":"tts","input":{"text":msg},"goal":"produce_audio","_conf":0.7}

    def _kw_classify(self, msg, skills, topic, conv=None):
        ul = msg.lower()
        # Priority order: evolve > shell > create > TTS > STT > voice_conv > voice_ambiguous
        return (self._kw_evolve(ul, msg, skills)
                or self._kw_shell(ul, msg, skills, conv)
                or self._kw_create(ul, msg)
                or self._kw_tts(ul, msg)
                or self._kw_stt(ul, msg, skills)
                or self._kw_voice_conv(ul, msg, skills)
                or self._kw_voice_ambiguous(ul, msg)
                or {"action":"chat","_conf":0.5})

    # ── Stage 2 (legacy): Expensive LLM classify — only used if fast model AND keywords both fail ──
    def _llm_classify(self, msg, skills, context, topic):
        """Fallback: use main LLM for classification. Slower but more capable."""
        descs = {}
        for sk in skills:
            vs = skills[sk]
            mp = SKILLS_DIR / sk / (vs[-1] if vs else "v1") / "meta.json"
            if mp.exists():
                try: descs[sk] = json.loads(mp.read_text()).get("description", sk)
                except: descs[sk] = sk
            else: descs[sk] = sk

        s = f"""Intent classifier. Skills: {json.dumps(descs, ensure_ascii=False)}
Context: {context}
Prefer action over chat. User speaks Polish.
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
