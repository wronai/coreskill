#!/usr/bin/env python3
"""
LearnedRepairStrategy — DecisionTree-based repair strategy selection.

Learns from past repair attempts (via RepairJournal) which strategy
works best for each issue type, replacing the hardcoded if/elif chain
in AutoRepair._plan_strategy().

Falls back to rule-based strategy when insufficient training data.
"""
import numpy as np
from typing import Optional, Dict, List, Tuple
from pathlib import Path

try:
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.preprocessing import LabelEncoder
    _HAS_SKLEARN = True
except ImportError:
    _HAS_SKLEARN = False


# Feature indices for the decision tree
ISSUE_TYPES = ["markdown", "syntax", "imports", "interface", "stub", "missing_dep", "read_error"]
STRATEGIES = ["strip_markdown", "auto_fix_imports", "add_interface", "pip_install",
              "rewrite_from_backup", "skip"]


class LearnedRepairStrategy:
    """DecisionTree that predicts best repair strategy from issue features.

    Features:
        - issue_type (encoded)
        - attempt_number (1-based)
        - severity_encoded (critical=2, high=1, medium=0)
        - has_skill_manager (0/1)

    Target:
        - strategy name

    Training data comes from RepairJournal entries.
    """

    MIN_TRAINING = 10  # minimum samples to fit the tree

    def __init__(self):
        self._tree = None
        self._issue_encoder = LabelEncoder() if _HAS_SKLEARN else None
        self._strategy_encoder = LabelEncoder() if _HAS_SKLEARN else None
        self._fitted = False
        self._train_count = 0

    @property
    def available(self) -> bool:
        return _HAS_SKLEARN and self._fitted

    def fit(self, records: List[Dict]):
        """Fit the tree from repair journal records.

        Each record should have:
            issue_type, strategy, attempt, severity, success, has_sm
        """
        if not _HAS_SKLEARN or len(records) < self.MIN_TRAINING:
            self._fitted = False
            return

        # Only learn from successful repairs
        successful = [r for r in records if r.get("success")]
        if len(successful) < self.MIN_TRAINING // 2:
            self._fitted = False
            return

        X = []
        y = []
        for r in successful:
            features = self._extract_features(r)
            if features is not None:
                X.append(features)
                y.append(r["strategy"])

        if len(X) < self.MIN_TRAINING // 2:
            self._fitted = False
            return

        X = np.array(X)

        # Encode strategies
        self._strategy_encoder.fit(STRATEGIES + list(set(y)))
        y_encoded = self._strategy_encoder.transform(y)

        self._tree = DecisionTreeClassifier(
            max_depth=5,
            min_samples_leaf=2,
            random_state=42,
        )
        self._tree.fit(X, y_encoded)
        self._fitted = True
        self._train_count = len(X)

    def predict(self, issue_type: str, attempt: int = 1,
                severity: str = "high", has_sm: bool = True) -> Optional[str]:
        """Predict the best strategy for a repair task.

        Returns strategy name or None if not fitted.
        """
        if not self._fitted or self._tree is None:
            return None

        features = self._extract_features({
            "issue_type": issue_type,
            "attempt": attempt,
            "severity": severity,
            "has_sm": has_sm,
        })
        if features is None:
            return None

        X = np.array([features])
        pred_idx = self._tree.predict(X)[0]

        try:
            return self._strategy_encoder.inverse_transform([pred_idx])[0]
        except (ValueError, IndexError):
            return None

    def predict_with_confidence(self, issue_type: str, attempt: int = 1,
                                severity: str = "high",
                                has_sm: bool = True) -> Optional[Dict]:
        """Predict with probability estimates."""
        if not self._fitted or self._tree is None:
            return None

        features = self._extract_features({
            "issue_type": issue_type,
            "attempt": attempt,
            "severity": severity,
            "has_sm": has_sm,
        })
        if features is None:
            return None

        X = np.array([features])
        proba = self._tree.predict_proba(X)[0]
        classes = self._strategy_encoder.classes_

        # Top predictions sorted by probability
        scored = sorted(zip(classes, proba), key=lambda x: -x[1])
        top_strategy, top_conf = scored[0]

        return {
            "strategy": top_strategy,
            "confidence": float(top_conf),
            "alternatives": {s: float(p) for s, p in scored[:3] if p > 0.05},
        }

    def _extract_features(self, record: Dict) -> Optional[np.ndarray]:
        """Extract feature vector from a record."""
        issue = record.get("issue_type", "")
        if issue in ISSUE_TYPES:
            issue_idx = ISSUE_TYPES.index(issue)
        else:
            issue_idx = len(ISSUE_TYPES)  # unknown

        severity_map = {"critical": 2, "high": 1, "medium": 0}
        sev = severity_map.get(record.get("severity", "high"), 1)

        return np.array([
            issue_idx,
            min(record.get("attempt", 1), 5),
            sev,
            1 if record.get("has_sm", True) else 0,
        ], dtype=float)

    def summary(self) -> str:
        if not self._fitted:
            return "LearnedRepair: not fitted (insufficient data)"
        return f"LearnedRepair: fitted on {self._train_count} samples, depth={self._tree.get_depth()}"


# ── Rule-based fallback (original logic from AutoRepair._plan_strategy) ──

def rule_based_strategy(issue_type: str, attempt: int, has_sm: bool = True) -> str:
    """Original hardcoded strategy selection (used as fallback)."""
    if issue_type == "markdown":
        return "strip_markdown"

    if issue_type == "syntax":
        if attempt == 1:
            return "strip_markdown"
        if attempt == 2 and has_sm:
            return "rewrite_from_backup"
        return "skip"

    if issue_type == "imports":
        if attempt <= 2:
            return "auto_fix_imports"
        return "pip_install"

    if issue_type == "interface":
        if attempt == 1:
            return "add_interface"
        return "skip"

    if issue_type == "stub":
        return "skip"

    if issue_type == "missing_dep":
        return "pip_install"

    return "skip"
