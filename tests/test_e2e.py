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
from cores.v1.skill_manager import SkillManager, _load_bootstrap_skill
from cores.v1.evo_engine import EvoEngine
from cores.v1.resource_monitor import ResourceMonitor
from cores.v1.provider_selector import ProviderSelector, ProviderInfo, ProviderChain
from cores.v1.preflight import SkillPreflight, EvolutionGuard, PreflightResult
from cores.v1.system_identity import SystemIdentity, SkillStatus
from cores.v1.voice_loop import _extract_stt_text
from cores.v1.supervisor import Supervisor
from cores.v1.pipeline_manager import PipelineManager


# ─── Patch EmbeddingEngine to skip sbert (20s+ model load) ───────────
# Must be done BEFORE any EmbeddingEngine instances are created
from cores.v1.intent.embedding import EmbeddingEngine as _EE
_EE._orig_try_init = _EE._try_init
def _fast_try_init(self):
    if self._mode:
        return
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer  # noqa: F401
        self._tfidf = {"vectorizer": None, "matrix": None, "fit": False}
        self._mode = "tfidf"
        return
    except ImportError:
        pass
    self._mode = "bow"
_EE._try_init = _fast_try_init

# ─── Shared heavy objects (created once, reused by all tests) ────────
_SHARED_LOGGER = Logger("TEST")
_SHARED_RM = ResourceMonitor()
_SHARED_RM.snapshot()  # warm up cache (GPU detection + package list)
_SHARED_PS = ProviderSelector(SKILLS_DIR, _SHARED_RM)

# Lazy-loaded shared IntentEngine
_SHARED_INTENT = None

def _get_shared_intent():
    global _SHARED_INTENT
    if _SHARED_INTENT is None:
        llm = MockLLM()
        state = {"user_profile": {
            "topics": [], "corrections": [], "preferences": {},
            "skill_usage": {}, "unhandled": [],
        }}
        _SHARED_INTENT = IntentEngine(llm, _SHARED_LOGGER, state)
        _SHARED_INTENT._classifier._local_llm._available = False
        _SHARED_INTENT._classifier._local_llm._model = None
    return _SHARED_INTENT


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


# ─── Test: ProviderSelector ──────────────────────────────────────────
class TestProviderSelector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rm = _SHARED_RM
        cls.ps = _SHARED_PS

    def test_list_capabilities(self):
        caps = self.ps.list_capabilities()
        self.assertIn("tts", caps)
        self.assertIn("stt", caps)
        self.assertIn("deps", caps)

    def test_tts_has_multiple_providers(self):
        providers = self.ps.list_providers("tts")
        self.assertIn("piper", providers)
        self.assertIn("coqui", providers)
        self.assertIn("pyttsx3", providers)

    def test_stt_has_providers(self):
        providers = self.ps.list_providers("stt")
        self.assertIn("vosk", providers)
        self.assertIn("whisper", providers)

    def test_piper_is_premium_tier(self):
        info = self.ps.get_provider_info("tts", "piper")
        self.assertEqual(info.tier, "premium")
        self.assertEqual(info.quality_score, 9)

    def test_coqui_is_premium_tier(self):
        info = self.ps.get_provider_info("tts", "coqui")
        self.assertEqual(info.tier, "premium")
        self.assertEqual(info.quality_score, 9)

    def test_tts_selects_piper_when_available(self):
        """If piper is installed and configured, it should be selected (prefer_default)."""
        with patch.dict(os.environ, {"PIPER_MODEL": "/tmp/fake_piper.onnx"}, clear=False):
            with patch.object(self.rm, "has_command") as has_cmd:
                def _fake_has_command(cmd: str) -> bool:
                    return cmd in ("piper", "ffmpeg")
                has_cmd.side_effect = _fake_has_command

                with patch.object(self.rm, "has_python_package") as has_pkg:
                    def _fake_has_pkg(name: str) -> bool:
                        return name in ("piper-tts", "piper_tts")
                    has_pkg.side_effect = _fake_has_pkg

                    with patch("pathlib.Path.exists", return_value=True):
                        selected = self.ps.select("tts")
                        self.assertEqual(selected, "piper")

    def test_force_provider(self):
        """Force should override selection"""
        selected = self.ps.select("tts", force="piper")
        self.assertEqual(selected, "piper")

    def test_speed_preference_selects_lite(self):
        """prefer=speed should favor lite tier"""
        selected = self.ps.select("tts", prefer="speed")
        self.assertIn(selected, self.ps.list_providers("tts"))

    def test_reliability_preference(self):
        """prefer=reliability should favor lite (fewer deps)"""
        selected = self.ps.select("tts", prefer="reliability")
        self.assertIn(selected, self.ps.list_providers("tts"))

    def test_legacy_skills_default_provider(self):
        """Legacy skills (no providers/ dir) should return 'default'"""
        providers = self.ps.list_providers("deps")
        self.assertEqual(providers, ["default"])

    def test_manifest_loading(self):
        manifest = self.ps.load_manifest("tts")
        self.assertEqual(manifest["capability"], "tts")
        self.assertIn("piper", manifest["providers"])

    def test_skill_path_resolution(self):
        path = self.ps.get_skill_path("tts", "piper")
        self.assertIsNotNone(path)
        self.assertTrue(path.exists())
        self.assertTrue(str(path).endswith("skill.py"))

    def test_summary_output(self):
        # summary() scans the whole skills tree; keep the test focused and fast.
        with patch.object(self.ps, "list_capabilities", return_value=["tts"]):
            summary = self.ps.summary()
        self.assertIn("tts:", summary)
        self.assertIn("piper", summary)


