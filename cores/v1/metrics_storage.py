"""metrics_storage.py — File I/O operations for metrics."""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import LOGS_DIR
from .metrics_types import SkillMetric, OperationMetric, SystemHealthSnapshot


METRICS_DIR = LOGS_DIR / "metrics"
SKILL_METRICS_FILE = METRICS_DIR / "skill_metrics.jsonl"
SYSTEM_METRICS_FILE = METRICS_DIR / "system_metrics.json"
OPERATIONS_FILE = METRICS_DIR / "operations.jsonl"


class MetricsStorage:
    """Handles all file I/O for metrics persistence."""
    
    def __init__(self):
        self._ensure_dirs()
    
    def _ensure_dirs(self) -> None:
        """Ensure metrics directories exist."""
        METRICS_DIR.mkdir(parents=True, exist_ok=True)
    
    # ── Skill Metrics Persistence ────────────────────────────────────────
    
    def append_skill_metric(self, metric: SkillMetric) -> None:
        """Append a skill metric to the JSONL file."""
        with open(SKILL_METRICS_FILE, "a") as f:
            f.write(metric.to_json() + "\n")
    
    def read_skill_metrics(self, skill_name: Optional[str] = None, 
                          last_n: int = 100) -> list[SkillMetric]:
        """Read skill metrics, optionally filtered by name."""
        metrics = []
        if not SKILL_METRICS_FILE.exists():
            return metrics
        
        with open(SKILL_METRICS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if skill_name and data.get("skill_name") != skill_name:
                        continue
                    metrics.append(SkillMetric(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return metrics[-last_n:] if skill_name else metrics
    
    def read_skill_metrics_since(self, skill_name: str, cutoff_ts: float) -> list[SkillMetric]:
        """Get metrics for a skill since a timestamp."""
        results = []
        if not SKILL_METRICS_FILE.exists():
            return results
        
        with open(SKILL_METRICS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("skill_name") != skill_name:
                        continue
                    ts = datetime.fromisoformat(
                        data["timestamp"].replace("Z", "+00:00"))
                    if ts.timestamp() >= cutoff_ts:
                        results.append(SkillMetric(**data))
                except (json.JSONDecodeError, ValueError, KeyError, TypeError):
                    continue
        return results
    
    def list_tracked_skills(self) -> list[str]:
        """Return skill names that have recorded metrics."""
        names = set()
        if not SKILL_METRICS_FILE.exists():
            return []
        with open(SKILL_METRICS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    name = data.get("skill_name")
                    if name:
                        names.add(name)
                except (json.JSONDecodeError, TypeError):
                    continue
        return sorted(names)
    
    # ── Operation Metrics Persistence ───────────────────────────────────
    
    def append_operation_metric(self, metric: OperationMetric) -> None:
        """Append an operation metric to the JSONL file."""
        with open(OPERATIONS_FILE, "a") as f:
            f.write(metric.to_json() + "\n")
    
    def read_operation_metrics(self, operation: Optional[str] = None,
                               last_n: int = 100) -> list[OperationMetric]:
        """Read operation metrics, optionally filtered by operation type."""
        metrics = []
        if not OPERATIONS_FILE.exists():
            return metrics
        
        with open(OPERATIONS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if operation and data.get("operation") != operation:
                        continue
                    metrics.append(OperationMetric(**data))
                except (json.JSONDecodeError, TypeError):
                    continue
        
        return metrics[-last_n:]
    
    def count_operations_since(self, operation: str, cutoff_ts: float) -> int:
        """Count operations of a specific type since timestamp."""
        count = 0
        if not OPERATIONS_FILE.exists():
            return count
        
        with open(OPERATIONS_FILE) as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("operation") != operation:
                        continue
                    ts = datetime.fromisoformat(
                        data["timestamp"].replace("Z", "+00:00"))
                    if ts.timestamp() > cutoff_ts:
                        count += 1
                except (json.JSONDecodeError, ValueError, KeyError):
                    continue
        return count
    
    # ── System Snapshot Persistence ─────────────────────────────────────
    
    def save_system_snapshot(self, snapshot: SystemHealthSnapshot) -> None:
        """Save a system health snapshot."""
        with open(SYSTEM_METRICS_FILE, "w") as f:
            json.dump(snapshot.__dict__, f, indent=2, default=str)
    
    def load_system_snapshot(self) -> Optional[SystemHealthSnapshot]:
        """Load the latest system health snapshot."""
        if not SYSTEM_METRICS_FILE.exists():
            return None
        try:
            data = json.loads(SYSTEM_METRICS_FILE.read_text())
            return SystemHealthSnapshot(**data)
        except (json.JSONDecodeError, TypeError):
            return None
