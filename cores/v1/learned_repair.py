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


# ── TieredRepair — 5-level escalation strategy ──────────────────────

class TieredRepair:
    """5-level repair escalation: each tier is progressively more aggressive.

    Tier 1 — Quick Fix:       strip_markdown, auto_fix_imports
    Tier 2 — Structural:      add_interface, rewrite_from_backup
    Tier 3 — Dependency:      pip_install
    Tier 4 — LLM-Assisted:    ask_llm_diagnosis + apply suggestion
    Tier 5 — Full Rewrite:    request complete skill rewrite via LLM

    Usage:
        tiered = TieredRepair()
        strategy = tiered.select(issue_type, attempt, severity, has_sm)
    """

    # Each tier: list of (issue_types_that_apply, strategy)
    TIERS = [
        # Tier 1: Quick Fix (cheap, safe)
        {
            "name": "quick_fix",
            "strategies": {
                "markdown": "strip_markdown",
                "syntax": "strip_markdown",
                "imports": "auto_fix_imports",
            },
        },
        # Tier 2: Structural Repair (moderate cost)
        {
            "name": "structural",
            "strategies": {
                "syntax": "rewrite_from_backup",
                "interface": "add_interface",
                "stub": "rewrite_from_backup",
            },
        },
        # Tier 3: Dependency Repair (external side-effect)
        {
            "name": "dependency",
            "strategies": {
                "imports": "pip_install",
                "missing_dep": "pip_install",
            },
        },
        # Tier 4: LLM-Assisted (expensive, uncertain)
        {
            "name": "llm_assisted",
            "strategies": {
                "syntax": "llm_diagnose",
                "imports": "llm_diagnose",
                "interface": "llm_diagnose",
                "stub": "llm_diagnose",
                "read_error": "llm_diagnose",
            },
        },
        # Tier 5: Full Rewrite (last resort)
        {
            "name": "full_rewrite",
            "strategies": {
                "syntax": "llm_rewrite",
                "imports": "llm_rewrite",
                "interface": "llm_rewrite",
                "stub": "llm_rewrite",
                "markdown": "llm_rewrite",
            },
        },
    ]

    def __init__(self):
        self._tier_attempts = {}  # (skill, issue) → current tier index

    def select(self, issue_type: str, attempt: int = 1,
               severity: str = "high", has_sm: bool = True,
               skill_name: str = "") -> str:
        """Select repair strategy based on escalation tier.

        Each call for the same (skill, issue) escalates to the next tier.
        Critical severity starts at tier 2.
        """
        key = (skill_name, issue_type)

        # Determine starting tier
        if key not in self._tier_attempts:
            start = 1 if severity != "critical" else 2
            self._tier_attempts[key] = start - 1  # 0-indexed

        tier_idx = self._tier_attempts[key]

        # Walk tiers from current level until we find a matching strategy
        while tier_idx < len(self.TIERS):
            tier = self.TIERS[tier_idx]
            strategy = tier["strategies"].get(issue_type)

            # Skip tiers that need SkillManager if unavailable
            if strategy in ("rewrite_from_backup",) and not has_sm:
                tier_idx += 1
                continue

            if strategy:
                self._tier_attempts[key] = tier_idx + 1  # escalate next time
                return strategy

            tier_idx += 1

        # All tiers exhausted
        self._tier_attempts[key] = 0  # reset for next repair cycle
        return "skip"

    def current_tier(self, skill_name: str, issue_type: str) -> int:
        """Return the current tier (1-based) for a skill/issue pair."""
        return self._tier_attempts.get((skill_name, issue_type), 0) + 1

    def reset(self, skill_name: str = "", issue_type: str = ""):
        """Reset escalation state. No args = reset all."""
        if skill_name and issue_type:
            self._tier_attempts.pop((skill_name, issue_type), None)
        elif not skill_name and not issue_type:
            self._tier_attempts.clear()

    def summary(self) -> str:
        if not self._tier_attempts:
            return "TieredRepair: no active escalations"
        lines = ["TieredRepair escalation state:"]
        for (skill, issue), tier_idx in sorted(self._tier_attempts.items()):
            tier_name = self.TIERS[min(tier_idx, len(self.TIERS) - 1)]["name"]
            lines.append(f"  {skill}/{issue}: tier {tier_idx + 1} ({tier_name})")
        return "\n".join(lines)
