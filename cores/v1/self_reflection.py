"""self_reflection.py — Autonomiczny system autorefleksji i diagnostyki.

Aktywuje się gdy:
- Skill zawiedzie lub timeout
- Długa operacja (>30s) bez odpowiedzi
- Użytkownik wyraźnie prosi o sprawdzenie systemu

Fazy:
1. DETECT — wykrycie anomalii (fail, stall, timeout)
2. DIAGNOSE — zebranie informacji diagnostycznych
3. ANALYZE — analiza przyczyny (LLM + heurystyki)
4. ACT — akcja naprawcza lub eskalacja
"""

import time
from pathlib import Path
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from .config import cpr, C
from .logger import Logger
from .self_healing.diagnostics import DiagnosticEngine


@dataclass
class ReflectionEvent:
    """Zdarzenie wymagające autorefleksji."""
    timestamp: float
    event_type: str  # "skill_fail", "timeout", "stall", "user_request"
    skill_name: str = ""
    error_msg: str = ""
    duration_ms: int = 0
    context: dict = field(default_factory=dict)


@dataclass  
class DiagnosisReport:
    """Raport diagnostyczny."""
    timestamp: str
    overall_status: str  # "healthy", "degraded", "critical"
    findings: List[Dict[str, Any]]
    recommendations: List[str]
    auto_fixable: List[str]
    requires_user: List[str]