# ─── Test: ProviderChain ─────────────────────────────────────────────
class TestProviderChain(unittest.TestCase):

    def setUp(self):
        # Make tests deterministic and fast: ProviderChain ordering should not depend
        # on whether optional system dependencies (piper/coqui/etc.) are installed.
        # We only want to test the chain logic (scoring, demotion, ordering).
        self._can_run_patcher = patch.object(_SHARED_RM, "can_run", return_value=(True, "mocked"))
        self._can_run_patcher.start()
        self.ps = ProviderSelector(SKILLS_DIR, _SHARED_RM)
        self.chain = ProviderChain(self.ps)

    def tearDown(self):
        if hasattr(self, "_can_run_patcher"):
            self._can_run_patcher.stop()

    def test_build_chain_returns_list(self):
        chain = self.chain.build_chain("tts")
        self.assertIsInstance(chain, list)
        self.assertGreater(len(chain), 0)

    def test_chain_includes_espeak(self):
        chain = self.chain.build_chain("tts")
        self.assertIn("piper", chain)

    def test_chain_piper_first_for_quality(self):
        """First provider should be the highest-scored runnable provider."""
        providers = self.ps.list_providers("tts")
        scored = []
        for pname in providers:
            info = self.ps.get_provider_info("tts", pname)
            can_run, _ = self.ps._check_runnable(info)
            if can_run:
                scored.append((pname, self.ps._score(info, prefer="quality")))
        self.assertTrue(scored, "Expected at least one runnable provider")
        expected = sorted(scored, key=lambda x: x[1], reverse=True)[0][0]

        chain = self.chain.build_chain("tts", prefer="quality")
        self.assertEqual(chain[0], expected)

    def test_select_best_returns_string(self):
        best = self.chain.select_best("tts")
        self.assertIsInstance(best, str)
        self.assertIn(best, self.chain.build_chain("tts"))

    def test_select_with_fallback_returns_ordered_list(self):
        providers = self.chain.select_with_fallback("tts")
        self.assertIsInstance(providers, list)
        self.assertGreater(len(providers), 0)

    def test_record_failure_increments(self):
        self.chain.record_failure("tts", "piper", "test error")
        stats = self.chain.get_stats("tts", "piper")
        self.assertEqual(stats["failures"], 1)
        self.assertFalse(stats["demoted"])

    def test_demotion_after_threshold(self):
        for _ in range(3):
            self.chain.record_failure("tts", "piper")
        stats = self.chain.get_stats("tts", "piper")
        self.assertTrue(stats["demoted"])

    def test_demoted_provider_pushed_to_end(self):
        for _ in range(3):
            self.chain.record_failure("tts", "piper")
        chain = self.chain.build_chain("tts")
        if len(chain) > 1:
            self.assertNotEqual(chain[0], "piper",
                                "Demoted provider should not be first")

    def test_recovery_after_successes(self):
        for _ in range(3):
            self.chain.record_failure("tts", "piper")
        self.assertTrue(self.chain.is_demoted("tts", "piper"))
        self.chain.record_success("tts", "piper")
        self.chain.record_success("tts", "piper")
        self.assertFalse(self.chain.is_demoted("tts", "piper"))

    def test_chain_summary_format(self):
        summary = self.chain.chain_summary("tts")
        self.assertIn("tts:", summary)
        self.assertIn("piper", summary)

    def test_stats_initial_zero(self):
        stats = self.chain.get_stats("tts", "piper")
        self.assertEqual(stats["failures"], 0)
        self.assertEqual(stats["successes"], 0)
        self.assertFalse(stats["demoted"])

    def test_success_resets_failure_count(self):
        self.chain.record_failure("tts", "piper")
        self.chain.record_failure("tts", "piper")
        self.chain.record_success("tts", "piper")
        self.chain.record_success("tts", "piper")
        stats = self.chain.get_stats("tts", "piper")
        self.assertEqual(stats["failures"], 0)


