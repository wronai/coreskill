"""diagnostics.py — DiagnosticEngine for system health checks.

Extracted from SelfReflection to reduce cyclomatic complexity.
Each check method is independent and can be run separately.
"""
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from ..logger import Logger
    from ..skill_manager import SkillManager


class DiagnosticEngine:
    """Engine for running system diagnostic checks.
    
    Extracted from SelfReflection to separate concerns:
    - This class: runs individual health checks
    - SelfReflection: orchestrates when/why to run diagnostics
    """
    
    def __init__(self, llm_client=None, skill_manager=None, logger=None):
        self.llm = llm_client
        self.sm = skill_manager
        self.log = logger
    
    # ── Individual Check Methods ─────────────────────────────────────
    
    def check_llm_health(self) -> dict:
        """Check if LLM API responds."""
        if not self.llm:
            return {"ok": False, "error": "LLM client not available", "critical": True}
            
        try:
            start = time.time()
            response = self.llm.chat(
                [{"role": "user", "content": "Respond with only 'OK'"}],
                max_tokens=5)
            latency_ms = int((time.time() - start) * 1000)
            
            if response and "error" not in response.lower():
                return {"ok": True, "latency_ms": latency_ms, "model": getattr(self.llm, 'model', 'unknown')}
            else:
                return {"ok": False, "error": response or "No response", "latency_ms": latency_ms}
        except Exception as e:
            return {"ok": False, "error": str(e), "critical": True}
    
    def check_system_commands(self) -> dict:
        """Check required system commands."""
        required = {
            "arecord": "alsa-utils",
            "sox": "sox",
            "ffmpeg": "ffmpeg", 
            "espeak-ng": "espeak-ng",
            "vosk-transcriber": "vosk (pip)",
        }
        
        missing = []
        for cmd, pkg in required.items():
            if not shutil.which(cmd):
                missing.append((cmd, pkg))
                
        if missing:
            apt_packages = [m[1] for m in missing if not m[1].startswith('vosk')]
            return {
                "ok": False,
                "missing": [m[0] for m in missing],
                "packages": [m[1] for m in missing],
                "install_cmd": f"sudo apt install {' '.join(set(apt_packages))}" if apt_packages else ""
            }
        return {"ok": True, "commands": list(required.keys())}
    
    def check_microphone(self) -> dict:
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
                return {"ok": False, "error": f"arecord -l failed: {result.stderr[:100]}"}
                
            lines = result.stdout.strip().split('\n')
            capture_cards = [l for l in lines if l.strip().startswith('card') and 'device' in l]
            
            if not capture_cards:
                return {"ok": False, "error": "No capture devices found"}
                
            return {"ok": True, "devices": len(capture_cards)}
        except Exception as e:
            return {"ok": False, "error": str(e)}
    
    def check_skills_health(self) -> dict:
        """Check health_check() of all skills."""
        if not self.sm:
            return {"ok": False, "error": "SkillManager not available"}
            
        broken = []
        all_skills = self.sm.list_skills()
        
        for skill_name in all_skills:
            try:
                health = self.sm.check_health(skill_name)
                # check_health returns bool or dict
                if isinstance(health, dict):
                    if not health.get("ok", True):
                        broken.append(skill_name)
                elif not health:
                    broken.append(skill_name)
            except Exception as e:
                broken.append(f"{skill_name}({str(e)[:20]})")
                
        if broken:
            return {"ok": False, "broken": broken, "total": len(all_skills)}
        return {"ok": True, "total": len(all_skills)}
    
    def check_vosk_model(self) -> dict:
        """Check if Vosk model exists."""
        model_paths = [
            Path.home() / ".cache" / "vosk" / "vosk-model-small-pl-0.22",
            Path.home() / ".cache" / "vosk" / "model",
            Path("/usr/share/vosk/model"),
        ]
        
        for p in model_paths:
            if p.exists():
                return {"ok": True, "path": str(p)}
                
        return {
            "ok": False,
            "error": "No Vosk model found",
            "searched": [str(p) for p in model_paths]
        }
    
    def check_tts_backend(self) -> dict:
        """Check TTS backend availability."""
        if shutil.which("espeak-ng"):
            return {"ok": True, "backend": "espeak-ng"}
        elif shutil.which("espeak"):
            return {"ok": True, "backend": "espeak"}
        else:
            return {"ok": False, "error": "No TTS backend found (espeak-ng/espeak)"}
    
    def check_disk_space(self) -> dict:
        """Check disk space availability."""
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
    
    # ── Full Scan ──────────────────────────────────────────────────────

    def full_scan(self, include_llm: bool = False) -> dict:
        """Run all diagnostic checks and return aggregated report.

        Returns dict with:
            status: "healthy" | "degraded" | "critical"
            checks: dict of check_name → result dict
            issues: list of problem descriptions
            auto_fixable: list of commands that can auto-fix issues
        """
        checks = {}
        issues = []
        auto_fixable = []

        # Run all non-LLM checks
        check_methods = [
            ("system_commands", self.check_system_commands),
            ("disk_space", self.check_disk_space),
            ("tts_backend", self.check_tts_backend),
            ("vosk_model", self.check_vosk_model),
            ("microphone", self.check_microphone),
            ("skills_health", self.check_skills_health),
        ]

        if include_llm:
            check_methods.insert(0, ("llm_health", self.check_llm_health))

        for name, method in check_methods:
            try:
                result = method()
                checks[name] = result
                if not result.get("ok"):
                    desc = result.get("error", "")
                    if not desc and "missing" in result:
                        desc = f"Missing: {', '.join(result['missing'])}"
                    if not desc and "broken" in result:
                        desc = f"Broken skills: {', '.join(result['broken'])}"
                    if not desc:
                        desc = f"{name} check failed"
                    issues.append({"check": name, "description": desc,
                                   "critical": result.get("critical", False)})
                    # Collect auto-fixable commands
                    if result.get("install_cmd"):
                        auto_fixable.append(result["install_cmd"])
            except Exception as e:
                checks[name] = {"ok": False, "error": str(e)}
                issues.append({"check": name, "description": str(e),
                               "critical": False})

        # Determine overall status
        critical = any(i.get("critical") for i in issues)
        if critical:
            status = "critical"
        elif issues:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "status": status,
            "checks": checks,
            "issues": issues,
            "auto_fixable": auto_fixable,
            "total_checks": len(check_methods),
            "passed": sum(1 for c in checks.values() if c.get("ok")),
            "failed": sum(1 for c in checks.values() if not c.get("ok")),
        }

    # ── LLM Analysis ───────────────────────────────────────────────────
    
    def llm_analyze_error(self, skill_name: str, error: str, findings: List[dict]) -> str:
        """Use LLM to analyze error and provide recommendation."""
        if not self.llm:
            return "[LLM not available]"
            
        try:
            context = f"""System evo-engine encountered a problem:
- Skill: {skill_name or 'general'}
- Error: {error or 'unknown'}
- Diagnostics: {json.dumps(findings, default=str, ensure_ascii=False)[:1000]}

As a technical expert of the evo-engine system, provide:
1. Most likely cause (1 sentence)
2. Specific fix command to execute
3. Whether it can be fixed automatically (yes/no)

Answer briefly, specifically, in Polish."""

            response = self.llm.chat(
                [{"role": "user", "content": context}],
                max_tokens=200, temperature=0.3)
            return response.strip() if response else ""
        except Exception as e:
            return f"[LLM analysis failed: {e}]"
    
    # ── Auto-fix Methods ───────────────────────────────────────────────
    
    def attempt_apt_install(self, fix_cmd: str) -> List[str]:
        """Attempt to install missing packages via apt."""
        actions = []
        if "apt install" not in fix_cmd:
            return actions
            
        try:
            # Extract package names
            pkgs = fix_cmd.replace("sudo apt install", "").strip().split()
            for pkg in pkgs:
                r = subprocess.run(
                    ["sudo", "apt", "install", "-y", pkg],
                    capture_output=True,
                    timeout=120
                )
                if r.returncode == 0:
                    actions.append(f"Installed {pkg}")
                else:
                    actions.append(f"Failed to install {pkg}")
        except Exception as e:
            actions.append(f"Installation error: {e}")
        
        return actions
