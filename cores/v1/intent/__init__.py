"""Intent classification package - 3-tier ML classifier.

Exports:
- SmartIntentClassifier: Main classifier with embedding → local LLM → remote LLM
- IntentResult: Classification result dataclass
- EmbeddingEngine: Sentence-transformers/TF-IDF/BOW embeddings
- LocalLLMClassifier: Ollama-based classification
- DEFAULT_TRAINING: Default training examples
"""
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
import json
import os
import time

from ..config import get_config_value
from .training import DEFAULT_TRAINING
from .embedding import EmbeddingEngine
from .local_llm import LocalLLMClassifier
from .knn_classifier import EmbeddingKNNClassifier
from .ensemble import EnsembleIntentClassifier, Vote


# ── Result types ──────────────────────────────────────────────────────

@dataclass
class IntentResult:
    """Result of intent classification."""
    action: str          # "use", "create", "evolve", "chat", "configure"
    skill: str = ""      # target skill name
    confidence: float = 0.0
    tier: str = ""       # which tier resolved: "embedding", "local_llm", "remote_llm", "fallback", "keyword_prefilter"
    input: dict = field(default_factory=dict)
    goal: str = ""
    all_scores: dict = field(default_factory=dict)  # debug: all candidate scores
    category: str = ""   # for configure action: "llm", etc.
    target: str = ""     # for configure action: model name, etc.

    def to_analysis(self) -> dict:
        """Convert to IntentEngine-compatible analysis dict."""
        d = {"action": self.action}
        if self.skill:
            d["skill"] = self.skill
        if self.input:
            d["input"] = self.input
        if self.goal:
            d["goal"] = self.goal
        if self.category:
            d["category"] = self.category
        if self.target:
            d["target"] = self.target
        d["_conf"] = self.confidence
        d["_tier"] = self.tier
        return d


# Load intent configuration
_INTENT_CONFIG = {
    "confidence_threshold": get_config_value("intent.confidence_threshold", 0.78),
    "sbert_threshold": get_config_value("intent.sbert_threshold", 0.70),
    "tfidf_threshold": get_config_value("intent.tfidf_threshold", 0.45),
    "bow_threshold": get_config_value("intent.bow_threshold", 0.35),
    "low_threshold_factor": get_config_value("intent.low_threshold_factor", 0.6),
    "min_threshold": get_config_value("intent.min_threshold", 0.25),
    "similarity_min": get_config_value("intent.similarity_min", 0.3),
    "training_file": get_config_value("intent.training_file", "intent_training.json"),
}


# Backward compatibility: re-export from old location
__all__ = [
    "SmartIntentClassifier",
    "IntentResult",
    "create_smart_classifier",
    "EmbeddingEngine",
    "LocalLLMClassifier",
    "DEFAULT_TRAINING",
]


