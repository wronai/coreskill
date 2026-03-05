"""repair_strategies.py — Fix implementations for AutoRepair system."""
import ast
import re
import subprocess
import sys
from pathlib import Path

from .config import cpr, C


class RepairStrategies:
    """Container for all repair strategy implementations."""
    
    def __init__(self, skill_manager=None, journal=None):
        self.sm = skill_manager
        self.journal = journal
    
    def _get_skill_path(self, skill_name, skills_dir):
        """Get the active skill.py path for a skill."""
        if self.sm:
            return self.sm.skill_path(skill_name)
        # Fallback: scan common locations
        for pattern in [
            skills_dir / skill_name / "v1" / "skill.py",
            skills_dir / skill_name / "providers" / "*" / "stable" / "skill.py",
        ]:
            if pattern.exists():
                return pattern
        return None
    
    # ── Tier 1-3: Automated Fixes ────────────────────────────────────────
    
    def fix_strip_markdown(self, path):
        """Remove markdown fences and LLM prose from skill code."""
        try:
            code = path.read_text()
            original = code

            # Remove ```python ... ``` blocks — extract code inside
            blocks = re.findall(r'```(?:python)?\s*\n(.*?)```', code, re.DOTALL)
            if blocks:
                code = max(blocks, key=len)
            elif "```" in code:
                lines = code.split("\n")
                code = "\n".join(l for l in lines if not l.strip().startswith("```"))

            # Remove lines that look like LLM prose (not Python)
            lines = code.split("\n")
            cleaned = []
            for line in lines:
                stripped = line.strip()
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
                    if len(stripped) > 60 and " " in stripped[:30]:
                        continue
                cleaned.append(line)

            code = "\n".join(cleaned)

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

    def fix_auto_imports(self, path):
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

    def fix_add_interface(self, path, skill_name):
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

    def fix_pip_install(self, error_description):
        """Try to pip install a missing package from error description."""
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

    def fix_from_backup(self, skill_name, current_path, skills_dir):
        """Try to restore from a backup version (v1, stable, etc.)."""
        parent = current_path.parent.parent

        candidates = []
        for d in ("stable", "v1"):
            backup = parent / d / "skill.py"
            if backup.exists() and backup != current_path:
                candidates.append(backup)

        if not candidates:
            return False, "No backup version found"

        for backup in candidates:
            try:
                code = backup.read_text()
                ast.parse(code)
                current_path.write_text(code)
                return True, f"Restored from {backup.parent.name}/"
            except SyntaxError:
                continue

        return False, "All backup versions also broken"

    # ── Tier 4-5: LLM-Assisted Repair ────────────────────────────────────

    def fix_llm_diagnose(self, skill_name, description, path):
        """Tier 4: Ask RepairJournal's LLM diagnosis for a targeted fix."""
        if not self.journal:
            return False, "RepairJournal not available"
        try:
            diagnosis = self.journal.ask_llm_diagnosis(
                skill_name=skill_name,
                error=description,
                attempted_fixes=[],
            )
            if not diagnosis or not diagnosis.get("fix_command"):
                return False, "LLM could not suggest a fix"

            fix_cmd = diagnosis["fix_command"]
            if fix_cmd == "manual":
                return False, f"LLM says manual fix needed: {diagnosis.get('diagnosis', '')}"

            safe_prefixes = ("sudo apt ", "pip install ", "pip3 install ",
                             f"{sys.executable} -m pip install ")
            if not any(fix_cmd.strip().startswith(p) for p in safe_prefixes):
                return False, f"LLM suggested unsafe command: {fix_cmd[:60]}"

            r = subprocess.run(
                fix_cmd, shell=True, capture_output=True, text=True, timeout=120)
            if r.returncode == 0:
                return True, f"LLM fix applied: {fix_cmd[:60]}"
            return False, f"LLM fix failed (rc={r.returncode}): {r.stderr[:80]}"
        except Exception as e:
            return False, f"llm_diagnose error: {e}"

    def fix_llm_rewrite(self, task, path):
        """Tier 5: Request complete skill rewrite from LLM."""
        if not self.sm or not hasattr(self.sm, 'smart_evolve'):
            return False, "SkillManager.smart_evolve not available"
        try:
            code = path.read_text()
            goal = (f"Napraw ten skill. Problem: {task.issue_type}: "
                    f"{task.description[:200]}. Przepisz cały kod od zera, "
                    f"zachowując tę samą funkcjonalność.")
            result = self.sm.smart_evolve(task.skill_name, goal)
            if result and isinstance(result, dict) and result.get("success"):
                return True, "LLM rewrote skill from scratch"
            new_code = path.read_text()
            if new_code != code:
                try:
                    ast.parse(new_code)
                    return True, "LLM rewrote skill (file changed)"
                except SyntaxError:
                    path.write_text(code)
                    return False, "LLM rewrite has syntax errors, reverted"
            return False, "LLM rewrite produced no changes"
        except Exception as e:
            return False, f"llm_rewrite error: {e}"
