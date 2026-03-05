#!/usr/bin/env python3
"""
evo-engine SkillPreflight + EvolutionGuard.

SkillPreflight: Pre-flight validation before skill execution.
  - Syntax check (ast.parse)
  - Import check (detect missing stdlib imports)
  - Interface check (has execute, get_info, health_check)
  - Auto-fix missing imports

EvolutionGuard: Prevents evolution loops where the same error repeats.
  - Fingerprint errors
  - Track error history per skill
  - Suggest strategy changes when same error repeats
"""
import ast
import hashlib
import re
import subprocess
import sys
from pathlib import Path


class PreflightResult:
    """Result of pre-flight validation."""
    def __init__(self, ok, stage="", error="", details=None):
        self.ok = ok
        self.stage = stage
        self.error = error
        self.details = details or {}

    def __repr__(self):
        if self.ok:
            return "PreflightResult(OK)"
        return f"PreflightResult(FAIL at {self.stage}: {self.error})"

    def to_dict(self):
        return {
            "ok": self.ok,
            "stage": self.stage,
            "error": self.error,
            "details": self.details,
        }


STDLIB_MODULES = {
    "shutil", "os", "sys", "json", "subprocess", "pathlib",
    "tempfile", "hashlib", "re", "time", "datetime", "traceback",
    "importlib", "ast", "threading", "signal", "socket",
}


