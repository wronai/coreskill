#!/usr/bin/env python3
"""
autonomy_loop.py — Closed-loop autonomy orchestrator for CoreSkill.

Connects DiagnosticEngine → AutoRepair → MetricsCollector → EventBus
into a self-healing cycle that runs periodically or on-demand.

Cycle:
    1. SCAN   — DiagnosticEngine.full_scan() detects issues
    2. TRIAGE — Prioritize issues by severity and confidence of known fixes
    3. REPAIR — AutoRepair.repair_skill() with TieredRepair escalation
    4. VERIFY — Re-scan to confirm fixes worked
    5. RECORD — MetricsCollector records outcomes, RepairJournal learns
    6. REPORT — Summary emitted via EventBus + logged
"""
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .config import cpr, C, SKILLS_DIR


@dataclass
class LoopCycleResult:
    """Result of a single autonomy loop cycle."""
    timestamp: str
    scan_status: str  # healthy / degraded / critical
    issues_found: int
    repairs_attempted: int
    repairs_succeeded: int
    repairs_failed: int
    duration_ms: int
    details: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def all_fixed(self) -> bool:
        return self.issues_found == 0 or self.repairs_succeeded == self.repairs_attempted

    def summary(self) -> str:
        icon = "✓" if self.all_fixed else "⚠"
        return (f"[AUTONOMY] {icon} Cykl: status={self.scan_status}, "
                f"problemy={self.issues_found}, "
                f"naprawione={self.repairs_succeeded}/{self.repairs_attempted}, "
                f"czas={self.duration_ms}ms")


