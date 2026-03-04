#!/usr/bin/env python3
"""
reflection_engine.py — Executes declarative reflection rules from config/system.json.

Wires reflection_rules into the actual system behavior:
- Monitors system state (failures, quality, drift)
- Matches rules against state
- Executes actions automatically
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Optional

from .config import get_config_value, SKILLS_DIR
from .skill_schema import get_schema_validation_stats


@dataclass
class SystemState:
    """Current system state for rule matching."""
    timestamp: float
    consecutive_failures: int = 0
    quality_score: float = 1.0
    drift_detected: bool = False
    new_user_query: Optional[str] = None
    skill_versions: int = 0
    manifest_valid: bool = True
    import_error: bool = False
    syntax_error: bool = False
    timeout: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "consecutive_failures": self.consecutive_failures,
            "quality_score": self.quality_score,
            "drift_detected": self.drift_detected,
            "new_user_query": self.new_user_query is not None,
            "skill_versions": self.skill_versions,
            "manifest_valid": self.manifest_valid,
            "import_error": self.import_error,
            "syntax_error": self.syntax_error,
            "timeout": self.timeout,
        }


@dataclass
class RuleMatch:
    """Matched rule with resolved action."""
    rule: dict
    priority: int
    action: str
    params: dict


class ReflectionRuleEngine:
    """Engine that evaluates and executes declarative reflection rules."""
    
    def __init__(self):
        self.rules = self._load_rules()
        self._failure_count = 0
        self._last_failure_time = 0.0
        self._cooldown = 60.0  # seconds between auto-reflections
        self._actions: dict[str, Callable] = {}
        self._register_default_actions()
    
    def _load_rules(self) -> list[dict]:
        """Load reflection_rules from system.json."""
        return get_config_value("reflection_rules", [])
    
    def _register_default_actions(self):
        """Register default action handlers."""
        self._actions = {
            "run_diagnostic": self._action_run_diagnostic,
            "reject_and_retry": self._action_reject_and_retry,
            "gc_trim": self._action_gc_trim,
            "auto_fix_imports": self._action_auto_fix_imports,
            "rewrite_from_backup": self._action_rewrite_from_backup,
            "reduce_complexity": self._action_reduce_complexity,
        }
    
    def reload_rules(self):
        """Reload rules from config (hot-swap)."""
        self.rules = self._load_rules()
    
    def record_failure(self, error_type: str = None):
        """Record a failure for rule matching."""
        now = time.time()
        if now - self._last_failure_time > self._cooldown:
            self._failure_count = 0
        self._failure_count += 1
        self._last_failure_time = now
    
    def record_success(self):
        """Reset failure counter on success."""
        self._failure_count = 0
    
    def evaluate_rules(self, state: SystemState) -> list[RuleMatch]:
        """Evaluate all rules against current state. Returns matched rules."""
        matches = []
        state_dict = state.to_dict()
        
        for rule in self.rules:
            trigger = rule.get("trigger", "")
            if self._match_trigger(trigger, state_dict):
                priority = self._get_priority(rule)
                matches.append(RuleMatch(
                    rule=rule,
                    priority=priority,
                    action=rule.get("action", ""),
                    params=rule.get("params", {})
                ))
        
        # Sort by priority (lower = higher priority)
        matches.sort(key=lambda m: m.priority)
        return matches
    
    def _match_trigger(self, trigger: str, state: dict) -> bool:
        """Match a trigger condition against state."""
        # Parse trigger expressions like "consecutive_failures >= 3"
        trigger = trigger.strip()
        
        # Boolean triggers
        if trigger in state:
            return bool(state.get(trigger))
        
        # Comparison triggers
        for op in [">=", "<=", ">", "<", "==", "!=", "="]:
            if op in trigger:
                parts = trigger.split(op)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value_str = parts[1].strip()
                    
                    # Get actual value
                    actual = state.get(key)
                    if actual is None:
                        return False
                    
                    # Parse expected value
                    try:
                        if "." in value_str:
                            expected = float(value_str)
                        else:
                            expected = int(value_str)
                    except ValueError:
                        expected = value_str
                    
                    # Compare
                    if op == ">=":
                        return actual >= expected
                    elif op == "<=":
                        return actual <= expected
                    elif op == ">":
                        return actual > expected
                    elif op == "<":
                        return actual < expected
                    elif op in ("==", "="):
                        return actual == expected
                    elif op == "!=":
                        return actual != expected
        
        return False
    
    def _get_priority(self, rule: dict) -> int:
        """Get rule priority (lower = higher priority)."""
        priority_map = {"high": 1, "medium": 5, "low": 10}
        return priority_map.get(rule.get("priority", "medium"), 5)
    
    def execute_action(self, match: RuleMatch, context: dict = None) -> dict:
        """Execute a matched rule's action."""
        action_name = match.action
        params = {**match.params, **(context or {})}
        
        if action_name in self._actions:
            try:
                result = self._actions[action_name](**params)
                return {"success": True, "action": action_name, "result": result}
            except Exception as e:
                return {"success": False, "action": action_name, "error": str(e)}
        
        return {"success": False, "action": action_name, "error": "Unknown action"}
    
    def run_cycle(self, state: SystemState) -> list[dict]:
        """Full cycle: evaluate rules + execute matched actions."""
        matches = self.evaluate_rules(state)
        results = []
        
        for match in matches:
            result = self.execute_action(match, state.to_dict())
            results.append(result)
            
            # Stop on critical failures
            if not result["success"] and match.priority <= 1:
                break
        
        return results
    
    # ─── Default Action Handlers ─────────────────────────────────────────
    
    def _action_run_diagnostic(self, **kwargs) -> str:
        """Run system diagnostic."""
        # This would trigger SelfReflection.run_diagnostic()
        return "diagnostic_triggered"
    
    def _action_reject_and_retry(self, skill: str = None, **kwargs) -> str:
        """Reject low-quality skill and retry."""
        return f"rejected_and_retry:{skill}"
    
    def _action_gc_trim(self, **kwargs) -> str:
        """Trigger garbage collection."""
        from .garbage_collector import EvolutionGarbageCollector
        gc = EvolutionGarbageCollector()
        # Would call gc methods here
        return "gc_triggered"
    
    def _action_auto_fix_imports(self, skill: str = None, **kwargs) -> str:
        """Auto-fix missing imports."""
        return f"auto_fix_imports:{skill}"
    
    def _action_rewrite_from_backup(self, skill: str = None, **kwargs) -> str:
        """Rewrite from stable backup."""
        return f"rewrite_from_backup:{skill}"
    
    def _action_reduce_complexity(self, skill: str = None, **kwargs) -> str:
        """Reduce skill complexity."""
        return f"reduce_complexity:{skill}"
    
    # ─── Factory Methods ───────────────────────────────────────────────────
    
    @classmethod
    def from_config(cls) -> "ReflectionRuleEngine":
        """Create engine from system.json config."""
        return cls()
    
    def summary(self) -> dict:
        """Human-readable summary."""
        return {
            "rules_loaded": len(self.rules),
            "actions_registered": list(self._actions.keys()),
            "current_failure_count": self._failure_count,
            "cooldown_active": time.time() - self._last_failure_time < self._cooldown
        }


