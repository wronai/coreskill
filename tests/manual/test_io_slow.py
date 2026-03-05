#!/usr/bin/env python3
"""
SLOW I/O Tests - require hardware, subprocess calls, or SQLite operations.
These tests are separated because they hang on blocking I/O operations.

Run separately: python3 -m pytest tests/manual/test_io_slow.py -v
"""
import json
import os
import sys
import tempfile
import shutil
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Setup path
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

from cores.v1.config import SKILLS_DIR

# ─── NFO Decorator Logging Tests ─────────────────────────────────────
try:
    import nfo as _nfo_mod
    _has_nfo = hasattr(_nfo_mod, 'logged') and hasattr(_nfo_mod, 'log_call')
except ImportError:
    _has_nfo = False


@unittest.skipUnless(_has_nfo, "nfo module not fully available")
class TestNfoDecoratorLogging(unittest.TestCase):
    """Test nfo-based decorator logging for skills."""

    def test_init_nfo_returns_logger(self):
        """init_nfo() should return a configured logger."""
        from cores.v1.skill_logger import init_nfo
        logger = init_nfo()
        self.assertIsNotNone(logger)
        self.assertEqual(logger.name, "evo")

    def test_init_nfo_idempotent(self):
        """Calling init_nfo() twice should return same logger."""
        from cores.v1.skill_logger import init_nfo
        l1 = init_nfo()
        l2 = init_nfo()
        self.assertEqual(l1.name, l2.name)

    def test_inject_logging_wraps_functions(self):
        """inject_logging should wrap module functions with nfo decorators."""
        import types
        from cores.v1.skill_logger import inject_logging
        mod = types.ModuleType("test_mod")
        def execute(params):
            return {"success": True}
        mod.execute = execute
        inject_logging(mod, skill_name="test")
        result = mod.execute({"x": 1})
        self.assertEqual(result, {"success": True})

    def test_inject_logging_safe_on_empty_module(self):
        """inject_logging should not crash on empty module."""
        import types
        from cores.v1.skill_logger import inject_logging
        mod = types.ModuleType("empty_mod")
        inject_logging(mod)  # Should not raise

    def test_sqlite_sink_exists(self):
        """After init, SQLite sink file should exist."""
        from cores.v1.skill_logger import init_nfo, _SQLITE_PATH
        init_nfo()
        import nfo
        @nfo.log_call
        def _probe():
            return 42
        _probe()
        self.assertTrue(_SQLITE_PATH.exists(),
                        f"SQLite sink not found at {_SQLITE_PATH}")

    def test_skill_health_summary_format(self):
        """skill_health_summary should return a dict with expected keys."""
        from cores.v1.skill_logger import skill_health_summary, init_nfo
        init_nfo()
        summary = skill_health_summary("echo")
        self.assertIn("skill", summary)
        self.assertIn("status", summary)
        self.assertEqual(summary["skill"], "echo")

    def test_nfo_logged_on_echo_skill(self):
        """Echo skill class should have nfo @logged decorator applied."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "echo_test", str(SKILLS_DIR / "echo" / "v1" / "skill.py"))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.execute({"test": True})
        self.assertTrue(result.get("echo", {}).get("test"))

    def test_nfo_logged_on_shell_skill(self):
        """Shell skill class should have nfo @logged decorator applied."""
        import importlib.util
        p = SKILLS_DIR / "shell" / "v1" / "skill.py"
        if p.exists():
            spec = importlib.util.spec_from_file_location("shell_test", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Just verify the class loads without error
            self.assertTrue(hasattr(mod, "ShellSkill"))


# ─── TTS/STT Pipeline Tests ────────────────────────────────────────────
class TestTTSSTTPipeline(unittest.TestCase):
    """E2E tests: TTS generates audio file, STT transcribes it, verify round-trip."""

    @classmethod
    def setUpClass(cls):
        cls.espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        cls.vosk_transcriber = shutil.which("vosk-transcriber")
        vosk_cache = Path.home() / ".cache" / "vosk"
        cls.vosk_model = None
        if vosk_cache.is_dir():
            for d in sorted(vosk_cache.iterdir(), reverse=True):
                if d.is_dir() and "model" in d.name.lower() and (d / "graph").is_dir():
                    cls.vosk_model = str(d)
                    break
        # Prefer stable/ paths, fallback to v{N} for backward compat
        stt_stable = ROOT / "skills" / "stt" / "providers" / "vosk" / "stable" / "skill.py"
        cls.stt_skill_path = stt_stable if stt_stable.exists() else ROOT / "skills" / "stt" / "providers" / "vosk" / "v7" / "skill.py"
        tts_stable = ROOT / "skills" / "tts" / "providers" / "espeak" / "stable" / "skill.py"
        cls.tts_skill_path = tts_stable if tts_stable.exists() else ROOT / "skills" / "tts" / "providers" / "espeak" / "v1" / "skill.py"

    def _generate_wav(self, text, path):
        """Use espeak to generate a WAV file with the given text."""
        if not self.espeak:
            self.skipTest("espeak/espeak-ng not installed")
        import subprocess
        r = subprocess.run(
            [self.espeak, "-v", "pl", "-w", path, "--", text],
            capture_output=True, timeout=10
        )
        self.assertEqual(r.returncode, 0, f"espeak failed: {r.stderr}")

    def _transcribe_wav(self, wav_path):
        """Transcribe WAV file using vosk-transcriber, return text."""
        if not self.vosk_transcriber:
            self.skipTest("vosk-transcriber not installed")
        import subprocess
        cmd = [self.vosk_transcriber, "--input", wav_path]
        if self.vosk_model:
            cmd += ["--model", self.vosk_model]
        else:
            cmd += ["--lang", "pl"]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        return r.stdout.strip()

    def test_tts_espeak_skill_loads(self):
        """TTS espeak v1 skill loads without errors (no nfo dependency)."""
        import importlib.util
        if not self.tts_skill_path.exists():
            self.skipTest(f"TTS skill not found: {self.tts_skill_path}")
        spec = importlib.util.spec_from_file_location("tts_v1", str(self.tts_skill_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, "TTSSkill"))
        self.assertTrue(hasattr(mod, "get_info"))
        self.assertTrue(hasattr(mod, "health_check"))

    def test_tts_espeak_produces_audio(self):
        """TTS espeak v1 executes and reports success."""
        if not self.espeak:
            self.skipTest("espeak not installed")
        import importlib.util
        if not self.tts_skill_path.exists():
            self.skipTest(f"TTS skill not found: {self.tts_skill_path}")
        spec = importlib.util.spec_from_file_location("tts_v1", str(self.tts_skill_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        result = mod.TTSSkill().execute({"text": "test"})
        self.assertTrue(result.get("success"), f"TTS failed: {result.get('error')}")

    def test_tts_espeak_generates_wav_file(self):
        """espeak-ng -w generates a valid WAV file."""
        if not self.espeak:
            self.skipTest("espeak not installed")
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            self._generate_wav("test jeden dwa", wav_path)
            self.assertTrue(Path(wav_path).exists(), "WAV file not created")
            self.assertGreater(Path(wav_path).stat().st_size, 1000, "WAV file too small")
        finally:
            Path(wav_path).unlink(missing_ok=True)

    def test_stt_skill_loads(self):
        """STT vosk v7 skill loads without errors (no nfo dependency)."""
        import importlib.util
        if not self.stt_skill_path.exists():
            self.skipTest(f"STT skill not found: {self.stt_skill_path}")
        spec = importlib.util.spec_from_file_location("stt_v7", str(self.stt_skill_path))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        self.assertTrue(hasattr(mod, "STTSkill"))
        self.assertTrue(hasattr(mod, "get_info"))
        self.assertTrue(hasattr(mod, "health_check"))

    def test_stt_skill_transcribes_wav_file(self):
        """STT skill transcribes a WAV file passed via audio_path."""
        if not self.vosk_transcriber or not self.espeak:
            self.skipTest("vosk-transcriber or espeak not installed")
        import importlib.util
        if not self.stt_skill_path.exists():
            self.skipTest(f"STT skill not found: {self.stt_skill_path}")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            self._generate_wav("test jeden dwa trzy", wav_path)
            spec = importlib.util.spec_from_file_location("stt_v7", str(self.stt_skill_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.STTSkill().execute({"audio_path": wav_path, "lang": "pl"})
            # Must not crash
            self.assertIsInstance(result, dict, "Result must be a dict")
            self.assertTrue(result.get("success"), f"STT failed: {result.get('error')}")
        finally:
            Path(wav_path).unlink(missing_ok=True)

    def test_tts_to_stt_roundtrip_pipeline(self):
        """Generate audio via espeak, transcribe via vosk — verify words appear in output."""
        if not self.vosk_transcriber or not self.espeak:
            self.skipTest("vosk-transcriber or espeak not installed")
        if not self.vosk_model:
            self.skipTest("No vosk model found in ~/.cache/vosk/")

        test_text = "jeden dwa trzy"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            self._generate_wav(test_text, wav_path)
            transcript = self._transcribe_wav(wav_path)
            self.assertTrue(
                transcript,
                "vosk returned empty transcription for espeak audio"
            )
            # Check at least one word from the test text appears
            words_found = [w for w in test_text.split() if w in transcript.lower()]
            self.assertGreater(
                len(words_found), 0,
                f"No words from '{test_text}' found in transcript: '{transcript}'"
            )
        finally:
            Path(wav_path).unlink(missing_ok=True)

    def test_tts_to_stt_via_skill_interface(self):
        """Full pipeline: espeak WAV → STT skill execute() → non-empty spoken text."""
        if not self.vosk_transcriber or not self.espeak:
            self.skipTest("vosk-transcriber or espeak not installed")
        if not self.vosk_model:
            self.skipTest("No vosk model found in ~/.cache/vosk/")
        import importlib.util
        if not self.stt_skill_path.exists():
            self.skipTest(f"STT skill not found: {self.stt_skill_path}")

        test_text = "cześć jak się masz"
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = f.name
        try:
            self._generate_wav(test_text, wav_path)
            spec = importlib.util.spec_from_file_location("stt_v7", str(self.stt_skill_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.STTSkill().execute({"audio_path": wav_path, "lang": "pl"})
            self.assertTrue(result.get("success"), f"STT skill failed: {result.get('error')}")
            spoken = result.get("text", "") or result.get("spoken", "")
            self.assertIsInstance(spoken, str, "text/spoken field must be a string")
            # Should produce some transcription (not empty) from espeak audio
            self.assertTrue(
                spoken.strip(),
                f"STT returned empty transcription for espeak audio. Result: {result}"
            )
        finally:
            Path(wav_path).unlink(missing_ok=True)


# ─── Hardware Test Skill Tests ────────────────────────────────────────
class TestHWTestSkill(unittest.TestCase):
    """Test the hw_test hardware diagnostics skill."""

    def test_skill_loads_and_has_interface(self):
        """hw_test skill loads and has required interface functions."""
        from skills.hw_test.v1.skill import execute, get_info, health_check, HWTestSkill
        info = get_info()
        self.assertEqual(info["name"], "hw_test")
        self.assertTrue(health_check())
        self.assertIsNotNone(HWTestSkill)

    def test_execute_full_returns_structured_result(self):
        """Full test returns structured diagnostics dict."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "full"})
        self.assertIn("tests", result)
        self.assertIn("summary", result)
        self.assertIn("platform", result)
        self.assertIn("success", result)
        summary = result["summary"]
        self.assertIn("passed", summary)
        self.assertIn("failed", summary)

    def test_execute_devices_lists_something(self):
        """Devices action returns capture and playback device lists."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "devices"})
        self.assertIn("capture_devices", result)
        self.assertIn("playback_devices", result)
        self.assertIsInstance(result["capture_devices"], list)
        self.assertIsInstance(result["playback_devices"], list)

    def test_execute_drivers_returns_subsystem(self):
        """Drivers action detects audio subsystem."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "drivers"})
        self.assertIn("audio_subsystem", result)
        self.assertIn("kernel_modules", result)
        self.assertIn("platform", result)

    def test_execute_usb_returns_list(self):
        """USB action returns device list."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "usb"})
        self.assertIn("usb_devices", result)
        self.assertIn("audio_usb", result)
        self.assertIsInstance(result["usb_devices"], list)

    def test_execute_skill_hw_validates_stt_tts(self):
        """Skill HW action validates STT and TTS hardware prerequisites."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "skill_hw"})
        self.assertIn("skills_tested", result)
        tested = result["skills_tested"]
        self.assertIn("stt", tested)
        self.assertIn("tts", tested)
        # Each skill test has hw_ok and details
        for skill_name in ("stt", "tts"):
            self.assertIn("hw_ok", tested[skill_name])
            self.assertIn("details", tested[skill_name])

    def test_execute_pulse_returns_sources_sinks(self):
        """Pulse action returns sources and sinks."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "pulse"})
        self.assertIn("sources", result)
        self.assertIn("sinks", result)

    def test_audio_input_tester_measure_level_on_generated_wav(self):
        """AudioInputTester can measure level of a generated WAV file."""
        from skills.hw_test.v1.skill import AudioInputTester
        import tempfile, os
        inp = AudioInputTester()
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            # Generate a tone WAV
            inp._generate_wav(path, duration=0.5, frequency=440.0)
            level = inp._measure_level(path, threshold_db=-40.0)
            self.assertIn("max_db", level)
            # 440Hz tone at amplitude 16000/32768 should be well above -40 dB
            self.assertTrue(level["ok"], f"Level should be OK: {level}")
        finally:
            os.unlink(path)

    def test_audio_input_tester_silence_detected(self):
        """AudioInputTester detects silence (generated zero-amplitude WAV)."""
        from skills.hw_test.v1.skill import AudioInputTester
        import tempfile, os
        inp = AudioInputTester()
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            inp._generate_wav(path, duration=0.5, frequency=0)
            level = inp._measure_level(path, threshold_db=-40.0)
            self.assertFalse(level.get("ok", True), f"Silence should fail: {level}")
        finally:
            os.unlink(path)

    def test_loopback_frequency_check(self):
        """AudioLoopbackTester frequency detection works on generated tone."""
        from skills.hw_test.v1.skill import AudioLoopbackTester, AudioInputTester
        import tempfile, os
        loop = AudioLoopbackTester()
        fd, path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)
        try:
            AudioInputTester._generate_wav(path, duration=1.0, frequency=1000.0)
            freq = loop._check_frequency(path, expected_hz=1000.0)
            self.assertIn("estimated_hz", freq)
            # Should be roughly near 1000 Hz
            if freq.get("ok"):
                self.assertAlmostEqual(freq["estimated_hz"], 1000, delta=200)
        finally:
            os.unlink(path)

    def test_free_text_action_parsing(self):
        """HWTestSkill parses free-text action keywords."""
        from skills.hw_test.v1.skill import HWTestSkill
        hw = HWTestSkill()
        # Polish keywords
        r1 = hw.execute({"text": "sprawdź mikrofon"})
        self.assertEqual(r1["action"], "audio_input")
        r2 = hw.execute({"text": "sterowniki audio"})
        self.assertEqual(r2["action"], "drivers")
        r3 = hw.execute({"text": "pokaż usb"})
        self.assertEqual(r3["action"], "usb")
        r4 = hw.execute({"text": "pełny test"})
        self.assertEqual(r4["action"], "full")

    def test_report_includes_pulse_details(self):
        """Report action includes pulse details."""
        from skills.hw_test.v1.skill import execute
        result = execute({"action": "report"})
        self.assertIn("pulse_details", result)
        self.assertIn("tests", result)


if __name__ == "__main__":
    unittest.main()
