"""metrics_collector.py — Permanent metrics collection for CoreSkill.

Refactored: 600 lines → thin wrapper importing from modular submodules.
- metrics_types.py — dataclasses (SkillMetric, OperationMetric, SystemHealthSnapshot)
- metrics_storage.py — file I/O operations (MetricsStorage)
- metrics_analyzer.py — analysis and anomaly detection (MetricsAnalyzer)

This module re-exports everything for backward compatibility.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_config_value
from .metrics_types import SkillMetric, OperationMetric, SystemHealthSnapshot
from .metrics_storage import MetricsStorage, SKILL_METRICS_FILE, OPERATIONS_FILE
from .metrics_analyzer import MetricsAnalyzer


# ─── Backward Compatible Exports ─────────────────────────────────────────
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


# ─── Main Collector Class (thin wrapper) ─────────────────────────────────

class MetricsCollector:
    """Collect and persist performance metrics.
    
    Refactored to delegate to specialized modules:
    - MetricsStorage: file I/O
    - MetricsAnalyzer: analysis and anomaly detection
    """
    
    def __init__(self, enabled: bool = None):
        self.enabled = enabled if enabled is not None else get_config_value(
            "autonomy.enable_metrics_collection", True
        )
        self.storage = MetricsStorage()
        self.analyzer = MetricsAnalyzer(self.storage)
    
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
        self.storage.append_skill_metric(metric)
    
    def get_skill_metrics(self, skill_name: str, last_n: int = 100) -> list[SkillMetric]:
        """Get recent metrics for a specific skill."""
        return self.storage.read_skill_metrics(skill_name, last_n)
    
    def get_skill_health(self, skill_name: str) -> dict:
        """Get health summary for a skill."""
        return self.analyzer.analyze_skill_health(skill_name)
    
    # ── Operation Metrics ────────────────────────────────────────────────
    
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
        self.storage.append_operation_metric(metric)
    
    def get_operation_stats(self, operation: str, last_n: int = 100) -> dict:
        """Get statistics for a specific operation type."""
        return self.analyzer.analyze_operation_stats(operation, last_n)
    
    # ── System Health ─────────────────────────────────────────────────────
    
    def save_system_snapshot(self, snapshot: SystemHealthSnapshot) -> None:
        """Save a system health snapshot."""
        if not self.enabled:
            return
        self.storage.save_system_snapshot(snapshot)
    
    def load_system_snapshot(self) -> Optional[SystemHealthSnapshot]:
        """Load the latest system health snapshot."""
        return self.storage.load_system_snapshot()
    
    def compute_system_health(self, skills_dir: Path) -> SystemHealthSnapshot:
        """Compute current system health from all metrics."""
        return self.analyzer.compute_system_health(skills_dir)
    
    # ── Event Bus Handlers ────────────────────────────────────────────────
    
    def on_skill_failed(self, sender, **kwargs):
        """EventBus handler: record a skill failure."""
        event = kwargs.get("event")
        if not event:
            return
        self.record_skill_execution(
            skill_name=event.skill_name,
            version="?",
            duration_ms=0,
            success=False,
            error=event.error or event.goal,
        )
    
    def on_repair_completed(self, sender, **kwargs):
        """EventBus handler: record repair outcome."""
        event = kwargs.get("event")
        if not event:
            return
        self.record_operation(
            operation="repair",
            duration_ms=0,
            success=event.success,
            details={"skill": event.skill_name, "strategy": event.strategy},
            error=event.message if not event.success else None,
        )
    
    # ── Anomaly Detection ────────────────────────────────────────────────
    
    def get_anomalies(self, window_minutes: int = 60) -> list:
        """Detect anomalies in the last time window."""
        return self.analyzer.get_anomalies(window_minutes)
    
    # ── Query Interface ───────────────────────────────────────────────────
    
    def get_summary(self) -> dict:
        """Get a human-readable summary of current metrics."""
        snapshot = self.storage.load_system_snapshot()
        return self.analyzer.get_summary(snapshot)


# ─── Convenience Functions ───────────────────────────────────────────────

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
