import subprocess
import shutil
import re


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
            # Use espeak with Polish voice (-v pl) and ensure proper encoding
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
    espeak_path = shutil.which("espeak-ng") or shutil.which("espeak")
    if espeak_path:
        try:
            # Quick test: espeak should respond to --version
            result = subprocess.run([espeak_path, "--version"], 
                                   capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return {"status": "ok"}
        except Exception:
            pass
    return {"status": "error", "message": "espeak not available"}


def execute(params: dict) -> dict:
    skill = TTSSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    import sys
    test_text = sys.argv[1] if len(sys.argv) > 1 else "Witaj w systemie TTS."
    result = execute({"text": test_text})
    print(result)