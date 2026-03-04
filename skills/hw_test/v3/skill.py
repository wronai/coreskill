import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
import wave
import struct
import math
from pathlib import Path

_SYSTEM = platform.system()
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
    return {"status": "ok" if any(shutil.which(t) for t in tools) else "error"}


class AudioInputTester:
    def run(self, duration: float = 2.0) -> dict:
        result = {
            "ok": False,
            "platform": _SYSTEM,
            "devices": self._list_capture_devices(),
            "default_source": self._get_default_source(),
            "record_test": None,
            "level_test": None,
            "issues": [],
            "recommendations": [],
        }

        if not result["devices"]:
            result["issues"].append("No capture devices detected")
            result["recommendations"].append("Connect a microphone or USB audio device")
            return result

        rec = self._record_test(duration)
        result["record_test"] = rec

        if not rec["ok"]:
            result["issues"].append(f"Recording failed: {rec.get('error', '?')}")
            result["recommendations"].append("Check microphone permissions and ALSA/PulseAudio config")
            return result

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

        try:
            os.unlink(rec.get("wav_path", ""))
        except Exception:
            pass

        return result

    def _list_capture_devices(self) -> list:
        devices = []
        if _IS_LINUX:
            devices.extend(self._alsa_capture_devices())
            devices.extend(self._pulse_sources())
        elif _IS_MAC:
            devices.extend(self._macos_audio_inputs())
        elif _IS_WIN:
            devices.extend(self._windows_audio_inputs())
        return devices

    def _alsa_capture_devices(self) -> list:
        if not shutil.which("arecord"):
            return []
        try:
            r = subprocess.run(
                ["arecord", "-l"],
                capture_output=True, text=True, timeout=5)
            devices = []
            for line in r.stdout.split("\n"):
                if line.strip().startswith("card"):
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
        if _IS_LINUX and shutil.which("pactl"):
            try:
                r = subprocess.run(
                    ["pactl", "get-default-source"],
                    capture_output=True, text=True, timeout=3)
                name = r.stdout.strip()
                rv = subprocess.run(
                    ["pactl", "get-source-volume", name],
                    capture_output=True, text=True, timeout=3)
                vol_str = rv.stdout.strip()
                volume_pct = None
                if "%" in vol_str:
                    try:
                        volume_pct = int(vol_str.split("%")[0].split("/")[-1].strip())
                    except (ValueError, IndexError):
                        pass
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
        return {"note": "Cannot determine default source on this platform"}

    def _record_test(self, duration: float) -> dict:
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

        self._generate_wav(wav_path, duration, frequency=0)
        return {
            "ok": False,
            "error": "No recording tool available (arecord/ffmpeg/sox)",
            "wav_path": wav_path,
            "generated_silence": True,
        }

    def _measure_level(self, wav_path: str, threshold_db: float = -40.0) -> dict:
        result = {"ok": False, "threshold_db": threshold_db}

        if shutil.which("sox"):
            try:
                r = subprocess.run(
                    ["sox", wav_path, "-n", "stat"],
                    capture_output=True, text=True, timeout=10)
                stats_text = r.stderr
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
            except Exception:
                pass

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
        try:
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
        except Exception:
            return 0.0

    @staticmethod
    def _generate_wav(path: str, duration: float, frequency: float = 440.0,
                      sample_rate: int = 16000):
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


class AudioOutputTester:
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

        result["playback_test"] = self._play_test_tone(duration)
        if result["playback_test"].get("ok"):
            result["ok"] = True
        else:
            result["issues"].append(
                f"Playback failed: {result['playback_test'].get('error', '?')}")

        return result

    def _list_playback_devices(self) -> list:
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

            return {"ok": False, "error": "No playback tool available"}
        finally:
            try:
                os.unlink(wav_path)
            except Exception:
                pass


class HwTestSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "").strip().lower()
            if "input" in text or "mic" in text or "record" in text:
                tester = AudioInputTester()
                result = tester.run()
                spoken = f"Audio input test complete. Devices found: {len(result.get('devices', []))}. "
                if result.get("ok"):
                    spoken += "Microphone is working properly."
                else:
                    spoken += "Issues detected. " + " ".join(result.get("issues", []))
                return {
                    "success": True,
                    "spoken": spoken,
                    "data": result
                }
            elif "output" in text or "speaker" in text or "play" in text:
                tester = AudioOutputTester()
                result = tester.run()
                spoken = f"Audio output test complete. Devices found: {len(result.get('devices', []))}. "
                if result.get("ok"):
                    spoken += "Speakers are working properly."
                else:
                    spoken += "Issues detected. " + " ".join(result.get("issues", []))
                return {
                    "success": True,
                    "spoken": spoken,
                    "data": result
                }
            else:
                # Run both tests
                input_tester = AudioInputTester()
                input_result = input_tester.run()
                output_tester = AudioOutputTester()
                output_result = output_tester.run()
                
                spoken = "Hardware test complete. "
                if input_result.get("ok") and output_result.get("ok"):
                    spoken += "Both microphone and speakers are working properly."
                else:
                    issues = []
                    if not input_result.get("ok"):
                        issues.extend(input_result.get("issues", []))
                    if not output_result.get("ok"):
                        issues.extend(output_result.get("issues", []))
                    spoken += "Issues detected: " + " ".join(issues)
                
                return {
                    "success": True,
                    "spoken": spoken,
                    "data": {
                        "input": input_result,
                        "output": output_result
                    }
                }
        except Exception as e:
            return {
                "success": False,
                "spoken": f"Hardware test failed: {str(e)}",
                "error": str(e)
            }


def execute(params: dict) -> dict:
    skill = HwTestSkill()
    return skill.execute(params)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = "both"
    result = execute({"text": text})
    print(json.dumps(result, indent=2))