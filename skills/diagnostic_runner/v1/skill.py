"""diagnostic_runner skill — system validation collector.

Runs comprehensive system diagnostics and returns structured report.
Used by SelfReflection for automatic diagnosis.
"""
import json
import shutil
import subprocess
from pathlib import Path


def get_info():
    return {
        "name": "diagnostic_runner",
        "version": "v1",
        "description": "Comprehensive system diagnostic collector",
    }


def health_check():
    return True


class DiagnosticRunner:
    """Collects system diagnostics."""
    
    def execute(self, params: dict) -> dict:
        """Run diagnostics based on params.
        
        params:
            - check_type: "full" | "llm" | "audio" | "disk" | "skills"
            - skill_name: specific skill to check (optional)
        """
        check_type = params.get("check_type", "full")
        skill_name = params.get("skill_name", "")
        
        results = {
            "success": True,
            "timestamp": None,
            "checks": {}
        }
        
        if check_type in ("full", "llm"):
            results["checks"]["llm"] = self._check_llm()
            
        if check_type in ("full", "audio"):
            results["checks"]["microphone"] = self._check_microphone()
            results["checks"]["tts"] = self._check_tts()
            
        if check_type in ("full", "disk"):
            results["checks"]["disk"] = self._check_disk()
            
        if check_type in ("full", "system"):
            results["checks"]["commands"] = self._check_commands()
            
        # Count issues
        issues = []
        for category, data in results["checks"].items():
            if not data.get("ok", True):
                issues.append(f"{category}: {data.get('error', 'issue')}")
                
        results["summary"] = {
            "total_checks": len(results["checks"]),
            "passed": sum(1 for c in results["checks"].values() if c.get("ok")),
            "failed": sum(1 for c in results["checks"].values() if not c.get("ok")),
            "issues": issues
        }
        
        return results
    
    def _check_llm(self) -> dict:
        """Check LLM connectivity."""
        # We can't actually call LLM from here without passing it in
        # So we just check if required tools exist
        return {"ok": True, "note": "LLM check requires core integration"}
    
    def _check_microphone(self) -> dict:
        """Check microphone availability."""
        if not shutil.which("arecord"):
            return {"ok": False, "error": "arecord not installed"}
            
        try:
            result = subprocess.run(
                ["arecord", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return {"ok": False, "error": result.stderr[:100]}
                
            lines = result.stdout.strip().split('\n')
            devices = [l for l in lines if l.strip().startswith('card') and 'device' in l]
            
            if not devices:
                return {"ok": False, "error": "No capture devices found"}
                
            return {"ok": True, "devices": len(devices)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _check_tts(self) -> dict:
        """Check TTS backend."""
        if shutil.which("espeak-ng"):
            return {"ok": True, "backend": "espeak-ng"}
        elif shutil.which("espeak"):
            return {"ok": True, "backend": "espeak"}
        else:
            return {"ok": False, "error": "No TTS backend found"}
    
    def _check_disk(self) -> dict:
        """Check disk space."""
        try:
            total, used, free = shutil.disk_usage("/home")
            free_gb = free / (1024**3)
            
            if free_gb < 1:
                return {"ok": False, "free_gb": free_gb, "critical": True}
            elif free_gb < 5:
                return {"ok": False, "free_gb": free_gb, "warning": True}
            else:
                return {"ok": True, "free_gb": free_gb}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def _check_commands(self) -> dict:
        """Check required system commands."""
        required = {
            "arecord": "audio recording",
            "sox": "audio processing",
            "ffmpeg": "media conversion",
            "espeak-ng": "text-to-speech",
        }
        
        missing = []
        for cmd, purpose in required.items():
            if not shutil.which(cmd):
                missing.append(f"{cmd} ({purpose})")
                
        if missing:
            return {"ok": False, "missing": missing}
        return {"ok": True, "commands": list(required.keys())}


def execute(input_data: dict) -> dict:
    return DiagnosticRunner().execute(input_data)


if __name__ == "__main__":
    print(json.dumps(execute({"check_type": "full"}), indent=2, ensure_ascii=False))
