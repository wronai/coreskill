#!/usr/bin/env python3
"""
preflight.py — Pre-flight validation before skill execution and evolution guards.

PROBLEM 1 (Pre-flight):
    SkillManager.exec_skill() loads and runs skill.py without checking
    if it even imports correctly. Result: "name 'shutil' is not defined"
    at RUNTIME, wasting an evolution cycle.

FIX:
    Before exec_skill(), run preflight:
    1. Syntax check (ast.parse)
    2. Import check (try import in subprocess)
    3. Interface check (has execute, get_info, health_check)
    4. Only THEN run execute()

PROBLEM 2 (Evolution guard):
    smart_evolve() generates new code via LLM, but doesn't check if the
    new code has the SAME bug. Result: v6→v7→v8→v9 all with "shutil not defined".

FIX:
    1. Before accepting evolved code, run preflight on it
    2. Track error fingerprints — if same error repeats, change strategy
    3. Inject explicit import requirements into LLM prompt
"""
import ast
import hashlib
import importlib.util
import json
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import Optional


class PreflightResult:
    """Result of pre-flight validation."""
    def __init__(self, ok: bool, stage: str = "", error: str = "",
                 details: dict = None):
        self.ok = ok
        self.stage = stage  # "syntax", "imports", "interface", "health"
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


