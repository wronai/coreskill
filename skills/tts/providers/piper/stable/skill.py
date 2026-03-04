import os
import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path


DEFAULT_MODEL_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pl/pl_PL/gwida/medium/pl_PL-gwida-medium.onnx"
DEFAULT_MODEL_JSON = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pl/pl_PL/gwida/medium/pl_PL-gwida-medium.onnx.json"


class PiperTTSSkill:
    def __init__(self):
        self._piper = shutil.which("piper")
        self._model_dir = Path.home() / ".local" / "share" / "piper"
        self._model_dir.mkdir(parents=True, exist_ok=True)

    def _get_model(self) -> Path:
        """Get or download Polish piper model."""
        model_path = self._model_dir / "pl_PL-gwida-medium.onnx"
        json_path = self._model_dir / "pl_PL-gwida-medium.onnx.json"

        # Check if model exists
        if model_path.exists() and json_path.exists():
            return model_path

        # Download model if not exists
        try:
            if not model_path.exists():
                urllib.request.urlretrieve(DEFAULT_MODEL_URL, model_path)
            if not json_path.exists():
                urllib.request.urlretrieve(DEFAULT_MODEL_JSON, json_path)
            return model_path
        except Exception:
            return None

    def execute(self, params: dict) -> dict:
        text = (params or {}).get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}

        if not self._piper:
            return {"success": False, "error": "piper not installed (pip install piper-tts)"}

        # Get or download model
        model_path = self._get_model()
        if not model_path:
            return {"success": False, "error": "Failed to get/download piper model"}

        speaker_cmd = shutil.which("aplay") or shutil.which("paplay")
        if not speaker_cmd:
            return {"success": False, "error": "No audio playback (need aplay/paplay)"}

        try:
            with tempfile.TemporaryDirectory(prefix="piper_tts_") as td:
                wav_path = Path(td) / "out.wav"

                # Generate WAV with piper
                r = subprocess.run(
                    [self._piper, "--model", str(model_path), "--output_file", str(wav_path)],
                    input=text,
                    text=True,
                    capture_output=True,
                    timeout=30,
                )
                if r.returncode != 0:
                    err = (r.stderr or r.stdout or "").strip()
                    return {"success": False, "error": f"piper failed: {err[:400]}"}

                if not wav_path.exists() or wav_path.stat().st_size == 0:
                    return {"success": False, "error": "piper produced empty audio"}

                # Play audio in background (non-blocking)
                subprocess.Popen(
                    [speaker_cmd, str(wav_path)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                return {
                    "success": True,
                    "spoken": True,
                    "method": "piper",
                    "model": "pl_PL-gwida-medium",
                    "quality": "high"
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
    if not shutil.which("piper"):
        return {"status": "error", "error": "piper not installed"}
    if not (shutil.which("aplay") or shutil.which("paplay")):
        return {"status": "error", "error": "need aplay or paplay"}
    # Check if model exists or can be downloaded
    model_dir = Path.home() / ".local" / "share" / "piper"
    model_path = model_dir / "pl_PL-gwida-medium.onnx"
    if model_path.exists():
        return {"status": "ok", "model": "pl_PL-gwida-medium", "ready": True}
    return {"status": "ok", "model": "will_download", "ready": True}


def execute(params: dict) -> dict:
    return PiperTTSSkill().execute(params)
