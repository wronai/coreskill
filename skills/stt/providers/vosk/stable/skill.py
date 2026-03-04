import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def get_info():
    return {
        "name": "stt",
        "version": "v1",
        "description": "Speech-to-Text: record from microphone and transcribe using system tools (vosk-transcriber).",
    }


def health_check():
    has_arecord = shutil.which("arecord") is not None
    has_vosk = shutil.which("vosk-transcriber") is not None
    return bool(has_vosk and (has_arecord or True))


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

    def _transcribe_vosk(self, wav_path: str, lang: str | None = None, retries: int = 1) -> dict:
        if not self._has_vosk:
            raise RuntimeError("Missing system command: vosk-transcriber")

        fd, out_path = tempfile.mkstemp(suffix=".txt", prefix="evo_stt_out_")
        os.close(fd)

        # Use txt output — vosk-transcriber has a bug in json mode
        # (monologue["text"] used before monologue is defined)
        cmd = ["vosk-transcriber", "--input", wav_path, "--output", out_path, "--output-type", "txt"]
        if lang:
            cmd += ["--lang", lang]

        last_err = ""
        for attempt in range(retries + 1):
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                break
            last_err = (proc.stderr or proc.stdout or "").strip()[-200:]
            if attempt < retries:
                import time
                time.sleep(0.5)
        else:
            raise RuntimeError(f"vosk-transcriber failed (exit {proc.returncode}): {last_err}")

        try:
            raw = Path(out_path).read_text(encoding="utf-8", errors="replace").strip()
        finally:
            try:
                Path(out_path).unlink(missing_ok=True)
            except Exception:
                pass

        return {"text": raw, "raw": raw}

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
            text = (result.get("text") or "").strip()

            return {
                "success": True,
                "text": text,
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
