"""repair_diagnosis.py — Diagnosis logic for AutoRepair system."""
import ast
from pathlib import Path

from .config import SKILLS_DIR


class RepairDiagnosis:
    """Diagnoses skill issues and creates repair tasks."""
    
    def __init__(self, skill_manager=None, gc=None):
        self.sm = skill_manager
        self.gc = gc
    
    def list_all_skills(self):
        """List all skill names from the skills directory."""
        names = set()
        if not SKILLS_DIR.is_dir():
            return names
        for d in SKILLS_DIR.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                names.add(d.name)
        return sorted(names)
    
    @staticmethod
    def _has_markdown_artifacts(code):
        """Check if code contains markdown ``` artifacts outside multiline strings."""
        in_multiline = False
        delimiter = None
        for line in code.split('\n'):
            stripped = line.strip()
            if not in_multiline:
                if stripped.startswith('"""') or stripped.startswith("'''"):
                    if stripped.count('"""') < 2 and stripped.count("'''") < 2:
                        in_multiline = True
                        delimiter = '"""' if '"""' in stripped else "'''"
                if stripped.startswith('```') and not in_multiline:
                    return True
            elif delimiter in stripped:
                in_multiline = False
        return False

    def _run_preflight_checks(self, code, path, issues):
        """Run preflight import and interface checks."""
        if not (self.sm and hasattr(self.sm, 'preflight')):
            return
        result = self.sm.preflight.check_imports(code, path)
        if not result.ok:
            issues.append(("imports", result.error, "high"))
        result = self.sm.preflight.check_interface(code)
        if not result.ok:
            issues.append(("interface", result.error, "high"))

    def diagnose_skill(self, skill_name):
        """Diagnose all issues for a skill. Returns list of (type, description, severity)."""
        issues = []
        path = self._get_skill_path(skill_name)
        if not path or not path.exists():
            return issues
        try:
            code = path.read_text()
        except Exception as e:
            issues.append(("read_error", f"Cannot read: {e}", "critical"))
            return issues
        
        if self._has_markdown_artifacts(code):
            issues.append(("markdown", "Markdown artifacts in skill code", "critical"))
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(("syntax", f"Line {e.lineno}: {e.msg}", "critical"))
            return issues
        self._run_preflight_checks(code, path, issues)
        if self.gc and self.gc.is_stub(path):
            issues.append(("stub", "Skill is a stub (no functional code)", "medium"))
        return issues
    
    def _get_skill_path(self, skill_name):
        """Get the active skill.py path for a skill."""
        if self.sm:
            return self.sm.skill_path(skill_name)
        for pattern in [
            SKILLS_DIR / skill_name / "v1" / "skill.py",
            SKILLS_DIR / skill_name / "providers" / "*" / "stable" / "skill.py",
        ]:
            if pattern.exists():
                return pattern
        return None
    
    def verify_fix(self, skill_name, issue_type, path):
        """Verify that a fix actually resolved the issue."""
        if not path or not path.exists():
            return False
        
        try:
            code = path.read_text()
        except Exception:
            return False
        
        if issue_type == "markdown":
            return "```" not in code
        
        if issue_type == "syntax":
            try:
                ast.parse(code)
                return True
            except SyntaxError:
                return False
        
        if issue_type == "imports":
            if self.sm and hasattr(self.sm, 'preflight'):
                return self.sm.preflight.check_imports(code, path).ok
            return True
        
        if issue_type == "interface":
            if self.sm and hasattr(self.sm, 'preflight'):
                return self.sm.preflight.check_interface(code).ok
            return True
        
        return True
