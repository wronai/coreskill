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


@dataclass
class IntentResult:
    """Result of intent classification."""
    action: str  # use, create, evolve, chat
    skill: str = ""  # skill name for 'use' action
    confidence: float = 0.0
    tier: str = "unknown"  # embedding, local_llm, remote_llm, fallback
    goal: str = ""  # human-readable intent description
    input: Dict[str, Any] = field(default_factory=dict)  # skill params
    all_scores: Dict[str, float] = field(default_factory=dict)  # all skill scores


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
        """Precompute embeddings for training examples by (action, skill)."""
        if not self._embedder.available:
            return
        
        # Group by (action, skill)
        from collections import defaultdict
        groups = defaultdict(list)
        for text, action, skill in self._training_data:
            key = (action, skill or "")
            groups[key].append(text)
        
        # Average embedding per group
        self._skill_vectors = {}
        for key, texts in groups.items():
            if texts:
                try:
                    vecs = self._embedder.encode(texts)
                    import numpy as np
                    avg = np.mean(vecs, axis=0)
                    self._skill_vectors[key] = avg
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

        # Tier 1: Embedding similarity
        result = self._embedding_classify(user_msg)
        threshold = self._MODE_THRESHOLDS.get(
            self._embedder._mode or "bow",
            self.CONFIDENCE_THRESHOLD
        )
        
        if result and result.confidence >= threshold:
            if record:
                self._record_use(result)
            return result

        # Tier 2: Local LLM (if available)
        if self._local_llm.available:
            result_local = self._local_llm.classify(user_msg, skills, context)
            if result_local:
                if record:
                    self._record_use(result_local)
                return result_local

        # Tier 3: Remote LLM fallback
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
        """Classify using embeddings (sbert/tf-idf/bow)."""
        if not self._embedder.available or not self._skill_vectors:
            return None

        try:
            import numpy as np
            user_vec = self._embedder.encode([user_msg])[0]
            
            # Cosine similarity to all skill vectors
            scores = []
            for key, vec in self._skill_vectors.items():
                action, skill = key
                sim = self._embedder.similarity(user_vec, vec)
                scores.append((sim, action, skill))
            
            if not scores:
                return None
            
            scores.sort(reverse=True)
            top_sim, top_action, top_skill = scores[0]
            
            # Build all_scores dict
            all_scores = {f"{a}:{s}": sim for sim, a, s in scores[:5]}
            
            # Normalize confidence based on embedding mode
            conf = min(top_sim * 1.2, 0.95)  # Scale up slightly
            
            return IntentResult(
                action=top_action,
                skill=top_skill if top_action == "use" else "",
                confidence=conf,
                tier=f"embedding_{self._embedder._mode}",
                goal=user_msg,
                all_scores=all_scores,
            )
        except Exception:
            return None

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
