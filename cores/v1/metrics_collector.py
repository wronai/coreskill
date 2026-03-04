#!/usr/bin/env python3
"""
metrics_collector.py — Permanent metrics collection for CoreSkill.

Collects and persists performance metrics to enable continuous improvement.
Integrates with skill lifecycle, quality gates, and reflection engine.

Storage:
- logs/metrics/skill_metrics.jsonl — Per-skill metrics over time
- logs/metrics/system_metrics.json — Aggregated system health
- logs/metrics/operations.jsonl — Individual operation timings
"""
import json
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .config import LOGS_DIR, get_config_value


METRICS_DIR = LOGS_DIR / "metrics"
SKILL_METRICS_FILE = METRICS_DIR / "skill_metrics.jsonl"
SYSTEM_METRICS_FILE = METRICS_DIR / "system_metrics.json"
OPERATIONS_FILE = METRICS_DIR / "operations.jsonl"


# ─── Metric Types ────────────────────────────────────────────────────────

@dataclass
class SkillMetric:
    """Metrics for a single skill execution."""
    timestamp: str
    skill_name: str
    version: str
    duration_ms: float
    success: bool
    quality_score: float
    intent_match: Optional[str] = None  # Which intent triggered this skill
    error: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


@dataclass
class OperationMetric:
    """Metrics for internal operations (evolve, create, validate, etc)."""
    timestamp: str
    operation: str  # 'evolve', 'create', 'validate', 'reflect', 'repair'
    duration_ms: float
    success: bool
    details: dict = field(default_factory=dict)
    error: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


@dataclass
class SystemHealthSnapshot:
    """System-wide health snapshot."""
    timestamp: str
    total_skills: int
    valid_manifests: int
    avg_quality_score: float
    success_rate_24h: float  # % of successful skill executions
    reflection_count_24h: int
    top_errors: list  # Most common errors in last 24h
    slowest_skills: list  # Skills with highest avg duration


# ─── Metrics Collector ─────────────────────────────────────────────────