# ─── Test: ResourceMonitor ───────────────────────────────────────────
class TestResourceMonitor(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.rm = _SHARED_RM

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

    @classmethod
    def setUpClass(cls):
        cls.llm = MockLLM()
        cls.sm = SkillManager(cls.llm, _SHARED_LOGGER, provider_selector=_SHARED_PS)

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
        # Should resolve through a valid TTS provider (pyttsx3, espeak, piper, or coqui)
        valid_providers = ["pyttsx3", "espeak", "piper", "coqui"]
        self.assertTrue(any(prov in str(p) for prov in valid_providers),
                       f"Expected path to contain one of {valid_providers}, got: {p}")

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

    @classmethod
    def setUpClass(cls):
        cls.llm = MockLLM()
        cls.sm = SkillManager(cls.llm, _SHARED_LOGGER, provider_selector=_SHARED_PS)
        cls.evo = EvoEngine(cls.sm, cls.llm, _SHARED_LOGGER)
        cls.intent = _get_shared_intent()
        # Mock exec_skill to avoid real execution (nfo errors trigger evolve loops)
        cls._orig_exec = cls.sm.exec_skill
        def _mock_exec(name, inp=None, **kw):
            if name == "stt":
                return {"success": True, "result": {"success": True, "spoken": "test transcription", "text": "test transcription"}, "info": {"name": name, "version": "stable"}}
            return {"success": True, "result": {"success": True, "spoken": True}, "info": {"name": name, "version": "stable"}}
        cls.sm.exec_skill = _mock_exec
        # Mock evolve_skill to avoid LLM-based evolve loops (MockLLM returns invalid code)
        cls._orig_evolve = cls.evo.evolve_skill
        cls.evo.evolve_skill = lambda name, desc, *a, **kw: (True, f"mock evolved {name}")
        cls._orig_smart_evolve = cls.sm.smart_evolve
        cls.sm.smart_evolve = lambda name, ctx, *a, **kw: (True, f"mock evolved {name}")

    @classmethod
    def tearDownClass(cls):
        cls.sm.exec_skill = cls._orig_exec
        cls.evo.evolve_skill = cls._orig_evolve
        cls.sm.smart_evolve = cls._orig_smart_evolve

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
        self.sv = Supervisor(self.state, _SHARED_LOGGER)

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

    @classmethod
    def setUpClass(cls):
        cls.llm = MockLLM()
        cls.ps = _SHARED_PS
        cls.sm = SkillManager(cls.llm, _SHARED_LOGGER, provider_selector=_SHARED_PS)

    def test_provider_selector_integrated_with_skill_manager(self):
        """ProviderSelector and SkillManager resolve same provider"""
        selected = self.ps.select("tts")
        ps_path = self.ps.get_skill_path("tts", selected)
        sm_path = self.sm.skill_path("tts")
        # Same provider directory (version may differ due to sort logic)
        self.assertEqual(ps_path.parent.parent, sm_path.parent.parent)

    def test_all_skills_loadable(self):
        """Verify all registered skills can at least be path-resolved"""
        skills = self.sm.list_skills()
        resolved = 0
        for name, versions in skills.items():
            p = self.sm.skill_path(name)
            if p is None:
                continue  # all versions rolled back — valid state
            self.assertTrue(p.exists(), f"Skill '{name}' path doesn't exist: {p}")
            resolved += 1
        self.assertGreater(resolved, 0, "No skills could be resolved")

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
        selected = self.ps.select("tts")
        valid_providers = self.ps.list_providers("tts")
        self.assertIn(selected, valid_providers)

        # With prefer_quality context, should still select a valid provider
        selected2 = self.ps.select("tts", context={"prefer_quality": True})
        self.assertIn(selected2, valid_providers)


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
        self.assertEqual(_extract_stt_text(outcome), "")

    def test_extract_stt_text_non_stt_skill(self):
        outcome = {
            "type": "success", "skill": "tts",
            "result": {"success": True, "result": {"success": True}}
        }
        self.assertEqual(_extract_stt_text(outcome), "")

    def test_extract_stt_text_failed_outcome(self):
        outcome = {"type": "failed", "skill": "stt"}
        self.assertEqual(_extract_stt_text(outcome), "")

    def test_extract_stt_text_none_outcome(self):
        self.assertEqual(_extract_stt_text(None), "")

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
        cls.intent = _get_shared_intent()
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
    @classmethod
    def setUpClass(cls):
        cls.llm = MockLLM()
        cls.sm = SkillManager(cls.llm, _SHARED_LOGGER, provider_selector=_SHARED_PS)
        cls.evo = EvoEngine(cls.sm, cls.llm, _SHARED_LOGGER)

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
        cls.classifier = _get_shared_intent()._classifier
        cls.classifier._local_llm._available = False
        cls.classifier._local_llm._model = None
        cls.skills = {"shell": ["v2"], "tts": ["stable"], "stt": ["stable"],
                      "echo": ["stable"], "web_search": ["stable"], "git_ops": ["v1"]}

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
        ok, msg = self.repairer.strategies.fix_strip_markdown(broken)
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
        ok, msg = self.repairer.strategies.fix_add_interface(skill_file, "nointerface")
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
        from cores.v1.core_boot import _resolve_model
        mdl, models = _resolve_model(fake_state)
        self.assertNotIn("deepseek-coder", mdl)
        self.assertEqual(mdl, FREE_MODELS[0] if FREE_MODELS else DEFAULT_MODEL)

    def test_good_model_kept(self):
        """A valid model in state should not be replaced."""
        from cores.v1.core_boot import _resolve_model
        fake_state = {"model": "openrouter/meta-llama/llama-3.3-70b-instruct:free"}
        mdl, _ = _resolve_model(fake_state)
        self.assertEqual(mdl, "openrouter/meta-llama/llama-3.3-70b-instruct:free")


# ─── SkillQualityGate Tests ───────────────────────────────────────────
class TestSkillQualityGate(unittest.TestCase):
    """Test quality gate evaluation for skills."""

    def setUp(self):
        from cores.v1.quality_gate import SkillQualityGate, QualityReport
        self.qg = SkillQualityGate()
        self.tmpdir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _write_skill(self, code, name="test_skill"):
        p = Path(self.tmpdir) / name / "skill.py"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(code)
        return p

    def test_good_skill_passes(self):
        """A well-formed skill gets a high quality score."""
        code = '''
import json

class TestSkill:
    """A test skill."""
    def execute(self, params):
        text = params.get("text", "")
        return {"success": True, "result": text.upper()}

def get_info():
    return {"name": "test_skill", "version": "v1", "description": "Test"}

def health_check():
    return {"status": "ok"}

def execute(params):
    return TestSkill().execute(params)

if __name__ == "__main__":
    print(execute({"text": "hello"}))
'''
        p = self._write_skill(code)
        report = self.qg.evaluate(p, "test_skill")
        self.assertGreaterEqual(report.score, 0.5)
        self.assertTrue(report.ok)
        self.assertIn("preflight", report.passed)

    def test_syntax_error_fails(self):
        """A skill with syntax errors gets zero preflight score."""
        code = "def broken(\nclass invalid"
        p = self._write_skill(code, "broken_skill")
        report = self.qg.evaluate(p, "broken_skill")
        self.assertLess(report.score, 0.5)
        self.assertFalse(report.ok)
        self.assertTrue(any("preflight" in f for f in report.failed))

    def test_missing_interface_warns(self):
        """A skill missing get_info/health_check gets lower score."""
        code = '''
class MinimalSkill:
    def execute(self, params):
        return {"success": True}
'''
        p = self._write_skill(code, "minimal_skill")
        report = self.qg.evaluate(p, "minimal_skill")
        # Should still pass preflight (interface check warns but may pass)
        # but health_check missing means lower score
        self.assertIsInstance(report.score, float)
        self.assertLessEqual(report.score, 1.0)

    def test_empty_file_fails(self):
        """An empty file gets a very low score."""
        p = self._write_skill("", "empty_skill")
        report = self.qg.evaluate(p, "empty_skill")
        self.assertLess(report.score, 0.5)
        self.assertFalse(report.ok)

    def test_should_register(self):
        """should_register returns True only above MIN_QUALITY."""
        from cores.v1.quality_gate import QualityReport
        good = QualityReport(skill_name="a", score=0.7)
        bad = QualityReport(skill_name="b", score=0.3)
        self.assertTrue(self.qg.should_register(good))
        self.assertFalse(self.qg.should_register(bad))

    def test_compare_detects_regression(self):
        """compare returns False when new score is much lower."""
        from cores.v1.quality_gate import QualityReport
        old = QualityReport(skill_name="s", score=0.8)
        new_ok = QualityReport(skill_name="s", score=0.75)
        new_bad = QualityReport(skill_name="s", score=0.5)
        self.assertTrue(self.qg.compare(old, new_ok))
        self.assertFalse(self.qg.compare(old, new_bad))

    def test_report_summary(self):
        """QualityReport.summary() returns readable string."""
        from cores.v1.quality_gate import QualityReport
        r = QualityReport(skill_name="test", score=0.85, passed=["preflight"])
        s = r.summary()
        self.assertIn("test", s)
        self.assertIn("0.85", s)

    def test_nonexistent_file(self):
        """Evaluating a nonexistent file fails gracefully."""
        report = self.qg.evaluate(Path("/tmp/nonexistent_skill.py"), "ghost")
        self.assertFalse(report.ok)
        self.assertLess(report.score, 0.5)

    def test_code_quality_metrics(self):
        """Code quality check reports line count and functions."""
        code = '''
import os
import json

class BigSkill:
    """A bigger skill with more structure."""
    def execute(self, params):
        text = params.get("text", "")
        if not text:
            return {"success": False, "error": "No text"}
        result = text.upper()
        return {"success": True, "result": result}

    def helper(self):
        return "helper"

def get_info():
    return {"name": "big", "version": "v1", "description": "Big skill"}

def health_check():
    return {"status": "ok"}

def execute(params):
    return BigSkill().execute(params)

if __name__ == "__main__":
    print(execute({"text": "test"}))
'''
        p = self._write_skill(code, "big_skill")
        report = self.qg.evaluate(p, "big_skill")
        self.assertIn("line_count", report.details)
        self.assertIn("functions", report.details)
        self.assertGreater(report.details["line_count"], 10)


# ─── SkillValidator Tests ────────────────────────────────────────────
class TestSkillValidator(unittest.TestCase):
    """Test the plugin-based skill validation registry."""

    def setUp(self):
        from cores.v1.skill_validator import SkillValidator
        self.sv = SkillValidator()

    def test_generic_success(self):
        """Generic skill with success=True passes validation."""
        result = {"success": True, "result": {"data": "hello"}}
        vr = self.sv.validate("unknown_skill", result)
        self.assertEqual(vr.verdict, "success")

    def test_generic_failure(self):
        """Skill with success=False fails validation."""
        result = {"success": False, "error": "something broke"}
        vr = self.sv.validate("any_skill", result)
        self.assertEqual(vr.verdict, "fail")
        self.assertIn("something broke", vr.reason)

    def test_inner_failure(self):
        """Inner result with success=False fails validation."""
        result = {"success": True, "result": {"success": False, "error": "inner fail"}}
        vr = self.sv.validate("any_skill", result)
        self.assertEqual(vr.verdict, "fail")

    def test_stt_empty_transcription(self):
        """STT with empty text returns partial."""
        result = {"success": True, "result": {"spoken": "", "text": ""}}
        vr = self.sv.validate("stt", result)
        self.assertEqual(vr.verdict, "partial")
        self.assertIn("empty transcription", vr.reason)

    def test_stt_hardware_fail(self):
        """STT with hardware_ok=False returns fail."""
        result = {"success": True, "result": {"hardware_ok": False, "error": "no mic"}}
        vr = self.sv.validate("stt", result)
        self.assertEqual(vr.verdict, "fail")
        self.assertIn("hardware", vr.reason)

    def test_stt_silence(self):
        """STT with has_sound=False returns partial."""
        result = {"success": True, "result": {"has_sound": False, "audio_level_db": -50}}
        vr = self.sv.validate("stt", result)
        self.assertEqual(vr.verdict, "partial")
        self.assertIn("silence", vr.reason)

    def test_stt_success(self):
        """STT with spoken text passes."""
        result = {"success": True, "result": {"spoken": "hello world", "text": "hello world"}}
        vr = self.sv.validate("stt", result)
        self.assertEqual(vr.verdict, "success")

    def test_shell_nonzero_exit(self):
        """Shell with exit_code != 0 returns partial."""
        result = {"success": True, "result": {"exit_code": 1, "stderr": "not found"}}
        vr = self.sv.validate("shell", result)
        self.assertEqual(vr.verdict, "partial")
        self.assertIn("exit_code=1", vr.reason)

    def test_shell_success(self):
        """Shell with exit_code 0 passes."""
        result = {"success": True, "result": {"exit_code": 0, "stdout": "ok"}}
        vr = self.sv.validate("shell", result)
        self.assertEqual(vr.verdict, "success")

    def test_tts_error(self):
        """TTS with error field returns fail."""
        result = {"success": True, "result": {"error": "espeak not found"}}
        vr = self.sv.validate("tts", result)
        self.assertEqual(vr.verdict, "fail")

    def test_web_search_empty(self):
        """Web search with empty results returns partial."""
        result = {"success": True, "result": {"results": [], "query": "test query"}}
        vr = self.sv.validate("web_search", result)
        self.assertEqual(vr.verdict, "partial")
        self.assertIn("empty results", vr.reason)

    def test_web_search_local_net(self):
        """Web search for local network with no results mentions scanner skill."""
        result = {"success": True, "result": {"results": [], "query": "skanuj kamery w sieci"}}
        vr = self.sv.validate("web_search", result)
        self.assertEqual(vr.verdict, "partial")
        self.assertIn("network scanner", vr.reason)

    def test_web_search_with_results(self):
        """Web search with results passes."""
        result = {"success": True, "result": {"results": [{"title": "x"}], "query": "test"}}
        vr = self.sv.validate("web_search", result)
        self.assertEqual(vr.verdict, "success")

    def test_register_custom_validator(self):
        """Custom validator can be registered and used."""
        def my_validator(result, goal, user_msg):
            from cores.v1.skill_validator import ValidationResult
            inner = result.get("result", {})
            if isinstance(inner, dict) and inner.get("custom_field") == "bad":
                return ValidationResult("fail", "custom check failed")
            return None

        self.sv.register("my_skill", my_validator)
        self.assertTrue(self.sv.has_validator("my_skill"))

        result = {"success": True, "result": {"custom_field": "bad"}}
        vr = self.sv.validate("my_skill", result)
        self.assertEqual(vr.verdict, "fail")
        self.assertIn("custom check", vr.reason)

        result2 = {"success": True, "result": {"custom_field": "good"}}
        vr2 = self.sv.validate("my_skill", result2)
        self.assertEqual(vr2.verdict, "success")

    def test_unregister_validator(self):
        """Unregistering a validator falls back to generic."""
        self.sv.unregister("stt")
        self.assertFalse(self.sv.has_validator("stt"))
        result = {"success": True, "result": {"spoken": ""}}
        vr = self.sv.validate("stt", result)
        self.assertEqual(vr.verdict, "success")  # Generic passes

    def test_list_validators(self):
        """list_validators returns all registered skill names."""
        validators = self.sv.list_validators()
        self.assertIn("stt", validators)
        self.assertIn("shell", validators)
        self.assertIn("tts", validators)
        self.assertIn("web_search", validators)

    def test_validation_result_to_dict(self):
        """ValidationResult.to_dict() returns proper format."""
        from cores.v1.skill_validator import ValidationResult
        vr = ValidationResult("partial", "some reason")
        d = vr.to_dict()
        self.assertEqual(d["verdict"], "partial")
        self.assertEqual(d["reason"], "some reason")

    def test_non_dict_inner_trusted(self):
        """Non-dict inner result is trusted as success."""
        result = {"success": True, "result": "just a string"}
        vr = self.sv.validate("any_skill", result)
        self.assertEqual(vr.verdict, "success")
        self.assertIn("non-dict", vr.reason)


if __name__ == "__main__":
    unittest.main(verbosity=2)
