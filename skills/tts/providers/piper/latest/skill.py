import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

# Pre-configured models - Polish + fallback
DEFAULT_MODELS = {
    "pl": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pl/pl_PL-gosia-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pl/pl_PL-gosia-medium.onnx.json",
        "name": "pl_PL-gosia-medium",
    },
    "en": {
        "url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US-amy-medium.onnx",
        "json_url": "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_US-amy-medium.onnx.json",
        "name": "en_US-amy-medium",
    },
}


def get_info():
    return {
        "name": "tts",
        "version": "v2",
        "description": "High-quality neural TTS with auto-model download (piper)",
    }


def health_check():
    piper = shutil.which("piper") or shutil.which("piper-tts")
    model = _get_model_path("pl")
    has_playback = shutil.which("aplay") or shutil.which("paplay") or shutil.which("pw-play")

    status = "ok" if piper and model and has_playback else "error"
    result = {
        "status": status,
        "piper_available": bool(piper),
        "model_available": bool(model),
        "playback_available": bool(has_playback),
        "model_path": str(model) if model else None,
    }
    if status == "error":
        errors = []
        if not piper:
            errors.append("piper not installed")
        if not model:
            errors.append("model not available")
        if not has_playback:
            errors.append("no audio playback")
        result["message"] = "; ".join(errors)
    return result


def _get_cache_dir() -> Path:
    """Get piper cache directory for models."""
    cache = Path.home() / ".cache" / "piper"
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def _get_model_path(lang: str = "pl") -> Path | None:
    """Get model path - from env, cache, or None."""
    # 1. Check env var first
    env_model = os.environ.get("PIPER_MODEL", "").strip()
    if env_model:
        path = Path(env_model)
        if path.exists():
            return path

    # 2. Check cache for downloaded models
    cache = _get_cache_dir()
    info = DEFAULT_MODELS.get(lang, DEFAULT_MODELS["pl"])
    model_name = info["name"]

    # Look for .onnx file
    candidate = cache / f"{model_name}.onnx"
    if candidate.exists():
        return candidate

    return None


def _download_file(url: str, dest: Path, timeout: int = 120) -> bool:
    """Download file with progress."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
        return dest.exists() and dest.stat().st_size > 1000
    except Exception:
        return False


def _ensure_model(lang: str = "pl") -> Path:
    """Ensure model exists - download if needed."""
    existing = _get_model_path(lang)
    if existing:
        return existing

    # Fallback: direct download
    info = DEFAULT_MODELS.get(lang, DEFAULT_MODELS["pl"])
    cache = _get_cache_dir()
    model_file = cache / f"{info['name']}.onnx"
    json_file = cache / f"{info['name']}.onnx.json"

    if not model_file.exists():
        ok = _download_file(info["url"], model_file)
        if not ok:
            raise RuntimeError(f"Failed to download model from {info['url']}")

    if not json_file.exists():
        _download_file(info["json_url"], json_file)

    return model_file


class PiperTTSSkill:
    """Piper TTS with auto-model download and streaming playback."""

    MAX_TEXT_LEN = 1000  # Reasonable limit for neural TTS

    def __init__(self):
        self._piper = shutil.which("piper") or shutil.which("piper-tts")
        self._play_cmd = (
            shutil.which("aplay") or
            shutil.which("paplay") or
            shutil.which("pw-play")
        )

    def _clean_for_tts(self, text: str) -> str:
        """Clean text for better speech synthesis."""
        if not text:
            return ""
        # Remove markdown
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`([^`]*)`', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove emojis
        text = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF'
                      r'\u2B50\u2705\u274C\u26A0\u2728\u2757\u2753'
                      r'\u25B6\u25C0\u27A1\u2B05\u2B06\u2B07'
                      r'\u2139\u2049\u203C\u2934\u2935'
                      r'\uFE0E\uFE0F\u200D]+', '', text)
        text = re.sub(r'[\u2192\u2190\u2191\u2193\u21D2\u21D0\u2022\u25CF\u25CB\u25A0\u25A1\u25B8\u25B9]', ' ', text)
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'  +', ' ', text)
        return text.strip()

    def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        lang = params.get("lang", "pl")[:2].lower()  # "pl_PL" -> "pl"
        speed = float(params.get("speed", 1.5))  # Default 150% speed

        if not text:
            return {"success": False, "error": "No text provided"}

        if not self._piper:
            return {"success": False, "error": "piper not installed (pip install piper-tts)"}

        if not self._play_cmd:
            return {"success": False, "error": "No audio playback (apt install alsa-utils)"}

        # Clean text
        clean = self._clean_for_tts(text)
        if not clean:
            return {"success": False, "error": "No speakable text after cleanup"}

        # Truncate long text
        if len(clean) > self.MAX_TEXT_LEN:
            clean = clean[:self.MAX_TEXT_LEN].rsplit(' ', 1)[0] + '...'

        try:
            # Ensure model (auto-download if needed)
            model_path = _ensure_model(lang)

            with tempfile.TemporaryDirectory(prefix="piper_tts_") as td:
                wav_path = Path(td) / "out.wav"

                # Build piper command with speed control
                # length_scale < 1 = faster, > 1 = slower
                length_scale = 1.0 / speed
                cmd = [
                    self._piper,
                    "--model", str(model_path),
                    "--output_file", str(wav_path),
                    "--length-scale", str(length_scale),
                ]

                # Generate speech (streaming to file)
                r = subprocess.run(
                    cmd,
                    input=clean,
                    text=True,
                    capture_output=True,
                    timeout=30,
                )
                if r.returncode != 0:
                    err = (r.stderr or r.stdout or "").strip()[:400]
                    return {"success": False, "error": f"piper failed: {err}"}

                if not wav_path.exists() or wav_path.stat().st_size < 100:
                    return {"success": False, "error": "piper produced empty audio"}

                # Play audio
                play = subprocess.run(
                    [self._play_cmd, str(wav_path)],
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if play.returncode != 0:
                    err = (play.stderr or play.stdout or "").strip()[:400]
                    return {"success": False, "error": f"playback failed: {err}"}

                return {
                    "success": True,
                    "spoken": True,
                    "text": clean[:100] + ("..." if len(clean) > 100 else ""),
                    "method": "piper-neural",
                    "model": model_path.name,
                    "lang": lang,
                    "speed": speed,
                }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "TTS timeout (>30s)"}
        except Exception as e:
            return {"success": False, "error": str(e)}


def execute(params: dict) -> dict:
    return PiperTTSSkill().execute(params)