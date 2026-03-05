#!/usr/bin/env python3
"""
smart_intent.py — ML-based intent classification for evo-engine.

Replaces ALL hardcoded _KW_* tuples in intent_engine.py with:

  Tier 1: Embedding similarity (~5ms)  — sentence-transformers
  Tier 2: Local LLM (~100ms)           — Qwen 3B via ollama
  Tier 3: Remote LLM (~300ms)          — fallback via LLMClient

Training data is a JSON file that GROWS from:
  - Default examples (shipped with evo-engine)
  - User corrections (/correct wrong right)
  - Successful skill executions (auto-learn)

Zero hardcoded keywords. Everything is learnable.

Usage:
    classifier = SmartIntentClassifier(state_dir=Path("~/.evo-engine"))
    result = classifier.classify("pogadajmy głosowo")
    # → IntentResult(intent="use", skill="stt", confidence=0.94, tier="embedding")
"""
import json
import hashlib
import time
import os
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional, List, Dict, Tuple

# Import ROOT for config file access
try:
    from .config import ROOT, get_config_value
    from .prompts import prompt_manager
    from .i18n import (
        ALL_TTS_KEYWORDS, ALL_STT_KEYWORDS, ALL_VOICE_MODE_KEYWORDS,
        ALL_SEARCH_KEYWORDS, ALL_SHELL_KEYWORDS, ALL_CREATE_KEYWORDS,
        ALL_EVOLVE_KEYWORDS, match_any_keyword,
    )
except ImportError:
    # Fallback for standalone usage
    ROOT = Path(__file__).resolve().parent.parent.parent
    def get_config_value(k, d=None): return d
    prompt_manager = None
    ALL_TTS_KEYWORDS = ALL_STT_KEYWORDS = ALL_VOICE_MODE_KEYWORDS = frozenset()
    ALL_SEARCH_KEYWORDS = ALL_SHELL_KEYWORDS = frozenset()
    ALL_CREATE_KEYWORDS = ALL_EVOLVE_KEYWORDS = frozenset()
    def match_any_keyword(text, kw): return any(k in text for k in kw)


# Load intent configuration from system.json
_INTENT_CONFIG = {
    "confidence_threshold": get_config_value("intent.confidence_threshold", 0.78),
    "sbert_threshold": get_config_value("intent.sbert_threshold", 0.70),
    "tfidf_threshold": get_config_value("intent.tfidf_threshold", 0.45),
    "bow_threshold": get_config_value("intent.bow_threshold", 0.35),
    "low_threshold_factor": get_config_value("intent.low_threshold_factor", 0.6),
    "min_threshold": get_config_value("intent.min_threshold", 0.25),
    "similarity_min": get_config_value("intent.similarity_min", 0.3),
    "training_file": get_config_value("intent.training_file", "intent_training.json"),
    "embedding_model": get_config_value("intent.embedding_model", "paraphrase-multilingual-MiniLM-L12-v2"),
    "tfidf_fallback": get_config_value("intent.tfidf_fallback", True),
    "local_llm_models": get_config_value("intent.local_llm_models", [
        "qwen3:4b", "qwen2.5:3b", "qwen2.5-coder:3b",
        "gemma3:4b", "phi4-mini", "llama3.2:3b"
    ]),
}


# ── Result types ──────────────────────────────────────────────────────

@dataclass
class IntentResult:
    """Result of intent classification."""
    action: str          # "use", "create", "evolve", "chat"
    skill: str = ""      # target skill name
    confidence: float = 0.0
    tier: str = ""       # which tier resolved: "embedding", "local_llm", "remote_llm", "fallback"
    input: dict = field(default_factory=dict)
    goal: str = ""
    all_scores: dict = field(default_factory=dict)  # debug: all candidate scores

    def to_analysis(self) -> dict:
        """Convert to IntentEngine-compatible analysis dict."""
        d = {"action": self.action}
        if self.skill:
            d["skill"] = self.skill
        if self.input:
            d["input"] = self.input
        if self.goal:
            d["goal"] = self.goal
        d["_conf"] = self.confidence
        d["_tier"] = self.tier
        return d


@dataclass
class TrainingExample:
    """Single training example: phrase → intent + skill."""
    phrase: str
    action: str       # "use", "create", "evolve", "chat"
    skill: str = ""   # e.g. "stt", "tts", "web_search"
    lang: str = "pl"
    source: str = "default"  # "default", "correction", "auto_learn"
    timestamp: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# Import engines from split modules
from .intent.embedding import EmbeddingEngine
from .intent.local_llm import LocalLLMClassifier


