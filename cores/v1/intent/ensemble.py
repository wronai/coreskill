"""
EnsembleIntentClassifier — weighted voting across multiple classifiers.

Combines KNN, cosine-similarity, and local LLM votes with configurable weights
to produce a more robust final intent classification than any single classifier.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict


@dataclass
class Vote:
    """A single classifier's vote."""
    action: str
    skill: str = ""
    confidence: float = 0.0
    source: str = ""  # "knn", "cosine", "local_llm"


@dataclass
class EnsembleResult:
    """Combined ensemble result."""
    action: str
    skill: str = ""
    confidence: float = 0.0
    tier: str = "ensemble"
    votes: List[Vote] = field(default_factory=list)
    agreement: float = 0.0  # fraction of voters that agree with top pick


# Default weights per classifier source
DEFAULT_WEIGHTS = {
    "knn": 0.45,
    "cosine": 0.25,
    "local_llm": 0.30,
}


class EnsembleIntentClassifier:
    """Combine multiple classifier votes with weighted confidence.

    Usage:
        ensemble = EnsembleIntentClassifier()
        ensemble.add_vote(Vote(action="use", skill="tts", confidence=0.85, source="knn"))
        ensemble.add_vote(Vote(action="use", skill="tts", confidence=0.70, source="cosine"))
        ensemble.add_vote(Vote(action="chat", confidence=0.60, source="local_llm"))
        result = ensemble.decide()
        # → action="use", skill="tts", confidence=0.79, agreement=0.67
    """

    MIN_CONFIDENCE = 0.30  # below this, ignore the vote entirely

    def __init__(self, weights: Dict[str, float] = None):
        self._weights = weights or dict(DEFAULT_WEIGHTS)
        self._votes: List[Vote] = []

    def reset(self):
        """Clear all votes for a new classification round."""
        self._votes.clear()

    def add_vote(self, vote: Vote):
        """Add a classifier's vote."""
        if vote.confidence >= self.MIN_CONFIDENCE:
            self._votes.append(vote)

    def decide(self) -> Optional[EnsembleResult]:
        """Combine votes with weighted voting. Returns EnsembleResult or None."""
        if not self._votes:
            return None

        # Aggregate weighted scores per (action, skill) pair
        weighted_scores: Dict[Tuple[str, str], float] = defaultdict(float)
        total_weight = 0.0

        for vote in self._votes:
            w = self._weights.get(vote.source, 0.20)
            key = (vote.action, vote.skill or "")
            weighted_scores[key] += vote.confidence * w
            total_weight += w

        if total_weight == 0:
            return None

        # Normalize scores
        for key in weighted_scores:
            weighted_scores[key] /= total_weight

        # Find top candidate
        top_key = max(weighted_scores, key=weighted_scores.get)
        top_action, top_skill = top_key
        top_score = weighted_scores[top_key]

        # Calculate agreement: fraction of voters matching top pick
        matching = sum(1 for v in self._votes
                       if v.action == top_action and (v.skill or "") == top_skill)
        agreement = matching / len(self._votes)

        # Boost confidence when all classifiers agree
        if agreement == 1.0 and len(self._votes) >= 2:
            top_score = min(top_score * 1.1, 0.98)

        return EnsembleResult(
            action=top_action,
            skill=top_skill if top_action == "use" else "",
            confidence=round(top_score, 4),
            tier="ensemble",
            votes=list(self._votes),
            agreement=round(agreement, 2),
        )
