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
            # Use espeak to speak the text and capture any output/errors
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
    return {"status": "ok" if (shutil.which("espeak-ng") or shutil.which("espeak")) else "error"}


def execute(params: dict) -> dict:
    """Module-level execute function that creates class instance and calls .execute(params)."""
    skill = TTSSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "Witaj w systemie TTS. To jest test mowy na język polski."}
    result = execute(test_params)
    print(result)