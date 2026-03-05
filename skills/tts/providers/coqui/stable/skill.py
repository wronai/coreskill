import shutil


def get_info():
    return {
        "name": "tts",
        "version": "stable",
        "description": "Coqui TTS provider (premium).",
    }


def health_check():
    # Keep lightweight: only check importability.
    try:
        import TTS  # noqa: F401
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def execute(params: dict) -> dict:
    # Not used in tests; keep safe fallback.
    return {
        "success": False,
        "error": "Coqui provider not configured in this environment",
        "spoken": False,
        "method": "coqui",
    }