class AutonomyLoop:
    """Closed-loop orchestrator: scan → triage → repair → verify → record.

    Components (all optional, gracefully degrades):
        diagnostics  — DiagnosticEngine (full_scan)
        repairer     — AutoRepair (repair_skill, TieredRepair)
        metrics      — MetricsCollector (record_operation, get_anomalies)
        event_bus    — EventBus (emit repair events)
        logger       — Logger (structured logging)
        skill_manager — SkillManager (list skills, health checks)
    """

    # Minimum seconds between automatic cycles (prevents thrashing)
    MIN_CYCLE_INTERVAL = 120

    def __init__(self, diagnostics=None, repairer=None, metrics=None,
                 event_bus=None, logger=None, skill_manager=None):
        self.diagnostics = diagnostics
        self.repairer = repairer
        self.metrics = metrics
        self.bus = event_bus
        self.log = logger
        self.sm = skill_manager

        self._history: List[LoopCycleResult] = []
        self._last_cycle_time = 0.0
        self._enabled = True
        self._cycle_count = 0

    # ── Main Cycle ────────────────────────────────────────────────────

    def run_cycle(self, force: bool = False, include_llm: bool = False) -> LoopCycleResult:
        """Run one full autonomy cycle.

        Args:
            force: Skip cooldown check.
            include_llm: Include LLM health check in scan (slower).

        Returns:
            LoopCycleResult with scan + repair outcomes.
        """
        now = time.monotonic()

        # Cooldown guard
        if not force and (now - self._last_cycle_time) < self.MIN_CYCLE_INTERVAL:
            remaining = int(self.MIN_CYCLE_INTERVAL - (now - self._last_cycle_time))
            return LoopCycleResult(
                timestamp=self._now_iso(),
                scan_status="skipped",
                issues_found=0, repairs_attempted=0,
                repairs_succeeded=0, repairs_failed=0,
                duration_ms=0,
                details=[{"note": f"Cooldown: {remaining}s remaining"}],
            )

        self._last_cycle_time = now
        self._cycle_count += 1
        t0 = time.monotonic()

        cpr(C.CYAN, f"[AUTONOMY] ── Cykl #{self._cycle_count} ──")

        # Phase 1: SCAN
        scan = self._phase_scan(include_llm)

        # Phase 2: TRIAGE — also include anomaly-detected skills
        repair_targets = self._phase_triage(scan)

        # Phase 3: REPAIR
        repair_results = self._phase_repair(repair_targets)

        # Phase 4: VERIFY (re-scan critical fixes)
        verified = self._phase_verify(repair_results)

        # Phase 5: RECORD
        elapsed_ms = int((time.monotonic() - t0) * 1000)
        succeeded = sum(1 for r in repair_results if r.get("fixed"))
        failed = sum(1 for r in repair_results if not r.get("fixed"))

        result = LoopCycleResult(
            timestamp=self._now_iso(),
            scan_status=scan.get("status", "unknown"),
            issues_found=len(repair_targets),
            repairs_attempted=len(repair_results),
            repairs_succeeded=succeeded,
            repairs_failed=failed,
            duration_ms=elapsed_ms,
            details=repair_results,
        )

        self._phase_record(result)
        self._history.append(result)

        cpr(C.CYAN, result.summary())
        return result

    # ── Phase Implementations ─────────────────────────────────────────

    def _phase_scan(self, include_llm: bool = False) -> dict:
        """Phase 1: Run DiagnosticEngine.full_scan()."""
        if not self.diagnostics:
            return {"status": "unknown", "issues": [], "checks": {}}

        try:
            scan = self.diagnostics.full_scan(include_llm=include_llm)
            status = scan.get("status", "unknown")
            n_issues = len(scan.get("issues", []))
            cpr(C.DIM, f"[AUTONOMY] Skan: {status} "
                       f"({scan.get('passed', 0)}/{scan.get('total_checks', 0)} OK, "
                       f"{n_issues} problemów)")
            return scan
        except Exception as e:
            cpr(C.YELLOW, f"[AUTONOMY] Błąd skanu: {e}")
            return {"status": "error", "issues": [], "error": str(e)}

    def _phase_triage(self, scan: dict) -> List[Dict]:
        """Phase 2: Prioritize issues for repair.

        Combines scan issues + metric anomalies + broken skills into
        a prioritized repair target list.
        """
        targets = []

        # Source 1: Diagnostic scan issues (broken skills)
        for issue in scan.get("issues", []):
            if issue.get("check") == "skills_health":
                # Extract individual broken skills
                checks = scan.get("checks", {})
                skills_result = checks.get("skills_health", {})
                for skill_name in skills_result.get("broken", []):
                    # Strip error suffix like "skill(err...)"
                    clean = skill_name.split("(")[0]
                    targets.append({
                        "skill": clean,
                        "source": "diagnostic_scan",
                        "severity": "high",
                        "description": f"Health check failed: {skill_name}",
                    })
            elif issue.get("check") == "system_commands":
                # System-level issue, not a skill repair
                targets.append({
                    "skill": "__system__",
                    "source": "diagnostic_scan",
                    "severity": "critical" if issue.get("critical") else "medium",
                    "description": issue.get("description", ""),
                    "auto_fix": scan.get("auto_fixable", []),
                })

        # Source 2: Metric anomalies (success rate drops, error storms)
        if self.metrics:
            try:
                anomalies = self.metrics.get_anomalies(window_minutes=30)
                for a in anomalies:
                    if a.get("type") in ("success_rate_drop", "error_storm"):
                        skill = a.get("skill_name", "")
                        if skill and not any(t["skill"] == skill for t in targets):
                            targets.append({
                                "skill": skill,
                                "source": "anomaly_detection",
                                "severity": a.get("severity", "medium"),
                                "description": a.get("description", "Anomaly detected"),
                            })
            except Exception:
                pass

        # Sort: critical first, then high, then medium
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        targets.sort(key=lambda t: severity_order.get(t.get("severity", "low"), 3))

        if targets:
            cpr(C.DIM, f"[AUTONOMY] Triage: {len(targets)} celów naprawy")

        return targets

    def _phase_repair(self, targets: List[Dict]) -> List[Dict]:
        """Phase 3: Attempt repairs on each target."""
        if not self.repairer or not targets:
            return []

        results = []
        for target in targets:
            skill = target.get("skill", "")

            # System-level issues: try auto-fix commands
            if skill == "__system__":
                result = self._repair_system(target)
                results.append(result)
                continue

            # Skill-level issues: delegate to AutoRepair
            try:
                cpr(C.DIM, f"[AUTONOMY] Naprawa: {skill} "
                           f"({target.get('source', '?')})")
                fixed, msg = self.repairer.repair_skill(skill)
                results.append({
                    "skill": skill,
                    "fixed": fixed,
                    "message": msg,
                    "source": target.get("source", ""),
                })
                if fixed:
                    cpr(C.GREEN, f"[AUTONOMY] ✓ {skill}: {msg[:60]}")
                else:
                    cpr(C.YELLOW, f"[AUTONOMY] ✗ {skill}: {msg[:60]}")
            except Exception as e:
                results.append({
                    "skill": skill,
                    "fixed": False,
                    "message": f"Exception: {e}",
                    "source": target.get("source", ""),
                })

        return results

    def _repair_system(self, target: dict) -> dict:
        """Attempt system-level repairs (apt install, etc.)."""
        auto_fix = target.get("auto_fix", [])
        if not auto_fix:
            return {"skill": "__system__", "fixed": False,
                    "message": "No auto-fix available"}

        # We don't auto-run apt commands without user consent
        cpr(C.YELLOW, f"[AUTONOMY] System wymaga: {'; '.join(auto_fix)}")
        return {
            "skill": "__system__",
            "fixed": False,
            "message": f"Requires manual: {auto_fix[0][:60]}",
            "auto_fix_commands": auto_fix,
        }

    def _phase_verify(self, repair_results: List[Dict]) -> List[Dict]:
        """Phase 4: Re-verify skills that were repaired."""
        if not self.sm or not repair_results:
            return repair_results

        for result in repair_results:
            if not result.get("fixed") or result.get("skill") == "__system__":
                continue
            skill = result["skill"]
            try:
                health = self.sm.check_health(skill)
                if isinstance(health, dict):
                    result["verified"] = health.get("ok", True)
                else:
                    result["verified"] = bool(health)
            except Exception:
                result["verified"] = False

        return repair_results

    def _phase_record(self, result: LoopCycleResult):
        """Phase 5: Record cycle outcome in metrics + log."""
        if self.metrics:
            try:
                self.metrics.record_operation(
                    operation="autonomy_cycle",
                    duration_ms=result.duration_ms,
                    success=result.all_fixed,
                    details={
                        "scan_status": result.scan_status,
                        "issues": result.issues_found,
                        "repaired": result.repairs_succeeded,
                        "failed": result.repairs_failed,
                        "cycle": self._cycle_count,
                    },
                )
            except Exception:
                pass

        if self.log:
            try:
                self.log.core("autonomy_cycle", {
                    "cycle": self._cycle_count,
                    "status": result.scan_status,
                    "issues": result.issues_found,
                    "repaired": result.repairs_succeeded,
                    "failed": result.repairs_failed,
                    "duration_ms": result.duration_ms,
                })
            except Exception:
                pass

    # ── Scheduler Integration ─────────────────────────────────────────

    def scheduled_cycle(self):
        """Entry point for ProactiveScheduler — runs cycle with cooldown."""
        if not self._enabled:
            return
        try:
            self.run_cycle(force=False)
        except Exception as e:
            cpr(C.YELLOW, f"[AUTONOMY] Błąd cyklu: {e}")

    # ── Control ───────────────────────────────────────────────────────

    def enable(self):
        self._enabled = True

    def disable(self):
        self._enabled = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def cycle_count(self) -> int:
        return self._cycle_count

    # ── Status / Summary ──────────────────────────────────────────────

    def status(self) -> dict:
        """Return current loop status."""
        last = self._history[-1] if self._history else None
        return {
            "enabled": self._enabled,
            "cycles": self._cycle_count,
            "last_status": last.scan_status if last else "never_run",
            "last_issues": last.issues_found if last else 0,
            "last_repaired": last.repairs_succeeded if last else 0,
            "last_duration_ms": last.duration_ms if last else 0,
            "cooldown_remaining": max(0, int(
                self.MIN_CYCLE_INTERVAL - (time.monotonic() - self._last_cycle_time)
            )),
        }

    def format_report(self) -> str:
        """Human-readable report of all cycles."""
        if not self._history:
            return "[AUTONOMY] Brak historii cykli."

        lines = [f"[AUTONOMY] Historia ({len(self._history)} cykli):"]
        for i, r in enumerate(self._history[-10:], 1):
            icon = "✓" if r.all_fixed else "⚠"
            lines.append(
                f"  {icon} #{i}: {r.scan_status} | "
                f"problemy={r.issues_found} | "
                f"naprawione={r.repairs_succeeded}/{r.repairs_attempted} | "
                f"{r.duration_ms}ms"
            )

        # Overall stats
        total_issues = sum(r.issues_found for r in self._history)
        total_fixed = sum(r.repairs_succeeded for r in self._history)
        total_failed = sum(r.repairs_failed for r in self._history)
        lines.append(f"\n  Suma: {total_issues} problemów, "
                     f"{total_fixed} naprawionych, {total_failed} nieudanych")

        return "\n".join(lines)

    # ── Helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()
