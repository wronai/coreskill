#!/usr/bin/env python3
"""
UCB1 BanditProviderSelector — exploration/exploitation balancer for provider selection.

Uses Upper Confidence Bound (UCB1) algorithm to balance:
- Exploitation: prefer providers with high success rates
- Exploration: try less-used providers to discover if they've improved

Wraps ProviderChain, adding UCB1 scoring as an overlay on top of
the existing score-based selection.
"""
import math
import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ArmStats:
    """Stats for a single UCB1 arm (provider)."""
    pulls: int = 0           # total times selected
    successes: int = 0       # successful executions
    total_reward: float = 0.0  # cumulative reward (quality score sum)
    last_pull: float = 0.0

    @property
    def mean_reward(self) -> float:
        return self.total_reward / self.pulls if self.pulls > 0 else 0.0

    @property
    def success_rate(self) -> float:
        return self.successes / self.pulls if self.pulls > 0 else 0.0


class UCB1BanditSelector:
    """UCB1-based provider selection overlay.

    Usage:
        bandit = UCB1BanditSelector()
        provider = bandit.select("tts", ["espeak", "coqui", "pyttsx3"])
        # ... execute with provider ...
        bandit.record("tts", "espeak", reward=0.8)

    The UCB1 score for each arm is:
        UCB1 = mean_reward + C * sqrt(ln(total_pulls) / arm_pulls)

    Where C controls exploration (higher C = more exploration).
    """

    C = 1.41  # exploration constant (sqrt(2) is theoretically optimal)
    MIN_PULLS = 2  # each arm gets at least this many pulls before UCB1 kicks in

    def __init__(self):
        # {(capability, provider): ArmStats}
        self._arms: Dict[Tuple[str, str], ArmStats] = {}
        self._total_pulls: Dict[str, int] = {}  # per capability

    def _key(self, cap: str, prov: str) -> Tuple[str, str]:
        return (cap, prov)

    def _get_arm(self, cap: str, prov: str) -> ArmStats:
        k = self._key(cap, prov)
        if k not in self._arms:
            self._arms[k] = ArmStats()
        return self._arms[k]

    def select(self, capability: str, providers: List[str],
               base_scores: Optional[Dict[str, float]] = None) -> str:
        """Select a provider using UCB1.

        Args:
            capability: e.g. "tts"
            providers: list of available provider names
            base_scores: optional dict of {provider: base_score} from ProviderSelector

        Returns:
            Selected provider name.
        """
        if not providers:
            return "default"
        if len(providers) == 1:
            return providers[0]

        total = self._total_pulls.get(capability, 0)

        # Phase 1: ensure each arm has MIN_PULLS (pure exploration)
        for prov in providers:
            arm = self._get_arm(capability, prov)
            if arm.pulls < self.MIN_PULLS:
                return prov

        # Phase 2: UCB1 selection
        best_prov = providers[0]
        best_ucb = -1.0

        for prov in providers:
            arm = self._get_arm(capability, prov)
            ucb = self._ucb1_score(arm, total, base_scores.get(prov, 0) if base_scores else 0)
            if ucb > best_ucb:
                best_ucb = ucb
                best_prov = prov

        return best_prov

    def _ucb1_score(self, arm: ArmStats, total_pulls: int,
                    base_score: float = 0) -> float:
        """Compute UCB1 score for an arm."""
        if arm.pulls == 0:
            return float('inf')  # unexplored = highest priority

        exploitation = arm.mean_reward
        exploration = self.C * math.sqrt(math.log(max(total_pulls, 1)) / arm.pulls)

        # Blend with base score (from ProviderSelector) if available
        # Normalize base_score to 0..1 range (typically 0..50)
        base_normalized = min(base_score / 50.0, 1.0) if base_score > 0 else 0

        return exploitation * 0.6 + exploration * 0.3 + base_normalized * 0.1

    def record(self, capability: str, provider: str, reward: float = 1.0,
               success: bool = True):
        """Record the outcome of using a provider.

        Args:
            capability: e.g. "tts"
            provider: provider that was used
            reward: quality score 0.0..1.0
            success: whether the execution succeeded
        """
        arm = self._get_arm(capability, provider)
        arm.pulls += 1
        arm.total_reward += reward
        arm.last_pull = time.time()
        if success:
            arm.successes += 1

        # Track total pulls per capability
        self._total_pulls[capability] = self._total_pulls.get(capability, 0) + 1

    def get_stats(self, capability: str, provider: str) -> Dict:
        """Get stats for a specific provider."""
        arm = self._get_arm(capability, provider)
        total = self._total_pulls.get(capability, 0)
        ucb = self._ucb1_score(arm, total) if arm.pulls > 0 else float('inf')
        return {
            "provider": provider,
            "pulls": arm.pulls,
            "successes": arm.successes,
            "success_rate": round(arm.success_rate, 3),
            "mean_reward": round(arm.mean_reward, 3),
            "ucb1_score": round(ucb, 3) if ucb != float('inf') else "inf",
        }

    def summary(self, capability: str, providers: List[str]) -> str:
        """Human-readable summary for a capability."""
        total = self._total_pulls.get(capability, 0)
        parts = [f"{capability} (total={total}):"]
        for prov in providers:
            s = self.get_stats(capability, prov)
            parts.append(
                f"  {prov}: pulls={s['pulls']}, "
                f"success={s['success_rate']:.0%}, "
                f"reward={s['mean_reward']:.2f}, "
                f"ucb1={s['ucb1_score']}"
            )
        return "\n".join(parts)

    def reset(self, capability: Optional[str] = None):
        """Reset stats. If capability given, reset only that capability."""
        if capability:
            keys_to_remove = [k for k in self._arms if k[0] == capability]
            for k in keys_to_remove:
                del self._arms[k]
            self._total_pulls.pop(capability, None)
        else:
            self._arms.clear()
            self._total_pulls.clear()
