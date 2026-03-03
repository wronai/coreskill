import subprocess
import sys
import os
import json
import importlib.util

class DepsSkill:
    def __init__(self):
        self.tools = {
            "tts": ["espeak", "festival"],
            "audio": ["aplay", "paplay", "ffplay", "mpv", "sox"],
            "stt": ["arecord", "parec", "pactl", "ffmpeg", "vosk-transcriber"],
            "network": ["curl", "wget"],
            "dev": ["git", "docker", "python3", "pip3", "node"],
            "text": ["sed", "awk", "grep", "jq"]
        }

    def check_system(self, cmd):
        try:
            r = subprocess.run(["which", cmd], capture_output=True, text=True, timeout=5)
            path = r.stdout.strip()
            return {"available": r.returncode == 0, "command": cmd, "path": path}
        except:
            return {"available": False, "command": cmd, "path": ""}

    def check_python_module(self, module_name):
        try:
            importlib.import_module(module_name)
            return {"available": True, "module": module_name}
        except ImportError:
            return {"available": False, "module": module_name}

    def pip_install(self, package, user=True):
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

    def execute(self, params: dict) -> dict:
        action = params.get("action", "check")
        if action == "scan":
            result = {}
            for category, cmds in self.tools.items():
                result[category] = {}
                for cmd in cmds:
                    check = self.check_system(cmd)
                    result[category][cmd] = check["available"]
            return {"success": True, "capabilities": result}
        elif action == "update_system":
            update_command = "apt-get update"
            check = self.check_system(update_command)
            if check["available"]:
                r = subprocess.run(update_command, capture_output=True, text=True)
                return {"success": True, "output": r.stdout[-300:]}
            else:
                return {"success": False, "error": f"Update command '{update_command}' not found."}
        elif action == "check_module":
            return self.check_python_module(params.get("module", ""))
        return {"success": False, "error": f"Unknown action: {action}"}

    def get_info(self):
        return {
            "name": "deps",
            "version": "v1",
            "description": "Dependency detection, installation, system capability scanning",
            "actions": ["scan", "check_module", "update_system"],
            "author": "evo-engine"
        }

    def health_check(self):
        return True

def get_info():
    return DepsSkill().get_info()

def health_check():
    return DepsSkill().health_check()

if __name__ == "__main__":
    d = DepsSkill()
    print(f"Info: {json.dumps(d.get_info(), indent=2)}")
    scan = d.execute({"action": "scan"})
    print(f"System scan: {json.dumps(scan, indent=2)}")
    update = d.execute({"action": "update_system"})
    print(f"Update system: {json.dumps(update, indent=2)}")