class SmartIntentClassifier:
    """
    3-tier ML intent classifier:
    1. Embeddings (sbert/tf-idf/bow) — fastest, 90%+ accuracy
    2. Local LLM (ollama) — when embeddings uncertain
    3. Remote LLM — last resort fallback
    
    Training data auto-persisted to intent_training.json.
    """

    # Base threshold - auto-adjusted by embedding mode
    CONFIDENCE_THRESHOLD = float(os.environ.get("EVO_INTENT_THRESHOLD",
                                               str(_INTENT_CONFIG["confidence_threshold"])))
    # Mode-specific thresholds
    _MODE_THRESHOLDS = {
        "sbert": _INTENT_CONFIG["sbert_threshold"],
        "tfidf": _INTENT_CONFIG["tfidf_threshold"],
        "bow":   _INTENT_CONFIG["bow_threshold"],
    }
    TRAINING_FILE = _INTENT_CONFIG["training_file"]

    def __init__(self, state_dir: Path = None, llm_client=None):
        self._state_dir = state_dir or Path.home() / ".evo-engine"
        self._embedder = EmbeddingEngine(cache_dir=self._state_dir / "models")
        self._local_llm = LocalLLMClassifier()
        self._llm_client = llm_client
        
        # Training data
        self._training_file = self._state_dir / self.TRAINING_FILE
        self._training_data = []
        self._skill_vectors = {}  # skill_name -> embedding vector
        self._knn = EmbeddingKNNClassifier()
        self._ensemble = EnsembleIntentClassifier()
        
        self._load_training()

    def _load_training(self):
        """Load training examples from file."""
        # Start with defaults
        self._training_data = list(DEFAULT_TRAINING)
        
        # Load persisted training if exists
        if self._training_file.exists():
            try:
                with open(self._training_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._training_data.extend(
                            [(d.get("text", ""), d.get("action", ""), d.get("skill", ""))
                             for d in data if isinstance(d, dict)]
                        )
            except Exception:
                pass
        
        # Precompute embeddings for training examples
        self._rebuild_skill_vectors()

    def _rebuild_skill_vectors(self):
        """Precompute embeddings for training examples by (action, skill).
        Also fits KNN classifier on individual training vectors."""
        if not self._embedder.available:
            return
        
        import numpy as np
        from collections import defaultdict
        groups = defaultdict(list)
        for text, action, skill in self._training_data:
            key = (action, skill or "")
            groups[key].append(text)
        
        # Average embedding per group (kept for cosine fallback)
        self._skill_vectors = {}
        all_vectors = []
        all_labels = []
        for key, texts in groups.items():
            if texts:
                try:
                    vecs = self._embedder.encode(texts)
                    avg = np.mean(vecs, axis=0)
                    self._skill_vectors[key] = avg
                    # Collect individual vectors for KNN
                    for v in vecs:
                        all_vectors.append(v)
                        all_labels.append(key)
                except Exception:
                    pass
        
        # Fit KNN classifier on individual training vectors
        if all_vectors:
            try:
                self._knn.fit(all_labels, np.array(all_vectors))
            except Exception:
                pass

    def classify(self, user_msg: str, skills: list = None,
                 context: str = "", record: bool = True, **kwargs) -> IntentResult:
        """
        Classify user intent using 3-tier approach.
        
        Args:
            user_msg: User message to classify
            skills: List of available skills
            context: Additional context string
            record: Whether to record this classification
            **kwargs: Additional arguments for compatibility (conv, etc.)
        
        Returns IntentResult with action, skill, confidence, tier.
        """
        user_msg = user_msg.strip()
        if not user_msg:
            return IntentResult(action="chat", confidence=1.0, tier="trivial")
        
        ul = user_msg.lower()
        
        # Stage 0: Fast keyword prefilter (high-confidence only)
        # Uses multilingual keywords from i18n module
        from ..i18n import (
            ALL_TTS_KEYWORDS, ALL_STT_KEYWORDS, ALL_VOICE_MODE_KEYWORDS,
            ALL_SEARCH_KEYWORDS, ALL_SHELL_KEYWORDS, ALL_CREATE_KEYWORDS,
            ALL_EVOLVE_KEYWORDS, ALL_CONFIGURE_KEYWORDS, match_any_keyword,
        )
        
        # TTS keywords (all European languages)
        if match_any_keyword(ul, ALL_TTS_KEYWORDS):
            return IntentResult(action="use", skill="tts", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Voice/STT keywords (all European languages)
        if match_any_keyword(ul, ALL_STT_KEYWORDS):
            return IntentResult(action="use", skill="stt", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Voice mode (all European languages)
        if match_any_keyword(ul, ALL_VOICE_MODE_KEYWORDS):
            return IntentResult(action="use", skill="stt", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Configure / settings (all European languages) - CHECK THIS FIRST
        if match_any_keyword(ul, ALL_CONFIGURE_KEYWORDS):
            target = self._extract_model_target(user_msg)
            return IntentResult(action="configure", category="llm", target=target,
                              confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Web search (all European languages)
        if match_any_keyword(ul, ALL_SEARCH_KEYWORDS):
            # Avoid matching "google" when part of openrouter/google/... model path
            if "google" in ul and ("openrouter/google" in ul or "google/gemma" in ul):
                pass
            else:
                return IntentResult(action="use", skill="web_search", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Shell (all European languages)
        if match_any_keyword(ul, ALL_SHELL_KEYWORDS):
            return IntentResult(action="use", skill="shell", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Create (all European languages)
        if match_any_keyword(ul, ALL_CREATE_KEYWORDS):
            return IntentResult(action="create", skill="", confidence=0.95, tier="keyword_prefilter", goal=user_msg)
        
        # Evolve/fix (all European languages)
        if match_any_keyword(ul, ALL_EVOLVE_KEYWORDS):
            return IntentResult(action="evolve", skill="", confidence=0.95, tier="keyword_prefilter", goal=user_msg)

        # Tier 1: Embedding similarity
        result = self._embedding_classify(user_msg)
        threshold = self._MODE_THRESHOLDS.get(
            self._embedder._mode or "bow",
            self.CONFIDENCE_THRESHOLD
        )
        
        # High-confidence embedding → return directly (fast path)
        if result and result.confidence >= threshold:
            if record:
                self._record_use(result)
            return result

        # Ensemble voting: collect votes from all available classifiers
        self._ensemble.reset()
        
        # Vote 1: Embedding result (KNN or cosine)
        if result and result.action != "chat":
            source = "knn" if "knn" in (result.tier or "") else "cosine"
            self._ensemble.add_vote(Vote(
                action=result.action, skill=result.skill,
                confidence=result.confidence, source=source))
        
        # Vote 2: Local LLM (if available)
        if self._local_llm.available:
            result_local = self._local_llm.classify(user_msg, skills, context)
            if result_local and result_local.action != "chat":
                self._ensemble.add_vote(Vote(
                    action=result_local.action, skill=result_local.skill,
                    confidence=result_local.confidence, source="local_llm"))
        
        # Decide via ensemble
        ensemble_result = self._ensemble.decide()
        if ensemble_result and ensemble_result.confidence >= _INTENT_CONFIG["min_threshold"]:
            final = IntentResult(
                action=ensemble_result.action,
                skill=ensemble_result.skill,
                confidence=ensemble_result.confidence,
                tier=f"ensemble({ensemble_result.agreement:.0%})",
                goal=user_msg,
                all_scores={f"{v.source}:{v.action}:{v.skill}": v.confidence
                            for v in ensemble_result.votes},
            )
            if record:
                self._record_use(final)
            return final

        # Tier 3: Remote LLM fallback (last resort)
        if self._llm_client:
            result_remote = self._llm_classify(user_msg, skills, context)
            if result_remote:
                if record:
                    self._record_use(result_remote)
                return result_remote

        # Fallback: use best embedding result even if low confidence
        low_threshold = max(threshold * _INTENT_CONFIG["low_threshold_factor"],
                           _INTENT_CONFIG["min_threshold"])
        if result and result.action != "chat" and result.confidence >= low_threshold:
            result.tier = "embedding_low"
            if record:
                self._record_use(result)
            return result

        # Default: chat
        return IntentResult(action="chat", confidence=0.5, tier="fallback")

    def _embedding_classify(self, user_msg: str) -> Optional[IntentResult]:
        """Classify using embeddings via KNN (preferred) or cosine fallback."""
        if not self._embedder.available or not self._skill_vectors:
            return None

        try:
            user_vec = self._embedder.encode([user_msg])[0]

            # Prefer KNN classifier when fitted
            if self._knn.available:
                result = self._knn.predict(user_vec)
                if result:
                    return IntentResult(
                        action=result["action"],
                        skill=result["skill"],
                        confidence=result["confidence"],
                        tier=f"knn_{self._embedder._mode}",
                        goal=user_msg,
                        all_scores=result["all_scores"],
                    )

            # Cosine fallback (when KNN not available or failed)
            return self._cosine_classify(user_vec, user_msg)
        except Exception:
            return None

    def _cosine_classify(self, user_vec, user_msg: str) -> Optional[IntentResult]:
        """Cosine similarity fallback classification."""
        scores = []
        for key, vec in self._skill_vectors.items():
            action, skill = key
            sim = self._embedder.similarity(user_vec, vec)
            scores.append((sim, action, skill))

        if not scores:
            return None

        scores.sort(reverse=True)
        top_sim, top_action, top_skill = scores[0]
        all_scores = {f"{a}:{s}": sim for sim, a, s in scores[:5]}
        conf = min(top_sim * 1.2, 0.95)

        # Handle configure action with target extraction
        category = ""
        target = ""
        if top_action == "configure":
            category = top_skill if top_skill else "llm"  # default to llm if empty
            target = self._extract_model_target(user_msg)
            top_skill = ""  # skill is empty for configure

        return IntentResult(
            action=top_action,
            skill=top_skill if top_action == "use" else "",
            confidence=conf,
            tier=f"embedding_{self._embedder._mode}",
            goal=user_msg,
            all_scores=all_scores,
            category=category,
            target=target,
        )

    def _extract_model_target(self, user_msg: str) -> str:
        """Extract model name/target from user message for configure intent."""
        import re
        ul = user_msg.lower()
        
        # Common model name patterns
        # Pattern 1: openrouter/namespace/model-name:variant (handles dots and colons like :free, :paid)
        # Match openrouter/ followed by namespace/model with optional :variant suffix
        openrouter_match = re.search(r'(openrouter/[a-z0-9\-]+/[a-z0-9\-\.:]+)', ul)
        if openrouter_match:
            return openrouter_match.group(1)
        
        # Pattern 2: namespace/model-name:variant without openrouter/ prefix
        # Match patterns like google/gemma-3-27b-it:free or moonshotai/kimi-k2.5
        model_match = re.search(r'([a-z][a-z0-9\-]*/[a-z][a-z0-9\-\.:]+)', ul)
        if model_match:
            model = model_match.group(1)
            # Add openrouter/ prefix if missing
            if not model.startswith("openrouter/"):
                return f"openrouter/{model}"
            return model
        
        # Pattern 3: just model name like "kimi-k2.5", "gemma-3-27b-it", "llama-3.3-70b" etc.
        simple_match = re.search(r'\b(gemma[\w\-\.:]*|qwen[\w\-\.:]*|llama[\w\-\.:]*|claude[\w\-\.:]*|gpt[\w\-\.:]*|kimi[\w\-\.:]*|deepseek[\w\-\.:]*|mistral[\w\-\.:]*)', ul)
        if simple_match:
            model = simple_match.group(1)
            return f"openrouter/{model}"
        
        return ""

    def _llm_classify(self, user_msg: str, skills: list, context: str) -> Optional[IntentResult]:
        """Classify using remote LLM (last resort)."""
        if not self._llm_client:
            return None
        
        # Simplified prompt for remote LLM
        skills_str = ", ".join(skills) if skills else "tts, stt, web_search"
        prompt = (
            f"Classify intent: skills=[{skills_str}], msg=\"{user_msg[:100]}\"\n"
            f'Respond JSON: {{"action":"use|create|evolve|chat","skill":"name","goal":"desc"}}'
        )
        
        try:
            # Try using llm_client.chat if available
            if hasattr(self._llm_client, 'chat'):
                response = self._llm_client.chat([{"role": "user", "content": prompt}])
                # Extract JSON from response
                import re, json
                m = re.search(r'\{[^}]+\}', response)
                if m:
                    d = json.loads(m.group())
                    return IntentResult(
                        action=d.get("action", "chat"),
                        skill=d.get("skill", ""),
                        confidence=0.75,
                        tier="remote_llm",
                        goal=d.get("goal", user_msg),
                    )
        except Exception:
            pass
        
        return None

    def _record_use(self, result: IntentResult):
        """Record successful classification for analytics."""
        # TODO: Could track usage patterns here
        pass

    def learn_from_correction(self, user_msg: str, wrong_action: str,
                              correct_action: str, correct_skill: str = ""):
        """Add a correction to training data."""
        self._training_data.append((user_msg, correct_action, correct_skill))
        self._save_training()
        self._rebuild_skill_vectors()

    def learn_from_success(self, user_msg: str, action: str, skill: str = ""):
        """Record a successful classification."""
        # Only add if not already similar to existing training
        if not self._is_similar_to_training(user_msg):
            self._training_data.append((user_msg, action, skill))
            self._save_training()
            self._rebuild_skill_vectors()

    def _is_similar_to_training(self, user_msg: str, threshold: float = 0.95) -> bool:
        """Check if user_msg is very similar to existing training examples."""
        if not self._embedder.available:
            return False
        
        try:
            user_vec = self._embedder.encode([user_msg])[0]
            for text, _, _ in self._training_data:
                text_vec = self._embedder.encode([text])[0]
                sim = self._embedder.similarity(user_vec, text_vec)
                if sim >= threshold:
                    return True
        except Exception:
            pass
        return False

    def _save_training(self):
        """Persist training data to file."""
        try:
            self._state_dir.mkdir(parents=True, exist_ok=True)
            data = [
                {"text": t, "action": a, "skill": s}
                for t, a, s in self._training_data
            ]
            with open(self._training_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def stats(self) -> Dict[str, Any]:
        """Return classifier statistics."""
        return {
            "training_examples": len(self._training_data),
            "embedding_mode": self._embedder._mode,
            "embedding_available": self._embedder.available,
            "local_llm_available": self._local_llm.available,
            "local_llm_model": self._local_llm._model,
        }

    def __repr__(self):
        s = self.stats()
        return (
            f"SmartIntent: {s['training_examples']} examples, "
            f"mode={s['embedding_mode']}, "
            f"local_llm={'✓ '+s['local_llm_model'] if s['local_llm_available'] else '✗'}"
        )


def create_smart_classifier(state_dir: Path = None,
                             llm_client=None) -> SmartIntentClassifier:
    """Factory function for creating SmartIntentClassifier."""
    return SmartIntentClassifier(
        state_dir=state_dir or Path.home() / ".evo-engine",
        llm_client=llm_client,
    )


# Backward compatibility: re-export from old location
__all__ = [
    "SmartIntentClassifier",
    "IntentResult",
    "create_smart_classifier",
    "EmbeddingEngine",
    "LocalLLMClassifier",
    "DEFAULT_TRAINING",
]
