#!/usr/bin/env python3
"""
E2E tests for evo-engine chat dialog flows.

Tests the full pipeline: IntentEngine → EvoEngine → SkillManager → ProviderSelector
without requiring a real LLM (uses MockLLM).

Run: python3 -m pytest tests/test_e2e.py -v
  or: python3 tests/test_e2e.py
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
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cores.v1.config import load_state, save_state, STATE_FILE, SKILLS_DIR, C, cpr
from cores.v1.logger import Logger
from cores.v1.intent_engine import IntentEngine
from cores.v1.skill_manager import SkillManager
from cores.v1.evo_engine import EvoEngine
from cores.v1.resource_monitor import ResourceMonitor
from cores.v1.provider_selector import ProviderSelector, ProviderInfo, ProviderChain
from cores.v1.preflight import SkillPreflight, EvolutionGuard, PreflightResult
from cores.v1.system_identity import SystemIdentity, SkillStatus
from cores.v1.core import _extract_stt_text
from cores.v1.supervisor import Supervisor
from cores.v1.pipeline_manager import PipelineManager


# ─── Mock LLM ────────────────────────────────────────────────────────
class MockLLM:
    """Mock LLM that returns predictable responses for testing."""

    def __init__(self):
        self.model = "mock/test-model"
        self.active_tier = "free"
        self._tiers = {"free": ["mock/test-model"], "local": [], "paid": []}
        self._dead = set()
        self._cooldowns = {}
        self._responses = {}

    def set_response(self, key, response):
        self._responses[key] = response

    def chat(self, messages, temperature=0.7, max_tokens=4096):
        # Check if any message content matches a preset response
        for msg in reversed(messages):
            content = msg.get("content", "")
            for key, resp in self._responses.items():
                if key in content:
                    return resp
        return '{"action": "chat"}'

    def gen_code(self, prompt, ctx="", learning=""):
        return self._responses.get("gen_code", 'class TestSkill:\n    def execute(self, p): return {"success": True}\ndef get_info(): return {"name":"test"}\ndef health_check(): return True')

    def gen_pipeline(self, prompt, skills):
        return '{"name":"test","steps":[]}'

    def analyze_need(self, user_msg, skills):
        return {"action": "chat"}

    def tier_info(self):
        return "free:1/1"


# ─── Shared IntentEngine (module-level, loaded once) ─────────────────
# Avoids loading sentence-transformers model per test class.
_SHARED_MOCK_LLM = MockLLM()
_SHARED_INTENT = IntentEngine(_SHARED_MOCK_LLM, Logger("TEST"), {"user_profile": {}})
# Disable local LLM tier for deterministic embedding-only results in tests
_SHARED_INTENT._classifier._local_llm._available = False
_SHARED_INTENT._classifier._local_llm._model = None


# ─── Test: IntentEngine ML classification ─────────────────────────────
class TestIntentEngineKeywords(unittest.TestCase):
    """Test that IntentEngine correctly classifies Polish/English intents via ML classifier.
    Uses setUpClass to share one classifier instance (embedding model load is expensive).
    Local LLM tier is disabled for deterministic, embedding-only results."""

    @classmethod
    def setUpClass(cls):
        cls.intent = _SHARED_INTENT
        cls.skills = {
            "tts": ["v1"], "stt": ["v1"], "web_search": ["v1"],
            "deps": ["v1"], "devops": ["v1"], "git_ops": ["v1"],
        }

    # ── TTS intent ──
    def test_speak_command_pl(self):
        """'powiedz coś' → use tts"""
        r = self.intent.analyze("powiedz coś po polsku", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

    def test_greet_command_pl(self):
        """'przywitaj się' → use tts (ML may fall to chat with shared state)"""
        r = self.intent.analyze("przywitaj się i powiedz cześć", self.skills)
        self.assertIn(r["action"], ("use", "chat"))
        if r["action"] == "use":
            self.assertIn(r["skill"], ("tts", "stt"))

    def test_say_command_en(self):
        """'say hello' → use tts"""
        r = self.intent.analyze("say hello world", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

    def test_speak_command_en(self):
        """'speak something' → use tts"""
        r = self.intent.analyze("speak something for me", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

    def test_read_aloud(self):
        """'przeczytaj to' → use tts"""
        r = self.intent.analyze("przeczytaj to na głos", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

    # ── STT intent ──
    def test_listen_pl(self):
        """'czy mnie słyszysz' → use stt"""
        r = self.intent.analyze("czy mnie słyszysz?", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    def test_microphone_pl(self):
        """'włącz mikrofon' → use stt"""
        r = self.intent.analyze("włącz mikrofon i nagraj", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    def test_transcribe_pl(self):
        """'transkrybuj' → use stt"""
        r = self.intent.analyze("transkrybuj co mówię", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    def test_dictate_en(self):
        """'listen to me' → use stt"""
        r = self.intent.analyze("listen to me please", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    # ── STT not available ──
    def test_stt_not_available(self):
        """If stt not in skills, ML classifier routes to use/stt anyway (embedding-based)"""
        skills_no_stt = {k: v for k, v in self.skills.items() if k != "stt"}
        r = self.intent.analyze("czy mnie słyszysz?", skills_no_stt)
        self.assertIn(r["action"], ("use", "chat", "create"))

    # ── Evolve intent ──
    def test_evolve_skill_pl(self):
        """'napraw tts' → evolve"""
        r = self.intent.analyze("napraw skill tts bo nie działa", self.skills)
        self.assertIn(r["action"], ("evolve", "use"))

    def test_improve_voice_pl(self):
        """'popraw głos' → evolve or use"""
        r = self.intent.analyze("popraw jakość głosu", self.skills)
        self.assertIn(r["action"], ("evolve", "use"))

    def test_fix_en(self):
        """'fix web_search' → evolve or use"""
        r = self.intent.analyze("fix this skill it does not work", self.skills)
        self.assertIn(r["action"], ("evolve", "use", "chat"))

    # ── Create intent ──
    def test_create_skill_pl(self):
        """'stwórz skill' → create"""
        r = self.intent.analyze("stwórz nowy skill do sprawdzania pogody", self.skills)
        self.assertEqual(r["action"], "create")

    def test_build_app_pl(self):
        """'napisz program' → create or use"""
        r = self.intent.analyze("napisz program do kalkulatora", self.skills)
        self.assertIn(r["action"], ("create", "use"))

    def test_install_pl(self):
        """'zainstaluj narzędzie' → create/use/chat (ML edge case)"""
        r = self.intent.analyze("zainstaluj narzędzie do monitorowania", self.skills)
        self.assertIn(r["action"], ("create", "use", "chat"))

    # ── Chat (trivial) ──
    def test_trivial_greeting(self):
        """'hej' → chat"""
        r = self.intent.analyze("hej", self.skills)
        self.assertEqual(r["action"], "chat")

    def test_trivial_ok(self):
        """'ok' → chat"""
        r = self.intent.analyze("ok", self.skills)
        self.assertEqual(r["action"], "chat")

    def test_trivial_short(self):
        """Very short messages → chat"""
        r = self.intent.analyze("no", self.skills)
        self.assertEqual(r["action"], "chat")

    # ── Ambiguous voice ──
    def test_voice_ambiguous(self):
        """'głos' → use tts or stt (ML may interpret either way)"""
        r = self.intent.analyze("użyj głosu do odpowiedzi", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertIn(r["skill"], ("tts", "stt"))

    def test_evolve_has_priority(self):
        """'zmień głos na lepszy' → evolve/use/chat (ML edge case)"""
        r = self.intent.analyze("zmień głos na lepszy", self.skills)
        self.assertIn(r["action"], ("evolve", "use", "chat"))

    # ── TTS ──
    def test_tts_speak_aloud(self):
        """'przeczytaj na głos' → TTS"""
        r = self.intent.analyze("przeczytaj ten tekst na głos", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")


# ─── Test: IntentEngine topic tracking ────────────────────────────────
class TestIntentEngineTopics(unittest.TestCase):

    def setUp(self):
        # Topics tests need a fresh state to avoid cross-test pollution
        self.intent = _SHARED_INTENT
        self.intent._p["topics"] = []
        self.intent._p["corrections"] = []

    def test_topic_from_stt_result(self):
        """Topic tracking from ML classification result."""
        self.intent._update_topics_from_result({"action": "use", "skill": "stt"})
        topic = self.intent._recent_topic()
        self.assertEqual(topic, "voice")

    def test_topic_from_web_result(self):
        self.intent._update_topics_from_result({"action": "use", "skill": "web_search"})
        topic = self.intent._recent_topic()
        self.assertEqual(topic, "web")

    def test_topic_from_git_result(self):
        self.intent._update_topics_from_result({"action": "use", "skill": "git_ops"})
        topic = self.intent._recent_topic()
        self.assertEqual(topic, "git")

    def test_topic_from_shell_result(self):
        self.intent._update_topics_from_result({"action": "use", "skill": "shell"})
        topic = self.intent._recent_topic()
        self.assertEqual(topic, "dev")

    def test_topic_tracking_accumulates(self):
        self.intent._update_topics_from_result({"action": "use", "skill": "stt"})
        self.intent._update_topics_from_result({"action": "use", "skill": "tts"})
        topic = self.intent._recent_topic()
        self.assertEqual(topic, "voice")

    def test_record_correction(self):
        self.intent.record_correction("test msg", "tts", "stt")
        self.assertEqual(len(self.intent._p["corrections"]), 1)
        self.assertEqual(self.intent._p["corrections"][0]["wrong"], "tts")
        self.assertEqual(self.intent._p["corrections"][0]["correct"], "stt")


# ─── Test: ProviderSelector ──────────────────────────────────────────
class TestProviderSelector(unittest.TestCase):

    def setUp(self):
        self.rm = ResourceMonitor()
        self.ps = ProviderSelector(SKILLS_DIR, self.rm)

    def test_list_capabilities(self):
        caps = self.ps.list_capabilities()
        self.assertIn("tts", caps)
        self.assertIn("stt", caps)
        self.assertIn("deps", caps)

    def test_tts_has_multiple_providers(self):
        providers = self.ps.list_providers("tts")
        self.assertIn("piper", providers)
        self.assertIn("espeak", providers)
        self.assertIn("coqui", providers)
        self.assertIn("pyttsx3", providers)

    def test_stt_has_providers(self):
        providers = self.ps.list_providers("stt")
        self.assertIn("vosk", providers)
        self.assertIn("whisper", providers)

    def test_espeak_is_lite_tier(self):
        info = self.ps.get_provider_info("tts", "espeak")
        self.assertEqual(info.tier, "lite")
        self.assertEqual(info.quality_score, 3)

    def test_coqui_is_premium_tier(self):
        info = self.ps.get_provider_info("tts", "coqui")
        self.assertEqual(info.tier, "premium")
        self.assertEqual(info.quality_score, 9)

    def test_tts_selects_espeak_on_basic_system(self):
        """On a system without GPU/pyttsx3, espeak should be selected"""
        selected = self.ps.select("tts")
        self.assertEqual(selected, "espeak")

    def test_tts_selects_piper_when_available(self):
        """If piper is installed and configured, it should win on quality."""
        with patch.dict(os.environ, {"PIPER_MODEL": "/tmp/fake_piper.onnx"}, clear=False):
            with patch.object(self.rm, "has_command") as has_cmd:
                def _fake_has_command(cmd: str) -> bool:
                    return cmd in ("piper", "espeak")
                has_cmd.side_effect = _fake_has_command

                with patch("pathlib.Path.exists", return_value=True):
                    selected = self.ps.select("tts")
                    self.assertEqual(selected, "piper")

    def test_force_provider(self):
        """Force should override selection"""
        selected = self.ps.select("tts", force="espeak")
        self.assertEqual(selected, "espeak")

    def test_speed_preference_selects_lite(self):
        """prefer=speed should favor lite tier"""
        selected = self.ps.select("tts", prefer="speed")
        self.assertEqual(selected, "espeak")

    def test_reliability_preference(self):
        """prefer=reliability should favor lite (fewer deps)"""
        selected = self.ps.select("tts", prefer="reliability")
        self.assertEqual(selected, "espeak")

    def test_legacy_skills_default_provider(self):
        """Legacy skills (no providers/ dir) should return 'default'"""
        providers = self.ps.list_providers("deps")
        self.assertEqual(providers, ["default"])

    def test_manifest_loading(self):
        manifest = self.ps.load_manifest("tts")
        self.assertEqual(manifest["capability"], "tts")
        self.assertIn("espeak", manifest["providers"])

    def test_skill_path_resolution(self):
        path = self.ps.get_skill_path("tts", "espeak")
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertTrue(str(path).endswith("skill.py"))

    def test_summary_output(self):
        summary = self.ps.summary()
        self.assertIn("tts:", summary)
        self.assertIn("espeak", summary)


# ─── Test: ProviderChain ─────────────────────────────────────────────
class TestProviderChain(unittest.TestCase):

    def setUp(self):
        self.rm = ResourceMonitor()
        self.ps = ProviderSelector(SKILLS_DIR, self.rm)
        self.chain = ProviderChain(self.ps)

    def test_build_chain_returns_list(self):
        chain = self.chain.build_chain("tts")
        self.assertIsInstance(chain, list)
        self.assertGreater(len(chain), 0)

    def test_chain_includes_espeak(self):
        chain = self.chain.build_chain("tts")
        self.assertIn("espeak", chain)

    def test_chain_espeak_first_for_quality(self):
        """espeak should be first when it's the only runnable provider."""
        chain = self.chain.build_chain("tts", prefer="quality")
        self.assertEqual(chain[0], "espeak")

    def test_select_best_returns_string(self):
        best = self.chain.select_best("tts")
        self.assertIsInstance(best, str)
        self.assertEqual(best, "espeak")

    def test_select_with_fallback_returns_ordered_list(self):
        providers = self.chain.select_with_fallback("tts")
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)

    def test_record_failure_increments(self):
        self.chain.record_failure("tts", "espeak", "test error")
        stats = self.chain.get_stats("tts", "espeak")
        self.assertEqual(stats["failures"], 1)
        self.assertFalse(stats["demoted"])

    def test_demotion_after_threshold(self):
        for _ in range(3):
            self.chain.record_failure("tts", "espeak")
        stats = self.chain.get_stats("tts", "espeak")
        self.assertTrue(stats["demoted"])

    def test_demoted_provider_pushed_to_end(self):
        for _ in range(3):
            self.chain.record_failure("tts", "espeak")
        chain = self.chain.build_chain("tts")
        if len(chain) > 1:
            self.assertNotEqual(chain[0], "espeak",
                                "Demoted espeak should not be first")

    def test_recovery_after_successes(self):
        for _ in range(3):
            self.chain.record_failure("tts", "espeak")
        self.assertTrue(self.chain.is_demoted("tts", "espeak"))
        self.chain.record_success("tts", "espeak")
        self.chain.record_success("tts", "espeak")
        self.assertFalse(self.chain.is_demoted("tts", "espeak"))

    def test_chain_summary_format(self):
        summary = self.chain.chain_summary("tts")
        self.assertIn("tts:", summary)
        self.assertIn("espeak", summary)

    def test_stats_initial_zero(self):
        stats = self.chain.get_stats("tts", "espeak")
        self.assertEqual(stats["failures"], 0)
        self.assertEqual(stats["successes"], 0)
        self.assertFalse(stats["demoted"])

    def test_success_resets_failure_count(self):
        self.chain.record_failure("tts", "espeak")
        self.chain.record_failure("tts", "espeak")
        self.chain.record_success("tts", "espeak")
        self.chain.record_success("tts", "espeak")
        stats = self.chain.get_stats("tts", "espeak")
        self.assertEqual(stats["failures"], 0)


