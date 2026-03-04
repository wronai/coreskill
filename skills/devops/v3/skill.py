"""
devops skill - Test, validate and deploy skills.
Bootstrap skill for evo-engine. No external dependencies.
"""
import subprocess
import sys
import os
import json
import ast
import importlib.util
from pathlib import Path


class DevOpsSkill:
    """Test, validate and deploy skills in isolated subprocess."""

    def check_syntax(self, file_path):
        """Check Python syntax without executing."""
        try:
            with open(file_path) as f:
                source = f.read()
            ast.parse(source)
            return {"success": True, "file": file_path, "error": None}
        except SyntaxError as e:
            return {"success": False, "file": file_path,
                    "error": f"Line {e.lineno}: {e.msg}"}

    def detect_imports(self, file_path):
        """Detect all imports in a Python file."""
        try:
            with open(file_path) as f:
                tree = ast.parse(f.read())
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name.split(".")[0])
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module.split(".")[0])
            return {"success": True, "imports": sorted(set(imports))}
        except Exception as e:
            return {"success": False, "error": str(e), "imports": []}

    def check_deps(self, file_path):
        """Check which imports are available and which are missing."""
        result = self.detect_imports(file_path)
        if not result["success"]:
            return result

        stdlib = {
            "os", "sys", "json", "subprocess", "pathlib", "datetime",
            "hashlib", "tempfile", "shutil", "traceback", "importlib",
            "ast", "re", "io", "threading", "time", "typing", "collections",
            "functools", "itertools", "math", "random", "socket", "http",
            "urllib", "base64", "copy", "logging", "abc", "dataclasses",
            "enum", "contextlib", "signal", "argparse", "textwrap",
            "string", "struct", "csv", "xml", "html", "email",
        }

        available = []
        missing = []
        for imp in result["imports"]:
            if imp in stdlib:
                available.append(imp)
                continue
            try:
                importlib.import_module(imp)
                available.append(imp)
            except ImportError:
                missing.append(imp)

        return {
            "success": len(missing) == 0,
            "imports": result["imports"],
            "available": available,
            "missing": missing,
            "error": f"Missing: {', '.join(missing)}" if missing else None
        }

    def find_system_alternatives(self, missing_modules):
        """Suggest system command alternatives for missing Python modules."""
        alternatives = {
            "pyttsx3": {"cmd": "espeak", "check": ["espeak", "--version"],
                        "hint": "Use subprocess.run(['espeak', text]) instead of pyttsx3"},
            "gtts": {"cmd": "espeak", "check": ["espeak", "--version"],
                     "hint": "Use espeak as fallback, or pip install gtts"},
            "requests": {"cmd": "curl", "check": ["curl", "--version"],
                         "hint": "Use urllib.request (stdlib) or subprocess curl"},
            "numpy": {"hint": "Use math stdlib module for basic math"},
            "pandas": {"hint": "Use csv stdlib module for basic data"},
        }
        results = {}
        for mod in missing_modules:
            if mod in alternatives:
                alt = alternatives[mod]
                if "check" in alt:
                    try:
                        r = subprocess.run(alt["check"], capture_output=True, timeout=5)
                        alt["available"] = r.returncode == 0
                    except:
                        alt["available"] = False
                results[mod] = alt
            else:
                results[mod] = {"hint": f"pip install {mod}", "available": False}
        return results

    def test_skill(self, skill_path, timeout=15):
        """Test a skill by running it in a subprocess."""
        skill_path = str(skill_path)
        # Step 1: Syntax check
        syntax = self.check_syntax(skill_path)
        if not syntax["success"]:
            return {"success": False, "phase": "syntax",
                    "error": syntax["error"], "output": ""}

        # Step 2: Dependency check
        deps = self.check_deps(skill_path)
        if not deps["success"]:
            alts = self.find_system_alternatives(deps["missing"])
            return {"success": False, "phase": "deps",
                    "missing": deps["missing"], "alternatives": alts,
                    "error": deps["error"], "output": ""}

        # Step 3: Run in subprocess
        try:
            r = subprocess.run(
                [sys.executable, skill_path],
                capture_output=True, text=True, timeout=timeout,
                cwd=str(Path(skill_path).parent),
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
            return {
                "success": r.returncode == 0,
                "phase": "runtime",
                "output": r.stdout[-500:] if r.stdout else "",
                "error": r.stderr[-500:] if r.stderr and r.returncode != 0 else None,
                "returncode": r.returncode
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "phase": "runtime",
                    "error": f"Timeout after {timeout}s", "output": ""}
        except Exception as e:
            return {"success": False, "phase": "runtime",
                    "error": str(e), "output": ""}

    def health_check_skill(self, skill_path):
        """Run skill's health_check() function."""
        try:
            spec = importlib.util.spec_from_file_location("sk", str(skill_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "health_check"):
                result = mod.health_check()
                return {"success": True, "healthy": result}
            return {"success": True, "healthy": None, "note": "No health_check function"}
        except Exception as e:
            return {"success": False, "healthy": False, "error": str(e)}

    def generate_fix_prompt(self, skill_path, test_result):
        """Generate a prompt for LLM to fix a broken skill."""
        phase = test_result.get("phase", "unknown")
        error = test_result.get("error", "")
        missing = test_result.get("missing", [])
        alternatives = test_result.get("alternatives", {})

        try:
            with open(skill_path) as f:
                code = f.read()
        except:
            code = "<could not read>"

        prompt = f"Fix this Python skill. Current code:\n```python\n{code}\n```\n\n"

        if phase == "deps" and missing:
            prompt += f"PROBLEM: Missing Python modules: {', '.join(missing)}\n"
            for mod, alt in alternatives.items():
                if alt.get("available"):
                    prompt += f"SOLUTION for {mod}: {alt['hint']}\n"
                else:
                    prompt += f"Alternative for {mod}: {alt.get('hint', 'unknown')}\n"
            prompt += "\nIMPORTANT: Do NOT use the missing modules. Use only stdlib + available system commands.\n"
        elif phase == "syntax":
            prompt += f"PROBLEM: Syntax error: {error}\n"
        elif phase == "runtime":
            prompt += f"PROBLEM: Runtime error: {error}\n"

        prompt += ("Return ONLY the complete fixed Python code.\n"
                   "Requirements: class with execute(dict)->dict, get_info()->dict, "
                   "health_check()->bool, __main__ test block.\n"
                   "execute() must return dict with 'success' and 'spoken' keys for TTS-like skills.")
        return prompt

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "test")
        path = input_data.get("path", "")

        if action == "test":
            return self.test_skill(path)
        elif action == "check_syntax":
            return self.check_syntax(path)
        elif action == "check_deps":
            return self.check_deps(path)
        elif action == "detect_imports":
            return self.detect_imports(path)
        elif action == "health_check_skill":
            return self.health_check_skill(path)
        elif action == "find_alternatives":
            return {"success": True, "alternatives":
                    self.find_system_alternatives(input_data.get("modules", []))}
        elif action == "generate_fix":
            test_result = input_data.get("test_result", {})
            return {"success": True,
                    "prompt": self.generate_fix_prompt(path, test_result)}
        return {"success": False, "error": f"Unknown action: {action}"}


def get_info():
    return {
        "name": "devops",
        "version": "v1",
        "description": "Test, validate and deploy skills. Detect deps, suggest fixes.",
        "actions": ["test", "check_syntax", "check_deps", "detect_imports",
                     "health_check_skill", "find_alternatives", "generate_fix"],
        "author": "evo-engine"
    }


def health_check():
    return {"status": "ok"}


def execute(params: dict) -> dict:
    """Module-level execute function for evo-engine."""
    try:
        skill = DevOpsSkill()
        return skill.execute(params)
    except Exception as e:
        return {"success": False, "error": str(e), "spoken": "DevOps skill failed."}


if __name__ == "__main__":
    d = DevOpsSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Syntax self-check: {d.check_syntax(__file__)}")
    print(f"Deps self-check: {json.dumps(d.check_deps(__file__), indent=2)}")