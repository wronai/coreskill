#!/usr/bin/env python3
"""
Event bus — lightweight pub/sub decoupling for core components.

Uses blinker signals to decouple AutoRepair ↔ EvoEngine ↔ SelfReflection.

Events:
    skill_failed      — a skill execution failed (emitted by EvoEngine)
    reflection_needed  — consecutive failures reached threshold (emitted by EvoEngine)
    repair_requested   — a specific skill needs repair (emitted by SelfReflection)
    repair_completed   — repair finished (emitted by AutoRepair)
    diagnosis_ready    — diagnostic report available (emitted by SelfReflection)
"""
from dataclasses import dataclass, field
from typing import Any, Optional

try:
    from blinker import Signal
    _HAS_BLINKER = True
except ImportError:
    _HAS_BLINKER = False


# ── Event payloads ───────────────────────────────────────────────────

@dataclass
class SkillFailedEvent:
    skill_name: str
    error: str = ""
    goal: str = ""
    user_msg: str = ""


@dataclass
class ReflectionNeededEvent:
    trigger: str = ""           # "failures" | "unhandled" | "pre_request"
    failures: list = field(default_factory=list)
    unhandled: list = field(default_factory=list)
    reflection_number: int = 0


@dataclass
class RepairRequestedEvent:
    skill_name: str
    issue_type: str = ""        # "syntax" | "imports" | "interface" | etc.
    error: str = ""


@dataclass
class RepairCompletedEvent:
    skill_name: str
    success: bool = False
    message: str = ""
    strategy: str = ""


@dataclass
class DiagnosisReadyEvent:
    skill_name: str = ""
    overall_status: str = ""
    auto_fixable: list = field(default_factory=list)
    requires_user: list = field(default_factory=list)
    findings: list = field(default_factory=list)
    fixes_applied: list = field(default_factory=list)


# ── Signals ──────────────────────────────────────────────────────────

if _HAS_BLINKER:
    skill_failed = Signal("skill_failed")
    reflection_needed = Signal("reflection_needed")
    repair_requested = Signal("repair_requested")
    repair_completed = Signal("repair_completed")
    diagnosis_ready = Signal("diagnosis_ready")
else:
    # Fallback: no-op signals when blinker not installed
    class _NoopSignal:
        def send(self, sender=None, **kwargs): pass
        def connect(self, receiver, sender=None, weak=True): pass
        def disconnect(self, receiver, sender=None): pass

    skill_failed = _NoopSignal()
    reflection_needed = _NoopSignal()
    repair_requested = _NoopSignal()
    repair_completed = _NoopSignal()
    diagnosis_ready = _NoopSignal()


# ── Bus helper ───────────────────────────────────────────────────────

class EventBus:
    """Central registry for wiring signal handlers at boot time.

    Usage:
        bus = EventBus()
        bus.wire(reflection=reflection, repairer=repairer, evo=evo, logger=logger)
    """

    def __init__(self):
        self._wired = False

    def wire(self, reflection=None, repairer=None, evo=None, logger=None):
        """Connect handlers to signals. Safe to call multiple times (idempotent)."""
        if self._wired:
            return
        self._wired = True

        if reflection:
            # When reflection is needed → run diagnostic + auto-fix
            reflection_needed.connect(reflection.on_reflection_needed, weak=False)

        if repairer:
            # When repair is requested → execute repair
            repair_requested.connect(repairer.on_repair_requested, weak=False)

        if logger:
            # Log all events
            skill_failed.connect(lambda sender, **kw: logger.core(
                "event.skill_failed",
                {"skill": kw.get("event", SkillFailedEvent("?")).skill_name}
            ), weak=False)
            repair_completed.connect(lambda sender, **kw: logger.core(
                "event.repair_completed",
                {"skill": kw.get("event", RepairCompletedEvent("?")).skill_name,
                 "success": kw.get("event", RepairCompletedEvent("?")).success}
            ), weak=False)

    @property
    def is_active(self):
        return _HAS_BLINKER and self._wired