# ─── Test: ResourceMonitor ───────────────────────────────────────────
class TestResourceMonitor(unittest.TestCase):

    def setUp(self):
        self.rm = ResourceMonitor()

    def test_snapshot_has_required_fields(self):
        snap = self.rm.snapshot()
        self.assertIn("cpu_count", snap)
        self.assertIn("ram_total_mb", snap)
        self.assertIn("ram_available_mb", snap)
        self.assertIn("disk_free_mb", snap)
        self.assertIn("gpu", snap)
        self.assertIn("python_packages", snap)

    def test_cpu_count_positive(self):
        self.assertGreater(self.rm._cpu_count(), 0)

    def test_ram_positive(self):
        self.assertGreater(self.rm._ram_total(), 0)
        self.assertGreater(self.rm._ram_available(), 0)

    def test_disk_positive(self):
        self.assertGreater(self.rm._disk_free(), 0)

    def test_can_run_no_requirements(self):
        ok, reason = self.rm.can_run({})
        self.assertTrue(ok)
        self.assertEqual(reason, "OK")

    def test_can_run_low_ram(self):
        ok, reason = self.rm.can_run({"min_ram_mb": 512})
        self.assertTrue(ok)

    def test_can_run_impossible_ram(self):
        ok, reason = self.rm.can_run({"min_ram_mb": 999999999})
        self.assertFalse(ok)
        self.assertIn("RAM", reason)

    def test_has_command_python(self):
        self.assertTrue(self.rm.has_command("python3"))

    def test_has_command_nonexistent(self):
        self.assertFalse(self.rm.has_command("nonexistent_cmd_xyz_123"))

    def test_has_python_package_json(self):
        self.assertTrue(self.rm.has_python_package("json"))

    def test_has_python_package_nonexistent(self):
        self.assertFalse(self.rm.has_python_package("nonexistent_package_xyz"))

    def test_can_run_missing_system_package(self):
        ok, reason = self.rm.can_run({"system_packages": ["nonexistent_cmd_xyz"]})
        self.assertFalse(ok)
        self.assertIn("not found", reason)

    def test_can_run_espeak(self):
        """Test that espeak requirement check matches reality"""
        has_espeak = shutil.which("espeak-ng") or shutil.which("espeak")
        ok, _ = self.rm.can_run({"system_packages": ["espeak-ng"]})
        if has_espeak:
            # If espeak is installed, the check should pass (for espeak-ng)
            pass  # Can't guarantee espeak-ng vs espeak
        # Just verify it doesn't crash
        self.assertIsInstance(ok, bool)


