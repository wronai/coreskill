"""metrics_analyzer.py — Analysis and anomaly detection for metrics."""
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .metrics_types import SkillMetric, SystemHealthSnapshot
from .metrics_storage import MetricsStorage, METRICS_DIR


class MetricsAnalyzer:
    """Analyzes metrics and detects anomalies."""
    
    def __init__(self, storage: MetricsStorage = None):
        self.storage = storage or MetricsStorage()
    
    # ── Skill Health Analysis ───────────────────────────────────────────
    
    def analyze_skill_health(self, skill_name: str, last_n: int = 50) -> dict:
        """Get health summary for a skill."""
        metrics = self.storage.read_skill_metrics(skill_name, last_n)
        if not metrics:
            return {"status": "unknown", "executions": 0}
        
        total = len(metrics)
        successes = sum(1 for m in metrics if m.success)
        avg_duration = sum(m.duration_ms for m in metrics) / total
        avg_quality = sum(m.quality_score for m in metrics) / total
        
        success_rate = successes / total
        if success_rate >= 0.95 and avg_quality >= 0.7:
            status = "healthy"
        elif success_rate >= 0.8:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "executions": total,
            "success_rate": round(success_rate, 2),
            "avg_duration_ms": round(avg_duration, 2),
            "avg_quality": round(avg_quality, 2),
            "last_execution": metrics[-1].timestamp if metrics else None
        }
    
    def analyze_operation_stats(self, operation: str, last_n: int = 100) -> dict:
        """Get statistics for a specific operation type."""
        from .metrics_storage import OPERATIONS_FILE
        import json
        
        metrics = []
        if not OPERATIONS_FILE.exists():
            return {"count": 0, "avg_duration": 0, "success_rate": 0}
        
        with open(OPERATIONS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("operation") == operation:
                        metrics.append(data)
                except (json.JSONDecodeError, TypeError):
                    continue
        
        recent = metrics[-last_n:]
        if not recent:
            return {"count": 0, "avg_duration": 0, "success_rate": 0}
        
        total = len(recent)
        successes = sum(1 for m in recent if m.get("success"))
        avg_duration = sum(m.get("duration_ms", 0) for m in recent) / total
        
        return {
            "count": total,
            "avg_duration_ms": round(avg_duration, 2),
            "success_rate": round(successes / total, 2),
            "last_timestamp": recent[-1].get("timestamp")
        }
    
    # ── System Health Computation ───────────────────────────────────────
    
    def compute_system_health(self, skills_dir: Path) -> SystemHealthSnapshot:
        """Compute current system health from all metrics."""
        from .skill_schema import get_schema_validation_stats
        
        total_skills = self._count_skills(skills_dir)
        manifest_stats = get_schema_validation_stats(skills_dir)
        
        cutoff = time.time() - 24 * 3600
        recent_metrics = self._get_recent_skill_metrics(cutoff)
        
        avg_quality, success_rate = self._calculate_skill_stats(recent_metrics)
        top_errors = self._get_top_errors(recent_metrics)
        slowest = self._get_slowest_skills(recent_metrics)
        reflection_count = self.storage.count_operations_since("reflect", cutoff)
        
        return SystemHealthSnapshot(
            timestamp=datetime.now(timezone.utc).isoformat(),
            total_skills=total_skills,
            valid_manifests=manifest_stats["valid"],
            avg_quality_score=round(avg_quality, 3),
            success_rate_24h=round(success_rate, 3),
            reflection_count_24h=reflection_count,
            top_errors=[{"error": e, "count": c} for e, c in top_errors],
            slowest_skills=[{"skill": s, "avg_ms": round(d, 2)} for s, d in slowest]
        )
    
    def _count_skills(self, skills_dir: Path) -> int:
        """Count total skills in skills directory."""
        if not skills_dir.exists():
            return 0
        return sum(1 for d in skills_dir.iterdir() 
                   if d.is_dir() and not d.name.startswith("."))
    
    def _get_recent_skill_metrics(self, cutoff: float) -> list[SkillMetric]:
        """Get skill metrics from last 24 hours."""
        import json
        from .metrics_storage import SKILL_METRICS_FILE
        
        recent_metrics = []
        if not SKILL_METRICS_FILE.exists():
            return recent_metrics
        
        with open(SKILL_METRICS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    ts = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                    if ts.timestamp() > cutoff:
                        recent_metrics.append(SkillMetric(**data))
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        return recent_metrics
    
    def _calculate_skill_stats(self, metrics: list[SkillMetric]) -> tuple[float, float]:
        """Calculate avg quality and success rate from metrics."""
        if not metrics:
            return 0.0, 0.0
        avg_quality = sum(m.quality_score for m in metrics) / len(metrics)
        successes = sum(1 for m in metrics if m.success)
        success_rate = successes / len(metrics)
        return avg_quality, success_rate
    
    def _get_top_errors(self, metrics: list[SkillMetric], limit: int = 5) -> list[tuple[str, int]]:
        """Get most frequent errors from metrics."""
        error_counts = {}
        for m in metrics:
            if m.error:
                error_counts[m.error] = error_counts.get(m.error, 0) + 1
        return sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    def _get_slowest_skills(self, metrics: list[SkillMetric], limit: int = 5) -> list[tuple[str, float]]:
        """Get skills with highest average duration."""
        skill_durations = {}
        for m in metrics:
            if m.skill_name not in skill_durations:
                skill_durations[m.skill_name] = []
            skill_durations[m.skill_name].append(m.duration_ms)
        
        avg_by_skill = {
            name: sum(durs) / len(durs) 
            for name, durs in skill_durations.items()
        }
        return sorted(avg_by_skill.items(), key=lambda x: x[1], reverse=True)[:limit]
    
    # ── Anomaly Detection ────────────────────────────────────────────────
    
    def get_anomalies(self, window_minutes: int = 60) -> list:
        """Detect anomalies in the last time window.
        
        Types: success_rate_drop, latency_spike, error_storm.
        """
        anomalies = []
        now = time.time()
        cutoff = now - (window_minutes * 60)
        
        tracked = self.storage.list_tracked_skills()
        for skill_name in tracked:
            metrics = self.storage.read_skill_metrics_since(skill_name, cutoff)
            if not metrics:
                continue
            
            total = len(metrics)
            
            # 1. Success rate drop (>20% below baseline)
            recent_rate = sum(1 for m in metrics if m.success) / total
            baseline = self._get_baseline_rate(skill_name)
            if baseline is not None and baseline > 0 and recent_rate < baseline - 0.20:
                anomalies.append({
                    "skill_name": skill_name,
                    "type": "success_rate_drop",
                    "severity": "high",
                    "description": (
                        f"{skill_name}: success rate {recent_rate:.0%} "
                        f"(baseline {baseline:.0%}, drop >20%)"
                    ),
                    "value": recent_rate,
                    "baseline": baseline,
                })
            
            # 2. Latency spike (p95 > 2x baseline)
            latencies = [m.duration_ms for m in metrics if m.duration_ms]
            if len(latencies) >= 5:
                p95 = sorted(latencies)[int(len(latencies) * 0.95)]
                baseline_p95 = self._get_baseline_p95(skill_name)
                if baseline_p95 and baseline_p95 > 0 and p95 > baseline_p95 * 2:
                    anomalies.append({
                        "skill_name": skill_name,
                        "type": "latency_spike",
                        "severity": "medium",
                        "description": f"{skill_name}: p95={p95:.0f}ms (baseline {baseline_p95:.0f}ms)",
                        "value": p95,
                        "baseline": baseline_p95,
                    })
            
            # 3. Error storm (>=5 errors in window)
            errors = [m for m in metrics if not m.success]
            if len(errors) >= 5:
                anomalies.append({
                    "skill_name": skill_name,
                    "type": "error_storm",
                    "severity": "critical",
                    "description": f"{skill_name}: {len(errors)} errors in {window_minutes}min",
                    "value": len(errors),
                    "baseline": None,
                })
        
        return anomalies
    
    def _get_baseline_rate(self, skill_name: str) -> Optional[float]:
        """Get baseline success rate from older metrics (before last hour)."""
        now = time.time()
        old_cutoff = now - 24 * 3600
        recent_cutoff = now - 3600
        
        metrics = []
        for m in self.storage.read_skill_metrics(skill_name, last_n=1000):
            try:
                ts = datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))
                t = ts.timestamp()
                if old_cutoff <= t < recent_cutoff:
                    metrics.append(m.success)
            except (ValueError, AttributeError):
                continue
        
        if len(metrics) < 3:
            return None
        return sum(1 for s in metrics if s) / len(metrics)
    
    def _get_baseline_p95(self, skill_name: str) -> Optional[float]:
        """Get baseline p95 latency from older metrics."""
        now = time.time()
        old_cutoff = now - 24 * 3600
        recent_cutoff = now - 3600
        
        latencies = []
        for m in self.storage.read_skill_metrics(skill_name, last_n=1000):
            try:
                ts = datetime.fromisoformat(m.timestamp.replace("Z", "+00:00"))
                t = ts.timestamp()
                if old_cutoff <= t < recent_cutoff and m.duration_ms:
                    latencies.append(m.duration_ms)
            except (ValueError, AttributeError):
                continue
        
        if len(latencies) < 5:
            return None
        return sorted(latencies)[int(len(latencies) * 0.95)]
    
    # ── Summary Interface ─────────────────────────────────────────────────
    
    def get_summary(self, snapshot: SystemHealthSnapshot = None) -> dict:
        """Get a human-readable summary of current metrics."""
        if snapshot is None:
            snapshot = self.storage.load_system_snapshot()
        if not snapshot:
            return {"status": "no_data"}
        
        return {
            "timestamp": snapshot.timestamp,
            "skills": {
                "total": snapshot.total_skills,
                "valid_manifests": snapshot.valid_manifests,
                "manifest_coverage": f"{snapshot.valid_manifests}/{snapshot.total_skills}"
            },
            "health": {
                "success_rate_24h": f"{snapshot.success_rate_24h*100:.1f}%",
                "avg_quality": f"{snapshot.avg_quality_score:.2f}",
                "reflections_24h": snapshot.reflection_count_24h
            },
            "issues": {
                "top_errors": snapshot.top_errors,
                "slowest_skills": snapshot.slowest_skills
            }
        }
