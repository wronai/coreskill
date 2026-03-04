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
        "version": "v2",
        "description": "Speech-to-Text with hardware validation and audio level detection.",
    }


def health_check():
    has_arecord = shutil.which("arecord") is not None
    has_vosk = shutil.which("vosk-transcriber") is not None
    # Check if microphone device exists
    mic_available = False
    if has_arecord:
        try:
            result = subprocess.run(
                ["arecord", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            mic_available = "card" in result.stdout and "device" in result.stdout
        except Exception:
            pass
    return bool(has_vosk and has_arecord and mic_available)


class STTSkill:
    def __init__(self):
        self._has_arecord = shutil.which("arecord") is not None
        self._has_ffmpeg = shutil.which("ffmpeg") is not None
        self._has_vosk = shutil.which("vosk-transcriber") is not None
        self._has_sox = shutil.which("sox") is not None

    def _check_microphone_hardware(self) -> tuple[bool, str]:
        """Check if microphone hardware is available. Returns (ok, message)."""
        if not self._has_arecord:
            return False, "Missing: arecord (install alsa-utils)"

        try:
            result = subprocess.run(
                ["arecord", "-l"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                return False, f"arecord -l failed: {result.stderr[:100]}"

            # Parse output for capture devices
            lines = result.stdout.strip().split('\n')
            capture_cards = [l for l in lines if l.strip().startswith('card') and 'device' in l]

            if not capture_cards:
                return False, "No capture devices found. Check microphone connection."

            return True, f"Found {len(capture_cards)} capture device(s)"
        except subprocess.TimeoutExpired:
            return False, "Hardware check timed out"
        except Exception as e:
            return False, f"Hardware check error: {e}"

    def _check_audio_level(self, wav_path: str, min_db: float = -40.0) -> tuple[bool, float, str]:
        """Check if audio file has sufficient volume. Returns (has_sound, db_level, message)."""
        if not Path(wav_path).exists():
            return False, -999, "Audio file not found"

        # Try sox first (more accurate)
        if self._has_sox:
            try:
                result = subprocess.run(
                    ["sox", wav_path, "-n", "stat"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                if result.returncode == 0:
                    # Parse RMS amplitude
                    for line in result.stderr.split('\n'):
                        if 'RMS amplitude' in line:
                            parts = line.split(':')
                            if len(parts) >= 2:
                                try:
                                    amplitude = float(parts[1].strip())
                                    # Convert to approximate dB
                                    if amplitude > 0:
                                        db = 20 * (amplitude ** 0.5) - 60  # Rough approximation
                                        has_sound = db > min_db
                                        return has_sound, db, f"RMS amplitude: {amplitude:.4f} (~{db:.1f}dB)"
                                except ValueError:
                                    pass
            except Exception:
                pass

        # Fallback: use ffmpeg volumedetect
        if self._has_ffmpeg:
            try:
                result = subprocess.run(
                    ["ffmpeg", "-i", wav_path, "-af", "volumedetect", "-f", "null", "-"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                stderr = result.stderr
                # Look for mean_volume
                for line in stderr.split('\n'):
                    if 'mean_volume' in line and 'dB' in line:
                        # Parse: [Parsed_volumedetect_0 @ 0x...] mean_volume: -XX.X dB
                        try:
                            db_str = line.split(':')[1].split('dB')[0].strip()
                            db = float(db_str)
                            has_sound = db > min_db
                            return has_sound, db, f"Mean volume: {db:.1f}dB (threshold: {min_db}dB)"
                        except (IndexError, ValueError):
                            pass
            except Exception:
                pass

        # Last resort: check file size (very rough)
        try:
            size = Path(wav_path).stat().st_size
            if size < 1000:  # Less than 1KB probably means silence
                return False, -999, f"File too small ({size} bytes) - likely silence"
        except Exception:
            pass

        return True, 0, "Audio level check inconclusive (proceeding)"

    def _record_wav(self, duration_s: int, sample_rate: int = 16000) -> tuple[str, tuple[bool, float, str]]:
        """Record audio and check levels. Returns (path, audio_check_result)."""
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

        # Check audio level immediately after recording
        level_check = self._check_audio_level(wav_path)
        return wav_path, level_check

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
        skip_hardware_check = params.get("skip_hardware_check", False)

        # Hardware validation
        if not skip_hardware_check and not input_audio:
            hw_ok, hw_msg = self._check_microphone_hardware()
            if not hw_ok:
                return {
                    "success": False,
                    "error": f"Hardware check failed: {hw_msg}",
                    "hardware_ok": False,
                    "text": "",
                }

        wav_path = None
        conv_tmp = None
        level_check = None

        try:
            if input_audio:
                wav_path = self._ensure_wav(str(input_audio), sample_rate=sample_rate)
                if Path(wav_path).resolve() != Path(input_audio).resolve():
                    conv_tmp = wav_path
                # Check level for provided audio too
                level_check = self._check_audio_level(wav_path)
            else:
                wav_path, level_check = self._record_wav(duration_s=duration_s, sample_rate=sample_rate)

            has_sound, db_level, level_msg = level_check

            # If no sound detected, return early with clear message
            if not has_sound:
                return {
                    "success": True,  # Skill worked, just no audio
                    "text": "",
                    "hardware_ok": True,
                    "audio_level_db": db_level,
                    "has_sound": False,
                    "warning": f"No sound detected ({level_msg}). Check microphone and speak louder.",
                    "audio_path": wav_path if input_audio else None,
                }

            result = self._transcribe_vosk(wav_path, lang=lang)
            text = (result.get("text") or "").strip()

            return {
                "success": True,
                "text": text,
                "hardware_ok": True,
                "audio_level_db": db_level,
                "has_sound": has_sound,
                "level_info": level_msg,
                "raw": result,
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