# ── Default training data ─────────────────────────────────────────────

def _load_default_training():
    """Load default training data from config file."""
    config_path = ROOT / "config" / "intent_training_default.json"
    
    if not config_path.exists():
        return []
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            examples = data.get("examples", [])
            return [
                (ex["phrase"], ex["action"], ex.get("skill", ""))
                for ex in examples
            ]
    except Exception as e:
        print(f"[SmartIntent] Warning: Could not load training data: {e}")
        return []


DEFAULT_TRAINING = _load_default_training()


# ── Main Classifier ───────────────────────────────────────────────────

class SmartIntentClassifier:
    """
    ML-based intent classifier for evo-engine.
    
    Replaces all hardcoded _KW_* tuples with learnable embeddings.
    
    Architecture:
        Tier 1: Embedding similarity (~5ms)
            - sentence-transformers (best) or TF-IDF or bag-of-words
            - Trained on examples from training_data.json
            - Confidence threshold: 0.78
        
        Tier 2: Local LLM (~100ms)
            - Qwen 3B or similar via ollama
            - Only if Tier 1 confidence < 0.78
            - Structured JSON output
        
        Tier 3: Remote LLM (~300ms)
            - Via existing LLMClient
            - Only if Tier 2 unavailable/fails
        
    Training data grows from:
        - DEFAULT_TRAINING (shipped)
        - User corrections (/correct)
        - Successful skill executions (auto-learn)
    """

    # Base threshold — auto-adjusted by embedding mode
    CONFIDENCE_THRESHOLD = float(os.environ.get("EVO_INTENT_THRESHOLD", 
                                               str(_INTENT_CONFIG["confidence_threshold"])))
    # Mode-specific thresholds (TF-IDF/BOW scores are inherently lower)
    _MODE_THRESHOLDS = {
        "sbert": _INTENT_CONFIG["sbert_threshold"],
        "tfidf": _INTENT_CONFIG["tfidf_threshold"],
        "bow":   _INTENT_CONFIG["bow_threshold"],
    }
    TRAINING_FILE = _INTENT_CONFIG["training_file"]

    def __init__(self, state_dir: Path = None, llm_client=None):
        self._state_dir = state_dir or Path.home() / ".evo-engine"
        self._state_dir.mkdir(parents=True, exist_ok=True)

        self._embedder = EmbeddingEngine(cache_dir=self._state_dir / "models")
        self._local_llm = LocalLLMClassifier()
        self._llm = llm_client  # remote fallback

        self._training_data: List[TrainingExample] = []
        self._embeddings = None  # numpy array of training embeddings
        self._dirty = False  # needs re-encoding

        self._load_training_data()
        self._stats = {"tier1": 0, "tier2": 0, "tier3": 0, "total": 0}

    # ── Training data management ──────────────────────────────────────

    def _training_path(self) -> Path:
        # Prefer logs/ directory for training data
        logs_path = self._state_dir / "logs" / self.TRAINING_FILE
        if logs_path.exists():
            return logs_path
        # Fallback: legacy location (state_dir root)
        legacy = self._state_dir / self.TRAINING_FILE
        if legacy.exists():
            return legacy
        # New files go to logs/
        logs_path.parent.mkdir(parents=True, exist_ok=True)
        return logs_path

    def _load_training_data(self):
        """Load training data: file + defaults."""
        path = self._training_path()

        # Load saved training data
        if path.exists():
            try:
                data = json.loads(path.read_text())
                self._training_data = [TrainingExample.from_dict(d) for d in data]
            except Exception:
                self._training_data = []

        # Merge defaults (add any missing)
        existing_phrases = {ex.phrase.lower().strip() for ex in self._training_data}
        for phrase, action, skill in DEFAULT_TRAINING:
            if phrase.lower().strip() not in existing_phrases:
                self._training_data.append(TrainingExample(
                    phrase=phrase, action=action, skill=skill,
                    source="default"
                ))

        self._dirty = True
        self._save_training_data()

    def _save_training_data(self):
        """Persist training data to JSON."""
        path = self._training_path()
        data = [ex.to_dict() for ex in self._training_data]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1))

    def add_example(self, phrase: str, action: str, skill: str = "",
                    source: str = "correction"):
        """Add a training example (from correction or auto-learn)."""
        from datetime import datetime, timezone
        self._training_data.append(TrainingExample(
            phrase=phrase, action=action, skill=skill,
            source=source,
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))
        self._dirty = True
        self._save_training_data()

    def learn_from_correction(self, user_msg: str, wrong_action: str,
                               correct_action: str, correct_skill: str = ""):
        """Learn from /correct command. Adds positive + negative example."""
        self.add_example(user_msg, correct_action, correct_skill, source="correction")
        # Also boost: add variations
        variations = self._generate_variations(user_msg)
        for v in variations[:2]:
            self.add_example(v, correct_action, correct_skill, source="correction_var")

    def learn_from_success(self, user_msg: str, action: str, skill: str):
        """Auto-learn from successful skill execution."""
        # Only if not already in training data
        msg_lower = user_msg.lower().strip()
        for ex in self._training_data:
            if ex.phrase.lower().strip() == msg_lower:
                return
        self.add_example(user_msg, action, skill, source="auto_learn")

    def _generate_variations(self, phrase: str) -> list:
        """Generate simple variations of a phrase for data augmentation."""
        words = phrase.split()
        variations = []
        # Drop first word
        if len(words) > 2:
            variations.append(" ".join(words[1:]))
        # Drop last word
        if len(words) > 2:
            variations.append(" ".join(words[:-1]))
        # Swap first two words
        if len(words) >= 2:
            swapped = [words[1], words[0]] + words[2:]
            variations.append(" ".join(swapped))
        return variations

    # ── Embedding index ───────────────────────────────────────────────

    def _ensure_embeddings(self):
        """Build/rebuild embedding index from training data."""
        if not self._dirty and self._embeddings is not None:
            return

        if not self._embedder.available:
            self._embeddings = None
            return

        phrases = [ex.phrase for ex in self._training_data]
        if not phrases:
            self._embeddings = None
            return

        try:
            self._embeddings = self._embedder.encode(phrases)
            self._dirty = False
        except Exception as e:
            self._embeddings = None

    # ── Classification ────────────────────────────────────────────────

    def _keyword_prefilter(self, user_msg: str) -> Optional[IntentResult]:
        """Stage 0: Fast keyword prefilter (high-confidence only).

        Uses i18n multilingual keywords for ~30 European languages.
        Returns IntentResult if matched, None otherwise.
        """
        ul = user_msg.lower()

        # TTS keywords - speak/read aloud (all languages)
        if match_any_keyword(ul, ALL_TTS_KEYWORDS):
            return IntentResult(action="use", skill="tts", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        # Voice/STT keywords - listen/record/transcribe (all languages)
        if match_any_keyword(ul, ALL_STT_KEYWORDS):
            return IntentResult(action="use", skill="stt", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        # Voice mode (all languages)
        if match_any_keyword(ul, ALL_VOICE_MODE_KEYWORDS):
            return IntentResult(action="use", skill="stt", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        # Web search (all languages)
        if match_any_keyword(ul, ALL_SEARCH_KEYWORDS):
            return IntentResult(action="use", skill="web_search", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        # Shell (all languages)
        if match_any_keyword(ul, ALL_SHELL_KEYWORDS):
            return IntentResult(action="use", skill="shell", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        # Create/evolve (all languages)
        if match_any_keyword(ul, ALL_CREATE_KEYWORDS):
            return IntentResult(action="create", skill="", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        if match_any_keyword(ul, ALL_EVOLVE_KEYWORDS):
            return IntentResult(action="evolve", skill="", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        return None

    def _embedding_fallback(self, result: Optional[IntentResult], threshold: float) -> Optional[IntentResult]:
        """Use best embedding result even if low confidence (fallback)."""
        if not result or result.action == "chat":
            return None

        low_threshold = max(
            threshold * _INTENT_CONFIG["low_threshold_factor"],
            _INTENT_CONFIG["min_threshold"]
        )
        if result.confidence >= low_threshold:
            result.tier = "embedding_low"
            return result
        return None

    def classify(self, user_msg: str, skills: dict = None,
                 context: str = "", conv: list = None) -> IntentResult:
        """
        Classify user intent through tiered system.

        Args:
            user_msg: The message to classify
            skills: Dict of skills with metadata {name: {description, providers, ...}}
            context: Conversation context string
            conv: Full conversation history

        Returns IntentResult with action, skill, confidence, tier.
        """
        self._stats["total"] += 1

        # Stage 0: Fast keyword prefilter
        result = self._keyword_prefilter(user_msg)
        if result:
            return result

        # Tier 1: Embedding similarity
        result = self._tier1_embedding(user_msg)
        threshold = self._MODE_THRESHOLDS.get(
            self._embedder._mode, self.CONFIDENCE_THRESHOLD
        )
        if result and result.confidence >= threshold:
            self._stats["tier1"] += 1
            return result

        # Tier 2: Local LLM
        result_llm = self._tier2_local_llm(user_msg, skills, context)
        if result_llm and result_llm.action != "chat":
            self._stats["tier2"] += 1
            return result_llm

        # Tier 3: Remote LLM (if available)
        if self._llm:
            result_remote = self._tier3_remote_llm(user_msg, skills, context)
            if result_remote and result_remote.action != "chat":
                self._stats["tier3"] += 1
                return result_remote

        # Fallback: use best embedding result even if low confidence
        fallback = self._embedding_fallback(result, threshold)
        if fallback:
            return fallback

        return IntentResult(action="chat", confidence=0.5, tier="fallback")

    @staticmethod
    def _aggregate_votes(top, training_data):
        """Aggregate top similarity matches into votes by (action, skill)."""
        votes = {}
        for score, idx in top:
            ex = training_data[idx]
            key = (ex.action, ex.skill)
            if key not in votes:
                votes[key] = {"score": 0.0, "count": 0, "examples": []}
            votes[key]["score"] += score
            votes[key]["count"] += 1
            votes[key]["examples"].append(ex.phrase[:50])
        return votes

    _SKILL_INPUT_DEFAULTS = {
        "tts": lambda msg: {"text": msg},
        "stt": lambda msg: {"duration_s": 5, "lang": "pl"},
        "shell": lambda msg: {"command": msg},
    }

    def _tier1_embedding(self, user_msg: str) -> Optional[IntentResult]:
        """Tier 1: Embedding-based similarity matching."""
        self._ensure_embeddings()

        if self._embeddings is None or len(self._embeddings) == 0:
            return None

        try:
            user_vec = self._embedder.encode([user_msg])
            if len(user_vec) == 0:
                return None
            user_vec = user_vec[0]

            scores = [(self._embedder.similarity(user_vec, tv), i)
                      for i, tv in enumerate(self._embeddings)]
            scores.sort(reverse=True)
            top = scores[:5]

            if not top or top[0][0] < _INTENT_CONFIG["similarity_min"]:
                return None

            votes = self._aggregate_votes(top, self._training_data)
            best_key = max(votes, key=lambda k: votes[k]["score"])
            best = votes[best_key]

            confidence = best["score"] / best["count"]
            if best["count"] >= 2:
                confidence = min(confidence + 0.05, 1.0)
            if best["count"] >= 3:
                confidence = min(confidence + 0.05, 1.0)

            action, skill = best_key
            builder = self._SKILL_INPUT_DEFAULTS.get(skill)
            input_data = builder(user_msg) if builder else {}

            return IntentResult(
                action=action,
                skill=skill,
                confidence=round(confidence, 3),
                tier="embedding",
                input=input_data,
                goal=f"{action}_{skill}" if skill else action,
                all_scores={
                    f"{k[0]}/{k[1]}": round(v["score"]/v["count"], 3)
                    for k, v in sorted(votes.items(), key=lambda x: -x[1]["score"])[:5]
                },
            )

        except Exception as e:
            return None

    def _tier2_local_llm(self, user_msg: str, skills: dict = None,
                          context: str = "") -> Optional[IntentResult]:
        """Tier 2: Local LLM classification with full skill schema."""
        return self._local_llm.classify(
            user_msg,
            skills=skills,  # Pass full dict with metadata
            context=context,
        )

    def _tier3_remote_llm(self, user_msg: str, skills: dict = None,
                           context: str = "") -> Optional[IntentResult]:
        """Tier 3: Remote LLM classification with full skill schema."""
        if not self._llm:
            return None

        # Build rich schema (reuse local LLM's schema builder)
        schema = self._local_llm._build_skill_schema(skills or {})
        
        prompt = (
            f"Classify user intent.\n\n"
            f"=== AVAILABLE TOOLS ===\n{schema}\n\n"
            f"=== ACTIONS ===\n"
            f"- use [skill] (execute existing tool)\n"
            f"- create [skill] (build new skill/program)\n"
            f"- evolve [skill] (fix/improve existing skill)\n"
            f"- configure [llm|tts|stt|voice] (change settings)\n"
            f"- chat (normal conversation)\n\n"
            f"=== PRIORITY RULES ===\n"
            f'1. "better/worse VOICE\" in voice context → configure tts\n'
            f'2. "better/worse MODEL\" → configure llm\n'
            f'3. "fix skill X\" when X exists → evolve X\n'
            f'4. "fix skill X\" when X not exists → create X\n\n'
            f"=== CONTEXT ===\n{context[:300] or 'None'}\n\n"
            f"=== MESSAGE ===\n\"{user_msg}\"\n\n"
            f"Return ONLY JSON:\n"
            f'{{"action":"use|create|evolve|configure|chat","skill":"name","goal":"...","reasoning":"brief"}}'
        )
        try:
            raw = self._llm.chat(
                [{"role": "system", "content": "Intent classifier. Return ONLY JSON."},
                 {"role": "user", "content": prompt}],
                temperature=0.1, max_tokens=100
            )
            import re
            m = re.search(r'\{[^}]+\}', raw or "")
            if not m:
                return None
            d = json.loads(m.group())
            return IntentResult(
                action=d.get("action", "chat"),
                skill=d.get("skill", ""),
                confidence=0.80,
                tier="remote_llm_schema",
                goal=d.get("goal", ""),
            )
        except Exception:
            return None

    # ── Stats ─────────────────────────────────────────────────────────

    def stats(self) -> dict:
        """Return classification statistics."""
        total = max(self._stats["total"], 1)
        return {
            "total": self._stats["total"],
            "tier1_embedding": self._stats["tier1"],
            "tier2_local_llm": self._stats["tier2"],
            "tier3_remote_llm": self._stats["tier3"],
            "tier1_pct": round(self._stats["tier1"] / total * 100, 1),
            "training_examples": len(self._training_data),
            "embedding_mode": self._embedder._mode,
            "local_llm_model": self._local_llm._model,
            "local_llm_available": self._local_llm.available,
        }

    def info(self) -> str:
        """Human-readable info string."""
        s = self.stats()
        return (
            f"SmartIntent: {s['training_examples']} examples, "
            f"mode={s['embedding_mode']}, "
            f"local_llm={'✓ '+s['local_llm_model'] if s['local_llm_available'] else '✗'}, "
            f"tier1={s['tier1_pct']}%"
        )


# ── Integration helper ────────────────────────────────────────────────

def create_smart_classifier(state_dir: Path = None,
                             llm_client=None) -> SmartIntentClassifier:
    """Factory function for creating SmartIntentClassifier."""
    return SmartIntentClassifier(
        state_dir=state_dir or Path.home() / ".evo-engine",
        llm_client=llm_client,
    )


# ── Demo / Test ───────────────────────────────────────────────────────

if __name__ == "__main__":
    import tempfile

    print("=== SmartIntentClassifier Demo ===\n")

    # Use temp dir to avoid polluting user home
    with tempfile.TemporaryDirectory() as tmpdir:
        classifier = SmartIntentClassifier(state_dir=Path(tmpdir))

        print(f"Mode: {classifier._embedder._mode}")
        print(f"Training examples: {len(classifier._training_data)}")
        print(f"Local LLM: {classifier._local_llm._model or 'not available'}")
        print()

        # Test classification
        test_msgs = [
            "pogadajmy głosowo",
            "możemy porozmawiać głosem?",
            "powiedz coś po polsku",
            "wyszukaj informacje o pythonie",
            "uruchom apt update",
            "commitnij zmiany",
            "napraw ten skill",
            "stwórz nowy skill do OCR",
            "cześć, jak się masz?",
            "jaka jest pogoda?",
            # Variations not in training data
            "gadajmy głosem",
            "mów coś do mnie głosowo",
            "szukaj w necie o AI",
        ]

        for msg in test_msgs:
            t0 = time.time()
            result = classifier.classify(msg)
            dt = (time.time() - t0) * 1000

            print(f"  \"{msg}\"")
            print(f"    → {result.action}/{result.skill or '-'} "
                  f"conf={result.confidence:.2f} tier={result.tier} "
                  f"({dt:.1f}ms)")
            if result.all_scores:
                top3 = list(result.all_scores.items())[:3]
                print(f"    scores: {dict(top3)}")
            print()

        # Test learning
        print("=== Learning from correction ===")
        classifier.learn_from_correction(
            "przetestuj skill echo",
            wrong_action="chat",
            correct_action="use",
            correct_skill="echo",
        )
        result = classifier.classify("przetestuj skill echo")
        print(f"  After correction: {result.action}/{result.skill} conf={result.confidence:.2f}")

        print(f"\n=== Stats ===")
        print(json.dumps(classifier.stats(), indent=2))


__all__ = [
    "SmartIntentClassifier",
    "IntentResult",
    "create_smart_classifier",
    "EmbeddingEngine",
    "LocalLLMClassifier",
    "DEFAULT_TRAINING",
]
