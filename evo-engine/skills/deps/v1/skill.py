"""
deps skill - Dependency detection, installation, and system capability scanning.
Bootstrap skill for evo-engine. No external dependencies.
"""
import subprocess
import sys
import os
import json
import importlib.util


class DepsSkill:
    """Detect, install and manage Python and system dependencies."""

    def check_python_module(self, module_name):
        """Check if a Python module is importable."""
        try:
            importlib.import_module(module_name)
            return {"available": True, "module": module_name}
        except ImportError:
            return {"available": False, "module": module_name}

    def check_system_command(self, cmd):
        """Check if a system command exists."""
        try:
            r = subprocess.run(
                ["which", cmd], capture_output=True, text=True, timeout=5)
            path = r.stdout.strip()
            return {"available": r.returncode == 0, "command": cmd, "path": path}
        except:
            return {"available": False, "command": cmd, "path": ""}

    def pip_install(self, package, user=True):
        """Install a Python package via pip."""
        cmd = [sys.executable, "-m", "pip", "install", package, "-q"]
        if user:
            cmd.append("--user")
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            return {
                "success": r.returncode == 0,
                "package": package,
                "output": r.stdout[-300:],
                "error": r.stderr[-300:] if r.returncode != 0 else None
            }
        except Exception as e:
            return {"success": False, "package": package, "error": str(e)}

    def scan_system(self):
        """Scan system for available tools and capabilities."""
        tools = {
            "tts": ["espeak", "festival", "say"],
            "audio": ["aplay", "paplay", "ffplay", "mpv", "sox"],
            "network": ["curl", "wget"],
            "dev": ["git", "docker", "python3", "pip3", "node"],
            "text": ["sed", "awk", "grep", "jq"],
        }
        result = {}
        for category, cmds in tools.items():
            result[category] = {}
            for cmd in cmds:
                check = self.check_system_command(cmd)
                result[category][cmd] = check["available"]
        return {"success": True, "capabilities": result}

    def suggest_alternatives(self, missing_module):
        """Suggest stdlib/system alternatives for missing Python packages."""
        alternatives = {
            "pyttsx3": {
                "system": ["espeak"],
                "code_hint": "subprocess.run(['espeak', '-v', lang, '--', text])",
                "description": "Use espeak system command for TTS"
            },
            "gtts": {
                "system": ["espeak"],
                "code_hint": "subprocess.run(['espeak', text])",
                "description": "Use espeak instead of Google TTS"
            },
            "requests": {
                "stdlib": "urllib.request",
                "code_hint": "urllib.request.urlopen(url).read()",
                "description": "Use stdlib urllib.request"
            },
            "numpy": {
                "stdlib": "math",
                "code_hint": "import math",
                "description": "Use stdlib math for basic operations"
            },
            "flask": {
                "stdlib": "http.server",
                "code_hint": "from http.server import HTTPServer, BaseHTTPRequestHandler",
                "description": "Use stdlib http.server for simple servers"
            },
            "beautifulsoup4": {
                "stdlib": "html.parser",
                "code_hint": "from html.parser import HTMLParser",
                "description": "Use stdlib html.parser"
            },
            "pyyaml": {
                "stdlib": "json",
                "code_hint": "import json",
                "description": "Use JSON format instead of YAML"
            },
        }
        if missing_module in alternatives:
            alt = alternatives[missing_module]
            # Check if system alternatives are available
            if "system" in alt:
                for cmd in alt["system"]:
                    check = self.check_system_command(cmd)
                    if check["available"]:
                        alt["system_available"] = True
                        alt["available_cmd"] = cmd
                        break
                else:
                    alt["system_available"] = False
            return {"success": True, "module": missing_module, "alternative": alt}
        return {"success": True, "module": missing_module,
                "alternative": {"description": f"Try: pip install {missing_module}",
                                "code_hint": f"pip install {missing_module}"}}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "scan")
        if action == "scan":
            return self.scan_system()
        elif action == "check_module":
            return self.check_python_module(input_data.get("module", ""))
        elif action == "check_command":
            return self.check_system_command(input_data.get("command", ""))
        elif action == "pip_install":
            return self.pip_install(input_data.get("package", ""))
        elif action == "suggest":
            return self.suggest_alternatives(input_data.get("module", ""))
        return {"success": False, "error": f"Unknown action: {action}"}


def get_info():
    return {
        "name": "deps",
        "version": "v1",
        "description": "Dependency detection, installation, system capability scanning",
        "actions": ["scan", "check_module", "check_command", "pip_install", "suggest"],
        "author": "evo-engine"
    }


def health_check():
    return True


if __name__ == "__main__":
    d = DepsSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    scan = d.scan_system()
    print(f"System scan: {json.dumps(scan, indent=2)}")
    alt = d.suggest_alternatives("pyttsx3")
    print(f"Alternative for pyttsx3: {json.dumps(alt, indent=2)}")
