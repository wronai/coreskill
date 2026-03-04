import subprocess
import sys
import os
import json
import importlib.util

class DepsSkill:
    def __init__(self):
        self.tools = {
            "tts": ["espeak", "espeak-ng", "festival"],
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
        except Exception:
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
                "output": r.stdout[-300:] if r.stdout else "",
                "error": r.stderr[-300:] if r.returncode != 0 and r.stderr else None
            }
        except Exception as e:
            return {"success": False, "package": package, "error": str(e)}

    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "")
            action = params.get("action", "check")
            
            if action == "scan":
                result = {}
                for category, cmds in self.tools.items():
                    result[category] = {}
                    for cmd in cmds:
                        check = self.check_system(cmd)
                        result[category][cmd] = check["available"]
                return {
                    "success": True,
                    "capabilities": result,
                    "spoken": "System capabilities scanned successfully"
                }
            
            elif action == "update_system":
                update_command = "apt-get update"
                check = self.check_system("apt-get")
                if check["available"]:
                    r = subprocess.run([update_command], capture_output=True, text=True, timeout=120)
                    return {
                        "success": r.returncode == 0,
                        "output": r.stdout[-300:] if r.stdout else "",
                        "error": r.stderr[-300:] if r.returncode != 0 and r.stderr else None,
                        "spoken": "System update completed" if r.returncode == 0 else "System update failed"
                    }
                else:
                    return {
                        "success": False,
                        "error": "Update command 'apt-get' not found.",
                        "spoken": "System update failed: apt-get not available"
                    }
            
            elif action == "check_module":
                module_name = params.get("module", "")
                if not module_name:
                    # Try to extract module name from text
                    import re
                    match = re.search(r'check\s+module\s+(\w+)', text.lower())
                    if match:
                        module_name = match.group(1)
                    else:
                        return {
                            "success": False,
                            "error": "No module name provided",
                            "spoken": "Please specify a Python module to check"
                        }
                result = self.check_python_module(module_name)
                return {
                    "success": result["available"],
                    "module": module_name,
                    "available": result["available"],
                    "spoken": f"Module {module_name} is {'available' if result['available'] else 'not available'}"
                }
            
            elif action == "install":
                # Try to extract package name from text
                import re
                match = re.search(r'install\s+(\S+)', text.lower())
                if match:
                    package = match.group(1)
                else:
                    package = params.get("package", "")
                if not package:
                    return {
                        "success": False,
                        "error": "No package name provided",
                        "spoken": "Please specify a package to install"
                    }
                result = self.pip_install(package)
                return {
                    "success": result["success"],
                    "package": package,
                    "output": result.get("output", ""),
                    "error": result.get("error"),
                    "spoken": f"Package {package} {'installed' if result['success'] else 'installation failed'}"
                }
            
            else:
                return {
                    "success": False,
                    "error": f"Unknown action: {action}",
                    "spoken": f"Unknown action: {action}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "spoken": "An error occurred while processing your request"
            }

    def get_info(self):
        return {
            "name": "deps",
            "version": "v1",
            "description": "Dependency detection, installation, system capability scanning",
            "actions": ["scan", "check_module", "update_system", "install"],
            "author": "evo-engine"
        }

    def health_check(self):
        try:
            # Check basic system commands
            espeak_check = self.check_system("espeak") or self.check_system("espeak-ng")
            python_check = self.check_system("python3")
            
            if espeak_check["available"] and python_check["available"]:
                return {"status": "ok"}
            else:
                return {
                    "status": "error",
                    "message": f"Missing dependencies: espeak={espeak_check['available']}, python3={python_check['available']}"
                }
        except Exception as e:
            return {"status": "error", "message": str(e)}

def get_info():
    return DepsSkill().get_info()

def health_check():
    return DepsSkill().health_check()

def execute(params: dict) -> dict:
    return DepsSkill().execute(params)

if __name__ == "__main__":
    d = DepsSkill()
    print(f"Info: {json.dumps(d.get_info(), indent=2)}")
    scan = d.execute({"action": "scan"})
    print(f"System scan: {json.dumps(scan, indent=2)}")
    update = d.execute({"action": "update_system"})
    print(f"Update system: {json.dumps(update, indent=2)}")
    health = d.health_check()
    print(f"Health check: {json.dumps(health, indent=2)}")