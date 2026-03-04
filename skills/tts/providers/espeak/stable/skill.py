import subprocess
import shutil


class TTSSkill:
    """Text-to-Speech using espeak (stdlib + subprocess only, zero pip deps)."""

    def __init__(self):
        self._backend = None
        for cmd in ("espeak-ng", "espeak"):
            if shutil.which(cmd):
                self._backend = cmd
                break

    def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
        if not self._backend:
            return {"success": False, "error": "espeak not installed (apt install espeak)"}
        try:
            subprocess.run(
                [self._backend, "-v", "pl", "--", text],
                check=True, capture_output=True, timeout=30
            )
            return {"success": True, "spoken": True, "text": text, "backend": self._backend}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "TTS timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_info():
    return {"name": "tts", "version": "v1", "description": "Text-to-Speech via espeak (stdlib only)"}


def health_check():
    return shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None


def check_readiness():
    """Multi-level readiness check: deps, hardware."""
    espeak = shutil.which("espeak-ng") or shutil.which("espeak")
    deps = {"espeak-ng": shutil.which("espeak-ng") is not None,
            "espeak": shutil.which("espeak") is not None}
    # Hardware: check for audio output via aplay -l
    aplay = shutil.which("aplay")
    speakers_ok = False
    speakers_info = ""
    if aplay:
        try:
            r = subprocess.run(["aplay", "-l"], capture_output=True, text=True, timeout=3)
            speakers_ok = "card" in r.stdout.lower()
            speakers_info = r.stdout.strip().split("\n")[0][:80] if r.stdout else r.stderr[:80]
        except Exception as e:
            speakers_info = str(e)
    hardware = {"speakers": speakers_ok, "speakers_info": speakers_info}
    issues = []
    if not espeak:
        issues.append("espeak/espeak-ng not installed (apt install espeak-ng)")
    if not speakers_ok:
        issues.append(f"No audio output detected: {speakers_info}")
    ok = bool(espeak) and speakers_ok
    return {"ok": ok, "deps": deps, "hardware": hardware, "resources": {}, "issues": issues}