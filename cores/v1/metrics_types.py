"""metrics_types.py — Metric dataclasses for CoreSkill."""
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional


@dataclass
class SkillMetric:
    """Metrics for a single skill execution."""
    timestamp: str
    skill_name: str
    version: str
    duration_ms: float
    success: bool
    quality_score: float
    intent_match: Optional[str] = None
    error: Optional[str] = None
    
    def to_json(self) -> str:
        return json.dumps(asdict(self), default=str)


@dataclass
class OperationMetric:
    """Metrics for internal operations (evolve, create, validate, etc)."""
    timestamp: str
    operation: str
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
    success_rate_24h: float
    reflection_count_24h: int
    top_errors: list
    slowest_skills: list