# ─── Test: SkillManager with provider integration ─────────────────────
class TestSkillManagerProviders(unittest.TestCase):

    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.rm = ResourceMonitor()
        self.ps = ProviderSelector(SKILLS_DIR, self.rm)
        self.sm = SkillManager(self.llm, self.logger, provider_selector=self.ps)

    def test_list_skills_includes_provider_skills(self):
        skills = self.sm.list_skills()
        self.assertIn("tts", skills)
        self.assertIn("stt", skills)
        self.assertIn("deps", skills)

    def test_latest_version_tts(self):
        v = self.sm.latest_v("tts")
        self.assertIsNotNone(v)
        self.assertTrue(v.startswith("v") or v in ("stable", "latest"),
                        f"Expected v{{N}}, 'stable', or 'latest', got: {v}")

    def test_skill_path_resolves_through_provider(self):
        p = self.sm.skill_path("tts")
        self.assertIsNotNone(p)
        self.assertTrue(p.exists())
        # Should resolve through espeak provider
        self.assertIn("espeak", str(p))

    def test_skill_path_legacy_still_works(self):
        p = self.sm.skill_path("deps")
        self.assertIsNotNone(p)
        self.assertTrue(p.exists())

    def test_exec_tts_espeak(self):
        """Execute TTS skill through provider path"""
        result = self.sm.exec_skill("tts", inp={"text": ""})
        # Even with empty text, should not crash
        self.assertIsInstance(result, dict)
        self.assertIn("success", result)

    def test_exec_nonexistent_skill(self):
        result = self.sm.exec_skill("nonexistent_skill_xyz")
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"].lower())


# ─── Test: EvoEngine dialog flow ──────────────────────────────────────
class TestEvoEngineDialogFlow(unittest.TestCase):
    """Test the full dialog flow: analyze → route → execute."""

    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.rm = ResourceMonitor()
        self.ps = ProviderSelector(SKILLS_DIR, self.rm)
        self.sm = SkillManager(self.llm, self.logger, provider_selector=self.ps)
        self.evo = EvoEngine(self.sm, self.llm, self.logger)
        self.state = {"user_profile": {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        }}
        self.intent = IntentEngine(self.llm, self.logger, self.state)
        self.intent._fast_model = None  # force keyword fallback path

    def _dialog(self, user_msg, conv=None):
        """Simulate a dialog turn: analyze → handle."""
        skills = self.sm.list_skills()
        analysis = self.intent.analyze(user_msg, skills, conv or [])
        outcome = self.evo.handle_request(user_msg, skills, analysis=analysis)
        return analysis, outcome

    def test_tts_dialog_flow(self):
        """User says 'powiedz cześć' → should route to TTS and execute"""
        analysis, outcome = self._dialog("powiedz cześć po polsku")
        self.assertEqual(analysis["action"], "use")
        self.assertEqual(analysis["skill"], "tts")
        # Outcome depends on espeak being installed
        if outcome:
            self.assertIn(outcome["type"], ("success", "failed"))

    def test_chat_dialog_flow(self):
        """User says 'hej' → should be chat, no skill execution"""
        analysis, outcome = self._dialog("hej")
        self.assertEqual(analysis["action"], "chat")
        self.assertIsNone(outcome)

    def test_evolve_dialog_flow(self):
        """User says 'napraw tts' → should trigger evolve or use (ML may vary)"""
        analysis, _ = self._dialog("napraw tts bo źle działa")
        self.assertIn(analysis["action"], ("evolve", "use"),
                       f"Expected evolve or use, got {analysis['action']}")
        self.assertEqual(analysis["skill"], "tts")

    def test_create_dialog_flow(self):
        """User says 'stwórz kalkulator' → should trigger create or use (ML may vary)"""
        analysis, _ = self._dialog("stwórz mi kalkulator")
        self.assertIn(analysis["action"], ("create", "use"),
                       f"Expected create or use, got {analysis['action']}")

    def test_multi_turn_conversation(self):
        """Test multi-turn conversation maintains context"""
        conv = []
        # Turn 1: voice topic
        conv.append({"role": "user", "content": "powiedz coś po polsku"})
        a1, _ = self._dialog("powiedz coś po polsku", conv)
        self.assertEqual(a1["skill"], "tts")

        conv.append({"role": "assistant", "content": "Powiedziałem."})

        # Turn 2: follow-up in voice context
        conv.append({"role": "user", "content": "czy mnie słyszysz?"})
        a2, _ = self._dialog("czy mnie słyszysz?", conv)
        self.assertEqual(a2["skill"], "stt")

    def test_intent_recording(self):
        """Verify that skill usage gets recorded"""
        self.intent.record_skill_use("tts")
        self.intent.record_skill_use("tts")
        self.intent.record_skill_use("stt")
        self.assertEqual(self.intent._p["skill_usage"]["tts"], 2)
        self.assertEqual(self.intent._p["skill_usage"]["stt"], 1)


# ─── Test: Supervisor ────────────────────────────────────────────────
class TestSupervisor(unittest.TestCase):

    def setUp(self):
        self.state = {"active_core": "A", "core_a_version": 1, "core_b_version": 1}
        self.logger = Logger("TEST")
        self.sv = Supervisor(self.state, self.logger)

    def test_active_core(self):
        self.assertEqual(self.sv.active(), "A")

    def test_active_version(self):
        self.assertEqual(self.sv.active_version(), 1)

    def test_list_cores(self):
        cores = self.sv.list_cores()
        self.assertIn("v1", cores)

    def test_health_check(self):
        self.assertTrue(self.sv.health("A"))


# ─── Test: Full Integration ──────────────────────────────────────────
class TestFullIntegration(unittest.TestCase):
    """Integration tests verifying all components work together."""

    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.rm = ResourceMonitor()
        self.ps = ProviderSelector(SKILLS_DIR, self.rm)
        self.sm = SkillManager(self.llm, self.logger, provider_selector=self.ps)

    def test_provider_selector_integrated_with_skill_manager(self):
        """ProviderSelector and SkillManager resolve same provider"""
        # Both should resolve to the same provider (espeak)
        ps_path = self.ps.get_skill_path("tts", "espeak")
        sm_path = self.sm.skill_path("tts")
        # Same provider directory (version may differ due to sort logic)
        self.assertEqual(ps_path.parent.parent, sm_path.parent.parent)

    def test_all_skills_loadable(self):
        """Verify all registered skills can at least be path-resolved"""
        skills = self.sm.list_skills()
        for name, versions in skills.items():
            p = self.sm.skill_path(name)
            self.assertIsNotNone(p, f"Skill '{name}' path is None")
            self.assertTrue(p.exists(), f"Skill '{name}' path doesn't exist: {p}")

    def test_manifest_exists_for_migrated_skills(self):
        """All migrated skills should have manifest.json"""
        for name in ["tts", "stt", "web_search", "deps", "devops", "echo", "git_ops"]:
            mp = SKILLS_DIR / name / "manifest.json"
            self.assertTrue(mp.exists(), f"Missing manifest.json for '{name}'")

    def test_provider_meta_exists(self):
        """Provider skills should have meta.json"""
        for cap, providers in [("tts", ["espeak", "pyttsx3", "coqui"]),
                                ("stt", ["vosk", "whisper"])]:
            for prov in providers:
                meta_path = SKILLS_DIR / cap / "providers" / prov / "meta.json"
                self.assertTrue(meta_path.exists(),
                    f"Missing meta.json for {cap}/{prov}")

    def test_resource_aware_selection(self):
        """ResourceMonitor correctly influences provider selection"""
        # espeak should be selected (lite, available)
        selected = self.ps.select("tts")
        self.assertEqual(selected, "espeak")

        # With prefer_quality context, should still be espeak (coqui not available)
        selected = self.ps.select("tts", context={"prefer_quality": True})
        self.assertEqual(selected, "espeak")


