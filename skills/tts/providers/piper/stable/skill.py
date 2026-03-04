import os
import shutil
import subprocess
import tempfile
from pathlib import Path


class PiperTTSSkill:
    def __init__(self):
        self._piper = shutil.which("piper")

    def execute(self, params: dict) -> dict:
        text = (params or {}).get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}

        if not self._piper:
            return {"success": False, "error": "piper not installed"}

        model = os.environ.get("PIPER_MODEL", "").strip()
        if not model:
            return {"success": False, "error": "PIPER_MODEL env var not set"}

        model_path = Path(model)
        if not model_path.exists():
            return {"success": False, "error": f"PIPER_MODEL path does not exist: {model}"}

        speaker_cmd = shutil.which("aplay") or shutil.which("paplay")
        if not speaker_cmd:
            return {"success": False, "error": "No audio playback command found (need aplay or paplay)"}

        try:
            with tempfile.TemporaryDirectory(prefix="piper_tts_") as td:
                wav_path = Path(td) / "out.wav"

                r = subprocess.run(
                    [self._piper, "--model", str(model_path), "--output_file", str(wav_path)],
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=60,
                )
                if r.returncode != 0:
                    err = (r.stderr or r.stdout or "").strip()
                    return {"success": False, "error": f"piper failed: {err[:400]}"}

                if not wav_path.exists() or wav_path.stat().st_size == 0:
                    return {"success": False, "error": "piper produced empty audio"}

                play = subprocess.run(
                    [speaker_cmd, str(wav_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if play.returncode != 0:
                    err = (play.stderr or play.stdout or "").strip()
                    return {"success": False, "error": f"audio playback failed: {err[:400]}"}

                return {
                    "success": True,
                    "spoken": True,
                    "method": "piper",
                }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "TTS timeout"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_info():
    return {
        "name": "tts",
        "version": "v1",
        "description": "High-quality offline Text-to-Speech via piper",
    }


def health_check():
    model = os.environ.get("PIPER_MODEL", "").strip()
    if not shutil.which("piper"):
        return {"status": "error", "error": "piper not installed"}
    if not model:
        return {"status": "error", "error": "PIPER_MODEL env var not set"}
    if not Path(model).exists():
        return {"status": "error", "error": f"PIPER_MODEL path does not exist: {model}"}
    if not (shutil.which("aplay") or shutil.which("paplay")):
        return {"status": "error", "error": "need aplay or paplay for playback"}
    return {"status": "ok"}


def execute(params: dict) -> dict:
    return PiperTTSSkill().execute(params)
