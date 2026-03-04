#!/usr/bin/env python3
"""
evo-engine AutoRepair — self-healing module with task-based loop and reflection.

Extracted from boot sequence and EvoEngine for autonomous repair:
  - Skill syntax/import/interface repair
  - Broken version cleanup (GC)
  - Model validation (reject code-only models)
  - Missing dependency auto-install
  - Reflection loop: diagnose → plan → fix → verify → reflect

Usage:
    repairer = AutoRepair(skill_manager, logger)
    report = repairer.run_boot_repair()   # full boot scan
    report = repairer.repair_skill(name)  # single skill
"""
import ast
import sys
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone

from .config import SKILLS_DIR, cpr, C, load_state, save_state
from .garbage_collector import EvolutionGarbageCollector


# ─── Repair Task Types ───────────────────────────────────────────────
class RepairTask:
    """Single repair task with status tracking."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    FAILED = "failed"
    SKIPPED = "skipped"

    def __init__(self, skill_name, issue_type, description, severity="medium"):
        self.skill_name = skill_name
        self.issue_type = issue_type  # syntax, imports, interface, stub, broken_version, missing_dep
        self.description = description
        self.severity = severity      # critical, high, medium, low
        self.status = self.PENDING
        self.attempts = 0
        self.max_attempts = 3
        self.result = None
        self.reflection = None

    def __repr__(self):
        return (f"RepairTask({self.skill_name}/{self.issue_type}: "
                f"{self.status}, {self.attempts}/{self.max_attempts})")


# ─── AutoRepair Engine ───────────────────────────────────────────────
class AutoRepair:
    """
    Self-healing engine with task-based repair loop.

    Flow per task:
        1. DIAGNOSE — identify exact issue (syntax? imports? interface? stub?)
        2. PLAN    — choose repair strategy
        3. FIX     — apply fix (auto_fix_imports, rewrite, pip install, GC)
        4. VERIFY  — re-run preflight to confirm fix
        5. REFLECT — if still broken, adjust strategy and retry
    """

    # Code-only models that produce garbage for Polish chat / skill generation
    CODE_ONLY_MODELS = (
        "deepseek-coder", "starcoder", "codellama", "codegemma",
        "stable-code", "codestral", "codeqwen",
    )

    def __init__(self, skill_manager=None, logger=None, identity=None):
        self.sm = skill_manager
        self.log = logger
        self.identity = identity
        self.gc = EvolutionGarbageCollector()
        self._tasks = []
        self._history = []  # completed tasks for reflection
        self._learned_strategy = None
        self._init_learned_strategy()

    def _init_learned_strategy(self):
        """Try to fit LearnedRepairStrategy from repair journal data."""
        try:
            from .learned_repair import LearnedRepairStrategy
            from .repair_journal import RepairJournal
            self._learned_strategy = LearnedRepairStrategy()
            journal = RepairJournal()
            if hasattr(journal, '_entries') and journal._entries:
                records = [
                    {"issue_type": e.get("error_signature", "").split(":")[0] if ":" in e.get("error_signature", "") else "syntax",
                     "strategy": e.get("fix_type", "skip"),
                     "attempt": 1,
                     "severity": "high",
                     "success": e.get("success", False),
                     "has_sm": True}
                    for e in journal._entries
                ]
                self._learned_strategy.fit(records)
        except Exception:
            pass

    # ── Boot Repair (full scan) ──────────────────────────────────────

    def run_boot_repair(self):
        """Full boot-time repair scan. Returns summary report dict."""
        report = {
            "started": datetime.now(timezone.utc).isoformat(),
            "tasks_created": 0,
            "fixed": 0,
            "failed": 0,
            "skipped": 0,
            "gc_deleted": 0,
            "details": [],
        }

        # Phase 1: GC — clean stubs and broken versions
        gc_reports = self.gc.cleanup_all(migrate=False, dry_run=False)
        gc_deleted = sum(len(r.get("deleted", [])) for r in gc_reports)
        report["gc_deleted"] = gc_deleted
        if gc_deleted:
            cpr(C.DIM, f"[REPAIR] GC: usunięto {gc_deleted} stub(ów)/broken wersji")

        # Phase 2: Scan all skills for issues
        self._tasks.clear()
        self._scan_all_skills()
        report["tasks_created"] = len(self._tasks)

        if not self._tasks:
            return report

        cpr(C.CYAN, f"[REPAIR] Znaleziono {len(self._tasks)} problemów do naprawy")

        # Phase 3: Execute repair loop
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

        # Summary
        if report["fixed"]:
            cpr(C.GREEN, f"[REPAIR] Naprawiono: {report['fixed']} skill(i)")
        if report["failed"]:
            cpr(C.YELLOW, f"[REPAIR] Nie udało się naprawić: {report['failed']} skill(i)")

        if self.log:
            self.log.core("auto_repair_boot", report)

        return report

    # ── Single Skill Repair ──────────────────────────────────────────

    def repair_skill(self, skill_name):
        """Repair a single skill. Returns (fixed: bool, message: str)."""
        self._tasks.clear()
        issues = self._diagnose_skill(skill_name)

        if not issues:
            return True, f"{skill_name}: brak problemów"

        for issue_type, desc, severity in issues:
            self._tasks.append(RepairTask(skill_name, issue_type, desc, severity))

        for task in self._tasks:
            self._execute_repair_task(task)

        fixed = all(t.status == RepairTask.FIXED for t in self._tasks)
        results = [f"{t.issue_type}:{t.status}" for t in self._tasks]
        return fixed, f"{skill_name}: {', '.join(results)}"

    def on_repair_requested(self, sender, **kwargs):
        """Event bus handler: repair a skill and emit repair_completed."""
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

    # ── Diagnosis ────────────────────────────────────────────────────

    def _scan_all_skills(self):
        """Scan all skills and create repair tasks for broken ones."""
        if not self.sm:
            return

        for skill_name in self._list_all_skills():
            issues = self._diagnose_skill(skill_name)
            for issue_type, desc, severity in issues:
                self._tasks.append(RepairTask(skill_name, issue_type, desc, severity))

    def _list_all_skills(self):
        """List all skill names from the skills directory."""
        names = set()
        if not SKILLS_DIR.is_dir():
            return names
        for d in SKILLS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                names.add(d.name)
        return sorted(names)

    def _diagnose_skill(self, skill_name):
        """Diagnose all issues for a skill. Returns list of (type, description, severity)."""
        issues = []
        path = self._get_skill_path(skill_name)

        if not path or not path.exists():
            return issues  # no file = nothing to repair

        try:
            code = path.read_text()
        except Exception as e:
            issues.append(("read_error", f"Cannot read: {e}", "critical"))
            return issues

        # Check 1: Markdown artifacts (LLM generated garbage)
        # Only check top-level code, not inside string literals
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str):
                    # Skip string literals - they may contain example code
                    continue
                # Check if any node contains markdown (for string nodes this would be already filtered)
                if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                    if isinstance(node.value.value, str) and "```" in node.value.value:
                        continue  # Skip markdown inside string literals
        except SyntaxError:
            pass  # Will be caught below

        # Simple check for markdown fences outside of strings (conservative)
        lines = code.split('\n')
        in_multiline_string = False
        string_delimiter = None
        for line in lines:
            stripped = line.strip()
            # Track multiline strings
            if not in_multiline_string:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') < 2 and stripped.count("'''") < 2:
                        in_multiline_string = True
                        string_delimiter = '"""' if '"""' in stripped else "'''"
            else:
                if string_delimiter in stripped:
                    in_multiline_string = False
                    continue
                # Inside multiline string - ignore markdown
                continue
            # Not in multiline string - check for markdown fences
            if stripped.startswith('```') and not in_multiline_string:
                issues.append(("markdown", "Markdown artifacts in skill code", "critical"))
                break

        # Check 2: Syntax
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(("syntax", f"Line {e.lineno}: {e.msg}", "critical"))
            return issues  # can't check further if syntax is broken

        # Check 3: Missing imports
        if self.sm and hasattr(self.sm, 'preflight'):
            result = self.sm.preflight.check_imports(code, path)
            if not result.ok:
                issues.append(("imports", result.error, "high"))

        # Check 4: Interface (get_info, health_check, execute)
        if self.sm and hasattr(self.sm, 'preflight'):
            result = self.sm.preflight.check_interface(code)
            if not result.ok:
                issues.append(("interface", result.error, "high"))

        # Check 5: Stub detection
        if self.gc.is_stub(path):
            issues.append(("stub", "Skill is a stub (no functional code)", "medium"))

        return issues

    def _get_skill_path(self, skill_name):
        """Get the active skill.py path for a skill."""
        if self.sm:
            return self.sm.skill_path(skill_name)
        # Fallback: scan common locations
        for pattern in [
            SKILLS_DIR / skill_name / "v1" / "skill.py",
            SKILLS_DIR / skill_name / "providers" / "*" / "stable" / "skill.py",
        ]:
            if pattern.exists():
                return pattern
        return None

    # ── Repair Task Execution (with reflection loop) ─────────────────

    def _execute_repair_task(self, task):
        """Execute a single repair task with retry + reflection."""
        task.status = RepairTask.IN_PROGRESS

        while task.attempts < task.max_attempts:
            task.attempts += 1

            # PLAN: choose strategy based on issue type + history
            strategy = self._plan_strategy(task)

            if strategy == "skip":
                task.status = RepairTask.SKIPPED
                task.result = "Skipped (no auto-fix available)"
                return

            # FIX: apply the repair
            fix_ok, fix_msg = self._apply_fix(task, strategy)

            if not fix_ok:
                task.result = fix_msg
                # REFLECT: can we try a different approach?
                task.reflection = self._reflect(task, fix_msg)
                if task.reflection == "give_up":
                    break
                cpr(C.DIM, f"[REPAIR] {task.skill_name}/{task.issue_type}: "
                          f"retry ({task.attempts}/{task.max_attempts}) — {task.reflection}")
                continue

            # VERIFY: confirm the fix worked
            verify_ok = self._verify_fix(task)

            if verify_ok:
                task.status = RepairTask.FIXED
                task.result = fix_msg
                cpr(C.GREEN, f"[REPAIR] ✓ {task.skill_name}: {task.issue_type} naprawiony")
                if self.log:
                    self.log.skill(task.skill_name, "auto_repaired", {
                        "issue": task.issue_type, "strategy": strategy,
                        "attempts": task.attempts})
                return
            else:
                # REFLECT on verification failure
                task.reflection = self._reflect(task, "Verification failed after fix")
                if task.reflection == "give_up":
                    break

        task.status = RepairTask.FAILED
        if not task.result:
            task.result = f"Failed after {task.attempts} attempts"
        cpr(C.YELLOW, f"[REPAIR] ✗ {task.skill_name}: {task.issue_type} — {task.result[:80]}")

    def _plan_strategy(self, task):
        """Choose repair strategy. Uses learned model when available, else rule-based."""
        # Try learned strategy first
        if self._learned_strategy and self._learned_strategy.available:
            result = self._learned_strategy.predict(
                issue_type=task.issue_type,
                attempt=task.attempts,
                severity=task.severity,
                has_sm=bool(self.sm),
            )
            if result:
                return result

        # Fallback: rule-based
        from .learned_repair import rule_based_strategy
        return rule_based_strategy(task.issue_type, task.attempts, bool(self.sm))

    def _apply_fix(self, task, strategy):
        """Apply a repair strategy. Returns (success: bool, message: str)."""
        path = self._get_skill_path(task.skill_name)
        if not path or not path.exists():
            return False, "Skill file not found"

        if strategy == "strip_markdown":
            return self._fix_strip_markdown(path)

        if strategy == "auto_fix_imports":
            return self._fix_auto_imports(path)

        if strategy == "add_interface":
            return self._fix_add_interface(path, task.skill_name)

        if strategy == "pip_install":
            return self._fix_pip_install(task.description)

        if strategy == "rewrite_from_backup":
            return self._fix_from_backup(task.skill_name, path)

        return False, f"Unknown strategy: {strategy}"

    def _verify_fix(self, task):
        """Verify that the fix actually resolved the issue."""
        path = self._get_skill_path(task.skill_name)
        if not path or not path.exists():
            return False

        try:
            code = path.read_text()
        except Exception:
            return False

        if task.issue_type == "markdown":
            return "```" not in code

        if task.issue_type == "syntax":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False

        if task.issue_type == "imports":
            if self.sm and hasattr(self.sm, 'preflight'):
                return self.sm.preflight.check_imports(code, path).ok
            return True

        if task.issue_type == "interface":
            if self.sm and hasattr(self.sm, 'preflight'):
                return self.sm.preflight.check_interface(code).ok
            return True

        return True

    def _reflect(self, task, failure_reason):
        """Reflect on failure and decide next action.
        Returns: strategy hint string or 'give_up'."""
        if task.attempts >= task.max_attempts:
            return "give_up"

        # If same failure repeats, give up
        if task.reflection and failure_reason == task.result:
            return "give_up"

        # Adjust strategy based on failure
        if "SyntaxError" in failure_reason and task.issue_type == "markdown":
            return "try_syntax_rewrite"

        if "not imported" in failure_reason:
            return "try_pip_install"

        return "retry_with_next_strategy"

    # ── Fix Implementations ──────────────────────────────────────────

    def _fix_strip_markdown(self, path):
        """Remove markdown fences and LLM prose from skill code."""
        try:
            code = path.read_text()
            original = code

            # Remove ```python ... ``` blocks — extract code inside
            import re
            blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', code, re.DOTALL)
            if blocks:
                # Use the longest code block
                code = max(blocks, key=len)
            elif "```" in code:
                # Just strip all backtick lines
                lines = code.split("\n")
                code = "\n".join(l for l in lines if not l.strip().startswith("```"))

            # Remove lines that look like LLM prose (not Python)
            lines = code.split("\n")
            cleaned = []
            for line in lines:
                stripped = line.strip()
                # Skip obvious prose lines (no Python syntax)
                if stripped and not any([
                    stripped.startswith(("#", "import ", "from ", "def ", "class ",
                                        "return ", "if ", "elif ", "else:", "for ",
                                        "while ", "try:", "except", "with ", "raise ",
                                        "yield ", "async ", "await ", "@", "    ",
                                        "\t", "'", '"', "(", ")", "[", "]", "{", "}")),
                    "=" in stripped,
                    stripped.startswith(("self.", "print(", "os.", "sys.", "subprocess.")),
                    stripped == "",
                    stripped == "pass",
                ]):
                    # Looks like prose, not code
                    if len(stripped) > 60 and " " in stripped[:30]:
                        continue
                cleaned.append(line)

            code = "\n".join(cleaned)

            # Verify the cleaned code parses
            try:
                ast.parse(code)
            except SyntaxError:
                return False, "Cleaned code still has syntax errors"

            if code != original:
                path.write_text(code)
                return True, "Stripped markdown/prose artifacts"
            return False, "No markdown artifacts found to strip"

        except Exception as e:
            return False, f"strip_markdown error: {e}"

    def _fix_auto_imports(self, path):
        """Auto-fix missing stdlib imports."""
        if not self.sm or not hasattr(self.sm, 'preflight'):
            return False, "No preflight available"

        try:
            code = path.read_text()
            fixed = self.sm.preflight.auto_fix_imports(code)
            if fixed != code:
                path.write_text(fixed)
                return True, "Auto-fixed missing imports"
            return False, "No imports to fix"
        except Exception as e:
            return False, f"auto_fix_imports error: {e}"

    def _fix_add_interface(self, path, skill_name):
        """Add missing get_info/health_check functions if absent."""
        try:
            code = path.read_text()
            tree = ast.parse(code)

            top_funcs = {n.name for n in ast.iter_child_nodes(tree)
                         if isinstance(n, ast.FunctionDef)}

            additions = []
            if "get_info" not in top_funcs:
                additions.append(
                    f'\ndef get_info():\n'
                    f'    return {{"name": "{skill_name}", "version": "v1", '
                    f'"description": "{skill_name} skill"}}\n'
                )
            if "health_check" not in top_funcs:
                additions.append(
                    '\ndef health_check():\n'
                    '    return True\n'
                )

            if additions:
                code = code.rstrip() + "\n\n" + "\n".join(additions) + "\n"
                path.write_text(code)
                return True, f"Added: {', '.join(a.split('(')[0].strip().split()[-1] for a in additions)}"
            return False, "Interface already complete"

        except Exception as e:
            return False, f"add_interface error: {e}"

    def _fix_pip_install(self, error_description):
        """Try to pip install a missing package from error description."""
        import re
        # Extract package name from error
        match = re.search(r"No module named '(\w+)'", error_description)
        if not match:
            match = re.search(r"not imported: (\w+)", error_description)
        if not match:
            return False, "Could not determine package name"

        pkg = match.group(1)
        try:
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", pkg, "-q"],
                capture_output=True, text=True, timeout=60)
            if r.returncode == 0:
                return True, f"Installed {pkg}"
            return False, f"pip install {pkg} failed: {r.stderr[:80]}"
        except Exception as e:
            return False, f"pip install error: {e}"

    def _fix_from_backup(self, skill_name, current_path):
        """Try to restore from a backup version (v1, stable, etc.)."""
        parent = current_path.parent.parent  # skill dir or provider dir

        # Look for backup versions
        candidates = []
        for d in ("stable", "v1"):
            backup = parent / d / "skill.py"
            if backup.exists() and backup != current_path:
                candidates.append(backup)

        if not candidates:
            return False, "No backup version found"

        # Use the first valid backup
        for backup in candidates:
            try:
                code = backup.read_text()
                ast.parse(code)
                # Valid backup found — copy it
                current_path.write_text(code)
                return True, f"Restored from {backup.parent.name}/"
            except SyntaxError:
                continue

        return False, "All backup versions also broken"

    # ── Model Validation ─────────────────────────────────────────────

    @classmethod
    def validate_model(cls, model_name):
        """Check if a model is suitable for chat (not code-only).
        Returns (valid: bool, reason: str)."""
        if not model_name:
            return False, "No model specified"
        lower = model_name.lower()
        for code_model in cls.CODE_ONLY_MODELS:
            if code_model in lower:
                return False, f"Code-only model: {code_model}"
        return True, "OK"

    @classmethod
    def suggest_better_model(cls, current_model, available_models):
        """Suggest a better model if current is code-only.
        Returns suggested model ID or None."""
        valid, _ = cls.validate_model(current_model)
        if valid:
            return None

        # Prefer: instruct > chat > general, larger > smaller
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

    # ── Status / Summary ─────────────────────────────────────────────

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
