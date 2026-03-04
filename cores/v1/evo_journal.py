#!/usr/bin/env python3
"""
evo-engine EvolutionJournal — tracks evolutionary iterations, quality scores,
reflections, and speed improvements across skill evolution cycles.

Provides data for:
  - Autonomous quality assessment after each evolution
  - Speed tracking (time per iteration, improvement rate)
  - Reflection log (what worked, what didn't, strategy adjustments)
  - Cross-iteration learning (avoid repeating failed strategies)

Storage: logs/evo_journal.jsonl (append-only, one JSON per line)
Summary: logs/evo_journal_summary.json (aggregated stats)
"""
import json
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, Dict, List

from .config import LOGS_DIR, cpr, C


class EvolutionEntry:
    """Single evolution attempt record."""

    def __init__(self, skill_name: str, iteration: int, goal: str):
        self.skill_name = skill_name
        self.iteration = iteration
        self.goal = goal
        self.started_at = time.time()
        self.finished_at: Optional[float] = None
        self.duration_ms: Optional[float] = None
        self.success = False
        self.quality_score: float = 0.0  # 0.0 - 1.0
        self.strategy: str = ""          # normal_evolve, auto_fix_imports, rewrite, etc.
        self.error: str = ""
        self.reflection: str = ""        # what the system learned
        self.code_size: int = 0
        self.test_passed: bool = False
        self.attempts: int = 0
        self.previous_score: float = 0.0  # score from previous iteration

    def finish(self, success: bool, quality_score: float = 0.0,
               reflection: str = "", error: str = ""):
        self.finished_at = time.time()
        self.duration_ms = (self.finished_at - self.started_at) * 1000
        self.success = success
        self.quality_score = quality_score
        self.reflection = reflection
        self.error = error

    def to_dict(self) -> dict:
        return {
            "skill": self.skill_name,
            "iteration": self.iteration,
            "goal": self.goal,
            "started_at": datetime.fromtimestamp(
                self.started_at, tz=timezone.utc).isoformat(),
            "duration_ms": round(self.duration_ms, 1) if self.duration_ms else None,
            "success": self.success,
            "quality_score": round(self.quality_score, 3),
            "previous_score": round(self.previous_score, 3),
            "improvement": round(self.quality_score - self.previous_score, 3),
            "strategy": self.strategy,
            "error": self.error[:500] if self.error else "",
            "reflection": self.reflection[:500] if self.reflection else "",
            "code_size": self.code_size,
            "test_passed": self.test_passed,
            "attempts": self.attempts,
        }