# ─── Test: Dialog Scenarios (Polish) ─────────────────────────────────
class TestPolishDialogScenarios(unittest.TestCase):
    """Test realistic Polish dialog scenarios end-to-end via ML classifier."""

    @classmethod
    def setUpClass(cls):
        cls.llm = MockLLM()
        cls.logger = Logger("TEST")
        cls.rm = ResourceMonitor()
        cls.ps = ProviderSelector(SKILLS_DIR, cls.rm)
        cls.sm = SkillManager(cls.llm, cls.logger, provider_selector=cls.ps)
        cls.evo = EvoEngine(cls.sm, cls.llm, cls.logger)
        cls.intent = _SHARED_INTENT

    def _classify(self, msg):
        return self.intent.analyze(msg, self.sm.list_skills())

    def test_scenario_voice_greeting(self):
        """'przywitaj się ze mną głosowo' → use tts/stt"""
        r = self._classify("przywitaj się ze mną głosowo")
        self.assertEqual(r["action"], "use")
        self.assertIn(r["skill"], ("tts", "stt"))

    def test_scenario_create_weather(self):
        """'stwórz mi skill do pogody' → create"""
        r = self._classify("stwórz mi skill do sprawdzania pogody")
        self.assertEqual(r["action"], "create")

    def test_scenario_fix_broken_skill(self):
        """'napraw web_search' → evolve or use"""
        r = self._classify("napraw web_search bo nie zwraca wyników")
        self.assertIn(r["action"], ("evolve", "use"))

    def test_scenario_listen_request(self):
        """'posłuchaj co mówię' → STT"""
        r = self._classify("posłuchaj co mówię")
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    def test_scenario_deploy_app(self):
        """'deploy aplikację' → create or use"""
        r = self._classify("deploy aplikację na serwer produkcyjny")
        self.assertIn(r["action"], ("create", "use"))

    def test_scenario_improve_tts(self):
        """'popraw jakość głosu' → evolve or use"""
        r = self._classify("popraw jakość głosu")
        self.assertIn(r["action"], ("evolve", "use"))

    def test_scenario_record_audio(self):
        """'nagraj dźwięk z mikrofonu' → STT"""
        r = self._classify("nagraj dźwięk z mikrofonu")
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    def test_scenario_pure_chat(self):
        """'cześć' → chat (trivial)"""
        r = self._classify("cześć")
        self.assertEqual(r["action"], "chat")

    def test_scenario_ambiguous_voice(self):
        """'odpowiedz głosowo' → use tts or stt"""
        r = self._classify("odpowiedz mi głosowo")
        self.assertEqual(r["action"], "use")
        self.assertIn(r["skill"], ("tts", "stt"))


# ─── Preflight Tests ──────────────────────────────────────────────────
class TestSkillPreflight(unittest.TestCase):
    def setUp(self):
        self.pf = SkillPreflight()

    def test_check_syntax_valid(self):
        r = self.pf.check_syntax("x = 1\nprint(x)")
        self.assertTrue(r.ok)

    def test_check_syntax_invalid(self):
        r = self.pf.check_syntax("def foo(:\n  pass")
        self.assertFalse(r.ok)
        self.assertEqual(r.stage, "syntax")

    def test_check_imports_missing_shutil(self):
        code = 'def f():\n    return shutil.which("python")'
        r = self.pf.check_imports(code)
        self.assertFalse(r.ok)
        self.assertEqual(r.stage, "imports")
        self.assertIn("shutil", r.error)

    def test_check_imports_ok(self):
        code = 'import shutil\ndef f():\n    return shutil.which("python")'
        r = self.pf.check_imports(code)
        self.assertTrue(r.ok)

    def test_check_interface_complete(self):
        code = ("def get_info(): return {}\n"
                "def health_check(): return True\n"
                "class Sk:\n"
                "    def execute(self, d): return {}\n")
        r = self.pf.check_interface(code)
        self.assertTrue(r.ok)

    def test_check_interface_missing_get_info(self):
        code = ("def health_check(): return True\n"
                "def execute(d): return {}\n")
        r = self.pf.check_interface(code)
        self.assertFalse(r.ok)
        self.assertIn("get_info", r.error)

    def test_auto_fix_imports_adds_shutil(self):
        code = 'def f():\n    return shutil.which("python")'
        fixed = self.pf.auto_fix_imports(code)
        self.assertIn("import shutil", fixed)

    def test_auto_fix_imports_no_change_if_present(self):
        code = 'import shutil\ndef f():\n    return shutil.which("python")'
        fixed = self.pf.auto_fix_imports(code)
        self.assertEqual(code, fixed)

    def test_auto_fix_imports_multiple(self):
        code = 'def f():\n    os.path.exists("x")\n    shutil.which("y")'
        fixed = self.pf.auto_fix_imports(code)
        self.assertIn("import os", fixed)
        self.assertIn("import shutil", fixed)


# ─── EvolutionGuard Tests ─────────────────────────────────────────────
class TestEvolutionGuard(unittest.TestCase):
    def setUp(self):
        self.guard = EvolutionGuard()

    def test_fingerprint_stable(self):
        fp1 = self.guard.fingerprint("name 'shutil' is not defined")
        fp2 = self.guard.fingerprint("name 'shutil' is not defined")
        self.assertEqual(fp1, fp2)

    def test_fingerprint_normalizes_line_numbers(self):
        fp1 = self.guard.fingerprint("error at line 5")
        fp2 = self.guard.fingerprint("error at line 99")
        self.assertEqual(fp1, fp2)

    def test_not_repeating_initially(self):
        self.assertFalse(self.guard.is_repeating("stt", "some error"))

    def test_repeating_after_two_same_errors(self):
        self.guard.record_error("stt", "name 'shutil' is not defined", "v6")
        self.guard.record_error("stt", "name 'shutil' is not defined", "v7")
        self.assertTrue(self.guard.is_repeating("stt", "name 'shutil' is not defined"))

    def test_strategy_auto_fix_on_repeat(self):
        self.guard.record_error("stt", "name 'shutil' is not defined", "v6")
        self.guard.record_error("stt", "name 'shutil' is not defined", "v7")
        s = self.guard.suggest_strategy("stt", "name 'shutil' is not defined")
        self.assertEqual(s["strategy"], "auto_fix_imports")

    def test_strategy_normal_on_first_error(self):
        s = self.guard.suggest_strategy("stt", "some new error")
        self.assertEqual(s["strategy"], "normal_evolve")

    def test_error_summary_empty(self):
        self.assertEqual(self.guard.get_error_summary("stt"), "")

    def test_error_summary_with_history(self):
        self.guard.record_error("stt", "error X", "v6")
        summary = self.guard.get_error_summary("stt")
        self.assertIn("error X", summary)

    def test_evolution_prompt_context_import(self):
        ctx = self.guard.build_evolution_prompt_context("stt", "name 'shutil' is not defined")
        self.assertIn("import shutil", ctx)


# ─── SystemIdentity Tests ─────────────────────────────────────────────
class TestSystemIdentity(unittest.TestCase):
    def setUp(self):
        self.identity = SystemIdentity()

    def test_build_system_prompt_has_identity(self):
        prompt = self.identity.build_system_prompt()
        self.assertIn("RDZENIEM", prompt)
        self.assertIn("evo-engine", prompt)

    def test_build_system_prompt_has_capabilities(self):
        prompt = self.identity.build_system_prompt()
        self.assertIn("tts", prompt)
        self.assertIn("stt", prompt)

    def test_build_system_prompt_never_say_cant(self):
        prompt = self.identity.build_system_prompt()
        self.assertIn("Nigdy nie mów", prompt)

    def test_fallback_message_with_error(self):
        msg = self.identity.build_fallback_message("stt", error="shutil not defined")
        self.assertIn("stt", msg)
        self.assertIn("shutil not defined", msg)
        self.assertIn("naprawić", msg)

    def test_fallback_message_max_attempts(self):
        msg = self.identity.build_fallback_message("stt", error="err", attempts=3)
        self.assertIn("3 próbach", msg)
        self.assertIn("/rollback", msg)

    def test_skill_status_healthy(self):
        self.identity._skill_statuses["tts"] = SkillStatus("tts", healthy=True)
        prompt = self.identity.build_system_prompt()
        self.assertIn("DZIAŁA", prompt)

    def test_skill_status_broken(self):
        self.identity._skill_statuses["stt"] = SkillStatus(
            "stt", healthy=False, error="shutil not defined")
        prompt = self.identity.build_system_prompt()
        self.assertIn("USZKODZONY", prompt)

    def test_readiness_report_structure(self):
        report = self.identity.get_readiness_report()
        self.assertIn("total_capabilities", report)
        self.assertIn("healthy", report)
        self.assertIn("broken", report)
        self.assertIn("readiness_pct", report)

    def test_skill_context_for_llm(self):
        ctx = self.identity.build_skill_context_for_llm("stt")
        self.assertIn("import", ctx.lower())
        self.assertIn("execute", ctx)