class SelfReflection:
    """Autonomiczny silnik autorefleksji systemu evo-engine."""
    
    # Progi czasowe
    STALL_THRESHOLD_S = 30  # Czas po którym uznajemy operację za "zawieszoną"
    TIMEOUT_THRESHOLD_S = 60  # Maksymalny czas operacji
    
    CONSECUTIVE_FAIL_THRESHOLD = 3  # Trigger reflection after N consecutive fails for any skill
    
    def __init__(self, llm_client, skill_manager, logger: Logger, state: dict):
        self.llm = llm_client
        self.sm = skill_manager
        self.log = logger
        self.state = state
        self.pending_events: List[ReflectionEvent] = []
        self.last_diagnosis: Optional[DiagnosisReport] = None
        self._operation_start_time: Optional[float] = None
        self._current_operation: str = ""
        # Generic consecutive-failure tracking per skill
        self._consecutive_failures: Dict[str, int] = {}
        self._last_reflect_per_skill: Dict[str, float] = {}
        self._reflect_cooldown = 60  # seconds between auto-reflections per skill
        # Repair journal + stable snapshots (lazy-init to avoid circular imports)
        self._journal = None
        self._snapshot = None
        # Diagnostic engine for health checks
        self._diagnostics = DiagnosticEngine(llm_client, skill_manager, logger)
    
    @property
    def journal(self):
        """Lazy-init RepairJournal."""
        if self._journal is None:
            from .repair_journal import RepairJournal
            self._journal = RepairJournal(llm_client=self.llm)
        return self._journal
    
    @property
    def snapshot(self):
        """Lazy-init StableSnapshot."""
        if self._snapshot is None:
            from .stable_snapshot import StableSnapshot
            self._snapshot = StableSnapshot(skill_manager=self.sm, logger=self.log)
        return self._snapshot
        
    def start_operation(self, operation_name: str):
        """Rozpocznij śledzenie operacji do wykrycia stall/timeout."""
        self._operation_start_time = time.time()
        self._current_operation = operation_name
        self.log.core("reflection_start_op", {"op": operation_name})
        
    def end_operation(self, success: bool = True, error: str = ""):
        """Zakończ śledzenie operacji, zgłoś jeśli timeout/fail."""
        if not self._operation_start_time:
            return
            
        duration = time.time() - self._operation_start_time
        
        if not success:
            self._trigger_event(ReflectionEvent(
                timestamp=time.time(),
                event_type="skill_fail",
                skill_name=self._current_operation.split(":")[0] if ":" in self._current_operation else "",
                error_msg=error,
                duration_ms=int(duration * 1000),
                context={"operation": self._current_operation}
            ))
        elif duration > self.STALL_THRESHOLD_S:
            self._trigger_event(ReflectionEvent(
                timestamp=time.time(),
                event_type="stall",
                skill_name=self._current_operation.split(":")[0] if ":" in self._current_operation else "",
                duration_ms=int(duration * 1000),
                context={"operation": self._current_operation}
            ))
            
        self._operation_start_time = None
        self._current_operation = ""
        
    def record_skill_outcome(self, skill_name: str, success: bool, partial: bool = False,
                              error: str = "") -> Optional[DiagnosisReport]:
        """Track consecutive failures for any skill. Returns DiagnosisReport if threshold hit.
        
        Call this after every skill execution. After CONSECUTIVE_FAIL_THRESHOLD
        consecutive non-successes, auto-triggers reflection diagnostic.
        
        Also records in RepairJournal for persistent learning and validates
        against StableSnapshot when available.
        """
        if success and not partial:
            # Reset counter on full success
            self._consecutive_failures[skill_name] = 0
            # Record success in journal (for recovery tracking)
            try:
                self.journal.record_success(skill_name, "skill execution OK")
            except Exception:
                pass
            return None
            
        # Increment counter
        count = self._consecutive_failures.get(skill_name, 0) + 1
        self._consecutive_failures[skill_name] = count
        
        if count < self.CONSECUTIVE_FAIL_THRESHOLD:
            return None
            
        # Check cooldown
        now = time.time()
        last_reflect = self._last_reflect_per_skill.get(skill_name, 0)
        if (now - last_reflect) < self._reflect_cooldown:
            return None
            
        # Threshold reached + cooldown expired → auto-reflect
        self._last_reflect_per_skill[skill_name] = now
        cpr(C.YELLOW, f"[REFLECT] {count} kolejnych błędów/ciszek dla '{skill_name}' "
                      f"— uruchamiam autorefleksję...")
        self.log.core("consecutive_fail_reflect", {
            "skill": skill_name, "count": count, "error": error[:200]})
        
        # Check journal for known fixes before running full diagnostic
        known_fix = self.journal.get_known_fix(error)
        if known_fix and known_fix.confidence >= 0.7:
            cpr(C.CYAN, f"[REFLECT] Znany fix z journala (conf={known_fix.confidence:.0%}): "
                        f"{known_fix.fix_type}")
        
        # Compare with stable version to understand if regression
        try:
            validation = self.snapshot.validate_against_stable(skill_name)
            if validation.get("matches") is False and validation.get("health_stable") == "ok":
                cpr(C.YELLOW, f"[REFLECT] Regresja vs stable: {validation.get('changes_summary', '?')}")
                cpr(C.CYAN, f"[REFLECT] Stable wersja działa — rozważ rollback: /snapshot restore {skill_name}")
        except Exception:
            pass
        
        report = self.run_diagnostic(skill_name, specific_error=error)
        
        # Actually attempt auto-fixes (not just recommend them)
        if report.auto_fixable:
            cpr(C.CYAN, "[REFLECT] Próbuję automatycznych napraw...")
            fixes_done = self.attempt_auto_fix(report)
            for fix in fixes_done:
                cpr(C.GREEN, f"[REFLECT] ✓ {fix}")
        
        # Record the reflection attempt in journal
        try:
            self.journal.record_attempt(
                skill_name=skill_name,
                error=error[:300],
                fix_type="auto_reflection",
                fix_command="run_diagnostic",
                success=report.overall_status != "critical",
                detail=f"status={report.overall_status}, "
                       f"fixes={len(report.auto_fixable)}, "
                       f"user_required={len(report.requires_user)}",
            )
        except Exception:
            pass
        
        # Reset counter after reflection (give fresh start)
        self._consecutive_failures[skill_name] = 0
        
        return report

    def check_stall(self) -> Optional[ReflectionEvent]:
        """Sprawdź czy bieżąca operacja nie przekroczyła progu stall."""
        if not self._operation_start_time or not self._current_operation:
            return None
            
        duration = time.time() - self._operation_start_time
        if duration > self.STALL_THRESHOLD_S:
            return ReflectionEvent(
                timestamp=time.time(),
                event_type="stall",
                skill_name=self._current_operation.split(":")[0] if ":" in self._current_operation else "",
                duration_ms=int(duration * 1000),
                context={"operation": self._current_operation}
            )
        return None
        
    def _trigger_event(self, event: ReflectionEvent):
        """Dodaj zdarzenie do kolejki i rozpocznij autorefleksję."""
        self.pending_events.append(event)
        cpr(C.YELLOW, f"[REFLECT] Wykryto: {event.event_type} | {event.skill_name} | {event.duration_ms}ms")
        self.log.core("reflection_trigger", {
            "type": event.event_type,
            "skill": event.skill_name,
            "duration_ms": event.duration_ms,
            "error": event.error_msg[:200]
        })
        
    def run_diagnostic(self, skill_name: str = "", specific_error: str = "") -> DiagnosisReport:
        """Uruchom pełną diagnostykę systemu."""
        cpr(C.CYAN, "[REFLECT] Uruchamiam diagnostykę systemu...")
        
        findings = []
        recommendations = []
        auto_fixable = []
        requires_user = []
        
        # 1. Check LLM API status
        llm_status = self._diagnostics.check_llm_health()
        findings.append({"category": "llm", **llm_status})
        if not llm_status["ok"]:
            recommendations.append(f"LLM: {llm_status.get('error', 'problem')}")
            if "rate limit" in llm_status.get("error", "").lower():
                auto_fixable.append("poczekaj na reset rate limit")
            elif "auth" in llm_status.get("error", "").lower():
                requires_user.append("Sprawdź klucz API w /apikey lub .evo_state.json")
                
        # 2. Check required system commands
        sys_status = self._diagnostics.check_system_commands()
        findings.append({"category": "system_commands", **sys_status})
        if not sys_status["ok"]:
            missing = sys_status.get("missing", [])
            recommendations.append(f"Brakuje: {', '.join(missing)}")
            if "sox" in missing or "ffmpeg" in missing:
                auto_fixable.append(f"sudo apt install {' '.join(missing)}")
                
        # 3. Check microphone availability (if STT used)
        if skill_name == "stt" or not skill_name:
            mic_status = self._diagnostics.check_microphone()
            findings.append({"category": "microphone", **mic_status})
            if not mic_status["ok"]:
                recommendations.append(f"Mikrofon: {mic_status.get('error', 'niedostępny')}")
                requires_user.append("Podłącz mikrofon lub sprawdź uprawnienia (arecord -l)")
                
        # 4. Check skills health status
        if self.sm:
            skills_status = self._diagnostics.check_skills_health()
            findings.append({"category": "skills", **skills_status})
            if not skills_status["ok"]:
                broken = skills_status.get("broken", [])
                recommendations.append(f"Uszkodzone skills: {', '.join(broken)}")
                auto_fixable.append("Automatyczna naprawa na starcie (/fix <skill>)")
                
        # 5. Check Vosk model (for STT)
        if skill_name == "stt" or not skill_name:
            vosk_status = self._diagnostics.check_vosk_model()
            findings.append({"category": "vosk_model", **vosk_status})
            if not vosk_status["ok"]:
                recommendations.append("Brak modelu Vosk")
                auto_fixable.append("Pobierz model: curl -L 'https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip'")
                
        # 6. Check TTS availability
        tts_status = self._diagnostics.check_tts_backend()
        findings.append({"category": "tts", **tts_status})
        if not tts_status["ok"]:
            recommendations.append(f"TTS: {tts_status.get('error', 'problem')}")
            auto_fixable.append("sudo apt install espeak-ng")
            
        # 7. Check disk space
        disk_status = self._diagnostics.check_disk_space()
        findings.append({"category": "disk", **disk_status})
        if not disk_status["ok"]:
            recommendations.append(f"Mało miejsca: {disk_status.get('free_gb', 0):.1f}GB")
            requires_user.append("Zwolnij miejsce na dysku")
            
        # Określ ogólny status
        critical_issues = [f for f in findings if not f.get("ok") and f.get("critical", False)]
        degraded_issues = [f for f in findings if not f.get("ok") and not f.get("critical", False)]
        
        if critical_issues:
            overall = "critical"
        elif degraded_issues:
            overall = "degraded"
        else:
            overall = "healthy"
            
        # Add LLM recommendation if we have specific error
        if specific_error or skill_name:
            llm_recommendation = self._diagnostics.llm_analyze_error(skill_name, specific_error, findings)
            if llm_recommendation:
                recommendations.append(f"[LLM Analysis] {llm_recommendation}")
                
        report = DiagnosisReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            overall_status=overall,
            findings=findings,
            recommendations=recommendations,
            auto_fixable=auto_fixable,
            requires_user=requires_user
        )
        
        self.last_diagnosis = report
        self._print_report(report)
        return report
        
    def _print_report(self, report: DiagnosisReport):
        """Wyświetl raport diagnostyczny."""
        status_color = C.GREEN if report.overall_status == "healthy" else C.YELLOW if report.overall_status == "degraded" else C.RED
        cpr(status_color, f"\n[REFLECT] === DIAGNOZA SYSTEMU: {report.overall_status.upper()} ===")
        
        for f in report.findings:
            cat = f.get("category", "?")
            ok = f.get("ok", False)
            icon = "✓" if ok else "✗"
            color = C.GREEN if ok else C.YELLOW if not f.get("critical") else C.RED
            
            if ok:
                cpr(color, f"  {icon} {cat}: OK")
            else:
                err = f.get("error", "problem")
                cpr(color, f"  {icon} {cat}: {err[:60]}")
                
        if report.recommendations:
            cpr(C.CYAN, "\n  Rekomendacje:")
            for r in report.recommendations:
                cpr(C.DIM, f"    • {r[:80]}")
                
        if report.auto_fixable:
            cpr(C.GREEN, "\n  Można naprawić automatycznie:")
            for a in report.auto_fixable:
                cpr(C.DIM, f"    → {a[:80]}")
                
        if report.requires_user:
            cpr(C.YELLOW, "\n  Wymaga działania użytkownika:")
            for u in report.requires_user:
                cpr(C.YELLOW, f"    ⚠ {u[:80]}")
                
    def attempt_auto_fix(self, report: DiagnosisReport) -> List[str]:
        """Spróbuj automatycznie naprawić problemy. Zwraca listę wykonanych akcji."""
        actions = []
        
        for fix_cmd in report.auto_fixable:
            if "apt install" in fix_cmd:
                cpr(C.CYAN, f"[REFLECT] Instaluję brakujące pakiety...")
                actions.extend(self._diagnostics.attempt_apt_install(fix_cmd))
        
        # Auto-repair broken skills detected in diagnostics
        broken_skills = []
        for f in report.findings:
            if f.get("category") == "skills" and not f.get("ok"):
                broken_skills = f.get("broken", [])
                break
        
        if broken_skills and self.sm:
            actions.extend(self._repair_broken_skills(broken_skills))
                    
        return actions

    def _repair_broken_skills(self, broken_skills: list) -> List[str]:
        """Repair broken skills via event bus signal or direct fallback."""
        actions = []
        try:
            from .event_bus import repair_requested, RepairRequestedEvent, _HAS_BLINKER
            if _HAS_BLINKER and repair_requested.receivers:
                # Decoupled path: emit signal, AutoRepair handles it
                for skill_name in broken_skills:
                    clean_name = skill_name.split("(")[0]
                    cpr(C.CYAN, f"[REFLECT] Naprawiam skill: {clean_name}...")
                    evt = RepairRequestedEvent(skill_name=clean_name)
                    results = repair_requested.send(self, event=evt)
                    for _, result in results:
                        if result:
                            actions.append(result)
                return actions
        except ImportError:
            pass

        # Fallback: direct import (backward compat when bus not wired)
        try:
            from .auto_repair import AutoRepair
            repairer = AutoRepair(skill_manager=self.sm, logger=self.log)
            for skill_name in broken_skills:
                clean_name = skill_name.split("(")[0]
                cpr(C.CYAN, f"[REFLECT] Naprawiam skill: {clean_name}...")
                fixed, msg = repairer.repair_skill(clean_name)
                if fixed:
                    actions.append(f"Naprawiono {clean_name}: {msg}")
                else:
                    actions.append(f"Nie udało się naprawić {clean_name}: {msg}")
        except Exception as e:
            actions.append(f"Błąd auto-repair: {e}")
        return actions

    def on_reflection_needed(self, sender, **kwargs):
        """Event bus handler: run diagnostic + auto-fix when reflection is requested.
        Returns DiagnosisReadyEvent with results."""
        from .event_bus import diagnosis_ready, DiagnosisReadyEvent
        event = kwargs.get("event")
        if not event:
            return None

        focus_skill = ""
        last_error = ""
        if event.failures:
            focus_skill = event.failures[-1].get("skill", "")
            last_error = event.failures[-1].get("error", "")

        report = self.run_diagnostic(focus_skill, last_error)

        fixes_applied = []
        if report.auto_fixable:
            cpr(C.CYAN, "[REFLECT] Próbuję automatycznych napraw...")
            fixes_applied = self.attempt_auto_fix(report)
            for fix in fixes_applied:
                cpr(C.GREEN, f"[REFLECT] ✓ {fix}")

        result = DiagnosisReadyEvent(
            skill_name=focus_skill,
            overall_status=report.overall_status,
            auto_fixable=report.auto_fixable,
            requires_user=report.requires_user,
            findings=report.findings,
            fixes_applied=fixes_applied,
        )
        diagnosis_ready.send(self, event=result)
        return result
        
    def get_summary(self) -> str:
        """Zwróć podsumowanie ostatniej diagnostyki."""
        if not self.last_diagnosis:
            return "Brak danych diagnostycznych. Uruchom /reflect"
        
        r = self.last_diagnosis
        return f"Status: {r.overall_status} | Problemy: {len([f for f in r.findings if not f.get('ok')])} | {len(r.auto_fixable)} auto-fix, {len(r.requires_user)} manual"
