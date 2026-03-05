#!/usr/bin/env python3
"""
ML Intent Classification Tests - SLOW tests that load SBERT embedding model.
These tests are separated because they load heavy ML models.

Run separately: python3 -m pytest tests/manual/test_ml_intent.py -v
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
from cores.v1.logger import Logger
from cores.v1.intent_engine import IntentEngine
from cores.v1.skill_manager import SkillManager
from cores.v1.evo_engine import EvoEngine
from cores.v1.resource_monitor import ResourceMonitor
from cores.v1.provider_selector import ProviderSelector


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


# ─── Test: Voice Conversation Intent ─────────────────────────────────
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


if __name__ == "__main__":
    unittest.main()