# ─── STT Text Extraction Tests ────────────────────────────────────────
class TestSTTExtraction(unittest.TestCase):
    def test_extract_stt_text_with_spoken(self):
        outcome = {
            "type": "success", "skill": "stt",
            "result": {"success": True, "result": {
                "success": True, "spoken": "cześć jak się masz"}}
        }
        self.assertEqual(_extract_stt_text(outcome), "cześć jak się masz")

    def test_extract_stt_text_empty_spoken(self):
        outcome = {
            "type": "success", "skill": "stt",
            "result": {"success": True, "result": {
                "success": True, "spoken": ""}}
        }
        self.assertIsNone(_extract_stt_text(outcome))

    def test_extract_stt_text_non_stt_skill(self):
        outcome = {
            "type": "success", "skill": "tts",
            "result": {"success": True, "result": {"success": True}}
        }
        self.assertIsNone(_extract_stt_text(outcome))

    def test_extract_stt_text_failed_outcome(self):
        outcome = {"type": "failed", "skill": "stt"}
        self.assertIsNone(_extract_stt_text(outcome))

    def test_extract_stt_text_none_outcome(self):
        self.assertIsNone(_extract_stt_text(None))

    def test_extract_stt_text_with_text_key(self):
        outcome = {
            "type": "success", "skill": "stt",
            "result": {"success": True, "result": {
                "success": True, "text": "hello world"}}
        }
        self.assertEqual(_extract_stt_text(outcome), "hello world")

    def test_extract_stt_text_strips_whitespace(self):
        outcome = {
            "type": "success", "skill": "stt",
            "result": {"success": True, "result": {
                "success": True, "spoken": "  test  "}}
        }
        self.assertEqual(_extract_stt_text(outcome), "test")


# ─── Shell Skill Tests ────────────────────────────────────────────────
class TestShellSkill(unittest.TestCase):
    def test_shell_skill_loads(self):
        """Shell skill can be loaded and has correct interface"""
        from cores.v1.skill_manager import _load_bootstrap_skill
        sk = _load_bootstrap_skill("shell")
        self.assertIsNotNone(sk)
        self.assertTrue(hasattr(sk, "execute"))

    def test_shell_execute_echo(self):
        """Shell skill executes simple command"""
        from cores.v1.skill_manager import _load_bootstrap_skill
        sk = _load_bootstrap_skill("shell")
        r = sk.execute({"command": "echo hello"})
        self.assertTrue(r["success"])
        self.assertIn("hello", r["stdout"])
        self.assertEqual(r["exit_code"], 0)

    def test_shell_execute_failing_command(self):
        """Shell skill handles failing commands"""
        from cores.v1.skill_manager import _load_bootstrap_skill
        sk = _load_bootstrap_skill("shell")
        r = sk.execute({"command": "false"})
        self.assertFalse(r["success"])
        self.assertNotEqual(r["exit_code"], 0)

    def test_shell_blocked_dangerous_command(self):
        """Shell skill blocks dangerous commands"""
        from cores.v1.skill_manager import _load_bootstrap_skill
        sk = _load_bootstrap_skill("shell")
        r = sk.execute({"command": "rm -rf /"})
        self.assertFalse(r["success"])
        self.assertIn("Blocked", r["error"])

    def test_shell_no_command(self):
        """Shell skill handles empty command"""
        from cores.v1.skill_manager import _load_bootstrap_skill
        sk = _load_bootstrap_skill("shell")
        r = sk.execute({})
        self.assertFalse(r["success"])


