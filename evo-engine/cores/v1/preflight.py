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

    def check_imports(self, code, skill_path=None):
        """Stage 2: Do all imports resolve? Detect missing stdlib imports."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return PreflightResult(False, "imports", "Cannot parse for import analysis")

        imports = set()
        used_names = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])
            elif isinstance(node, ast.Name):
                used_names.add(node.id)

        missing = []
        for name in used_names:
            if name in STDLIB_MODULES and name not in imports:
                if f"{name}." in code or f"{name}(" in code:
                    missing.append(name)

        if missing:
            return PreflightResult(False, "imports",
                f"Used but not imported: {', '.join(sorted(missing))}. "
                f"Add: {'; '.join(f'import {m}' for m in sorted(missing))}",
                {"missing_imports": sorted(missing)})

        # Subprocess import test (catches dynamic issues)
        if skill_path and skill_path.exists():
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

    def auto_fix_imports(self, code):
        """Auto-fix missing stdlib imports by adding them at the top."""
        try:
            tree = ast.parse(code)
        except SyntaxError:
            return code

        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.add(node.module.split(".")[0])

        to_add = []
        for mod in STDLIB_MODULES:
            if mod not in imports and (f"{mod}." in code or f"{mod}(" in code):
                to_add.append(mod)

        if not to_add:
            return code

        import_lines = [f"import {m}" for m in sorted(to_add)]
        lines = code.split("\n")

        # Find last import line
        last_import = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import = i

        if last_import >= 0:
            for j, imp in enumerate(import_lines):
                lines.insert(last_import + 1 + j, imp)
        else:
            insert_at = 0
            if lines and lines[0].startswith("#!"):
                insert_at = 1
            if len(lines) > insert_at and lines[insert_at].startswith('"""'):
                for i in range(insert_at + 1, len(lines)):
                    if '"""' in lines[i]:
                        insert_at = i + 1
                        break
            for j, imp in enumerate(import_lines):
                lines.insert(insert_at + j, imp)

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
        """Suggest evolution strategy based on error history."""
        if self.is_repeating(skill_name, current_error):
            if "not defined" in current_error:
                return {
                    "strategy": "auto_fix_imports",
                    "instructions": "Ten sam błąd importu się powtarza. Auto-fix imports.",
                }
            elif "ModuleNotFoundError" in current_error:
                return {
                    "strategy": "install_deps",
                    "instructions": "Brakujący moduł Python. Zainstaluj przez pip.",
                }
            else:
                return {
                    "strategy": "rewrite_from_scratch",
                    "instructions": "Błąd się powtarza. Przepisz skill od zera.",
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
