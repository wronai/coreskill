"""
Whisper STT Skill - High-quality speech recognition using faster-whisper.
Falls back to openai-whisper if faster-whisper unavailable.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import warnings
from pathlib import Path

# Suppress FP16 warnings on CPU
warnings.filterwarnings("ignore", message=".*FP16 is not supported on CPU.*")


def get_info():
    return {
        "name": "stt",
        "version": "v1",
        "description": "Speech-to-Text: high-quality transcription using Whisper (faster-whisper).",
    }


def health_check():
    has_whisper = False
    try:
        import faster_whisper
        has_whisper = True
    except ImportError:
        try:
            import whisper
            has_whisper = True
        except ImportError:
            pass
    has_ffmpeg = shutil.which("ffmpeg") is not None
    return bool(has_whisper and has_ffmpeg)


class WhisperSTTSkill:
    MODEL_SIZES = ["tiny", "base", "small", "medium", "large-v3"]
    DEFAULT_MODEL = "small"  # Good balance: fast + accurate for Polish

    def __init__(self):
        self._has_ffmpeg = shutil.which("ffmpeg") is not None
        self._has_arecord = shutil.which("arecord") is not None
        self._model = None
        self._model_size = None
        self._faster_mode = None  # True = faster-whisper, False = openai-whisper

    def _load_model(self, size: str = None, lang_hint: str = None):
        """Lazy-load whisper model with auto-detection of backend."""
        if size is None:
            size = self.DEFAULT_MODEL

        # Already loaded?
        if self._model and self._model_size == size:
            return self._model, self._faster_mode

        # Try faster-whisper first (much faster)
        try:
            from faster_whisper import WhisperModel

            # Auto-detect compute type based on available resources
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
                compute_type = "float16" if device == "cuda" else "int8"
            except ImportError:
                device = "cpu"
                compute_type = "int8"

            self._model = WhisperModel(size, device=device, compute_type=compute_type)
            self._model_size = size
            self._faster_mode = True
            return self._model, True
        except Exception as e:
            pass

        # Fallback to openai-whisper
        try:
            import whisper

            self._model = whisper.load_model(size)
            self._model_size = size
            self._faster_mode = False
            return self._model, False
        except Exception as e:
            raise RuntimeError(f"Failed to load Whisper model ({size}). Install: pip install faster-whisper") from e

    def _record_wav(self, duration_s: int, sample_rate: int = 16000) -> str:
        """Record audio from microphone using arecord."""
        if not self._has_arecord:
            raise RuntimeError("Missing system command: arecord (install alsa-utils)")

        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="evo_whisper_")
        os.close(fd)

        cmd = [
            "arecord",
            "-q",
            "-d", str(int(duration_s)),
            "-f", "S16_LE",
            "-r", str(int(sample_rate)),
            "-c", "1",
            wav_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return wav_path

    def _ensure_wav(self, input_path: str, sample_rate: int = 16000) -> str:
        """Convert input to WAV format if needed."""
        p = Path(input_path)
        if not p.exists():
            raise FileNotFoundError(str(p))

        if p.suffix.lower() == ".wav":
            return str(p)

        if not self._has_ffmpeg:
            raise RuntimeError("ffmpeg required for audio conversion")

        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="evo_whisper_conv_")
        os.close(fd)
        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(p),
            "-ac", "1", "-ar", str(int(sample_rate)),
            wav_path,
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        return wav_path

    def _check_audio_level(self, wav_path: str, min_db: float = -40.0) -> tuple:
        """Check if audio has sufficient volume. Returns (has_sound, db_level, message)."""
        if not Path(wav_path).exists():
            return False, -999.0, "Audio file not found"

        if not self._has_ffmpeg:
            # Fallback: file size check
            size = Path(wav_path).stat().st_size
            return size > 1000, 0.0, f"Size: {size}b"

        try:
            result = subprocess.run(
                ["ffmpeg", "-i", wav_path, "-af", "volumedetect", "-f", "null", "-"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stderr.split('\n'):
                if 'mean_volume' in line and 'dB' in line:
                    try:
                        db_str = line.split(':')[1].split('dB')[0].strip()
                        db = float(db_str)
                        return db > min_db, db, f"Mean: {db:.1f}dB"
                    except (IndexError, ValueError):
                        pass
        except Exception:
            pass

        return True, 0.0, "Level check inconclusive"

    def _transcribe_faster(self, model, wav_path: str, lang: str = None) -> dict:
        """Transcribe using faster-whisper."""
        segments, info = model.transcribe(wav_path, language=lang, beam_size=5)
        text_parts = []
        confidence_scores = []

        for segment in segments:
            text_parts.append(segment.text)
            confidence_scores.append(getattr(segment, 'avg_logprob', -0.5))

        full_text = " ".join(text_parts).strip()
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0.5

        # Normalize confidence to 0-1 range (logprob is typically -1 to 0)
        normalized_confidence = min(1.0, max(0.0, 1.0 + (avg_confidence / 2)))

        return {
            "text": full_text,
            "language": info.language,
            "language_probability": info.language_probability,
            "confidence": normalized_confidence,
            "segments": len(text_parts),
        }

    def _transcribe_openai(self, model, wav_path: str, lang: str = None) -> dict:
        """Transcribe using openai-whisper (fallback)."""
        import whisper

        result = model.transcribe(wav_path, language=lang)
        text = result.get("text", "").strip()

        # Estimate confidence from segment probabilities if available
        segs = result.get("segments", [])
        confidences = [s.get("avg_logprob", -0.5) for s in segs if "avg_logprob" in s]
        avg_conf = sum(confidences) / len(confidences) if confidences else -0.5
        normalized_conf = min(1.0, max(0.0, 1.0 + (avg_conf / 2)))

        return {
            "text": text,
            "language": result.get("language"),
            "confidence": normalized_conf,
            "segments": len(segs),
        }

    def execute(self, params: dict) -> dict:
        """Main execution: record or load audio, transcribe with Whisper."""
        duration_s = int(params.get("duration_s", 4))
        lang = params.get("lang", "pl")  # Default Polish
        input_audio = params.get("audio_path")
        model_size = params.get("model", self.DEFAULT_MODEL)
        sample_rate = int(params.get("sample_rate", 16000))

        wav_path = None
        conv_tmp = None

        try:
            # Load model first (fails fast if not available)
            model, is_faster = self._load_model(model_size, lang)

            # Get audio input
            if input_audio:
                wav_path = self._ensure_wav(str(input_audio), sample_rate=sample_rate)
                if Path(wav_path).resolve() != Path(input_audio).resolve():
                    conv_tmp = wav_path
            else:
                wav_path = self._record_wav(duration_s=duration_s, sample_rate=sample_rate)

            # Check audio level
            has_sound, db_level, level_msg = self._check_audio_level(wav_path)
            if not has_sound:
                return {
                    "success": True,
                    "text": "",
                    "hardware_ok": True,
                    "has_sound": False,
                    "audio_level_db": db_level,
                    "warning": f"No sound detected ({level_msg}). Check microphone.",
                    "audio_path": wav_path if input_audio else None,
                }

            # Transcribe
            if is_faster:
                result = self._transcribe_faster(model, wav_path, lang=lang)
            else:
                result = self._transcribe_openai(model, wav_path, lang=lang)

            text = result.get("text", "")
            confidence = result.get("confidence", 0.0)

            return {
                "success": True,
                "text": text,
                "hardware_ok": True,
                "has_sound": True,
                "audio_level_db": db_level,
                "level_info": level_msg,
                "confidence": confidence,
                "language": result.get("language"),
                "backend": "faster-whisper" if is_faster else "openai-whisper",
                "model": self._model_size,
                "audio_path": wav_path if input_audio else None,
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "hardware_ok": False,
                "text": "",
            }

        finally:
            # Cleanup temp files
            for path in [wav_path, conv_tmp]:
                if path and not (input_audio and Path(path).resolve() == Path(input_audio).resolve()):
                    try:
                        Path(path).unlink(missing_ok=True)
                    except Exception:
                        pass


def execute(input_data: dict) -> dict:
    return WhisperSTTSkill().execute(input_data)


if __name__ == "__main__":
    inp = {}
    if len(sys.argv) > 1:
        inp["audio_path"] = sys.argv[1]
    else:
        inp["duration_s"] = 5
    print(json.dumps(execute(inp), indent=2, ensure_ascii=False))
