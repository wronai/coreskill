"""auto_repair.py — Self-healing engine with task-based repair loop.

Refactored: 859 lines → thin wrapper importing from modular submodules:
- repair_task.py — RepairTask dataclass
- repair_diagnosis.py — RepairDiagnosis (issue detection)
- repair_strategies.py — RepairStrategies (fix implementations)
"""
import ast
import sys
import subprocess
import time as _time
from pathlib import Path
from datetime import datetime, timezone

from .config import SKILLS_DIR, cpr, C, load_state, save_state
from .garbage_collector import EvolutionGarbageCollector
from .repair_task import RepairTask
from .repair_diagnosis import RepairDiagnosis
from .repair_strategies import RepairStrategies


# ─── Backward Compatible Exports ─────────────────────────────────────────
__all__ = ["AutoRepair", "RepairTask"]


# ─── AutoRepair Engine (thin wrapper) ────────────────────────────────────

class AutoRepair:
    """Self-healing engine with task-based repair loop.
    
    Refactored to delegate to specialized modules:
    - RepairDiagnosis: issue detection
    - RepairStrategies: fix implementations
    """
    
    CODE_ONLY_MODELS = (
        "deepseek-coder", "starcoder", "codellama", "codegemma",
        "stable-code", "codestral", "codeqwen",
    )

    def __init__(self, skill_manager=None, logger=None, journal=None):
        self.sm = skill_manager
        self.log = logger
        self.journal = journal
        self.gc = EvolutionGarbageCollector()
        self._tasks = []
        self.diagnosis = RepairDiagnosis(skill_manager, self.gc)
        self.strategies = RepairStrategies(skill_manager, journal)
        self._learned_strategy = None
        self._tiered_repair = None
        self._init_learned_strategy()
        self._init_tiered_repair()

    def _init_learned_strategy(self):
        """Initialize learned repair strategy from RepairJournal data."""
        try:
            from .learned_repair import LearnedRepairStrategy
            self._learned_strategy = LearnedRepairStrategy()
            if self.journal:
                entries = self.journal.get_all_successful_repairs()
                if len(entries) >= 10:
                    self._learned_strategy.fit(entries)
        except Exception:
            pass

    def _init_tiered_repair(self):
        """Initialize tiered repair escalation."""
        try:
            from .tiered_repair import TieredRepair
            self._tiered_repair = TieredRepair()
        except Exception:
            pass

    # ── Boot Repair ─────────────────────────────────────────────────────
    
    def run_boot_repair(self):
        """Run full repair cycle at boot. Returns report dict."""
        report = {
            "started": datetime.now(timezone.utc).isoformat(),
            "gc_reclaimed": 0,
            "tasks_created": 0,
            "fixed": 0,
            "failed": 0,
            "skipped": 0,
            "details": [],
        }
        
        # Phase 1: GC cleanup
        report["gc_reclaimed"] = self.gc.run_cleanup()
        
        # Phase 2: Scan and create tasks
        self._tasks.clear()
        for skill_name in self.diagnosis.list_all_skills():
            issues = self.diagnosis.diagnose_skill(skill_name)
            for issue_type, desc, severity in issues:
                self._tasks.append(RepairTask(skill_name, issue_type, desc, severity))
        
        report["tasks_created"] = len(self._tasks)
        if not self._tasks:
            return report
        
        cpr(C.CYAN, f"[REPAIR] Znaleziono {len(self._tasks)} problemów do naprawy")
        
        # Phase 3: Execute repairs
        for task in self._tasks:
            self._execute_repair_task(task)
            report["details"].append({
                "skill": task.skill_name,
                "issue": task.issue_type,
                "status": task.status,
                "attempts": task.attempts,
                "result": task.result,
            })
        
        report["fixed"] = sum(1 for t in self._tasks if t.status == RepairTask.FIXED)
        report["failed"] = sum(1 for t in self._tasks if t.status == RepairTask.FAILED)
        report["skipped"] = sum(1 for t in self._tasks if t.status == RepairTask.SKIPPED)
        report["finished"] = datetime.now(timezone.utc).isoformat()
        
        if report["fixed"]:
            cpr(C.GREEN, f"[REPAIR] Naprawiono: {report['fixed']} skill(i)")
        if report["failed"]:
            cpr(C.YELLOW, f"[REPAIR] Nie udało się naprawić: {report['failed']} skill(i)")
        
        if self.log:
            self.log.core("auto_repair_boot", report)
        
        return report

    # ── Single Skill Repair ────────────────────────────────────────────
    
    def repair_skill(self, skill_name):
        """Repair a single skill. Returns (fixed: bool, message: str)."""
        self._tasks.clear()
        
        # Try known fix first
        known_applied = self._try_known_fix(skill_name)
        if known_applied:
            return True, f"{skill_name}: naprawiono znanym rozwiązaniem"
        
        issues = self.diagnosis.diagnose_skill(skill_name)
        if not issues:
            return True, f"{skill_name}: brak problemów"
        
        for issue_type, desc, severity in issues:
            self._tasks.append(RepairTask(skill_name, issue_type, desc, severity))
        
        for task in self._tasks:
            self._execute_repair_task(task)
        
        fixed = all(t.status == RepairTask.FIXED for t in self._tasks)
        results = [f"{t.issue_type}:{t.status}" for t in self._tasks]
        return fixed, f"{skill_name}: {', '.join(results)}"

    def _try_known_fix(self, skill_name):
        """Try a known fix from RepairJournal."""
        if not self.journal:
            return False
        history = self.journal.get_history(skill_name, last_n=5)
        if not history:
            return False
        last_error = next(
            (h for h in reversed(history) if h.fix_result == "fail"), None)
        if not last_error:
            return False
        known = self.journal.get_known_fix(last_error.error_full)
        if not known or known.confidence < 0.7:
            return False
        
        path = self.strategies._get_skill_path(skill_name, SKILLS_DIR)
        if not path:
            return False
        
        cpr(C.CYAN, f"[REPAIR] {skill_name}: próbuję znane rozwiązanie "
                    f"({known.fix_type}, confidence={known.confidence:.0%})")
        
        task = RepairTask(skill_name, "known_fix", known.fix_type, "high")
        fix_ok, fix_msg = self._apply_fix(task, known.fix_type)
        if fix_ok:
            verify_ok = self.diagnosis.verify_fix(skill_name, "known_fix", path)
            if verify_ok:
                self.journal.record_attempt(
                    skill_name, last_error.error_full, known.fix_type,
                    known.fix_command, success=True, detail="known_fix_applied")
                cpr(C.GREEN, f"[REPAIR] ✓ {skill_name}: znane rozwiązanie zadziałało")
                return True
        
        self.journal.record_attempt(
            skill_name, last_error.error_full, known.fix_type,
            known.fix_command, success=False, detail="known_fix_failed")
        return False

    # ── Repair Task Execution ───────────────────────────────────────────
    
    def _execute_repair_task(self, task):
        """Execute a repair task with retry + reflection."""
        task.status = RepairTask.IN_PROGRESS
        
        while task.attempts < task.max_attempts:
            task.attempts += 1
            t0 = _time.monotonic()
            
            strategy = self._plan_strategy(task)
            if strategy == "skip":
                task.status = RepairTask.SKIPPED
                task.result = "Skipped (no auto-fix available)"
                return
            
            fix_ok, fix_msg = self._apply_fix(task, strategy)
            elapsed_ms = int((_time.monotonic() - t0) * 1000)
            
            if not fix_ok:
                task.result = fix_msg
                self._journal_record(task, strategy, False, fix_msg, elapsed_ms)
                task.reflection = self._reflect(task, fix_msg)
                if task.reflection == "give_up":
                    break
                cpr(C.DIM, f"[REPAIR] {task.skill_name}/{task.issue_type}: "
                          f"retry ({task.attempts}/{task.max_attempts}) — {task.reflection}")
                continue
            
            path = self.strategies._get_skill_path(task.skill_name, SKILLS_DIR)
            verify_ok = self.diagnosis.verify_fix(task.skill_name, task.issue_type, path)
            
            if verify_ok:
                task.status = RepairTask.FIXED
                task.result = fix_msg
                self._journal_record(task, strategy, True, fix_msg, elapsed_ms)
                cpr(C.GREEN, f"[REPAIR] ✓ {task.skill_name}: {task.issue_type} naprawiony")
                if self.log:
                    self.log.skill(task.skill_name, "auto_repaired", {
                        "issue": task.issue_type, "strategy": strategy,
                        "attempts": task.attempts})
                return
            else:
                self._journal_record(task, strategy, False,
                                     "Verification failed after fix", elapsed_ms)
                task.reflection = self._reflect(task, "Verification failed after fix")
                if task.reflection == "give_up":
                    break
        
        task.status = RepairTask.FAILED
        if not task.result:
            task.result = f"Failed after {task.attempts} attempts"
        cpr(C.YELLOW, f"[REPAIR] ✗ {task.skill_name}: {task.issue_type} — {task.result[:80]}")

    def _journal_record(self, task, strategy, success, detail, duration_ms=0):
        """Record a repair attempt in RepairJournal."""
        if not self.journal:
            return
        try:
            self.journal.record_attempt(
                skill_name=task.skill_name,
                error=task.description,
                fix_type=strategy,
                fix_command=strategy,
                success=success,
                detail=detail[:300],
                duration_ms=duration_ms,
            )
        except Exception:
            pass

    def _plan_strategy(self, task):
        """Choose repair strategy with 3-level selection."""
        avoid = set()
        if self.journal:
            try:
                avoid = set(self.journal.get_failed_fixes(task.description))
            except Exception:
                pass
        
        if self._learned_strategy and self._learned_strategy.available:
            result = self._learned_strategy.predict(
                issue_type=task.issue_type,
                attempt=task.attempts,
                severity=task.severity,
                has_sm=bool(self.sm),
            )
            if result and result not in avoid:
                return result
        
        if self._tiered_repair:
            result = self._tiered_repair.select(
                issue_type=task.issue_type,
                attempt=task.attempts,
                severity=task.severity,
                has_sm=bool(self.sm),
                skill_name=task.skill_name,
            )
            if result and result not in avoid:
                return result
        
        from .learned_repair import rule_based_strategy
        result = rule_based_strategy(task.issue_type, task.attempts, bool(self.sm))
        if result in avoid:
            cpr(C.DIM, f"[REPAIR] {task.skill_name}: pomijam strategię '{result}' "
                      f"(journal: zawsze zawodzi)")
            return "skip"
        return result

    def _apply_fix(self, task, strategy):
        """Apply a repair strategy."""
        path = self.strategies._get_skill_path(task.skill_name, SKILLS_DIR)
        if not path or not path.exists():
            return False, "Skill file not found"
        
        if strategy == "strip_markdown":
            return self.strategies.fix_strip_markdown(path)
        if strategy == "auto_fix_imports":
            return self.strategies.fix_auto_imports(path)
        if strategy == "add_interface":
            return self.strategies.fix_add_interface(path, task.skill_name)
        if strategy == "pip_install":
            return self.strategies.fix_pip_install(task.description)
        if strategy == "rewrite_from_backup":
            return self.strategies.fix_from_backup(task.skill_name, path, SKILLS_DIR)
        if strategy == "llm_diagnose":
            return self.strategies.fix_llm_diagnose(task.skill_name, task.description, path)
        if strategy == "llm_rewrite":
            return self.strategies.fix_llm_rewrite(task, path)
        
        return False, f"Unknown strategy: {strategy}"

    def _reflect(self, task, failure_reason):
        """Reflect on failure and decide next action."""
        if task.attempts >= task.max_attempts:
            return "give_up"
        if task.reflection and failure_reason == task.result:
            return "give_up"
        if "SyntaxError" in failure_reason and task.issue_type == "markdown":
            return "try_syntax_rewrite"
        if "not imported" in failure_reason:
            return "try_pip_install"
        return "retry_with_next_strategy"

    # ── Model Validation ─────────────────────────────────────────────────
    
    @classmethod
    def validate_model(cls, model_name):
        """Check if a model is suitable for chat (not code-only)."""
        if not model_name:
            return False, "No model specified"
        lower = model_name.lower()
        for code_model in cls.CODE_ONLY_MODELS:
            if code_model in lower:
                return False, f"Code-only model: {code_model}"
        return True, "OK"

    @classmethod
    def suggest_better_model(cls, current_model, available_models):
        """Suggest a better model if current is code-only."""
        valid, _ = cls.validate_model(current_model)
        if valid:
            return None
        
        _preferred = ("instruct", "chat", "llama", "qwen2.5:", "mistral", "gemma")
        best = None
        best_score = -1
        for m in available_models:
            mv, _ = cls.validate_model(m)
            if not mv:
                continue
            score = sum(5 - i for i, kw in enumerate(_preferred) if kw in m.lower())
            if score > best_score:
                best = m
                best_score = score
        return best

    # ── Event Handlers ───────────────────────────────────────────────────
    
    def on_repair_requested(self, sender, **kwargs):
        """Event bus handler: repair a skill."""
        from .event_bus import repair_completed, RepairCompletedEvent
        event = kwargs.get("event")
        if not event:
            return None
        fixed, msg = self.repair_skill(event.skill_name)
        result_evt = RepairCompletedEvent(
            skill_name=event.skill_name, success=fixed, message=msg)
        repair_completed.send(self, event=result_evt)
        action = f"Naprawiono {event.skill_name}: {msg}" if fixed else \
                 f"Nie udało się naprawić {event.skill_name}: {msg}"
        return action

    # ── Status ───────────────────────────────────────────────────────────
    
    def get_task_summary(self):
        """Return human-readable summary of all tasks."""
        if not self._tasks:
            return "[REPAIR] Brak zadań naprawczych."
        lines = ["[REPAIR] Status zadań:"]
        for t in self._tasks:
            icon = {"fixed": "✓", "failed": "✗", "skipped": "⊘",
                    "pending": "…", "in_progress": "⟳"}.get(t.status, "?")
            lines.append(f"  {icon} {t.skill_name}/{t.issue_type}: "
                        f"{t.status} ({t.attempts} prób)")
            if t.result:
                lines.append(f"    → {t.result[:80]}")
        return "\n".join(lines)