class EvolutionJournal:
    """
    Persistent journal for evolutionary cycles.

    Tracks:
      - Per-skill evolution history (iterations, scores, strategies)
      - Global patterns (which strategies work best)
      - Speed trends (faster iterations over time)
      - Reflection summaries (what to avoid, what to prefer)
    """

    JOURNAL_FILE = "evo_journal.jsonl"
    SUMMARY_FILE = "evo_journal_summary.json"

    def __init__(self):
        self._dir = LOGS_DIR / "evo"
        self._dir.mkdir(parents=True, exist_ok=True)
        self._journal_path = self._dir / self.JOURNAL_FILE
        self._summary_path = self._dir / self.SUMMARY_FILE
        self._current: Dict[str, EvolutionEntry] = {}  # skill -> active entry
        self._summary = self._load_summary()

    def _load_summary(self) -> dict:
        if self._summary_path.exists():
            try:
                return json.loads(self._summary_path.read_text())
            except Exception:
                pass
        return {
            "total_evolutions": 0,
            "total_successes": 0,
            "total_failures": 0,
            "avg_duration_ms": 0.0,
            "avg_quality": 0.0,
            "strategy_stats": {},       # strategy -> {count, success_rate}
            "skill_stats": {},          # skill -> {evolutions, best_score, avg_score}
            "failed_patterns": [],      # error patterns to avoid
            "successful_patterns": [],  # strategies that work
            "speed_trend": [],          # last 20 durations for trend
        }

    def _save_summary(self):
        try:
            self._summary_path.write_text(json.dumps(self._summary, indent=2))
        except Exception:
            pass

    def _append_entry(self, entry: EvolutionEntry):
        try:
            with open(self._journal_path, "a") as f:
                f.write(json.dumps(entry.to_dict()) + "\n")
        except Exception:
            pass

    # ── Public API ────────────────────────────────────────────────────

    def start_evolution(self, skill_name: str, goal: str,
                        strategy: str = "normal_evolve") -> EvolutionEntry:
        """Begin tracking an evolution cycle."""
        iteration = self._get_next_iteration(skill_name)
        entry = EvolutionEntry(skill_name, iteration, goal)
        entry.strategy = strategy
        entry.previous_score = self._get_last_score(skill_name)
        self._current[skill_name] = entry
        return entry

    def finish_evolution(self, skill_name: str, success: bool,
                         quality_score: float = 0.0,
                         reflection: str = "",
                         error: str = "",
                         code_size: int = 0,
                         test_passed: bool = False,
                         attempts: int = 1):
        """Complete an evolution cycle with results."""
        entry = self._current.pop(skill_name, None)
        if not entry:
            return
        entry.finish(success, quality_score, reflection, error)
        entry.code_size = code_size
        entry.test_passed = test_passed
        entry.attempts = attempts
        self._append_entry(entry)
        self._update_summary(entry)
        self._save_summary()

    def reflect(self, skill_name: str, result: dict, error: str = "") -> dict:
        """
        Generate reflection on evolution result.

        Returns:
            {
                "quality_score": float,
                "reflection": str,
                "suggested_strategy": str,
                "avoid_patterns": [str],
                "speed_assessment": str,
            }
        """
        score = self._compute_quality(skill_name, result)
        prev_score = self._get_last_score(skill_name)
        improvement = score - prev_score

        # Analyze what happened
        reflection_parts = []
        if score >= 0.8:
            reflection_parts.append("Wysoka jakość — skill działa poprawnie")
        elif score >= 0.5:
            reflection_parts.append("Częściowy sukces — skill wymaga dopracowania")
        else:
            reflection_parts.append("Niska jakość — potrzebna rewizja strategii")

        if improvement > 0.1:
            reflection_parts.append(f"Poprawa +{improvement:.2f} względem poprzedniej wersji")
        elif improvement < -0.1:
            reflection_parts.append(f"Regresja {improvement:.2f} — rozważ rollback")

        if error:
            reflection_parts.append(f"Błąd: {error[:100]}")

        # Strategy suggestion based on history
        suggested = self._suggest_strategy(skill_name, error, score)

        # Speed assessment
        speed_trend = self._summary.get("speed_trend", [])
        if len(speed_trend) >= 3:
            recent_avg = sum(speed_trend[-3:]) / 3
            older_avg = sum(speed_trend[:3]) / max(len(speed_trend[:3]), 1)
            if recent_avg < older_avg * 0.8:
                speed_note = "Przyspieszenie ewolucji"
            elif recent_avg > older_avg * 1.2:
                speed_note = "Spowolnienie — sprawdź model LLM"
            else:
                speed_note = "Stabilna prędkość"
        else:
            speed_note = "Za mało danych do oceny trendu"

        # Avoid patterns from history
        avoid = self._get_avoid_patterns(skill_name, error)

        return {
            "quality_score": score,
            "previous_score": prev_score,
            "improvement": improvement,
            "reflection": " | ".join(reflection_parts),
            "suggested_strategy": suggested,
            "avoid_patterns": avoid,
            "speed_assessment": speed_note,
        }

    def get_skill_history(self, skill_name: str, last_n: int = 10) -> List[dict]:
        """Get recent evolution history for a skill."""
        entries = []
        if not self._journal_path.exists():
            return entries
        try:
            lines = self._journal_path.read_text().strip().split("\n")
            for line in reversed(lines):
                if not line.strip():
                    continue
                entry = json.loads(line)
                if entry.get("skill") == skill_name:
                    entries.append(entry)
                    if len(entries) >= last_n:
                        break
        except Exception:
            pass
        return list(reversed(entries))

    def get_global_stats(self) -> dict:
        """Get aggregated evolution statistics."""
        s = self._summary
        total = s["total_evolutions"] or 1
        return {
            "total_evolutions": s["total_evolutions"],
            "success_rate": round(s["total_successes"] / total * 100, 1),
            "avg_duration_ms": round(s["avg_duration_ms"], 0),
            "avg_quality": round(s["avg_quality"], 3),
            "top_strategies": self._top_strategies(),
            "skills_evolved": len(s.get("skill_stats", {})),
            "speed_trend": s.get("speed_trend", [])[-5:],
        }

    def format_report(self) -> str:
        """Human-readable evolution report."""
        stats = self.get_global_stats()
        lines = [
            f"[EVO JOURNAL] Ewolucje: {stats['total_evolutions']} | "
            f"Sukces: {stats['success_rate']}% | "
            f"Śr. jakość: {stats['avg_quality']} | "
            f"Śr. czas: {stats['avg_duration_ms']}ms",
        ]
        top = stats.get("top_strategies", [])
        if top:
            lines.append(f"  Najlepsze strategie: {', '.join(f'{s[0]}({s[1]}%)' for s in top[:3])}")
        return "\n".join(lines)

    # ── Internal helpers ──────────────────────────────────────────────

    def _get_next_iteration(self, skill_name: str) -> int:
        stats = self._summary.get("skill_stats", {}).get(skill_name, {})
        return stats.get("evolutions", 0) + 1

    def _get_last_score(self, skill_name: str) -> float:
        stats = self._summary.get("skill_stats", {}).get(skill_name, {})
        return stats.get("last_score", 0.0)

    def _compute_quality(self, skill_name: str, result: dict) -> float:
        """Compute quality score from skill execution result."""
        score = 0.0

        # Base: did it succeed?
        if result.get("success"):
            score += 0.4
        inner = result.get("result", {})
        if isinstance(inner, dict) and inner.get("success"):
            score += 0.2

        # Test passing?
        if result.get("test_passed"):
            score += 0.2

        # No error messages?
        if not result.get("error") and not (
                isinstance(inner, dict) and inner.get("error")):
            score += 0.1

        # Has meaningful output?
        if isinstance(inner, dict):
            output_keys = {k for k in inner if k not in (
                "success", "error", "exit_code")}
            if output_keys:
                score += 0.1

        return min(score, 1.0)

    def _suggest_strategy(self, skill_name: str, error: str,
                          current_score: float) -> str:
        """Suggest best strategy based on history."""
        if not error:
            if current_score >= 0.8:
                return "keep"
            return "normal_evolve"

        el = error.lower()
        if "import" in el or "module" in el:
            return "auto_fix_imports"
        if "syntax" in el:
            return "rewrite_from_scratch"
        if "timeout" in el:
            return "optimize_performance"
        if "stub" in el or "not implemented" in el:
            return "rewrite_from_scratch"
        if "interface" in el or "get_info" in el or "health_check" in el:
            return "normal_evolve"  # needs LLM to add missing functions
        if "preflight" in el:
            return "normal_evolve"

        # Check history: which strategy worked best for this skill?
        history = self.get_skill_history(skill_name, 5)
        successful = [h for h in history if h.get("success")]
        if successful:
            strategies = [h["strategy"] for h in successful]
            if strategies:
                from collections import Counter
                return Counter(strategies).most_common(1)[0][0]

        return "normal_evolve"

    def _get_avoid_patterns(self, skill_name: str, error: str) -> List[str]:
        """Get error patterns to avoid from history."""
        history = self.get_skill_history(skill_name, 10)
        failed = [h for h in history if not h.get("success") and h.get("error")]
        patterns = []
        for h in failed[-3:]:
            err = h["error"][:80]
            if err and err not in patterns:
                patterns.append(err)
        return patterns

    def _top_strategies(self) -> List[tuple]:
        """Return top strategies by success rate."""
        stats = self._summary.get("strategy_stats", {})
        result = []
        for strategy, data in stats.items():
            count = data.get("count", 0)
            if count >= 2:  # min 2 attempts
                rate = round(data.get("successes", 0) / count * 100, 0)
                result.append((strategy, rate))
        result.sort(key=lambda x: x[1], reverse=True)
        return result[:5]

    def _update_summary(self, entry: EvolutionEntry):
        """Update running summary stats."""
        s = self._summary
        s["total_evolutions"] += 1
        if entry.success:
            s["total_successes"] += 1
        else:
            s["total_failures"] += 1

        # Running average duration
        n = s["total_evolutions"]
        if entry.duration_ms:
            s["avg_duration_ms"] = (
                s["avg_duration_ms"] * (n - 1) + entry.duration_ms) / n
            # Speed trend (last 50)
            trend = s.setdefault("speed_trend", [])
            trend.append(round(entry.duration_ms, 0))
            s["speed_trend"] = trend[-50:]

        # Running average quality
        s["avg_quality"] = (
            s["avg_quality"] * (n - 1) + entry.quality_score) / n

        # Strategy stats
        st = s.setdefault("strategy_stats", {}).setdefault(
            entry.strategy, {"count": 0, "successes": 0})
        st["count"] += 1
        if entry.success:
            st["successes"] += 1

        # Skill stats
        sk = s.setdefault("skill_stats", {}).setdefault(
            entry.skill_name, {
                "evolutions": 0, "best_score": 0.0,
                "avg_score": 0.0, "last_score": 0.0
            })
        sk["evolutions"] += 1
        sk["last_score"] = entry.quality_score
        if entry.quality_score > sk["best_score"]:
            sk["best_score"] = entry.quality_score
        sk["avg_score"] = (
            sk["avg_score"] * (sk["evolutions"] - 1) + entry.quality_score
        ) / sk["evolutions"]

        # Error patterns
        if not entry.success and entry.error:
            patterns = s.setdefault("failed_patterns", [])
            pattern = entry.error[:80]
            if pattern not in patterns:
                patterns.append(pattern)
            s["failed_patterns"] = patterns[-30:]

        # Successful patterns
        if entry.success and entry.strategy:
            patterns = s.setdefault("successful_patterns", [])
            if entry.strategy not in patterns:
                patterns.append(entry.strategy)
            s["successful_patterns"] = patterns[-20:]
