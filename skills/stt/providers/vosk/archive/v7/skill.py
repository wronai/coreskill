import json
import os
import shutil
import subprocess
from pathlib import Path
import tempfile
import sys

def get_info():
    return {
        "name": "stt",
        "version": "v1",
        "description": "Speech-to-Text: record from microphone and transcribe using system tools (vosk-transcriber).",
    }

def health_check():
    has_arecord = shutil.which("arecord") is not None
    has_vosk = shutil.which("vosk-transcriber") is not None
    return bool(has_vosk and has_arecord)

def check_readiness():
    """Multi-level readiness check: deps, hardware, resources."""
    deps = {
        "arecord": shutil.which("arecord") is not None,
        "vosk-transcriber": shutil.which("vosk-transcriber") is not None,
        "ffmpeg": shutil.which("ffmpeg") is not None,
    }
    # Hardware: probe mic via arecord -l
    mic_ok = False
    mic_info = ""
    if deps["arecord"]:
        try:
            r = subprocess.run(["arecord", "-l"], capture_output=True, text=True, timeout=3)
            mic_ok = "card" in r.stdout.lower()
            mic_info = r.stdout.strip().split("\n")[0][:80] if r.stdout else r.stderr[:80]
        except Exception as e:
            mic_info = str(e)
    hardware = {"microphone": mic_ok, "mic_info": mic_info}
    # Resources: vosk model
    vosk_cache = Path.home() / ".cache" / "vosk"
    model_path = None
    if vosk_cache.is_dir():
        for d in sorted(vosk_cache.iterdir(), reverse=True):
            if d.is_dir() and "model" in d.name.lower() and (d / "graph").is_dir():
                model_path = str(d)
                break
    resources = {"vosk_model": model_path}
    issues = []
    if not deps["arecord"]: issues.append("arecord not installed (apt install alsa-utils)")
    if not deps["vosk-transcriber"]: issues.append("vosk-transcriber not installed (pip install vosk)")
    if not mic_ok: issues.append(f"No microphone detected: {mic_info}")
    if not model_path: issues.append("No vosk model in ~/.cache/vosk/ (run: vosk-transcriber --list-models)")
    ok = deps["arecord"] and deps["vosk-transcriber"] and mic_ok and bool(model_path)
    return {"ok": ok, "deps": deps, "hardware": hardware, "resources": resources, "issues": issues}

class STTSkill:
    def __init__(self):
        self._has_arecord = shutil.which("arecord") is not None
        self._has_ffmpeg = shutil.which("ffmpeg") is not None
        self._has_vosk = shutil.which("vosk-transcriber") is not None

    def _record_wav(self, duration_s: int, sample_rate: int = 16000) -> str:
        if not self._has_arecord:
            raise RuntimeError("Missing system command: arecord")

        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="evo_stt_")
        os.close(fd)

        cmd = [
            "arecord",
            "-q",
            "-d",
            str(int(duration_s)),
            "-f",
            "S16_LE",
            "-r",
            str(int(sample_rate)),
            "-c",
            "1",
            wav_path,
        ]
        subprocess.run(cmd, check=True)
        return wav_path

    def _ensure_wav(self, input_path: str, sample_rate: int = 16000) -> str:
        p = Path(input_path)
        if not p.exists():
            raise FileNotFoundError(str(p))

        if p.suffix.lower() == ".wav":
            return str(p)

        if not self._has_ffmpeg:
            raise RuntimeError("Input is not .wav and ffmpeg is not available to convert")

        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="evo_stt_conv_")
        os.close(fd)
        cmd = [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-i",
            str(p),
            "-ac",
            "1",
            "-ar",
            str(int(sample_rate)),
            wav_path,
        ]
        subprocess.run(cmd, check=True)
        return wav_path

    def _find_model_path(self, lang: str | None = None) -> str | None:
        """Find extracted vosk model directory in cache."""
        cache = Path.home() / ".cache" / "vosk"
        if not cache.is_dir():
            return None
        tag = f"-{lang}" if lang else ""
        for d in sorted(cache.iterdir(), reverse=True):
            if d.is_dir() and "model" in d.name.lower():
                if tag and tag not in d.name:
                    continue
                if (d / "conf" / "model.conf").exists() or (d / "graph").is_dir():
                    return str(d)
        return None

    def _transcribe_vosk(self, wav_path: str, lang: str | None = None) -> dict:
        if not self._has_vosk:
            raise RuntimeError("Missing system command: vosk-transcriber")

        cmd = ["vosk-transcriber", "--input", wav_path]
        model_path = self._find_model_path(lang)
        if model_path:
            cmd += ["--model", model_path]
        elif lang:
            cmd += ["--lang", lang]

        r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        text = (r.stdout or "").strip()
        if r.returncode != 0 and not text:
            stderr_snippet = (r.stderr or "")[-200:]
            raise RuntimeError(f"vosk-transcriber failed (exit {r.returncode}): {stderr_snippet}")

        return {"text": text}

    def execute(self, params: dict) -> dict:
        duration_s = int(params.get("duration_s", 4))
        lang = params.get("lang")
        input_audio = params.get("audio_path")
        sample_rate = int(params.get("sample_rate", 16000))

        wav_path = None
        conv_tmp = None
        try:
            if input_audio:
                wav_path = self._ensure_wav(str(input_audio), sample_rate=sample_rate)
                if Path(wav_path).resolve() != Path(input_audio).resolve():
                    conv_tmp = wav_path
            else:
                wav_path = self._record_wav(duration_s=duration_s, sample_rate=sample_rate)

            result = self._transcribe_vosk(wav_path, lang=lang)
            text = ""
            if isinstance(result, dict):
                text = (result.get("text") or result.get("result") or result.get("transcript") or "")

            return {
                "success": True,
                "spoken": text,
                "raw": result,
                "audio_path": wav_path,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}
        finally:
            # Only delete recordings we created (not user-provided files)
            try:
                if wav_path and not input_audio:
                    Path(wav_path).unlink(missing_ok=True)
            except Exception:
                pass
            try:
                if conv_tmp:
                    Path(conv_tmp).unlink(missing_ok=True)
            except Exception:
                pass

def execute(input_data: dict) -> dict:
    return STTSkill().execute(input_data)

if __name__ == "__main__":
    inp = {}
    if len(sys.argv) > 1:
        inp["audio_path"] = sys.argv[1]
    else:
        inp["duration_s"] = 3
    print(json.dumps(execute(inp), indent=2, ensure_ascii=False))