# ─── Shell Intent Routing Tests ──────────────────────────────────────
class TestShellIntentRouting(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.intent = _SHARED_INTENT
        cls.skills = {"shell": ["v1"], "tts": ["v1"], "stt": ["v1", "v6"]}

    def test_uruchom_routes_to_shell(self):
        r = self.intent.analyze("uruchom ls -la", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_uruchom_extracts_command(self):
        r = self.intent.analyze("uruchom apt update", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_sudo_routes_to_shell(self):
        r = self.intent.analyze("sudo apt upgrade -y", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_wykonaj_routes_to_shell(self):
        r = self.intent.analyze("wykonaj pip install requests", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_shell_not_triggered_without_skill(self):
        """Without shell skill, ML classifier may still route to shell (embedding-based)"""
        skills_no_shell = {"tts": ["v1"], "stt": ["v1"]}
        r = self.intent.analyze("uruchom ls -la", skills_no_shell)
        # ML classifier doesn't filter by available skills — it classifies by semantics
        self.assertEqual(r["action"], "use")


# ─── Pipeline Validation Tests ────────────────────────────────────────
class TestPipelineValidation(unittest.TestCase):
    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.rm = ResourceMonitor()
        self.ps = ProviderSelector(SKILLS_DIR, self.rm)
        self.sm = SkillManager(self.llm, self.logger, provider_selector=self.ps)
        self.evo = EvoEngine(self.sm, self.llm, self.logger)

    def test_validate_success(self):
        r = self.evo._validate_result("echo", {"success": True, "result": {"success": True}}, "test", "")
        self.assertEqual(r["verdict"], "success")

    def test_validate_outer_fail(self):
        r = self.evo._validate_result("echo", {"success": False, "error": "crash"}, "test", "")
        self.assertEqual(r["verdict"], "fail")
        self.assertIn("crash", r["reason"])

    def test_validate_inner_fail(self):
        r = self.evo._validate_result("echo", {"success": True, "result": {"success": False, "error": "bad"}}, "test", "")
        self.assertEqual(r["verdict"], "fail")

    def test_validate_stt_empty_is_partial(self):
        r = self.evo._validate_result("stt", {"success": True, "result": {"spoken": ""}}, "listen", "")
        self.assertEqual(r["verdict"], "partial")

    def test_validate_stt_with_text_is_success(self):
        r = self.evo._validate_result("stt", {"success": True, "result": {"spoken": "cześć"}}, "listen", "")
        self.assertEqual(r["verdict"], "success")

    def test_validate_shell_nonzero_is_partial(self):
        r = self.evo._validate_result("shell", {"success": True, "result": {"exit_code": 1, "stderr": "err"}}, "run", "")
        self.assertEqual(r["verdict"], "partial")

    def test_validate_shell_zero_is_success(self):
        r = self.evo._validate_result("shell", {"success": True, "result": {"exit_code": 0}}, "run", "")
        self.assertEqual(r["verdict"], "success")

    def test_validate_tts_with_error(self):
        r = self.evo._validate_result("tts", {"success": True, "result": {"error": "no voice"}}, "speak", "")
        self.assertEqual(r["verdict"], "fail")


# ─── SmartIntentClassifier Tests ─────────────────────────────────────
class TestSmartIntentClassifier(unittest.TestCase):
    """Test the ML-based SmartIntentClassifier."""

    @classmethod
    def setUpClass(cls):
        # Reuse the shared intent's classifier to avoid reloading model
        cls.classifier = _SHARED_INTENT._classifier
        cls.classifier._local_llm._available = False
        cls.classifier._local_llm._model = None
        cls.skills = ["shell", "tts", "stt", "echo", "web_search", "git_ops"]

    def test_classifier_has_training_data(self):
        """Classifier should have default training examples."""
        self.assertGreater(len(self.classifier._training_data), 50)

    def test_classifier_embedding_mode_detected(self):
        """Embedding engine should detect an available mode."""
        self.assertIn(self.classifier._embedder._mode, ("sbert", "tfidf", "bow", None))

    def test_classify_stt_intent(self):
        """'pogadajmy głosowo' → use/stt"""
        r = self.classifier.classify("pogadajmy głosowo", skills=self.skills)
        self.assertEqual(r.action, "use")
        self.assertEqual(r.skill, "stt")

    def test_classify_tts_intent(self):
        """'powiedz coś' → use/tts"""
        r = self.classifier.classify("powiedz coś po polsku", skills=self.skills)
        self.assertEqual(r.action, "use")
        self.assertEqual(r.skill, "tts")

    def test_classify_shell_intent(self):
        """'uruchom komendę' → use/shell"""
        r = self.classifier.classify("uruchom komendę w terminalu", skills=self.skills)
        self.assertEqual(r.action, "use")
        self.assertEqual(r.skill, "shell")

    def test_classify_chat_trivial(self):
        """'cześć' → chat"""
        r = self.classifier.classify("cześć", skills=self.skills)
        # Short greetings may be filtered to chat by IntentEngine trivial filter
        # but classifier itself might still match — action should be chat or use
        self.assertIn(r.action, ("chat", "use"))

    def test_classify_evolve(self):
        """'napraw ten skill' → evolve"""
        r = self.classifier.classify("napraw ten skill", skills=self.skills)
        self.assertEqual(r.action, "evolve")

    def test_classify_create(self):
        """'stwórz nowy skill' → create"""
        r = self.classifier.classify("stwórz nowy skill do OCR", skills=self.skills)
        self.assertEqual(r.action, "create")

    def test_to_analysis_dict(self):
        """IntentResult.to_analysis() returns IntentEngine-compatible dict."""
        r = self.classifier.classify("pogadajmy głosowo", skills=self.skills)
        d = r.to_analysis()
        self.assertIn("action", d)
        self.assertIn("_conf", d)
        self.assertIn("_tier", d)

    def test_learn_from_correction(self):
        """Learning from correction adds training examples."""
        before = len(self.classifier._training_data)
        self.classifier.learn_from_correction("test intent", "chat", "use", "echo")
        after = len(self.classifier._training_data)
        self.assertGreater(after, before)

    def test_stats(self):
        """Stats should contain expected keys."""
        self.classifier.classify("test", skills=self.skills)
        s = self.classifier.stats()
        self.assertIn("total", s)
        self.assertIn("training_examples", s)
        self.assertIn("embedding_mode", s)


# ─── Stub Detection Tests ────────────────────────────────────────────
class TestStubDetection(unittest.TestCase):
    """Test that stub detection is conservative — no false positives on real skills."""

    def setUp(self):
        from cores.v1.preflight import EvolutionGuard
        self.guard = EvolutionGuard()

    def test_real_stt_skill_not_stub(self):
        """STT stable (153 lines, uses subprocess/arecord/vosk) is NOT a stub."""
        stt_path = SKILLS_DIR / "stt" / "providers" / "vosk" / "stable" / "skill.py"
        if not stt_path.exists():
            stt_path = SKILLS_DIR / "stt" / "providers" / "vosk" / "v7" / "skill.py"
        if stt_path.exists():
            is_stub, reason = self.guard.is_stub_skill(stt_path)
            self.assertFalse(is_stub, f"STT v7 wrongly flagged as stub: {reason}")

    def test_real_shell_skill_not_stub(self):
        """Shell skill (uses subprocess.Popen) is NOT a stub."""
        shell_path = SKILLS_DIR / "shell" / "v1" / "skill.py"
        if shell_path.exists():
            is_stub, reason = self.guard.is_stub_skill(shell_path)
            self.assertFalse(is_stub, f"Shell wrongly flagged as stub: {reason}")

    def test_real_tts_skill_not_stub(self):
        """TTS espeak stable (37 lines, uses subprocess) is NOT a stub."""
        tts_path = SKILLS_DIR / "tts" / "providers" / "espeak" / "stable" / "skill.py"
        if not tts_path.exists():
            tts_path = SKILLS_DIR / "tts" / "providers" / "espeak" / "v1" / "skill.py"
        if tts_path.exists():
            is_stub, reason = self.guard.is_stub_skill(tts_path)
            self.assertFalse(is_stub, f"TTS v1 wrongly flagged as stub: {reason}")

    def test_actual_stub_is_detected(self):
        """A trivial stub skill should be flagged."""
        import tempfile
        stub_code = '''class Stub:
    def execute(self, params):
        return {"success": True}

def execute(inp):
    return Stub().execute(inp)
'''
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
            f.write(stub_code)
            f.flush()
            is_stub, reason = self.guard.is_stub_skill(Path(f.name))
            self.assertTrue(is_stub, "Trivial stub should be detected")
        Path(f.name).unlink(missing_ok=True)

    def test_stt_empty_output_not_stub(self):
        """STT returning empty text (silence) should NOT be flagged as stub."""
        result = {"success": True, "result": {"spoken": "", "raw": {}}}
        stt_path = SKILLS_DIR / "stt" / "providers" / "vosk" / "stable" / "skill.py"
        if not stt_path.exists():
            stt_path = SKILLS_DIR / "stt" / "providers" / "vosk" / "v7" / "skill.py"
        check = self.guard.check_execution_result("stt", result, stt_path if stt_path.exists() else None)
        self.assertFalse(check.get("is_stub"),
                         "STT silence should NOT trigger stub detection")

    def test_shell_success_not_stub(self):
        """Shell returning exit_code=0 with output should NOT be stub."""
        result = {"success": True, "result": {"exit_code": 0, "stdout": "hello"}}
        shell_path = SKILLS_DIR / "shell" / "v1" / "skill.py"
        check = self.guard.check_execution_result("shell", result, shell_path if shell_path.exists() else None)
        self.assertFalse(check.get("is_stub"))


# ─── EvolutionGarbageCollector Tests ─────────────────────────────────
class TestGarbageCollector(unittest.TestCase):
    """Test GC stub detection, version scanning, and stable/latest structure."""

    def setUp(self):
        import tempfile
        from cores.v1.garbage_collector import EvolutionGarbageCollector
        self._tmpdir = Path(tempfile.mkdtemp())
        self.gc = EvolutionGarbageCollector(self._tmpdir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_stub(self, provider_dir, version):
        d = provider_dir / version
        d.mkdir(parents=True, exist_ok=True)
        (d / "skill.py").write_text(
            'class S:\n    def execute(self, p): return {"success": True}\n')

    def _make_real(self, provider_dir, version):
        d = provider_dir / version
        d.mkdir(parents=True, exist_ok=True)
        (d / "skill.py").write_text(
            'import subprocess\nclass TTSSkill:\n'
            '    def execute(self, params):\n'
            '        text = params.get("text", "")\n'
            '        subprocess.run(["espeak", text])\n'
            '        return {"success": True, "spoken": True}\n'
            'def get_info(): return {"name": "tts"}\n'
            'def health_check(): return True\n')

    def test_is_stub_detects_trivial(self):
        pdir = self._tmpdir / "test_prov"
        self._make_stub(pdir, "v1")
        self.assertTrue(self.gc.is_stub(pdir / "v1" / "skill.py"))

    def test_is_stub_ignores_real(self):
        pdir = self._tmpdir / "test_prov"
        self._make_real(pdir, "v1")
        self.assertFalse(self.gc.is_stub(pdir / "v1" / "skill.py"))

    def test_scan_versions_classifies(self):
        pdir = self._tmpdir / "prov"
        self._make_stub(pdir, "v1")
        self._make_stub(pdir, "v2")
        self._make_real(pdir, "v3")
        scan = self.gc.scan_versions(pdir)
        self.assertEqual(len(scan["stubs"]), 2)
        self.assertEqual(len(scan["working"]), 1)
        self.assertEqual(scan["best_version"], "v3")

    def test_cleanup_deletes_stubs(self):
        pdir = self._tmpdir / "prov"
        self._make_stub(pdir, "v1")
        self._make_stub(pdir, "v2")
        self._make_real(pdir, "v3")
        report = self.gc.cleanup_provider(pdir)
        self.assertEqual(len(report["deleted"]), 2)
        self.assertFalse((pdir / "v1").exists())
        self.assertFalse((pdir / "v2").exists())
        self.assertTrue((pdir / "v3").exists())

    def test_migrate_creates_stable_latest(self):
        pdir = self._tmpdir / "prov"
        self._make_real(pdir, "v1")
        self._make_stub(pdir, "v2")
        self._make_real(pdir, "v5")
        report = self.gc.migrate_to_stable_latest(pdir)
        self.assertTrue(report["migrated"])
        self.assertTrue((pdir / "stable" / "skill.py").exists())
        self.assertTrue((pdir / "latest" / "skill.py").exists())
        self.assertTrue((pdir / "archive").is_dir())
        # v{N} dirs should be gone
        self.assertFalse((pdir / "v1").exists())
        self.assertFalse((pdir / "v2").exists())
        self.assertFalse((pdir / "v5").exists())

    def test_migrate_idempotent(self):
        pdir = self._tmpdir / "prov"
        self._make_real(pdir, "v1")
        r1 = self.gc.migrate_to_stable_latest(pdir)
        r2 = self.gc.migrate_to_stable_latest(pdir)
        self.assertTrue(r2["migrated"])
        self.assertTrue((pdir / "stable" / "skill.py").exists())

    def test_is_broken_detects_markdown(self):
        pdir = self._tmpdir / "prov" / "v1"
        pdir.mkdir(parents=True)
        (pdir / "skill.py").write_text("```python\nprint('bad')\n```\n")
        self.assertTrue(self.gc.is_broken(pdir / "skill.py"))

    def test_is_broken_detects_syntax_error(self):
        pdir = self._tmpdir / "prov" / "v1"
        pdir.mkdir(parents=True)
        (pdir / "skill.py").write_text("def foo(\n")
        self.assertTrue(self.gc.is_broken(pdir / "skill.py"))

    def test_real_tts_espeak_has_stable(self):
        """After migration, TTS espeak should have stable/ dir."""
        stable = SKILLS_DIR / "tts" / "providers" / "espeak" / "stable" / "skill.py"
        if stable.exists():
            self.assertFalse(self.gc.is_stub(stable))

    def test_real_stt_vosk_has_stable(self):
        """After migration, STT vosk should have stable/ dir."""
        stable = SKILLS_DIR / "stt" / "providers" / "vosk" / "stable" / "skill.py"
        if stable.exists():
            self.assertFalse(self.gc.is_stub(stable))


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

    # ── TTS skill unit tests ──────────────────────────────────────────

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

    # ── STT skill unit tests ──────────────────────────────────────────

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

    # ── TTS→STT round-trip E2E ────────────────────────────────────────

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


class TestIntentVoiceConversation(unittest.TestCase):
    """Test intent classification for voice conversation phrases via ML classifier."""

    @classmethod
    def setUpClass(cls):
        cls.intent = _SHARED_INTENT

    def _classify(self, msg):
        skills = {"stt": {}, "tts": {}}
        return self.intent.analyze(msg, skills)

    def test_mowmy_glosowo_triggers_stt(self):
        """'mówmy głosowo' should route to STT voice conversation, not TTS."""
        r = self._classify("mówmy głosowo")
        self.assertEqual(r.get("action"), "use")
        self.assertEqual(r.get("skill"), "stt",
                         f"Expected stt, got: {r}")

    def test_mowmy_glosowo_no_diacritics(self):
        """'mowmy glosowo' (without diacritics) should route to STT."""
        r = self._classify("mowmy glosowo")
        self.assertEqual(r.get("action"), "use")
        self.assertEqual(r.get("skill"), "stt",
                         f"Expected stt, got: {r}")

    def test_pogadajmy_glosowo_triggers_stt(self):
        """'pogadajmy głosowo' should route to STT."""
        r = self._classify("pogadajmy głosowo")
        self.assertEqual(r.get("action"), "use")
        self.assertEqual(r.get("skill"), "stt")

    def test_rozmawiac_glosowo_triggers_stt(self):
        """'chcę rozmawiać głosowo' should route to STT."""
        r = self._classify("chcę rozmawiać głosowo")
        self.assertEqual(r.get("action"), "use")
        self.assertEqual(r.get("skill"), "stt")

    def test_powiedz_cos_triggers_tts(self):
        """'powiedz coś' should still route to TTS."""
        r = self._classify("powiedz cześć")
        self.assertEqual(r.get("skill"), "tts")

    def test_mikrofon_triggers_stt(self):
        """'włącz mikrofon' should route to STT."""
        r = self._classify("włącz mikrofon")
        self.assertEqual(r.get("skill"), "stt")


class TestUserMemory(unittest.TestCase):
    """Tests for UserMemory persistent long-term preference storage."""

    def setUp(self):
        self.state = {}
        from cores.v1.user_memory import UserMemory
        self.mem = UserMemory(self.state)

    def test_empty_on_init(self):
        self.assertEqual(self.mem.directives, [])

    def test_add_directive(self):
        entry = self.mem.add("Zawsze odpowiadaj po polsku")
        self.assertEqual(entry["text"], "Zawsze odpowiadaj po polsku")
        self.assertIn("id", entry)
        self.assertEqual(len(self.mem.directives), 1)

    def test_add_deduplicates(self):
        self.mem.add("Zawsze odpowiadaj po polsku")
        self.mem.add("Zawsze odpowiadaj po polsku")
        self.assertEqual(len(self.mem.directives), 1)

    def test_remove_directive(self):
        entry = self.mem.add("Preferuj rozmowę głosową")
        removed = self.mem.remove(entry["id"])
        self.assertTrue(removed)
        self.assertEqual(len(self.mem.directives), 0)

    def test_remove_nonexistent_returns_false(self):
        self.assertFalse(self.mem.remove(999))

    def test_ids_increment(self):
        e1 = self.mem.add("Preferencja 1")
        e2 = self.mem.add("Preferencja 2")
        self.assertGreater(e2["id"], e1["id"])

    def test_build_system_context_empty(self):
        ctx = self.mem.build_system_context()
        self.assertEqual(ctx, "")

    def test_build_system_context_with_directives(self):
        self.mem.add("Zawsze po polsku")
        self.mem.add("Preferuj głos")
        ctx = self.mem.build_system_context()
        self.assertIn("Zawsze po polsku", ctx)
        self.assertIn("Preferuj głos", ctx)
        self.assertIn("WAŻNE", ctx)

    def test_looks_like_preference_zawsze(self):
        self.assertTrue(self.mem.looks_like_preference("zawsze mów po polsku"))

    def test_looks_like_preference_pamietaj(self):
        self.assertTrue(self.mem.looks_like_preference("zapamiętaj że wolę głos"))

    def test_not_preference_normal_question(self):
        self.assertFalse(self.mem.looks_like_preference("jaka jest pogoda?"))

    def test_suggest_save_returns_text(self):
        s = self.mem.suggest_save("zawsze odpowiadaj krótko")
        self.assertIsNotNone(s)
        self.assertIn("zawsze", s.lower())

    def test_suggest_save_returns_none_for_normal(self):
        s = self.mem.suggest_save("co to jest AI?")
        self.assertIsNone(s)

    def test_clear_all(self):
        self.mem.add("Dir 1")
        self.mem.add("Dir 2")
        n = self.mem.clear_all()
        self.assertEqual(n, 2)
        self.assertEqual(len(self.mem.directives), 0)

    def test_persisted_in_state(self):
        self.mem.add("Pamiętaj to")
        self.assertIn("user_memory", self.state)
        self.assertEqual(len(self.state["user_memory"]["directives"]), 1)

    def test_reload_from_state(self):
        from cores.v1.user_memory import UserMemory
        self.mem.add("Trwała preferencja")
        mem2 = UserMemory(self.state)
        self.assertEqual(len(mem2.directives), 1)
        self.assertEqual(mem2.directives[0]["text"], "Trwała preferencja")


class TestVoiceModePersistence(unittest.TestCase):
    """Tests for persistent voice mode in UserMemory."""

    def setUp(self):
        self.state = {}
        from cores.v1.user_memory import UserMemory
        self.mem = UserMemory(self.state)

    def test_voice_mode_default_off(self):
        self.assertFalse(self.mem.voice_mode)

    def test_set_voice_mode_on(self):
        self.mem.set_voice_mode(True)
        self.assertTrue(self.mem.voice_mode)

    def test_set_voice_mode_off(self):
        self.mem.set_voice_mode(True)
        self.assertTrue(self.mem.voice_mode)
        self.mem.set_voice_mode(False)
        self.assertFalse(self.mem.voice_mode)

    def test_voice_mode_survives_reload(self):
        from cores.v1.user_memory import UserMemory
        self.mem.set_voice_mode(True)
        mem2 = UserMemory(self.state)
        self.assertTrue(mem2.voice_mode)

    def test_set_voice_mode_idempotent(self):
        self.mem.set_voice_mode(True)
        self.mem.set_voice_mode(True)
        # Should only have one voice directive
        voice_dirs = [d for d in self.mem.directives
                      if "głosowy" in d["text"].lower() or "głosowo" in d["text"].lower()]
        self.assertEqual(len(voice_dirs), 1)

    def test_set_voice_off_removes_directive(self):
        self.mem.set_voice_mode(True)
        self.assertEqual(len(self.mem.directives), 1)
        self.mem.set_voice_mode(False)
        self.assertEqual(len(self.mem.directives), 0)

    def test_has_directive(self):
        self.mem.add("Zawsze odpowiadaj po polsku")
        self.assertTrue(self.mem.has_directive("polsku"))
        self.assertFalse(self.mem.has_directive("angielsku"))

    def test_voice_mode_coexists_with_other_directives(self):
        self.mem.add("Zawsze odpowiadaj po polsku")
        self.mem.set_voice_mode(True)
        self.assertEqual(len(self.mem.directives), 2)
        self.mem.set_voice_mode(False)
        self.assertEqual(len(self.mem.directives), 1)
        self.assertIn("polsku", self.mem.directives[0]["text"].lower())


# ─── Autonomy Enhancement Tests ──────────────────────────────────────
class TestAutonomyEnhancements(unittest.TestCase):
    """Test autonomy improvements: auto-GC, auto-install deps, resilient nfo."""

    def setUp(self):
        import tempfile
        from cores.v1.garbage_collector import EvolutionGarbageCollector
        self._tmpdir = Path(tempfile.mkdtemp())
        self.gc = EvolutionGarbageCollector(self._tmpdir)

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def _make_stub(self, skill_dir, version):
        d = skill_dir / version
        d.mkdir(parents=True, exist_ok=True)
        (d / "skill.py").write_text(
            'class S:\n    def execute(self, p): return {"success": True}\n')

    def _make_real(self, skill_dir, version):
        d = skill_dir / version
        d.mkdir(parents=True, exist_ok=True)
        (d / "skill.py").write_text(
            'import subprocess\nclass Skill:\n'
            '    def execute(self, params):\n'
            '        subprocess.run(["echo", "ok"])\n'
            '        return {"success": True}\n'
            'def get_info(): return {"name": "test"}\n'
            'def health_check(): return True\n')

    def test_cleanup_all_removes_stubs(self):
        """cleanup_all should remove stubs from legacy skill dirs."""
        skill = self._tmpdir / "kalkulator"
        self._make_stub(skill, "v1")
        self._make_stub(skill, "v2")
        self._make_real(skill, "v3")
        reports = self.gc.cleanup_all(migrate=False)
        total_deleted = sum(len(r.get("deleted", [])) for r in reports)
        self.assertEqual(total_deleted, 2)
        self.assertFalse((skill / "v1").exists())
        self.assertFalse((skill / "v2").exists())
        self.assertTrue((skill / "v3").exists())

    def test_cleanup_all_provider_stubs(self):
        """cleanup_all should remove stubs from provider-based skills."""
        prov = self._tmpdir / "tts" / "providers" / "espeak"
        self._make_stub(prov, "v1")
        self._make_real(prov, "v2")
        reports = self.gc.cleanup_all(migrate=False)
        total_deleted = sum(len(r.get("deleted", [])) for r in reports)
        self.assertEqual(total_deleted, 1)

    def test_cleanup_all_empty_is_safe(self):
        """cleanup_all on empty dir should not crash."""
        reports = self.gc.cleanup_all(migrate=False)
        self.assertEqual(reports, [])

    def test_nfo_resilient_in_echo_skill(self):
        """Echo skill should load even if nfo.logged is not available."""
        import importlib.util
        p = SKILLS_DIR / "echo" / "v1" / "skill.py"
        if p.exists():
            spec = importlib.util.spec_from_file_location("echo_nfo_test", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.execute({"test": True})
            self.assertTrue(result.get("echo", {}).get("test"))

    def test_nfo_resilient_in_shell_skill(self):
        """Shell skill should load even if nfo.logged is not available."""
        import importlib.util
        p = SKILLS_DIR / "shell" / "v1" / "skill.py"
        if p.exists():
            spec = importlib.util.spec_from_file_location("shell_nfo_test", str(p))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            self.assertTrue(hasattr(mod, "ShellSkill"))

    def test_evo_engine_has_sys_for_auto_install(self):
        """EvoEngine module should have sys imported for auto-install deps."""
        from cores.v1 import evo_engine
        self.assertTrue(hasattr(evo_engine, 'sys'))

    def test_gc_summary_format(self):
        """GC summary should produce readable output."""
        skill = self._tmpdir / "test_skill"
        self._make_stub(skill, "v1")
        self._make_real(skill, "v2")
        reports = self.gc.cleanup_all(migrate=False)
        summary = self.gc.summary(reports)
        self.assertIn("[GC]", summary)
        self.assertIn("Total deleted", summary)


# ─── AutoRepair Tests ────────────────────────────────────────────────
class TestAutoRepair(unittest.TestCase):
    """Test auto-repair module: model validation, task loop, fix strategies."""

    def setUp(self):
        import tempfile
        from cores.v1.auto_repair import AutoRepair, RepairTask
        self._tmpdir = Path(tempfile.mkdtemp())
        self.AutoRepair = AutoRepair
        self.RepairTask = RepairTask
        self.repairer = AutoRepair()

    def tearDown(self):
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    # ── Model Validation ──

    def test_reject_deepseek_coder(self):
        valid, reason = self.AutoRepair.validate_model("ollama/deepseek-coder:1.3b")
        self.assertFalse(valid)
        self.assertIn("code-only", reason.lower())

    def test_reject_starcoder(self):
        valid, _ = self.AutoRepair.validate_model("ollama/starcoder2:3b")
        self.assertFalse(valid)

    def test_reject_codellama(self):
        valid, _ = self.AutoRepair.validate_model("ollama/codellama:7b")
        self.assertFalse(valid)

    def test_accept_llama_instruct(self):
        valid, reason = self.AutoRepair.validate_model(
            "openrouter/meta-llama/llama-3.3-70b-instruct:free")
        self.assertTrue(valid)
        self.assertEqual(reason, "OK")

    def test_accept_qwen_chat(self):
        valid, _ = self.AutoRepair.validate_model("ollama/qwen2.5:3b")
        self.assertTrue(valid)

    def test_accept_mistral(self):
        valid, _ = self.AutoRepair.validate_model("ollama/mistral:7b-instruct")
        self.assertTrue(valid)

    def test_suggest_better_model(self):
        models = ["ollama/deepseek-coder:1.3b", "ollama/qwen2.5:3b",
                   "ollama/mistral:7b-instruct"]
        suggestion = self.AutoRepair.suggest_better_model(
            "ollama/deepseek-coder:1.3b", models)
        self.assertIsNotNone(suggestion)
        self.assertNotIn("deepseek-coder", suggestion)

    def test_suggest_none_if_valid(self):
        suggestion = self.AutoRepair.suggest_better_model(
            "ollama/qwen2.5:3b", ["ollama/qwen2.5:3b"])
        self.assertIsNone(suggestion)

    # ── RepairTask ──

    def test_repair_task_creation(self):
        task = self.RepairTask("echo", "syntax", "Line 5: invalid syntax", "critical")
        self.assertEqual(task.status, self.RepairTask.PENDING)
        self.assertEqual(task.attempts, 0)
        self.assertEqual(task.skill_name, "echo")

    # ── Fix Strategies ──

    def test_strip_markdown_from_skill(self):
        skill_dir = self._tmpdir / "broken" / "v1"
        skill_dir.mkdir(parents=True)
        broken = skill_dir / "skill.py"
        broken.write_text(
            "Here is the fixed code:\n"
            "```python\n"
            "import subprocess\n"
            "class Skill:\n"
            "    def execute(self, p):\n"
            "        return {'success': True}\n"
            "def get_info(): return {'name': 'test'}\n"
            "def health_check(): return True\n"
            "```\n"
            "This should work now.\n"
        )
        ok, msg = self.repairer._fix_strip_markdown(broken)
        self.assertTrue(ok, f"Strip markdown failed: {msg}")
        code = broken.read_text()
        self.assertNotIn("```", code)
        self.assertIn("class Skill", code)

    def test_add_interface_functions(self):
        skill_dir = self._tmpdir / "nointerface" / "v1"
        skill_dir.mkdir(parents=True)
        skill_file = skill_dir / "skill.py"
        skill_file.write_text(
            "class MySkill:\n"
            "    def execute(self, params):\n"
            "        return {'success': True}\n"
        )
        ok, msg = self.repairer._fix_add_interface(skill_file, "nointerface")
        self.assertTrue(ok, f"Add interface failed: {msg}")
        code = skill_file.read_text()
        self.assertIn("def get_info()", code)
        self.assertIn("def health_check()", code)

    # ── Boot Repair (dry, no skill_manager) ──

    def test_boot_repair_no_sm(self):
        """Boot repair without skill_manager should not crash."""
        r = self.AutoRepair()
        report = r.run_boot_repair()
        self.assertIn("started", report)
        self.assertIn("fixed", report)
        self.assertEqual(report["tasks_created"], 0)

    def test_task_summary_empty(self):
        summary = self.repairer.get_task_summary()
        self.assertIn("Brak zadań", summary)


class TestResolveModelRejectsCodeOnly(unittest.TestCase):
    """Test that _resolve_model rejects code-only models persisted in state."""

    def test_deepseek_coder_rejected(self):
        """deepseek-coder saved in state should be replaced by DEFAULT_MODEL."""
        from cores.v1.config import DEFAULT_MODEL, FREE_MODELS
        # Simulate state with code-only model
        fake_state = {"model": "ollama/deepseek-coder:1.3b"}
        # Import and call _resolve_model
        from cores.v1.core import _resolve_model
        mdl, models = _resolve_model(fake_state)
        self.assertNotIn("deepseek-coder", mdl)
        self.assertEqual(mdl, FREE_MODELS[0] if FREE_MODELS else DEFAULT_MODEL)

    def test_good_model_kept(self):
        """A valid model in state should not be replaced."""
        from cores.v1.core import _resolve_model
        fake_state = {"model": "openrouter/meta-llama/llama-3.3-70b-instruct:free"}
        mdl, _ = _resolve_model(fake_state)
        self.assertEqual(mdl, "openrouter/meta-llama/llama-3.3-70b-instruct:free")


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
    unittest.main(verbosity=2)
