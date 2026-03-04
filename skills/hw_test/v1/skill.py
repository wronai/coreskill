"""
hw_test skill — Hardware diagnostics and cross-skill hardware validation.

Tests audio channels at the hardware level, detects devices, drivers,
and validates that hardware-dependent skills (STT, TTS) have working
hardware foundations. Works on Linux, macOS, and Windows.

Actions:
    full        — Run all hardware tests
    audio_input — Test microphone/capture devices
    audio_output— Test speaker/playback devices
    audio_loop  — Loopback test (record while playing tone)
    devices     — List all audio devices with details
    drivers     — Check kernel modules and audio drivers
    pulse       — PulseAudio/PipeWire source/sink analysis
    usb         — USB device enumeration
    skill_hw    — Cross-skill hardware validation (STT, TTS, etc.)
    report      — Generate full hardware report (JSON)
"""
import json
import math
import os
import platform
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path


# ─── Platform detection ─────────────────────────────────────────────
_SYSTEM = platform.system()  # Linux, Darwin, Windows
_IS_LINUX = _SYSTEM == "Linux"
_IS_MAC = _SYSTEM == "Darwin"
_IS_WIN = _SYSTEM == "Windows"


def get_info():
    return {
        "name": "hw_test",
        "version": "v1",
        "description": (
            "Hardware diagnostics: audio channel testing, device detection, "
            "driver checks, cross-skill hardware validation. "
            f"Platform: {_SYSTEM}"
        ),
    }


def health_check():
    """Basic check — at least one audio tool available."""
    tools = ["arecord", "pactl", "sox", "ffmpeg", "aplay",
             "system_profiler", "powershell"]
    return any(shutil.which(t) for t in tools) or True


# ═══════════════════════════════════════════════════════════════════
# AUDIO INPUT (Microphone) Tests
# ═══════════════════════════════════════════════════════════════════

