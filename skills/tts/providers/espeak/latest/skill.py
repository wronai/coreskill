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
            return {
                "success": True,
                "spoken": True,
                "text": text,
                "backend": self._backend,
                "stderr": result.stderr.decode().strip() if result.stderr else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "TTS timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_info():
    return {"name": "tts", "version": "v1", "description": "Text-to-Speech via espeak (stdlib only)"}


def health_check():
    espeak_available = shutil.which("espeak-ng") is not None or shutil.which("espeak") is not None
    return {"status": "ok" if espeak_available else "error", "message": "espeak not found" if not espeak_available else ""}


def execute(params: dict) -> dict:
    skill = TTSSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "Witaj w Evo-Engine. Rozmiar instalacji: ~150–300 MB."}
    result = execute(test_params)
    print(result)