class MetricsCollector:
    """Collect and persist performance metrics."""
    
    def __init__(self, enabled: bool = None):
        self.enabled = enabled if enabled is not None else get_config_value(
            "autonomy.enable_metrics_collection", True
        )
        self._ensure_dirs()
    
    def _ensure_dirs(self) -> None:
        """Ensure metrics directories exist."""
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
    
    # ── Skill Metrics ────────────────────────────────────────────────────
    
    def record_skill_execution(self,
                                skill_name: str,
                                version: str,
                                duration_ms: float,
                                success: bool,
                                quality_score: float = 0.0,
                                intent_match: str = None,
                                error: str = None) -> None:
        """Record metrics for a skill execution."""
        if not self.enabled:
            return
        
        metric = SkillMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            skill_name=skill_name,
            version=version,
            duration_ms=duration_ms,
            success=success,
            quality_score=quality_score,
            intent_match=intent_match,
            error=error
        )
        
        with open(SKILL_METRICS_FILE, "a") as f:
            f.write(metric.to_json() + "\n")
    
    def get_skill_metrics(self, skill_name: str, last_n: int = 100) -> list[SkillMetric]:
        """Get recent metrics for a specific skill."""
        metrics = []
        if not SKILL_METRICS_FILE.exists():
            return metrics
        
        with open(SKILL_METRICS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("skill_name") == skill_name:
                        metrics.append(SkillMetric(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return metrics[-last_n:]
    
    def get_skill_health(self, skill_name: str) -> dict:
        """Get health summary for a skill."""
        metrics = self.get_skill_metrics(skill_name, last_n=50)
        if not metrics:
            return {"status": "unknown", "executions": 0}
        
        total = len(metrics)
        successes = sum(1 for m in metrics if m.success)
        avg_duration = sum(m.duration_ms for m in metrics) / total
        avg_quality = sum(m.quality_score for m in metrics) / total
        
        # Status based on success rate
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
    
    # ── Operation Metrics ───────────────────────────────────────────────
    
    def record_operation(self,
                         operation: str,
                         duration_ms: float,
                         success: bool,
                         details: dict = None,
                         error: str = None) -> None:
        """Record an internal operation metric."""
        if not self.enabled:
            return
        
        metric = OperationMetric(
            timestamp=datetime.now(timezone.utc).isoformat(),
            operation=operation,
            duration_ms=duration_ms,
            success=success,
            details=details or {},
            error=error
        )
        
        with open(OPERATIONS_FILE, "a") as f:
            f.write(metric.to_json() + "\n")
    
    def get_operation_stats(self, operation: str, last_n: int = 100) -> dict:
        """Get statistics for a specific operation type."""
        metrics = []
        if not OPERATIONS_FILE.exists():
            return {"count": 0, "avg_duration": 0, "success_rate": 0}
        
        with open(OPERATIONS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("operation") == operation:
                        metrics.append(OperationMetric(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        
        recent = metrics[-last_n:]
        if not recent:
            return {"count": 0, "avg_duration": 0, "success_rate": 0}
        
        total = len(recent)
        successes = sum(1 for m in recent if m.success)
        avg_duration = sum(m.duration_ms for m in recent) / total
        
        return {
            "count": total,
            "avg_duration_ms": round(avg_duration, 2),
            "success_rate": round(successes / total, 2),
            "last_timestamp": recent[-1].timestamp
        }
    
    # ── System Health ───────────────────────────────────────────────────
    
    def save_system_snapshot(self, snapshot: SystemHealthSnapshot) -> None:
        """Save a system health snapshot."""
        if not self.enabled:
            return
        
        with open(SYSTEM_METRICS_FILE, "w") as f:
            json.dump(asdict(snapshot), f, indent=2, default=str)
    
    def load_system_snapshot(self) -> Optional[SystemHealthSnapshot]:
        """Load the latest system health snapshot."""
        if not SYSTEM_METRICS_FILE.exists():
            return None
        
        try:
            data = json.loads(SYSTEM_METRICS_FILE.read_text())
            return SystemHealthSnapshot(**data)
        except (json.JSONDecodeError, TypeError):
            return None
    
    def _count_skills(self, skills_dir: Path) -> int:
        """Count total skills in skills directory."""
        if not skills_dir.exists():
            return 0
        return sum(1 for d in skills_dir.iterdir() 
                   if d.is_dir() and not d.name.startswith("."))

    def _get_recent_skill_metrics(self, cutoff: float) -> list[SkillMetric]:
        """Get skill metrics from last 24 hours."""
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

    def _count_reflections(self, cutoff: float) -> int:
        """Count reflection operations in last 24 hours."""
        reflection_count = 0
        if not OPERATIONS_FILE.exists():
            return reflection_count
            
        with open(OPERATIONS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("operation") == "reflect":
                        ts = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                        if ts.timestamp() > cutoff:
                            reflection_count += 1
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        return reflection_count

    def compute_system_health(self, skills_dir: Path) -> SystemHealthSnapshot:
        """Compute current system health from all metrics."""
        from .skill_schema import get_schema_validation_stats
        
        # Collect all metrics components
        total_skills = self._count_skills(skills_dir)
        manifest_stats = get_schema_validation_stats(skills_dir)
        
        cutoff = time.time() - 24 * 3600
        recent_metrics = self._get_recent_skill_metrics(cutoff)
        
        avg_quality, success_rate = self._calculate_skill_stats(recent_metrics)
        top_errors = self._get_top_errors(recent_metrics)
        slowest = self._get_slowest_skills(recent_metrics)
        reflection_count = self._count_reflections(cutoff)
        
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
    
    # ── Query Interface ───────────────────────────────────────────────────
    
    def get_summary(self) -> dict:
        """Get a human-readable summary of current metrics."""
        snapshot = self.load_system_snapshot()
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


# ─── Convenience Functions ─────────────────────────────────────────────

# Global collector instance
_collector: Optional[MetricsCollector] = None


def get_collector() -> MetricsCollector:
    """Get or create global metrics collector."""
    global _collector
    if _collector is None:
        _collector = MetricsCollector()
    return _collector


def record_skill_execution(*args, **kwargs) -> None:
    """Record skill execution metric."""
    get_collector().record_skill_execution(*args, **kwargs)


def record_operation(*args, **kwargs) -> None:
    """Record operation metric."""
    get_collector().record_operation(*args, **kwargs)


def get_skill_health(skill_name: str) -> dict:
    """Get health for a skill."""
    return get_collector().get_skill_health(skill_name)


def get_system_health_summary() -> dict:
    """Get system health summary."""
    return get_collector().get_summary()


def compute_and_save_system_health(skills_dir: Path) -> SystemHealthSnapshot:
    """Compute and save system health."""
    collector = get_collector()
    snapshot = collector.compute_system_health(skills_dir)
    collector.save_system_snapshot(snapshot)
    return snapshot


# ─── Exports ───────────────────────────────────────────────────────────

__all__ = [
    "MetricsCollector",
    "SkillMetric",
    "OperationMetric",
    "SystemHealthSnapshot",
    "get_collector",
    "record_skill_execution",
    "record_operation",
    "get_skill_health",
    "get_system_health_summary",
    "compute_and_save_system_health",
]