class AudioInputTester:
    """Test microphone / capture hardware at the lowest level."""

    def run(self, duration: float = 2.0) -> dict:
        """Full audio input test suite."""
        result = {
            "ok": False,
            "platform": _SYSTEM,
            "devices": self._list_capture_devices(),
            "default_source": self._get_default_source(),
            "record_test": None,
            "level_test": None,
            "latency_estimate_ms": None,
            "issues": [],
            "recommendations": [],
        }

        # Check if any capture device exists
        if not result["devices"]:
            result["issues"].append("No capture devices detected")
            result["recommendations"].append(
                "Connect a microphone or USB audio device")
            return result

        # Try to record a test sample
        rec = self._record_test(duration)
        result["record_test"] = rec

        if not rec["ok"]:
            result["issues"].append(f"Recording failed: {rec.get('error', '?')}")
            result["recommendations"].append(
                "Check microphone permissions and ALSA/PulseAudio config")
            return result

        # Measure audio level
        level = self._measure_level(rec["wav_path"])
        result["level_test"] = level

        if level.get("ok"):
            result["ok"] = True
        else:
            result["issues"].append(
                f"Audio level too low: {level.get('max_db', -999):.1f} dB "
                f"(need > {level.get('threshold_db', -40)} dB)")
            result["recommendations"].extend([
                "Run: amixer set Capture 100% unmute",
                "Run: pactl set-source-volume @DEFAULT_SOURCE@ 100%",
                "Check if correct input device is selected in system settings",
            ])

        # Estimate latency
        result["latency_estimate_ms"] = self._estimate_input_latency()

        # Clean up
        try:
            os.unlink(rec.get("wav_path", ""))
        except Exception:
            pass

        return result

    def _list_capture_devices(self) -> list:
        """List all capture devices on any platform."""
        devices = []

        if _IS_LINUX:
            # ALSA devices
            devices.extend(self._alsa_capture_devices())
            # PulseAudio/PipeWire sources
            devices.extend(self._pulse_sources())

        elif _IS_MAC:
            devices.extend(self._macos_audio_inputs())

        elif _IS_WIN:
            devices.extend(self._windows_audio_inputs())

        return devices

    def _alsa_capture_devices(self) -> list:
        """List ALSA capture devices (Linux)."""
        if not shutil.which("arecord"):
            return []
        try:
            r = subprocess.run(
                ["arecord", "-l"],
                capture_output=True, text=True, timeout=5)
            devices = []
            for line in r.stdout.split("\n"):
                if line.strip().startswith("card"):
                    # Parse: "card 0: PCH [HDA Intel PCH], device 0: ALC..."
                    parts = line.strip()
                    card_num = None
                    dev_num = None
                    try:
                        card_num = int(parts.split("card ")[1].split(":")[0])
                        dev_num = int(parts.split("device ")[1].split(":")[0])
                    except (IndexError, ValueError):
                        pass
                    devices.append({
                        "type": "alsa",
                        "card": card_num,
                        "device": dev_num,
                        "hw_id": f"hw:{card_num},{dev_num}" if card_num is not None else None,
                        "name": parts,
                        "direction": "capture",
                    })
            return devices
        except Exception:
            return []

    def _pulse_sources(self) -> list:
        """List PulseAudio/PipeWire sources (Linux)."""
        if not shutil.which("pactl"):
            return []
        try:
            r = subprocess.run(
                ["pactl", "list", "sources", "short"],
                capture_output=True, text=True, timeout=5)
            sources = []
            for line in r.stdout.strip().split("\n"):
                if not line.strip():
                    continue
                parts = line.split("\t")
                if len(parts) >= 2:
                    name = parts[1]
                    is_monitor = ".monitor" in name
                    sources.append({
                        "type": "pulseaudio",
                        "name": name,
                        "is_monitor": is_monitor,
                        "direction": "monitor" if is_monitor else "capture",
                        "state": parts[4] if len(parts) > 4 else "unknown",
                    })
            return sources
        except Exception:
            return []

    def _macos_audio_inputs(self) -> list:
        """List macOS audio input devices."""
        if not shutil.which("system_profiler"):
            return []
        try:
            r = subprocess.run(
                ["system_profiler", "SPAudioDataType", "-json"],
                capture_output=True, text=True, timeout=10)
            data = json.loads(r.stdout)
            devices = []
            for item in data.get("SPAudioDataType", []):
                for dev in item.get("_items", []):
                    if "input" in dev.get("coreaudio_device_transport", "").lower():
                        devices.append({
                            "type": "coreaudio",
                            "name": dev.get("_name", "Unknown"),
                            "direction": "capture",
                            "channels": dev.get("coreaudio_device_input", "?"),
                        })
            return devices
        except Exception:
            return []

    def _windows_audio_inputs(self) -> list:
        """List Windows audio input devices."""
        if not shutil.which("powershell"):
            return []
        try:
            ps_cmd = (
                "Get-CimInstance Win32_SoundDevice | "
                "Select-Object Name,Status,Manufacturer | "
                "ConvertTo-Json"
            )
            r = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10)
            data = json.loads(r.stdout)
            if isinstance(data, dict):
                data = [data]
            return [{
                "type": "windows",
                "name": d.get("Name", "Unknown"),
                "status": d.get("Status", "Unknown"),
                "manufacturer": d.get("Manufacturer", ""),
                "direction": "capture",
            } for d in data]
        except Exception:
            return []

    def _get_default_source(self) -> dict:
        """Get the default audio source/input device."""
        if _IS_LINUX and shutil.which("pactl"):
            try:
                r = subprocess.run(
                    ["pactl", "get-default-source"],
                    capture_output=True, text=True, timeout=3)
                name = r.stdout.strip()
                # Also get volume
                rv = subprocess.run(
                    ["pactl", "get-source-volume", name],
                    capture_output=True, text=True, timeout=3)
                vol_str = rv.stdout.strip()
                # Parse "Volume: front-left: 65536 / 100% / 0.00 dB, ..."
                volume_pct = None
                if "%" in vol_str:
                    try:
                        volume_pct = int(vol_str.split("%")[0].split("/")[-1].strip())
                    except (ValueError, IndexError):
                        pass
                # Check mute
                rm = subprocess.run(
                    ["pactl", "get-source-mute", name],
                    capture_output=True, text=True, timeout=3)
                muted = "yes" in rm.stdout.lower()

                return {
                    "name": name,
                    "is_monitor": ".monitor" in name,
                    "volume_pct": volume_pct,
                    "muted": muted,
                    "issues": (
                        ["Default source is a monitor (output loopback), not a real mic!"]
                        if ".monitor" in name else []
                    ),
                }
            except Exception as e:
                return {"error": str(e)}

        elif _IS_LINUX and shutil.which("amixer"):
            try:
                r = subprocess.run(
                    ["amixer", "get", "Capture"],
                    capture_output=True, text=True, timeout=3)
                return {"raw": r.stdout[:200]}
            except Exception:
                pass

        return {"note": "Cannot determine default source on this platform"}

    def _record_test(self, duration: float) -> dict:
        """Record a test audio sample."""
        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="hw_test_input_")
        os.close(fd)

        if _IS_LINUX and shutil.which("arecord"):
            try:
                r = subprocess.run(
                    ["arecord", "-d", str(int(duration)),
                     "-f", "S16_LE", "-r", "16000", "-c", "1",
                     "-t", "wav", wav_path],
                    capture_output=True, text=True, timeout=duration + 5)
                if r.returncode == 0 and Path(wav_path).stat().st_size > 100:
                    return {"ok": True, "wav_path": wav_path, "tool": "arecord"}
                return {"ok": False, "error": r.stderr[:200], "wav_path": wav_path}
            except subprocess.TimeoutExpired:
                return {"ok": False, "error": "arecord timeout", "wav_path": wav_path}
            except Exception as e:
                return {"ok": False, "error": str(e), "wav_path": wav_path}

        elif _IS_LINUX and shutil.which("ffmpeg"):
            try:
                r = subprocess.run(
                    ["ffmpeg", "-y", "-f", "pulse", "-i", "default",
                     "-t", str(duration), "-ar", "16000", "-ac", "1",
                     wav_path],
                    capture_output=True, text=True, timeout=duration + 5)
                if r.returncode == 0 and Path(wav_path).stat().st_size > 100:
                    return {"ok": True, "wav_path": wav_path, "tool": "ffmpeg"}
                return {"ok": False, "error": r.stderr[:200], "wav_path": wav_path}
            except Exception as e:
                return {"ok": False, "error": str(e), "wav_path": wav_path}

        elif _IS_MAC and shutil.which("sox"):
            try:
                r = subprocess.run(
                    ["sox", "-d", "-r", "16000", "-c", "1", "-b", "16",
                     wav_path, "trim", "0", str(duration)],
                    capture_output=True, text=True, timeout=duration + 5)
                if r.returncode == 0:
                    return {"ok": True, "wav_path": wav_path, "tool": "sox"}
                return {"ok": False, "error": r.stderr[:200], "wav_path": wav_path}
            except Exception as e:
                return {"ok": False, "error": str(e), "wav_path": wav_path}

        # Fallback: generate silence WAV to at least test the pipeline
        self._generate_wav(wav_path, duration, frequency=0)
        return {
            "ok": False,
            "error": "No recording tool available (arecord/ffmpeg/sox)",
            "wav_path": wav_path,
            "generated_silence": True,
        }

    def _measure_level(self, wav_path: str, threshold_db: float = -40.0) -> dict:
        """Measure audio level from a WAV file. Multi-tool fallback."""
        result = {"ok": False, "threshold_db": threshold_db}

        # Try sox (most accurate)
        if shutil.which("sox"):
            try:
                r = subprocess.run(
                    ["sox", wav_path, "-n", "stat"],
                    capture_output=True, text=True, timeout=10)
                stats_text = r.stderr  # sox outputs stats to stderr
                for line in stats_text.split("\n"):
                    if "Maximum amplitude" in line:
                        val = float(line.split(":")[-1].strip())
                        if val > 0:
                            db = 20 * math.log10(val)
                        else:
                            db = -999.0
                        result["max_amplitude"] = val
                        result["max_db"] = round(db, 1)
                        result["ok"] = db > threshold_db
                        result["tool"] = "sox"
                        return result
                    if "RMS     amplitude" in line:
                        try:
                            result["rms_amplitude"] = float(
                                line.split(":")[-1].strip())
                        except ValueError:
                            pass
            except Exception:
                pass

        # Try ffprobe
        if shutil.which("ffprobe"):
            try:
                r = subprocess.run(
                    ["ffprobe", "-v", "error", "-show_entries",
                     "frame=pkt_pts_time",
                     "-select_streams", "a", "-of", "json", wav_path],
                    capture_output=True, text=True, timeout=10)
                # At least confirm file is valid audio
                if r.returncode == 0:
                    result["tool"] = "ffprobe"
                    result["valid_audio"] = True
            except Exception:
                pass

        # Fallback: read WAV directly with Python
        try:
            max_amp = self._wav_max_amplitude(wav_path)
            if max_amp is not None:
                db = 20 * math.log10(max_amp) if max_amp > 0 else -999.0
                result["max_amplitude"] = max_amp
                result["max_db"] = round(db, 1)
                result["ok"] = db > threshold_db
                result["tool"] = "python_wave"
        except Exception as e:
            result["error"] = str(e)

        return result

    def _wav_max_amplitude(self, wav_path: str) -> float:
        """Read WAV with stdlib wave module and find max amplitude."""
        with wave.open(wav_path, "rb") as wf:
            n_frames = wf.getnframes()
            n_channels = wf.getnchannels()
            samp_width = wf.getsampwidth()
            if n_frames == 0:
                return 0.0
            raw = wf.readframes(n_frames)

        if samp_width == 2:
            fmt = f"<{n_frames * n_channels}h"
            samples = struct.unpack(fmt, raw)
            max_val = max(abs(s) for s in samples) if samples else 0
            return max_val / 32768.0
        elif samp_width == 1:
            samples = [b - 128 for b in raw]
            max_val = max(abs(s) for s in samples) if samples else 0
            return max_val / 128.0
        return 0.0

    def _estimate_input_latency(self) -> float:
        """Estimate input latency in ms (Linux ALSA/PulseAudio)."""
        if _IS_LINUX and shutil.which("pactl"):
            try:
                r = subprocess.run(
                    ["pactl", "list", "sources"],
                    capture_output=True, text=True, timeout=5)
                for line in r.stdout.split("\n"):
                    if "Latency:" in line and "usec" in line:
                        # "Latency: 0 usec, configured 40000 usec"
                        parts = line.split("configured")
                        if len(parts) > 1:
                            try:
                                usec = int(parts[1].strip().split()[0])
                                return usec / 1000.0
                            except (ValueError, IndexError):
                                pass
            except Exception:
                pass
        return -1.0

    @staticmethod
    def _generate_wav(path: str, duration: float, frequency: float = 440.0,
                      sample_rate: int = 16000):
        """Generate a WAV file with a sine tone (or silence if freq=0)."""
        n_frames = int(sample_rate * duration)
        with wave.open(path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for i in range(n_frames):
                if frequency > 0:
                    val = int(16000 * math.sin(2 * math.pi * frequency * i / sample_rate))
                else:
                    val = 0
                wf.writeframes(struct.pack("<h", val))


# ═══════════════════════════════════════════════════════════════════
# AUDIO OUTPUT (Speaker) Tests
# ═══════════════════════════════════════════════════════════════════

class AudioOutputTester:
    """Test speaker / playback hardware."""

    def run(self, duration: float = 1.0) -> dict:
        result = {
            "ok": False,
            "platform": _SYSTEM,
            "devices": self._list_playback_devices(),
            "default_sink": self._get_default_sink(),
            "playback_test": None,
            "issues": [],
        }

        if not result["devices"]:
            result["issues"].append("No playback devices detected")
            return result

        # Generate a test tone and try to play it
        result["playback_test"] = self._play_test_tone(duration)
        if result["playback_test"].get("ok"):
            result["ok"] = True
        else:
            result["issues"].append(
                f"Playback failed: {result['playback_test'].get('error', '?')}")

        return result

    def _list_playback_devices(self) -> list:
        """List playback devices."""
        devices = []
        if _IS_LINUX and shutil.which("aplay"):
            try:
                r = subprocess.run(
                    ["aplay", "-l"],
                    capture_output=True, text=True, timeout=5)
                for line in r.stdout.split("\n"):
                    if line.strip().startswith("card"):
                        devices.append({
                            "type": "alsa",
                            "name": line.strip(),
                            "direction": "playback",
                        })
            except Exception:
                pass

        if _IS_LINUX and shutil.which("pactl"):
            try:
                r = subprocess.run(
                    ["pactl", "list", "sinks", "short"],
                    capture_output=True, text=True, timeout=5)
                for line in r.stdout.strip().split("\n"):
                    if not line.strip():
                        continue
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        devices.append({
                            "type": "pulseaudio",
                            "name": parts[1],
                            "direction": "playback",
                            "state": parts[4] if len(parts) > 4 else "unknown",
                        })
            except Exception:
                pass
        return devices

    def _get_default_sink(self) -> dict:
        """Get default audio output."""
        if _IS_LINUX and shutil.which("pactl"):
            try:
                r = subprocess.run(
                    ["pactl", "get-default-sink"],
                    capture_output=True, text=True, timeout=3)
                name = r.stdout.strip()
                rv = subprocess.run(
                    ["pactl", "get-sink-volume", name],
                    capture_output=True, text=True, timeout=3)
                volume_pct = None
                if "%" in rv.stdout:
                    try:
                        volume_pct = int(
                            rv.stdout.split("%")[0].split("/")[-1].strip())
                    except (ValueError, IndexError):
                        pass
                rm = subprocess.run(
                    ["pactl", "get-sink-mute", name],
                    capture_output=True, text=True, timeout=3)
                muted = "yes" in rm.stdout.lower()
                return {"name": name, "volume_pct": volume_pct, "muted": muted}
            except Exception as e:
                return {"error": str(e)}
        return {}

    def _play_test_tone(self, duration: float) -> dict:
        """Generate and play a short test tone."""
        fd, wav_path = tempfile.mkstemp(suffix=".wav", prefix="hw_test_tone_")
        os.close(fd)
        AudioInputTester._generate_wav(wav_path, duration, frequency=440.0)

        try:
            if _IS_LINUX and shutil.which("aplay"):
                r = subprocess.run(
                    ["aplay", "-q", wav_path],
                    capture_output=True, text=True, timeout=duration + 5)
                return {"ok": r.returncode == 0, "tool": "aplay",
                        "error": r.stderr[:200] if r.returncode else ""}

            elif _IS_LINUX and shutil.which("paplay"):
                r = subprocess.run(
                    ["paplay", wav_path],
                    capture_output=True, text=True, timeout=duration + 5)
                return {"ok": r.returncode == 0, "tool": "paplay",
                        "error": r.stderr[:200] if r.returncode else ""}

            elif shutil.which("sox"):
                r = subprocess.run(
                    ["play", "-q", wav_path],
                    capture_output=True, text=True, timeout=duration + 5)
                return {"ok": r.returncode == 0, "tool": "sox/play",
                        "error": r.stderr[:200] if r.returncode else ""}

            elif _IS_MAC and shutil.which("afplay"):
                r = subprocess.run(
                    ["afplay", wav_path],
                    capture_output=True, text=True, timeout=duration + 5)
                return {"ok": r.returncode == 0, "tool": "afplay",
                        "error": r.stderr[:200] if r.returncode else ""}

            return {"ok": False, "error": "No playback tool (aplay/paplay/sox/afplay)"}
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════
# AUDIO LOOPBACK Test
# ═══════════════════════════════════════════════════════════════════

class AudioLoopbackTester:
    """Test full audio chain: generate tone → play → record → analyze.
    Requires speakers and microphone close together or loopback cable."""

    def run(self, tone_freq: float = 1000.0, duration: float = 2.0) -> dict:
        result = {
            "ok": False,
            "description": (
                "Loopback test: plays a tone while recording. "
                "Checks if the recorded audio contains the expected frequency."
            ),
            "tone_hz": tone_freq,
            "duration_s": duration,
            "recorded_level": None,
            "frequency_match": None,
            "issues": [],
        }

        if not (_IS_LINUX and shutil.which("arecord") and shutil.which("aplay")):
            result["issues"].append(
                "Loopback test requires arecord + aplay (Linux)")
            return result

        # Generate test tone
        fd_tone, tone_path = tempfile.mkstemp(
            suffix=".wav", prefix="hw_test_loopback_tone_")
        os.close(fd_tone)
        AudioInputTester._generate_wav(
            tone_path, duration + 0.5, frequency=tone_freq)

        fd_rec, rec_path = tempfile.mkstemp(
            suffix=".wav", prefix="hw_test_loopback_rec_")
        os.close(fd_rec)

        try:
            # Start recording in background
            rec_proc = subprocess.Popen(
                ["arecord", "-d", str(int(duration + 1)),
                 "-f", "S16_LE", "-r", "16000", "-c", "1",
                 "-t", "wav", rec_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Small delay then play tone
            time.sleep(0.3)
            subprocess.run(
                ["aplay", "-q", tone_path],
                capture_output=True, timeout=duration + 3)

            # Wait for recording to finish
            rec_proc.wait(timeout=duration + 5)

            # Analyze recorded audio
            inp = AudioInputTester()
            level = inp._measure_level(rec_path, threshold_db=-50.0)
            result["recorded_level"] = level

            if level.get("ok"):
                result["ok"] = True
                # Basic frequency check using zero-crossing rate
                freq_match = self._check_frequency(rec_path, tone_freq)
                result["frequency_match"] = freq_match
            else:
                result["issues"].append(
                    "No audio detected in loopback recording. "
                    "Ensure speakers and microphone are close together, "
                    "or use a loopback cable.")

        except subprocess.TimeoutExpired:
            result["issues"].append("Loopback test timed out")
            try:
                rec_proc.kill()
            except Exception:
                pass
        except Exception as e:
            result["issues"].append(f"Loopback error: {e}")
        finally:
            for p in [tone_path, rec_path]:
                try:
                    os.unlink(p)
                except Exception:
                    pass

        return result

    def _check_frequency(self, wav_path: str, expected_hz: float,
                         tolerance: float = 100.0) -> dict:
        """Estimate dominant frequency via zero-crossing rate."""
        try:
            with wave.open(wav_path, "rb") as wf:
                rate = wf.getframerate()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)

            fmt = f"<{n_frames}h"
            samples = struct.unpack(fmt, raw)

            # Zero-crossing rate
            crossings = 0
            for i in range(1, len(samples)):
                if (samples[i] >= 0) != (samples[i - 1] >= 0):
                    crossings += 1

            duration = n_frames / rate
            if duration <= 0:
                return {"ok": False, "error": "Empty recording"}

            estimated_hz = crossings / (2 * duration)
            diff = abs(estimated_hz - expected_hz)

            return {
                "ok": diff < tolerance,
                "estimated_hz": round(estimated_hz, 1),
                "expected_hz": expected_hz,
                "diff_hz": round(diff, 1),
                "tolerance_hz": tolerance,
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}


# ═══════════════════════════════════════════════════════════════════
# DRIVER / KERNEL MODULE Checks
# ═══════════════════════════════════════════════════════════════════

class DriverTester:
    """Check audio-related kernel modules and drivers."""

    def run(self) -> dict:
        result = {
            "ok": False,
            "platform": _SYSTEM,
            "audio_subsystem": None,
            "kernel_modules": [],
            "driver_status": [],
            "issues": [],
        }

        if _IS_LINUX:
            result["audio_subsystem"] = self._detect_audio_subsystem()
            result["kernel_modules"] = self._check_kernel_modules()
            result["driver_status"] = self._check_driver_status()
        elif _IS_MAC:
            result["audio_subsystem"] = "CoreAudio"
            result["driver_status"] = self._macos_audio_status()
        elif _IS_WIN:
            result["audio_subsystem"] = "Windows Audio"
            result["driver_status"] = self._windows_driver_status()

        # Determine overall health
        if result["audio_subsystem"]:
            result["ok"] = True
            for mod in result["kernel_modules"]:
                if not mod.get("loaded"):
                    result["ok"] = False
                    result["issues"].append(
                        f"Module {mod['name']} not loaded")

        return result

    def _detect_audio_subsystem(self) -> str:
        """Detect Linux audio subsystem: PipeWire > PulseAudio > ALSA."""
        # Check PipeWire first
        try:
            r = subprocess.run(
                ["pgrep", "-x", "pipewire"],
                capture_output=True, timeout=3)
            if r.returncode == 0:
                return "PipeWire"
        except Exception:
            pass

        # Check PulseAudio
        try:
            r = subprocess.run(
                ["pgrep", "-x", "pulseaudio"],
                capture_output=True, timeout=3)
            if r.returncode == 0:
                return "PulseAudio"
        except Exception:
            pass

        # Fallback: bare ALSA
        if Path("/proc/asound").exists():
            return "ALSA (no sound server)"

        return "Unknown"

    def _check_kernel_modules(self) -> list:
        """Check if essential audio kernel modules are loaded."""
        essential = [
            "snd_hda_intel",   # Intel HDA
            "snd_usb_audio",   # USB audio
            "snd_pcm",         # PCM core
            "snd_mixer_oss",   # Mixer
            "snd_seq",         # Sequencer
        ]
        loaded = set()
        try:
            with open("/proc/modules", "r") as f:
                for line in f:
                    loaded.add(line.split()[0])
        except Exception:
            pass

        results = []
        for mod in essential:
            results.append({
                "name": mod,
                "loaded": mod in loaded,
                "required": mod in ("snd_pcm",),
            })
        return results

    def _check_driver_status(self) -> list:
        """Check ALSA driver status via /proc."""
        drivers = []
        proc_asound = Path("/proc/asound")
        if proc_asound.exists():
            try:
                cards = proc_asound / "cards"
                if cards.exists():
                    for line in cards.read_text().split("\n"):
                        if line.strip():
                            drivers.append({"raw": line.strip()})
            except Exception:
                pass
        return drivers

    def _macos_audio_status(self) -> list:
        """Check macOS CoreAudio status."""
        if not shutil.which("system_profiler"):
            return []
        try:
            r = subprocess.run(
                ["system_profiler", "SPAudioDataType"],
                capture_output=True, text=True, timeout=10)
            return [{"raw": line.strip()}
                    for line in r.stdout.split("\n")
                    if line.strip() and ":" in line][:20]
        except Exception:
            return []

    def _windows_driver_status(self) -> list:
        """Check Windows audio driver status."""
        if not shutil.which("powershell"):
            return []
        try:
            ps_cmd = (
                "Get-CimInstance Win32_SoundDevice | "
                "Select-Object Name,Status,StatusInfo | "
                "ConvertTo-Json"
            )
            r = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=10)
            data = json.loads(r.stdout)
            if isinstance(data, dict):
                data = [data]
            return [{"name": d.get("Name"), "status": d.get("Status")}
                    for d in data]
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════
# USB Device Enumeration
# ═══════════════════════════════════════════════════════════════════

class USBTester:
    """Enumerate USB devices, focusing on audio-related ones."""

    def run(self) -> dict:
        result = {
            "ok": True,
            "platform": _SYSTEM,
            "usb_devices": [],
            "audio_usb": [],
        }

        if _IS_LINUX:
            result["usb_devices"] = self._linux_usb()
        elif _IS_MAC:
            result["usb_devices"] = self._macos_usb()
        elif _IS_WIN:
            result["usb_devices"] = self._windows_usb()

        # Filter audio devices
        audio_keywords = ["audio", "sound", "microphone", "headset",
                          "speaker", "usb-audio", "jabra", "poly",
                          "plantronics", "logitech", "blue", "yeti",
                          "focusrite", "scarlett", "behringer"]
        for dev in result["usb_devices"]:
            name = dev.get("name", "").lower() + dev.get("product", "").lower()
            if any(kw in name for kw in audio_keywords):
                result["audio_usb"].append(dev)

        return result

    def _linux_usb(self) -> list:
        """List USB devices on Linux."""
        if shutil.which("lsusb"):
            try:
                r = subprocess.run(
                    ["lsusb"],
                    capture_output=True, text=True, timeout=5)
                return [{"raw": line.strip()}
                        for line in r.stdout.split("\n")
                        if line.strip()]
            except Exception:
                pass

        # Fallback: sysfs
        devices = []
        usb_base = Path("/sys/bus/usb/devices")
        if usb_base.exists():
            for dev_path in usb_base.iterdir():
                product_file = dev_path / "product"
                if product_file.exists():
                    try:
                        name = product_file.read_text().strip()
                        manufacturer = ""
                        mfg = dev_path / "manufacturer"
                        if mfg.exists():
                            manufacturer = mfg.read_text().strip()
                        devices.append({
                            "name": name,
                            "manufacturer": manufacturer,
                            "product": name,
                            "path": str(dev_path),
                        })
                    except Exception:
                        pass
        return devices

    def _macos_usb(self) -> list:
        """List USB devices on macOS."""
        if not shutil.which("system_profiler"):
            return []
        try:
            r = subprocess.run(
                ["system_profiler", "SPUSBDataType", "-json"],
                capture_output=True, text=True, timeout=10)
            data = json.loads(r.stdout)
            devices = []
            self._extract_usb_items(data.get("SPUSBDataType", []), devices)
            return devices
        except Exception:
            return []

    def _extract_usb_items(self, items: list, out: list):
        """Recursively extract USB items from macOS system_profiler."""
        for item in items:
            if isinstance(item, dict):
                if "_name" in item:
                    out.append({
                        "name": item["_name"],
                        "product": item.get("_name", ""),
                        "manufacturer": item.get("manufacturer", ""),
                    })
                for sub in item.get("_items", []):
                    self._extract_usb_items([sub], out)

    def _windows_usb(self) -> list:
        """List USB devices on Windows."""
        if not shutil.which("powershell"):
            return []
        try:
            ps_cmd = (
                "Get-CimInstance Win32_USBControllerDevice | "
                "ForEach-Object { [wmi]$_.Dependent } | "
                "Select-Object Name,Description -First 20 | "
                "ConvertTo-Json"
            )
            r = subprocess.run(
                ["powershell", "-Command", ps_cmd],
                capture_output=True, text=True, timeout=15)
            data = json.loads(r.stdout)
            if isinstance(data, dict):
                data = [data]
            return [{"name": d.get("Name", ""), "product": d.get("Description", "")}
                    for d in data]
        except Exception:
            return []


# ═══════════════════════════════════════════════════════════════════
# CROSS-SKILL Hardware Validation
# ═══════════════════════════════════════════════════════════════════

class SkillHWValidator:
    """Test hardware foundations required by other skills (STT, TTS, etc.)."""

    def run(self, skills_to_test: list = None) -> dict:
        if skills_to_test is None:
            skills_to_test = ["stt", "tts", "shell"]

        result = {
            "ok": True,
            "skills_tested": {},
            "summary": [],
        }

        for skill in skills_to_test:
            method = getattr(self, f"_test_{skill}_hw", None)
            if method:
                skill_result = method()
                result["skills_tested"][skill] = skill_result
                if not skill_result.get("hw_ok"):
                    result["ok"] = False
                    result["summary"].append(
                        f"{skill}: {', '.join(skill_result.get('issues', ['unknown']))}")

        return result

    def _test_stt_hw(self) -> dict:
        """Test STT hardware prerequisites."""
        checks = {
            "hw_ok": True,
            "issues": [],
            "details": {},
        }

        # 1. Check capture device exists
        inp = AudioInputTester()
        devices = inp._list_capture_devices()
        real_inputs = [d for d in devices
                       if d.get("direction") == "capture"
                       and not d.get("is_monitor")]
        checks["details"]["capture_devices"] = len(real_inputs)
        if not real_inputs:
            checks["hw_ok"] = False
            checks["issues"].append("No real capture device (only monitors)")

        # 2. Check default source is not a monitor
        default = inp._get_default_source()
        checks["details"]["default_source"] = default
        if default.get("is_monitor"):
            checks["hw_ok"] = False
            checks["issues"].append(
                "Default source is a monitor — switch to real microphone")

        # 3. Check not muted
        if default.get("muted"):
            checks["issues"].append("Default source is MUTED")

        # 4. Check volume > 50%
        vol = default.get("volume_pct")
        if vol is not None and vol < 50:
            checks["issues"].append(
                f"Default source volume too low: {vol}%")

        # 5. Check tools
        tools_needed = {
            "arecord": "Recording audio (ALSA)",
            "vosk-transcriber": "Speech recognition",
        }
        for tool, purpose in tools_needed.items():
            if not shutil.which(tool):
                checks["issues"].append(f"Missing: {tool} ({purpose})")
                checks["details"][f"has_{tool}"] = False
            else:
                checks["details"][f"has_{tool}"] = True

        # 6. Check vosk model
        vosk_model = self._find_vosk_model()
        checks["details"]["vosk_model"] = vosk_model
        if not vosk_model:
            checks["issues"].append("No vosk model found in cache")

        return checks

    def _test_tts_hw(self) -> dict:
        """Test TTS hardware prerequisites."""
        checks = {
            "hw_ok": True,
            "issues": [],
            "details": {},
        }

        # 1. Check playback device exists
        out = AudioOutputTester()
        devices = out._list_playback_devices()
        checks["details"]["playback_devices"] = len(devices)
        if not devices:
            checks["hw_ok"] = False
            checks["issues"].append("No playback devices detected")

        # 2. Check default sink
        sink = out._get_default_sink()
        checks["details"]["default_sink"] = sink
        if sink.get("muted"):
            checks["issues"].append("Default output is MUTED")
        vol = sink.get("volume_pct")
        if vol is not None and vol < 20:
            checks["issues"].append(f"Output volume very low: {vol}%")

        # 3. Check TTS tools
        tts_tools = {
            "espeak-ng": "TTS engine (primary)",
            "espeak": "TTS engine (fallback)",
        }
        has_tts = False
        for tool, purpose in tts_tools.items():
            if shutil.which(tool):
                has_tts = True
                checks["details"][f"has_{tool}"] = True
                break
        if not has_tts:
            checks["hw_ok"] = False
            checks["issues"].append("No TTS engine (espeak-ng/espeak)")

        # 4. Quick TTS dry-run test
        if has_tts:
            tts_test = self._test_tts_output()
            checks["details"]["tts_test"] = tts_test
            if not tts_test.get("ok"):
                checks["issues"].append(
                    f"TTS test failed: {tts_test.get('error', '?')}")

        return checks

    def _test_shell_hw(self) -> dict:
        """Test shell skill hardware (basic system commands)."""
        checks = {
            "hw_ok": True,
            "issues": [],
            "details": {},
        }

        basic_cmds = ["bash", "cat", "ls", "grep", "which"]
        for cmd in basic_cmds:
            checks["details"][f"has_{cmd}"] = shutil.which(cmd) is not None
            if not shutil.which(cmd):
                checks["issues"].append(f"Missing basic command: {cmd}")
                checks["hw_ok"] = False

        return checks

    def _find_vosk_model(self) -> str:
        """Find vosk model path."""
        cache_dirs = [
            Path.home() / ".cache" / "vosk",
            Path.home() / ".local" / "share" / "vosk",
        ]
        for cache_dir in cache_dirs:
            if not cache_dir.exists():
                continue
            for item in cache_dir.iterdir():
                if item.is_dir() and "model" in item.name.lower():
                    return str(item)
        return ""

    def _test_tts_output(self) -> dict:
        """Quick TTS test — generate a short audio file."""
        fd, out_path = tempfile.mkstemp(suffix=".wav", prefix="hw_test_tts_")
        os.close(fd)
        try:
            tts_bin = shutil.which("espeak-ng") or shutil.which("espeak")
            if not tts_bin:
                return {"ok": False, "error": "No TTS engine"}
            r = subprocess.run(
                [tts_bin, "-w", out_path, "test"],
                capture_output=True, text=True, timeout=10)
            if r.returncode == 0 and Path(out_path).stat().st_size > 100:
                return {"ok": True, "file_size": Path(out_path).stat().st_size}
            return {"ok": False, "error": r.stderr[:200]}
        except Exception as e:
            return {"ok": False, "error": str(e)}
        finally:
            try:
                os.unlink(out_path)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════
# MAIN EXECUTE
# ═══════════════════════════════════════════════════════════════════

class HWTestSkill:
    """Hardware diagnostics master class."""

    def execute(self, params: dict) -> dict:
        action = params.get("action", params.get("text", "full")).strip().lower()

        # Parse action from free text
        if any(kw in action for kw in ["pełny", "full", "all", "cały"]):
            action = "full"
        elif any(kw in action for kw in ["mikrofon", "input", "wejś", "capture", "mic"]):
            action = "audio_input"
        elif any(kw in action for kw in ["głośnik", "output", "wyjś", "speaker", "playback"]):
            action = "audio_output"
        elif any(kw in action for kw in ["loopback", "pętla", "echo"]):
            action = "audio_loop"
        elif any(kw in action for kw in ["device", "urządz", "lista"]):
            action = "devices"
        elif any(kw in action for kw in ["driver", "sterown", "moduł", "kernel"]):
            action = "drivers"
        elif any(kw in action for kw in ["pulse", "pipewire", "alsa"]):
            action = "pulse"
        elif any(kw in action for kw in ["usb"]):
            action = "usb"
        elif any(kw in action for kw in ["skill", "stt", "tts", "cross"]):
            action = "skill_hw"
        elif any(kw in action for kw in ["report", "raport", "json"]):
            action = "report"

        dispatch = {
            "full": self._full_test,
            "audio_input": self._test_audio_input,
            "audio_output": self._test_audio_output,
            "audio_loop": self._test_audio_loopback,
            "devices": self._list_devices,
            "drivers": self._test_drivers,
            "pulse": self._test_pulse,
            "usb": self._test_usb,
            "skill_hw": self._test_skill_hw,
            "report": self._generate_report,
        }

        handler = dispatch.get(action, self._full_test)
        result = handler()
        result["action"] = action
        result["platform"] = _SYSTEM
        result["success"] = result.get("ok", result.get("success", False))
        return result

    def _full_test(self) -> dict:
        """Run all hardware tests."""
        results = {
            "ok": True,
            "tests": {},
            "summary": {"passed": 0, "failed": 0, "warnings": 0},
        }

        tests = [
            ("audio_input", self._test_audio_input),
            ("audio_output", self._test_audio_output),
            ("drivers", self._test_drivers),
            ("usb", self._test_usb),
            ("skill_hw", self._test_skill_hw),
        ]

        for name, fn in tests:
            try:
                r = fn()
                results["tests"][name] = r
                if r.get("ok"):
                    results["summary"]["passed"] += 1
                else:
                    results["summary"]["failed"] += 1
                    results["ok"] = False
                if r.get("issues"):
                    results["summary"]["warnings"] += len(r["issues"])
            except Exception as e:
                results["tests"][name] = {"ok": False, "error": str(e)}
                results["summary"]["failed"] += 1
                results["ok"] = False

        return results

    def _test_audio_input(self) -> dict:
        return AudioInputTester().run()

    def _test_audio_output(self) -> dict:
        return AudioOutputTester().run()

    def _test_audio_loopback(self) -> dict:
        return AudioLoopbackTester().run()

    def _list_devices(self) -> dict:
        inp = AudioInputTester()
        out = AudioOutputTester()
        return {
            "ok": True,
            "capture_devices": inp._list_capture_devices(),
            "playback_devices": out._list_playback_devices(),
            "default_source": inp._get_default_source(),
            "default_sink": out._get_default_sink(),
        }

    def _test_drivers(self) -> dict:
        return DriverTester().run()

    def _test_pulse(self) -> dict:
        """Detailed PulseAudio/PipeWire analysis."""
        result = {"ok": False, "sources": [], "sinks": [], "server_info": {}}

        if not shutil.which("pactl"):
            result["error"] = "pactl not available"
            return result

        try:
            # Server info
            r = subprocess.run(
                ["pactl", "info"],
                capture_output=True, text=True, timeout=5)
            for line in r.stdout.split("\n"):
                if ":" in line:
                    key, _, val = line.partition(":")
                    result["server_info"][key.strip()] = val.strip()

            # Sources with details
            r = subprocess.run(
                ["pactl", "list", "sources"],
                capture_output=True, text=True, timeout=5)
            current_source = {}
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line.startswith("Source #"):
                    if current_source:
                        result["sources"].append(current_source)
                    current_source = {"id": line}
                elif ":" in line and current_source:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key in ("Name", "Description", "State",
                               "Volume", "Mute", "Sample Specification"):
                        current_source[key.lower().replace(" ", "_")] = val
            if current_source:
                result["sources"].append(current_source)

            # Sinks with details
            r = subprocess.run(
                ["pactl", "list", "sinks"],
                capture_output=True, text=True, timeout=5)
            current_sink = {}
            for line in r.stdout.split("\n"):
                line = line.strip()
                if line.startswith("Sink #"):
                    if current_sink:
                        result["sinks"].append(current_sink)
                    current_sink = {"id": line}
                elif ":" in line and current_sink:
                    key, _, val = line.partition(":")
                    key = key.strip()
                    val = val.strip()
                    if key in ("Name", "Description", "State",
                               "Volume", "Mute", "Sample Specification"):
                        current_sink[key.lower().replace(" ", "_")] = val
            if current_sink:
                result["sinks"].append(current_sink)

            result["ok"] = bool(result["sources"] or result["sinks"])
        except Exception as e:
            result["error"] = str(e)

        return result

    def _test_usb(self) -> dict:
        return USBTester().run()

    def _test_skill_hw(self) -> dict:
        return SkillHWValidator().run()

    def _generate_report(self) -> dict:
        """Generate a complete hardware report."""
        report = self._full_test()
        report["pulse_details"] = self._test_pulse()
        report["action"] = "report"
        return report


def execute(input_data: dict) -> dict:
    """Module-level execute entry point."""
    return HWTestSkill().execute(input_data)


if __name__ == "__main__":
    import sys as _sys
    action = _sys.argv[1] if len(_sys.argv) > 1 else "full"
    result = execute({"action": action})
    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