class SkillPreflight:
    """Pre-flight validation for skill files."""

    REQUIRED_EXPORTS = ["execute", "get_info", "health_check"]

    def check_all(self, skill_path):
        """Run all pre-flight checks in order."""
        if not skill_path.exists():
            return PreflightResult(False, "exists", f"File not found: {skill_path}")

        code = skill_path.read_text()

        r = self.check_syntax(code)
        if not r.ok:
            return r

        r = self.check_imports(code, skill_path)
        if not r.ok:
            return r

        r = self.check_interface(code)
        if not r.ok:
            return r

        return PreflightResult(True)

    def check_syntax(self, code):
        """Stage 1: Can Python parse this file?"""
        try:
            ast.parse(code)
            return PreflightResult(True)
        except SyntaxError as e:
            return PreflightResult(False, "syntax",
                f"Line {e.lineno}: {e.msg}",
                {"line": e.lineno, "offset": e.offset})

    @staticmethod
    def _check_static_imports(code, tree):
        """Check for missing stdlib imports via AST. Returns list of missing module names."""
        imports = set()
        used_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Name):
                used_names.add(node.id)
        return [n for n in used_names
                if n in STDLIB_MODULES and n not in imports
                and (f"{n}." in code or f"{n}(" in code)]

    @staticmethod
    def _check_runtime_import(skill_path):
        """Run subprocess import test. Returns PreflightResult on failure, None on success."""
        if not (skill_path and skill_path.exists()):
            return None
        test_code = (
            f"import sys; sys.path.insert(0, '{skill_path.parent}'); "
            f"import importlib.util; "
            f"spec = importlib.util.spec_from_file_location('test', '{skill_path}'); "
            f"mod = importlib.util.module_from_spec(spec); "
            f"spec.loader.exec_module(mod); "
            f"print('IMPORT_OK')"
        )
        try:
            r = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True, text=True, timeout=10
            )
            if "IMPORT_OK" not in r.stdout:
                error = r.stderr.strip().split("\n")[-1] if r.stderr else "Unknown import error"
                return PreflightResult(False, "imports", error)
        except subprocess.TimeoutExpired:
            return PreflightResult(False, "imports", "Import timed out (>10s)")
        return None

    def check_imports(self, code, skill_path=None):
        """Stage 2: Do all imports resolve? Detect missing stdlib imports."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return PreflightResult(False, "imports", "Cannot parse for import analysis")

        missing = self._check_static_imports(code, tree)
        if missing:
            return PreflightResult(False, "imports",
                f"Used but not imported: {', '.join(sorted(missing))}. "
                f"Add: {'; '.join(f'import {m}' for m in sorted(missing))}",
                {"missing_imports": sorted(missing)})

        rt_result = self._check_runtime_import(skill_path)
        if rt_result:
            return rt_result

        return PreflightResult(True)

    def check_interface(self, code):
        """Stage 3: Does the skill expose required interface?"""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return PreflightResult(False, "interface", "Cannot parse")

        top_level_funcs = set()
        classes_with_execute = []

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef):
                top_level_funcs.add(node.name)
            elif isinstance(node, ast.ClassDef):
                methods = {n.name for n in ast.walk(node)
                           if isinstance(n, ast.FunctionDef)}
                if "execute" in methods:
                    classes_with_execute.append(node.name)

        missing = []
        for req in self.REQUIRED_EXPORTS:
            if req not in top_level_funcs:
                if req == "execute" and classes_with_execute:
                    continue
                missing.append(req)

        if missing:
            return PreflightResult(False, "interface",
                f"Missing required exports: {', '.join(missing)}",
                {"missing": missing, "found_functions": sorted(top_level_funcs),
                 "classes_with_execute": classes_with_execute})

        return PreflightResult(True)

    @staticmethod
    def _collect_existing_imports(tree):
        """Collect top-level module names already imported in AST."""
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        return imports

    @staticmethod
    def _find_insert_position(lines):
        """Find the best line index to insert new imports."""
        # After last existing import if any
        for i in range(len(lines) - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                return i + 1
        # Otherwise after shebang and module docstring
        pos = 0
        if lines and lines[0].startswith("#!"):
            pos = 1
        if len(lines) > pos and lines[pos].startswith('"""'):
            for i in range(pos + 1, len(lines)):
                if '"""' in lines[i]:
                    return i + 1
        return pos

    def auto_fix_imports(self, code):
        """Auto-fix missing stdlib imports by adding them at the top."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code

        existing = self._collect_existing_imports(tree)
        to_add = [m for m in STDLIB_MODULES
                   if m not in existing and (f"{m}." in code or f"{m}(" in code)]
        if not to_add:
            return code

        lines = code.split("\n")
        insert_at = self._find_insert_position(lines)
        for j, m in enumerate(sorted(to_add)):
            lines.insert(insert_at + j, f"import {m}")
        return "\n".join(lines)


class EvolutionGuard:
    """
    Prevents evolution loops where the same error repeats.
    Tracks error fingerprints and suggests strategy changes.
    """

    def __init__(self):
        self._error_history = {}  # skill_name -> [{"fingerprint", "error", "version"}]
        self._max_same_error = 2

    def fingerprint(self, error):
        """Create error fingerprint (normalize for minor variations)."""
        normalized = error.lower().strip()
        normalized = re.sub(r'line \d+', 'line N', normalized)
        normalized = re.sub(r'v\d+', 'vN', normalized)
        normalized = re.sub(r'/[^\s]+/', '/PATH/', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def record_error(self, skill_name, error, version=""):
        """Record an error for a skill."""
        if skill_name not in self._error_history:
            self._error_history[skill_name] = []
        fp = self.fingerprint(error)
        self._error_history[skill_name].append({
            "fingerprint": fp, "error": error, "version": version,
        })

    def is_repeating(self, skill_name, error):
        """Check if this error has been seen before for this skill."""
        fp = self.fingerprint(error)
        history = self._error_history.get(skill_name, [])
        count = sum(1 for h in history if h["fingerprint"] == fp)
        return count >= self._max_same_error

    def get_error_summary(self, skill_name):
        """Get error history summary for LLM context."""
        history = self._error_history.get(skill_name, [])
        if not history:
            return ""

        groups = {}
        for h in history:
            fp = h["fingerprint"]
            if fp not in groups:
                groups[fp] = {"error": h["error"], "count": 0, "versions": []}
            groups[fp]["count"] += 1
            if h["version"]:
                groups[fp]["versions"].append(h["version"])

        lines = ["HISTORIA BŁĘDÓW (NIE POWTARZAJ TYCH SAMYCH):"]
        for fp, info in groups.items():
            lines.append(
                f"  - [{info['count']}x] {info['error'][:100]} "
                f"(w wersjach: {', '.join(info['versions'][-3:])})"
            )
        return "\n".join(lines)

    def suggest_strategy(self, skill_name, current_error):
        """Suggest evolution strategy based on error history and error type."""
        # Detect specific error patterns for better strategy selection
        error_lower = current_error.lower()

        # Validation errors (missing params, empty inputs) - likely interface/logic issue
        if any(kw in error_lower for kw in ["missing required", "validation", "missing 'path'", "no such file or directory: ''"]):
            return {
                "strategy": "add_interface",
                "instructions": "Skill ma błąd walidacji parametrów. Dodaj sprawdzanie wejścia i sensowne wartości domyślne.",
            }

        # IO/File errors - path issues, permissions
        if any(kw in error_lower for kw in ["no such file or directory", "permission denied", "not found"]):
            return {
                "strategy": "normal_evolve",
                "instructions": "Błąd ścieżki pliku lub IO. Upewnij się że ścieżki są prawidłowe i pliki istnieją.",
            }

        # Import errors
        if "not defined" in error_lower or "nameerror" in error_lower:
            return {
                "strategy": "auto_fix_imports",
                "instructions": "Błąd importu/zmiennej. Dodaj brakujące importy.",
            }

        if "modulenotfounderror" in error_lower or "no module named" in error_lower:
            return {
                "strategy": "install_deps",
                "instructions": "Brakujący moduł Python. Zainstaluj przez pip lub użyj alternatywy stdlib.",
            }

        # Syntax errors
        if "syntaxerror" in error_lower or "indentationerror" in error_lower:
            return {
                "strategy": "rewrite_from_scratch",
                "instructions": "Błąd składni. Przepisz kod poprawnie.",
            }

        # Check for repeating errors
        if self.is_repeating(skill_name, current_error):
            return {
                "strategy": "rewrite_from_scratch",
                "instructions": "Ten sam błąd się powtarza. Przepisz skill od zera z inaczej.",
            }

        return {
            "strategy": "normal_evolve",
            "instructions": "Standardowa ewolucja z kontekstem błędu.",
        }

    def build_evolution_prompt_context(self, skill_name, current_error):
        """Build extra context for LLM to prevent same mistakes."""
        parts = []

        summary = self.get_error_summary(skill_name)
        if summary:
            parts.append(summary)

        if "not defined" in current_error:
            match = re.search(r"name '(\w+)' is not defined", current_error)
            if match:
                missing = match.group(1)
                parts.append(
                    f"KRYTYCZNE: Dodaj 'import {missing}' na górze pliku! "
                    f"Poprzednie wersje zapominały o tym imporcie."
                )

        if "ModuleNotFoundError" in current_error:
            match = re.search(r"No module named '(\w+)'", current_error)
            if match:
                parts.append(
                    f"KRYTYCZNE: Moduł '{match.group(1)}' nie jest zainstalowany. "
                    f"Użyj alternatywy z biblioteki standardowej."
                )

        return "\n".join(parts) if parts else ""

    _FUNCTIONAL_MARKERS = ("subprocess", "os.system", "urllib", "socket",
                           "shutil.which", "Popen", "tempfile")
    _TRIVIAL_LINES = {"pass", "return", "return None", "return {}",
                      "return True", "return False"}

    @staticmethod
    def _is_trivial_execute(code):
        """Check if code has only a trivial execute() returning hardcoded success."""
        if not re.search(
            r'def execute\(self[^)]*\):\s*\n\s*return\s*\{\s*["\']success["\']\s*:\s*True\s*\}',
            code, re.MULTILINE
        ):
            return False
        m = re.search(r'def execute\(self[^)]*\):(.*?)(?=\n    def |\nclass |\Z)',
                      code, re.DOTALL)
        if m:
            body = [l.strip() for l in m.group(1).split("\n")
                    if l.strip() and not l.strip().startswith("#")]
            return len(body) <= 2
        return False

    def is_stub_skill(self, skill_path):
        """Detect if skill is a stub (placeholder/test implementation).
        Conservative: only flag clearly non-functional code.
        Real skills with subprocess/os/urllib calls are never stubs."""
        if not skill_path or not skill_path.exists():
            return False, "File not found"

        code = skill_path.read_text()
        lines = [l.strip() for l in code.split("\n") if l.strip()]

        if any(f in code for f in self._FUNCTIONAL_MARKERS):
            return False, ""
        if len(lines) < 8:
            return True, f"Too short ({len(lines)} lines) with no functional code"

        body_lines = [l for l in lines
                      if not l.startswith("#") and not l.startswith('"""')
                      and not l.startswith("'''")]
        meaningful = [l for l in body_lines if l not in self._TRIVIAL_LINES]
        if len(meaningful) < 5:
            return True, f"Only {len(meaningful)} meaningful lines"

        if self._is_trivial_execute(code):
            return True, "execute() returns hardcoded success with no logic"

        return False, ""

    def check_execution_result(self, skill_name, result, skill_path=None):
        """Analyze skill execution result for stub detection - ONLY based on code, not output."""
        # Check skill code if path provided
        if skill_path:
            is_stub, reason = self.is_stub_skill(skill_path)
            if is_stub:
                return {
                    "is_stub": True,
                    "issue": f"Stub skill detected: {reason}",
                    "suggestion": "Rewrite skill with full implementation"
                }
        
        return {"is_stub": False}