# ─── Integration Helper ─────────────────────────────────────────────────

class ProactiveReflection:
    """High-level integration that wires rule engine into system."""
    
    def __init__(self, evo_engine=None, skill_manager=None):
        self.engine = ReflectionRuleEngine()
        self.evo = evo_engine
        self.sm = skill_manager
        self._last_check = 0.0
    
    def check_and_reflect(self, force: bool = False) -> list[dict]:
        """Check system state and run reflection if needed."""
        now = time.time()
        if not force and now - self._last_check < 30:  # Min 30s between checks
            return []
        
        self._last_check = now
        
        # Build current state
        state = self._build_state()
        
        # Run rule cycle
        return self.engine.run_cycle(state)
    
    def _build_state(self) -> SystemState:
        """Build current system state."""
        # Get manifest stats
        manifest_stats = get_schema_validation_stats(SKILLS_DIR)
        
        # Get skill version counts
        total_versions = 0
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            prov_dir = skill_dir / "providers"
            if prov_dir.exists():
                for p in prov_dir.iterdir():
                    if p.is_dir():
                        total_versions += len([v for v in p.iterdir() if v.is_dir()])
            else:
                total_versions += len([v for v in skill_dir.iterdir() if v.is_dir() and v.name.startswith("v")])
        
        return SystemState(
            timestamp=time.time(),
            consecutive_failures=self.engine._failure_count,
            skill_versions=total_versions,
            manifest_valid=manifest_stats["invalid"] == 0,
        )
    
    def summary(self) -> dict:
        """Get summary of reflection status."""
        return {
            "engine": self.engine.summary(),
            "last_check": self._last_check,
        }


# ─── Convenience Functions ─────────────────────────────────────────────

_engine: Optional[ReflectionRuleEngine] = None


def get_rule_engine() -> ReflectionRuleEngine:
    """Get or create global rule engine."""
    global _engine
    if _engine is None:
        _engine = ReflectionRuleEngine()
    return _engine


def evaluate_reflection_rules(state: SystemState) -> list[RuleMatch]:
    """Evaluate rules against state."""
    return get_rule_engine().evaluate_rules(state)


def run_reflection_cycle() -> list[dict]:
    """Run full reflection cycle."""
    engine = get_rule_engine()
    state = SystemState(timestamp=time.time())
    return engine.run_cycle(state)


# ─── Exports ───────────────────────────────────────────────────────────

__all__ = [
    "ReflectionRuleEngine",
    "ProactiveReflection",
    "SystemState",
    "RuleMatch",
    "get_rule_engine",
    "evaluate_reflection_rules",
    "run_reflection_cycle",
]