class SkillPreflight:
    """
    Pre-flight validation for skill files.
    
    Run BEFORE exec_skill() and BEFORE accepting evolved code.
    """

    REQUIRED_EXPORTS = ["execute", "get_info", "health_check"]
    REQUIRED_CLASS_METHOD = "execute"

    def check_all(self, skill_path: Path) -> PreflightResult:
        """Run all pre-flight checks in order."""
        if not skill_path.exists():
            return PreflightResult(False, "exists", f"File not found: {skill_path}")

        code = skill_path.read_text()

        # 1. Syntax
        r = self.check_syntax(code)
        if not r.ok:
            return r

        # 2. Imports
        r = self.check_imports(code, skill_path)
        if not r.ok:
            return r

        # 3. Interface
        r = self.check_interface(code)
        if not r.ok:
            return r

        return PreflightResult(True)

    def check_syntax(self, code: str) -> PreflightResult:
        """Stage 1: Can Python parse this file?"""
        try:
            ast.parse(code)
            return PreflightResult(True)
        except SyntaxError as e:
            return PreflightResult(False, "syntax",
                f"Line {e.lineno}: {e.msg}",
                {"line": e.lineno, "offset": e.offset})

    def check_imports(self, code: str, skill_path: Path = None) -> PreflightResult:
        """
        Stage 2: Do all imports resolve?
        
        Uses subprocess to avoid polluting current process.
        Catches the exact "name 'X' is not defined" problem.
        """
        # Extract all imports from AST
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

        # Check for commonly-forgotten imports
        STDLIB_MODULES = {
            "shutil", "os", "sys", "json", "subprocess", "pathlib",
            "tempfile", "hashlib", "re", "time", "datetime", "traceback",
            "importlib", "ast", "threading", "signal", "socket",
        }

        # Find names used in code that look like module-level calls
        # but aren't imported
        missing = []
        for name in used_names:
            if name in STDLIB_MODULES and name not in imports:
                # Check if it's actually used as a module (not a variable)
                if f"{name}." in code or f"{name}(" in code:
                    missing.append(name)

        if missing:
            return PreflightResult(False, "imports",
                f"Used but not imported: {', '.join(sorted(missing))}. "
                f"Add: {'; '.join(f'import {m}' for m in sorted(missing))}",
                {"missing_imports": sorted(missing)})

        # Subprocess import test (catches dynamic import issues)
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

    def check_interface(self, code: str) -> PreflightResult:
        """
        Stage 3: Does the skill expose required interface?
        - get_info() function
        - health_check() function
        - execute() function OR class with execute() method
        """
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
                # Check if it's a class method
                if req == "execute" and classes_with_execute:
                    continue
                missing.append(req)

        if missing:
            return PreflightResult(False, "interface",
                f"Missing required exports: {', '.join(missing)}",
                {"missing": missing, "found_functions": sorted(top_level_funcs),
                 "classes_with_execute": classes_with_execute})

        return PreflightResult(True)

    def auto_fix_imports(self, code: str) -> str:
        """
        Attempt to auto-fix missing imports.
        
        If code uses shutil.which() but doesn't import shutil,
        add 'import shutil' at the top.
        """
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

        STDLIB = {
            "shutil", "os", "sys", "json", "subprocess", "pathlib",
            "tempfile", "hashlib", "re", "time", "datetime", "traceback",
            "importlib", "ast", "threading", "signal",
        }

        to_add = []
        for mod in STDLIB:
            if mod not in imports and (f"{mod}." in code or f"{mod}(" in code):
                to_add.append(mod)

        if not to_add:
            return code

        # Insert imports after any existing imports or at top
        import_lines = [f"import {m}" for m in sorted(to_add)]
        lines = code.split("\n")

        # Find last import line
        last_import = -1
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("import ") or stripped.startswith("from "):
                last_import = i

        if last_import >= 0:
            # Insert after last import
            for j, imp in enumerate(import_lines):
                lines.insert(last_import + 1 + j, imp)
        else:
            # Insert at top (after shebang/docstring)
            insert_at = 0
            if lines and lines[0].startswith("#!"):
                insert_at = 1
            if len(lines) > insert_at and lines[insert_at].startswith('"""'):
                # Skip docstring
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
    
    PROBLEM: v6→v7→v8→v9 all with "shutil not defined"
    
    HOW:
    1. Fingerprint each error
    2. If same fingerprint seen 2+ times → change strategy
    3. Auto-fix imports before asking LLM
    4. Inject error history into LLM prompt
    """

    def __init__(self):
        self._error_history = {}  # skill_name -> [{"fingerprint": ..., "error": ..., "version": ...}]
        self._max_same_error = 2

    def fingerprint(self, error: str) -> str:
        """Create error fingerprint (normalize for minor variations)."""
        # Remove line numbers, file paths, version numbers
        import re
        normalized = error.lower().strip()
        normalized = re.sub(r'line \d+', 'line N', normalized)
        normalized = re.sub(r'v\d+', 'vN', normalized)
        normalized = re.sub(r'/[^\s]+/', '/PATH/', normalized)
        normalized = re.sub(r'\s+', ' ', normalized)
        return hashlib.md5(normalized.encode()).hexdigest()[:12]

    def record_error(self, skill_name: str, error: str, version: str = ""):
        """Record an error for a skill."""
        if skill_name not in self._error_history:
            self._error_history[skill_name] = []
        fp = self.fingerprint(error)
        self._error_history[skill_name].append({
            "fingerprint": fp,
            "error": error,
            "version": version,
        })

    def is_repeating(self, skill_name: str, error: str) -> bool:
        """Check if this error has been seen before for this skill."""
        fp = self.fingerprint(error)
        history = self._error_history.get(skill_name, [])
        count = sum(1 for h in history if h["fingerprint"] == fp)
        return count >= self._max_same_error

    def get_error_summary(self, skill_name: str) -> str:
        """Get error history summary for LLM context."""
        history = self._error_history.get(skill_name, [])
        if not history:
            return ""

        # Group by fingerprint
        groups = {}
        for h in history:
            fp = h["fingerprint"]
            if fp not in groups:
                groups[fp] = {"error": h["error"], "count": 0, "versions": []}
            groups[fp]["count"] += 1
            if h["version"]:
                groups[fp]["versions"].append(h["version"])

        lines = ["HISTORIA BLEDOW (NIE POWTARZAJ TYCH SAMYCH):"]
        for fp, info in groups.items():
            lines.append(
                f"  - [{info['count']}x] {info['error'][:100]} "
                f"(w wersjach: {', '.join(info['versions'][-3:])})"
            )
        return "\n".join(lines)

    def suggest_strategy(self, skill_name: str, current_error: str) -> dict:
        """
        Suggest evolution strategy based on error history.
        
        Returns:
            {"strategy": "...", "instructions": "..."}
        """
        if self.is_repeating(skill_name, current_error):
            # Same error repeating — drastic measures
            if "not defined" in current_error:
                # Missing import — auto-fix instead of LLM
                return {
                    "strategy": "auto_fix_imports",
                    "instructions": (
                        "Ten sam blad importu powtarza sie. "
                        "Zamiast pytac LLM, automatycznie dodaj brakujace importy."
                    ),
                }
            elif "ModuleNotFoundError" in current_error:
                # Missing pip package
                return {
                    "strategy": "install_deps",
                    "instructions": (
                        "Brakujacy modul Python. Zainstaluj przez pip "
                        "przed kolejna proba ewolucji."
                    ),
                }
            else:
                # Unknown repeating error — try different approach
                return {
                    "strategy": "rewrite_from_scratch",
                    "instructions": (
                        "Blad powtarza sie po kilku probach naprawy. "
                        "Przepisz skill od zera z minimalnym kodem."
                    ),
                }
        else:
            return {
                "strategy": "normal_evolve",
                "instructions": "Standardowa ewolucja z kontekstem bledu.",
            }

    def build_evolution_prompt_context(self, skill_name: str,
                                        current_error: str) -> str:
        """
        Build extra context for LLM when evolving a skill.
        Prevents same mistakes.
        """
        parts = []

        # Error history
        summary = self.get_error_summary(skill_name)
        if summary:
            parts.append(summary)

        # Specific guards based on error type
        if "not defined" in current_error:
            # Extract the missing name
            import re
            match = re.search(r"name '(\w+)' is not defined", current_error)
            if match:
                missing = match.group(1)
                parts.append(
                    f"KRYTYCZNE: Dodaj 'import {missing}' na gorze pliku! "
                    f"Poprzednie wersje zapominaly o tym imporcie."
                )

        if "ModuleNotFoundError" in current_error:
            import re
            match = re.search(r"No module named '(\w+)'", current_error)
            if match:
                missing_mod = match.group(1)
                parts.append(
                    f"KRYTYCZNE: Modul '{missing_mod}' nie jest zainstalowany. "
                    f"Uzyj alternatywy z biblioteki standardowej lub "
                    f"dodaj subprocess.run(['pip','install','{missing_mod}']) w __init__."
                )

        return "\n".join(parts) if parts else ""


# === Integration with existing SkillManager ===

def patch_exec_skill(original_exec_skill, preflight: SkillPreflight):
    """
    Wrap SkillManager.exec_skill to add pre-flight checks.
    
    BEFORE: load module → run execute() → crash with 'shutil not defined'
    AFTER:  preflight check → fix if possible → load → run
    """
    def patched(name, input_data=None, version=None):
        # Get skill path
        # (This would need access to skill_path method — shown as concept)
        from pathlib import Path
        skill_dir = Path(__file__).parent.parent.parent / "skills"
        
        # Find skill file
        skill_p = None
        skill_base = skill_dir / name
        if skill_base.exists():
            # Find latest version
            versions = sorted([
                v.name for v in skill_base.iterdir()
                if v.is_dir() and v.name.startswith("v")
            ])
            if versions:
                target = version if version else versions[-1]
                skill_p = skill_base / target / "skill.py"

        if skill_p and skill_p.exists():
            # Run preflight
            result = preflight.check_all(skill_p)
            if not result.ok:
                if result.stage == "imports" and result.details.get("missing_imports"):
                    # Auto-fix imports
                    code = skill_p.read_text()
                    fixed = preflight.auto_fix_imports(code)
                    if fixed != code:
                        skill_p.write_text(fixed)
                        # Re-check
                        result = preflight.check_all(skill_p)

                if not result.ok:
                    return {
                        "success": False,
                        "error": f"Preflight failed ({result.stage}): {result.error}",
                        "preflight": result.to_dict(),
                    }

        # Preflight passed — run original
        return original_exec_skill(name, input_data, version)
    return patched


def patch_smart_evolve(original_smart_evolve, guard: EvolutionGuard,
                       preflight: SkillPreflight):
    """
    Wrap SkillManager.smart_evolve to add evolution guards.
    
    BEFORE: generate code → save → test → fail → repeat same bug
    AFTER:  check error history → adjust prompt → generate → preflight → save
    """
    def patched(name, error_info, *args, **kwargs):
        error_str = str(error_info)

        # Check if repeating
        strategy = guard.suggest_strategy(name, error_str)

        if strategy["strategy"] == "auto_fix_imports":
            # Don't ask LLM — just fix imports
            from pathlib import Path
            skill_dir = Path(__file__).parent.parent.parent / "skills"
            skill_base = skill_dir / name
            versions = sorted([
                v.name for v in skill_base.iterdir()
                if v.is_dir() and v.name.startswith("v")
            ])
            if versions:
                skill_p = skill_base / versions[-1] / "skill.py"
                if skill_p.exists():
                    code = skill_p.read_text()
                    fixed = preflight.auto_fix_imports(code)
                    if fixed != code:
                        skill_p.write_text(fixed)
                        guard.record_error(name, error_str, versions[-1])
                        return True, f"Auto-fixed imports in {name}/{versions[-1]}"

        # Record this error
        guard.record_error(name, error_str)

        # Add context to prevent same mistake
        extra_context = guard.build_evolution_prompt_context(name, error_str)

        # Call original with extra context
        # (This would need kwargs support in smart_evolve)
        return original_smart_evolve(name, error_info, *args,
                                     extra_context=extra_context, **kwargs)
    return patched


if __name__ == "__main__":
    # === Test Preflight ===
    print("=== PREFLIGHT TESTS ===\n")
    pf = SkillPreflight()

    # Test: missing import
    code_bad = textwrap.dedent("""
    def get_info():
        return {"name": "test"}
    def health_check():
        return True
    def execute(data):
        return {"path": shutil.which("python3")}
    """).strip()

    r = pf.check_imports(code_bad)
    print(f"Missing import test: {r}")
    assert not r.ok
    assert "shutil" in r.error

    # Test: auto-fix
    fixed = pf.auto_fix_imports(code_bad)
    print(f"Auto-fixed:\n{fixed[:100]}...")
    assert "import shutil" in fixed

    # Test: good code
    code_good = textwrap.dedent("""
    import shutil
    def get_info():
        return {"name": "test"}
    def health_check():
        return True
    class TestSkill:
        def execute(self, data):
            return {"path": shutil.which("python3")}
    """).strip()

    r = pf.check_interface(code_good)
    print(f"Interface test (good): {r}")
    assert r.ok

    # === Test Evolution Guard ===
    print("\n=== EVOLUTION GUARD TESTS ===\n")
    guard = EvolutionGuard()

    # Simulate repeating error
    guard.record_error("stt", "name 'shutil' is not defined", "v6")
    guard.record_error("stt", "name 'shutil' is not defined", "v7")

    print(f"Is repeating: {guard.is_repeating('stt', 'name shutil is not defined')}")
    assert guard.is_repeating("stt", "name 'shutil' is not defined")

    strategy = guard.suggest_strategy("stt", "name 'shutil' is not defined")
    print(f"Strategy: {strategy}")
    assert strategy["strategy"] == "auto_fix_imports"

    context = guard.build_evolution_prompt_context("stt", "name 'shutil' is not defined")
    print(f"Evolution context:\n{context}")
    assert "import shutil" in context

    print("\nAll tests passed!")
