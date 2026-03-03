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
from cores.v1.provider_selector import ProviderSelector, ProviderInfo
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


# ─── Test: IntentEngine keyword classification ────────────────────────
class TestIntentEngineKeywords(unittest.TestCase):
    """Test that IntentEngine correctly classifies Polish/English intents via keyword fallback."""

    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.state = {"user_profile": {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        }}
        self.intent = IntentEngine(self.llm, self.logger, self.state)
        self.intent._fast_model = None  # force keyword fallback path
        self.skills = {
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
        """'przywitaj się' → use tts"""
        r = self.intent.analyze("przywitaj się głosowo", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

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
        """'dictate mode' → use stt"""
        r = self.intent.analyze("start dictate mode please", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    # ── STT not available → create ──
    def test_stt_not_available_creates(self):
        """If stt not in skills, should create it"""
        skills_no_stt = {k: v for k, v in self.skills.items() if k != "stt"}
        r = self.intent.analyze("czy mnie słyszysz?", skills_no_stt)
        self.assertEqual(r["action"], "create")
        self.assertEqual(r["name"], "stt")

    # ── Evolve intent ──
    def test_evolve_skill_pl(self):
        """'napraw tts' → evolve tts"""
        r = self.intent.analyze("napraw skill tts bo nie działa", self.skills)
        self.assertEqual(r["action"], "evolve")
        self.assertEqual(r["skill"], "tts")

    def test_improve_voice_pl(self):
        """'popraw głos' → evolve tts"""
        r = self.intent.analyze("popraw jakość głosu", self.skills)
        self.assertEqual(r["action"], "evolve")
        self.assertEqual(r["skill"], "tts")

    def test_fix_en(self):
        """'fix web_search' → evolve web_search"""
        r = self.intent.analyze("fix web_search it returns empty", self.skills)
        self.assertEqual(r["action"], "evolve")
        self.assertEqual(r["skill"], "web_search")

    # ── Create intent ──
    def test_create_skill_pl(self):
        """'stwórz skill do pogody' → create"""
        r = self.intent.analyze("stwórz skill do sprawdzania pogody", self.skills)
        self.assertEqual(r["action"], "create")

    def test_build_app_pl(self):
        """'napisz program' → create"""
        r = self.intent.analyze("napisz program do kalkulatora", self.skills)
        self.assertEqual(r["action"], "create")

    def test_install_pl(self):
        """'zainstaluj narzędzie' → create"""
        r = self.intent.analyze("zainstaluj narzędzie do monitorowania", self.skills)
        self.assertEqual(r["action"], "create")

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

    # ── Ambiguous voice → TTS (not STT) ──
    def test_voice_ambiguous_defaults_tts(self):
        """'głos' alone → TTS (speak), not STT"""
        r = self.intent.analyze("użyj głosu do odpowiedzi", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

    # ── Evolve priority over create ──
    def test_evolve_has_priority(self):
        """'zmień głos na lepszy' → evolve (not create)"""
        r = self.intent.analyze("zmień głos na lepszy", self.skills)
        self.assertEqual(r["action"], "evolve")

    # ── TTS priority over STT ──
    def test_tts_priority_over_stt(self):
        """'powiedz coś' → TTS even if voice context"""
        self.state["user_profile"]["topics"] = ["voice"] * 5
        r = self.intent.analyze("powiedz mi jak się masz", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")


# ─── Test: IntentEngine topic tracking ────────────────────────────────
class TestIntentEngineTopics(unittest.TestCase):

    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.state = {"user_profile": {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        }}
        self.intent = IntentEngine(self.llm, self.logger, self.state)
        self.intent._fast_model = None  # force keyword fallback path

    def test_topic_detection_voice(self):
        topics = self.intent._detect_topics("powiedz coś głosem")
        self.assertIn("voice", topics)

    def test_topic_detection_web(self):
        topics = self.intent._detect_topics("szukaj w internecie")
        self.assertIn("web", topics)

    def test_topic_detection_git(self):
        topics = self.intent._detect_topics("zrób git commit")
        self.assertIn("git", topics)

    def test_topic_detection_dev(self):
        topics = self.intent._detect_topics("napisz kod w pythonie")
        self.assertIn("dev", topics)

    def test_topic_tracking_updates(self):
        self.intent._update_topics("powiedz coś głosem")
        self.intent._update_topics("nagraj mnie z mikrofonu")
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
        self.assertTrue(v.startswith("v"))

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
        """User says 'napraw tts' → should trigger evolve"""
        analysis, _ = self._dialog("napraw tts bo źle działa")
        self.assertEqual(analysis["action"], "evolve")
        self.assertEqual(analysis["skill"], "tts")

    def test_create_dialog_flow(self):
        """User says 'stwórz kalkulator' → should trigger create"""
        analysis, _ = self._dialog("stwórz mi kalkulator")
        self.assertEqual(analysis["action"], "create")

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
    """Test realistic Polish dialog scenarios end-to-end."""

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

    def _classify(self, msg):
        return self.intent.analyze(msg, self.sm.list_skills())

    def test_scenario_voice_greeting(self):
        """'przywitaj się ze mną głosowo' → TTS"""
        r = self._classify("przywitaj się ze mną głosowo")
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")

    def test_scenario_create_weather(self):
        """'stwórz mi skill do pogody' → create"""
        r = self._classify("stwórz mi skill do sprawdzania pogody")
        self.assertEqual(r["action"], "create")

    def test_scenario_fix_broken_skill(self):
        """'napraw web_search nie zwraca wyników' → evolve"""
        r = self._classify("napraw web_search bo nie zwraca wyników")
        self.assertEqual(r["action"], "evolve")
        self.assertEqual(r["skill"], "web_search")

    def test_scenario_listen_request(self):
        """'posłuchaj co mówię' → STT"""
        r = self._classify("posłuchaj co mówię")
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "stt")

    def test_scenario_deploy_app(self):
        """'deploy aplikację na serwer' → create"""
        r = self._classify("deploy aplikację na serwer produkcyjny")
        self.assertEqual(r["action"], "create")

    def test_scenario_improve_tts(self):
        """'popraw jakość głosu' → evolve tts"""
        r = self._classify("popraw jakość głosu")
        self.assertEqual(r["action"], "evolve")
        self.assertEqual(r["skill"], "tts")

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
        """'użyj głosu' without listen → TTS"""
        r = self._classify("odpowiedz mi głosowo")
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "tts")


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
    def setUp(self):
        self.llm = MockLLM()
        self.logger = Logger("TEST")
        self.state = {}
        self.intent = IntentEngine(self.llm, self.logger, self.state)
        self.intent._fast_model = None  # force keyword fallback path
        self.skills = {"shell": ["v1"], "tts": ["v1"], "stt": ["v1", "v6"]}

    def test_uruchom_routes_to_shell(self):
        r = self.intent.analyze("uruchom ls -la", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_uruchom_extracts_command(self):
        r = self.intent.analyze("uruchom apt update", self.skills)
        self.assertEqual(r["input"]["command"], "apt update")

    def test_sudo_routes_to_shell(self):
        r = self.intent.analyze("sudo apt upgrade -y", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_wykonaj_routes_to_shell(self):
        r = self.intent.analyze("wykonaj pip install requests", self.skills)
        self.assertEqual(r["action"], "use")
        self.assertEqual(r["skill"], "shell")

    def test_shell_not_triggered_without_skill(self):
        """Without shell skill, shell keywords shouldn't route to shell"""
        skills_no_shell = {"tts": ["v1"], "stt": ["v1"]}
        r = self.intent.analyze("uruchom ls -la", skills_no_shell)
        self.assertNotEqual(r.get("skill"), "shell")


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
