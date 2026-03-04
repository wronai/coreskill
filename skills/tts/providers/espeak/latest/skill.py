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
            result = subprocess.run(
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
    return {"status": "ok" if (shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None) else "error"}


def execute(params: dict) -> dict:
    skill = TTSSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Simple test
    skill = TTSSkill()
    result = skill.execute({"text": "Test TTS"})
    print(result)