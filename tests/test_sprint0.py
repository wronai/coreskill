#!/usr/bin/env python3
"""
Tests for Sprint 0: BaseSkill + YAML Manifest, Semantic Dedup, Pipeline Retry.

Run: python3 -m pytest tests/test_sprint0.py -v
"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cores.v1.base_skill import (
    BaseSkill, SkillManifest, InputField,
    generate_scaffold, generate_manifest_yaml, _make_module_functions,
)
from cores.v1.skill_forge import (
    SkillForge, ErrorBudget, SkillMatch, is_conversational,
)
from cores.v1.pipeline_manager import PipelineManager
from cores.v1.logger import Logger


# ═════════════════════════════════════════════════════════════════════
# Day 1: BaseSkill + YAML Manifest
# ═════════════════════════════════════════════════════════════════════

class TestBaseSkill(unittest.TestCase):
    """Tests for BaseSkill class."""

    def test_baseskill_execute_not_implemented(self):
        """BaseSkill.execute() raises NotImplementedError."""
        skill = BaseSkill()
        with self.assertRaises(NotImplementedError):
            skill.execute({})

    def test_baseskill_safe_execute_catches_errors(self):
        """safe_execute wraps errors instead of crashing."""
        class BrokenSkill(BaseSkill):
            name = "broken"
            def execute(self, params):
                raise ValueError("something went wrong")

        skill = BrokenSkill()
        result = skill.safe_execute({"text": "test"})
        self.assertFalse(result["success"])
        self.assertIn("something went wrong", result["error"])
        self.assertIn("traceback", result)

    def test_baseskill_safe_execute_normalizes_output(self):
        """safe_execute adds success=True if missing."""
        class SimpleSkill(BaseSkill):
            name = "simple"
            def execute(self, params):
                return {"result": "hello"}

        skill = SimpleSkill()
        result = skill.safe_execute({"text": "test"})
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], "hello")

    def test_baseskill_safe_execute_non_dict_input(self):
        """safe_execute normalizes non-dict input to {text: str}."""
        class EchoSkill(BaseSkill):
            name = "echo"
            def execute(self, params):
                return {"success": True, "text": params.get("text", "")}

        skill = EchoSkill()
        result = skill.safe_execute("hello world")
        self.assertTrue(result["success"])
        self.assertEqual(result["text"], "hello world")

    def test_baseskill_safe_execute_non_dict_result(self):
        """safe_execute normalizes non-dict result."""
        class ReturnString(BaseSkill):
            name = "ret_str"
            def execute(self, params):
                return "just a string"

        skill = ReturnString()
        result = skill.safe_execute({})
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], "just a string")

    def test_baseskill_get_info(self):
        """get_info returns skill metadata."""
        class MySkill(BaseSkill):
            name = "my_skill"
            version = "v2"
            description = "Does things"

        skill = MySkill()
        info = skill.get_info()
        self.assertEqual(info["name"], "my_skill")
        self.assertEqual(info["version"], "v2")
        self.assertEqual(info["description"], "Does things")

    def test_baseskill_health_check(self):
        """Default health_check returns ok."""
        skill = BaseSkill()
        self.assertEqual(skill.health_check(), {"status": "ok"})

    def test_baseskill_not_implemented_caught_by_safe(self):
        """safe_execute catches NotImplementedError gracefully."""
        skill = BaseSkill()
        result = skill.safe_execute({})
        self.assertFalse(result["success"])
        self.assertIn("not implemented", result["error"].lower())


class TestMakeModuleFunctions(unittest.TestCase):
    """Tests for _make_module_functions helper."""

    def test_make_module_functions(self):
        """_make_module_functions returns execute, get_info, health_check."""
        class TestSkill(BaseSkill):
            name = "test"
            version = "v1"
            description = "test skill"
            def execute(self, params):
                return {"success": True, "echo": params.get("text", "")}

        execute, get_info, health_check = _make_module_functions(TestSkill)

        result = execute({"text": "hello"})
        self.assertTrue(result["success"])
        self.assertEqual(result["echo"], "hello")

        info = get_info()
        self.assertEqual(info["name"], "test")

        hc = health_check()
        self.assertEqual(hc["status"], "ok")

    def test_make_module_functions_error_handling(self):
        """Module-level execute via _make_module_functions catches errors."""
        class BadSkill(BaseSkill):
            name = "bad"
            def execute(self, params):
                raise RuntimeError("boom")

        execute, _, _ = _make_module_functions(BadSkill)
        result = execute({"text": "test"})
        self.assertFalse(result["success"])
        self.assertIn("boom", result["error"])


class TestSkillManifest(unittest.TestCase):
    """Tests for SkillManifest YAML/JSON manifest."""

    def test_from_dict_basic(self):
        """Parse manifest from dict."""
        data = {
            "name": "camera_scanner",
            "version": "v1",
            "description": "Scans network for cameras",
            "input": {
                "network": {"type": "string", "default": "192.168.1.0/24"},
                "timeout": {"type": "integer", "required": True},
            },
            "output": {"success": "bool", "devices": "list"},
            "tags": ["network", "scanner"],
        }
        m = SkillManifest.from_dict(data)
        self.assertEqual(m.name, "camera_scanner")
        self.assertEqual(m.version, "v1")
        self.assertEqual(len(m.inputs), 2)
        self.assertEqual(m.inputs[0].name, "network")
        self.assertEqual(m.inputs[0].default, "192.168.1.0/24")
        self.assertTrue(m.inputs[1].required)

    def test_from_dict_simple_types(self):
        """Parse manifest with simple type strings."""
        data = {
            "name": "simple",
            "input": {"text": "string", "count": "integer"},
        }
        m = SkillManifest.from_dict(data)
        self.assertEqual(len(m.inputs), 2)
        self.assertEqual(m.inputs[0].type, "string")

    def test_validate_input_required(self):
        """Validate catches missing required fields."""
        m = SkillManifest.from_dict({
            "name": "test",
            "input": {"query": {"type": "string", "required": True}},
        })
        errors = m.validate_input({})
        self.assertEqual(len(errors), 1)
        self.assertIn("query", errors[0])

    def test_validate_input_type_mismatch(self):
        """Validate catches type mismatches."""
        m = SkillManifest.from_dict({
            "name": "test",
            "input": {"count": {"type": "integer"}},
        })
        errors = m.validate_input({"count": "not_a_number"})
        self.assertEqual(len(errors), 1)
        self.assertIn("expected integer", errors[0])

    def test_validate_input_passes(self):
        """Validate returns empty list for valid input."""
        m = SkillManifest.from_dict({
            "name": "test",
            "input": {"text": {"type": "string", "required": True}},
        })
        errors = m.validate_input({"text": "hello"})
        self.assertEqual(len(errors), 0)

    def test_get_defaults(self):
        """get_defaults returns default values."""
        m = SkillManifest.from_dict({
            "name": "test",
            "input": {
                "text": {"type": "string", "default": "hello"},
                "count": {"type": "integer"},
            },
        })
        defaults = m.get_defaults()
        self.assertEqual(defaults, {"text": "hello"})

    def test_to_dict_roundtrip(self):
        """to_dict produces valid dict that can be re-parsed."""
        original = {
            "name": "test_skill",
            "version": "v1",
            "description": "A test",
            "input": {"query": {"type": "string", "required": True}},
            "tags": ["test"],
        }
        m = SkillManifest.from_dict(original)
        d = m.to_dict()
        m2 = SkillManifest.from_dict(d)
        self.assertEqual(m.name, m2.name)
        self.assertEqual(len(m.inputs), len(m2.inputs))

    def test_from_file_json(self):
        """Load manifest from JSON file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump({"name": "from_file", "version": "v2"}, f)
            f.flush()
            m = SkillManifest.from_file(Path(f.name))
            self.assertEqual(m.name, "from_file")
            self.assertEqual(m.version, "v2")
            os.unlink(f.name)

    def test_from_file_missing(self):
        """from_file returns None for missing file."""
        m = SkillManifest.from_file(Path("/tmp/nonexistent_manifest.json"))
        self.assertIsNone(m)

    def test_manifest_with_requires(self):
        """Parse manifest with requires section."""
        data = {
            "name": "shell_tool",
            "requires": {
                "commands": ["bash", "curl"],
                "packages": ["requests"],
            },
        }
        m = SkillManifest.from_dict(data)
        self.assertIn("bash", m.requires_commands)
        self.assertIn("requests", m.requires_packages)


class TestScaffoldGeneration(unittest.TestCase):
    """Tests for generate_scaffold and generate_manifest_yaml."""

    def test_generate_scaffold_basic(self):
        """generate_scaffold produces valid Python with BaseSkill."""
        m = SkillManifest(name="camera_scanner", description="Scan network")
        code = generate_scaffold(m)
        self.assertIn("class CameraScanner(BaseSkill):", code)
        self.assertIn('name = "camera_scanner"', code)
        self.assertIn("def execute(self, params", code)
        self.assertIn("_make_module_functions", code)

    def test_generate_scaffold_with_inputs(self):
        """generate_scaffold includes input parsing from manifest."""
        m = SkillManifest(
            name="calculator",
            inputs=[InputField(name="expression", type="string", default="0")]
        )
        code = generate_scaffold(m)
        self.assertIn('expression = params.get("expression"', code)

    def test_generate_manifest_yaml(self):
        """generate_manifest_yaml produces valid YAML-like content."""
        yaml_str = generate_manifest_yaml(
            "test_skill", "A test skill",
            inputs={"query": {"type": "string"}},
            tags=["test"])
        self.assertIn("name: test_skill", yaml_str)
        self.assertIn("query:", yaml_str)
        self.assertIn("tags:", yaml_str)


# ═════════════════════════════════════════════════════════════════════
# Day 2: Semantic Dedup (SkillForge)
# ═════════════════════════════════════════════════════════════════════

class TestIsConversational(unittest.TestCase):
    """Tests for conversational query detection."""

    def test_greetings_are_conversational(self):
        self.assertTrue(is_conversational("cześć"))
        self.assertTrue(is_conversational("Hello"))
        self.assertTrue(is_conversational("hej"))

    def test_questions_are_conversational(self):
        self.assertTrue(is_conversational("co to jest Python?"))
        self.assertTrue(is_conversational("how does this work?"))
        self.assertTrue(is_conversational("kim jesteś?"))

    def test_farewells_are_conversational(self):
        self.assertTrue(is_conversational("pa"))
        self.assertTrue(is_conversational("bye"))
        self.assertTrue(is_conversational("do widzenia"))

    def test_action_queries_are_not_conversational(self):
        self.assertFalse(is_conversational("stwórz kalkulator"))
        self.assertFalse(is_conversational("create a web scraper"))
        self.assertFalse(is_conversational("build network scanner"))

    def test_empty_is_conversational(self):
        self.assertTrue(is_conversational(""))
        self.assertTrue(is_conversational("  "))

    def test_short_non_action_is_conversational(self):
        self.assertTrue(is_conversational("ok thanks"))
        self.assertTrue(is_conversational("super"))


class TestErrorBudget(unittest.TestCase):
    """Tests for ErrorBudget."""

    def test_initial_not_exhausted(self):
        eb = ErrorBudget(max_errors_per_hour=3)
        self.assertFalse(eb.exhausted())

    def test_exhausted_after_max(self):
        eb = ErrorBudget(max_errors_per_hour=3)
        for _ in range(3):
            eb.record_error()
        self.assertTrue(eb.exhausted())

    def test_not_exhausted_below_max(self):
        eb = ErrorBudget(max_errors_per_hour=5)
        for _ in range(4):
            eb.record_error()
        self.assertFalse(eb.exhausted())

    def test_time_until_reset(self):
        eb = ErrorBudget(max_errors_per_hour=2)
        self.assertEqual(eb.time_until_reset(), 0)
        eb.record_error()
        eb.record_error()
        # Should be > 0 since errors are recent
        self.assertGreater(eb.time_until_reset(), 0)


class TestSkillForge(unittest.TestCase):
    """Tests for SkillForge semantic dedup."""

    def setUp(self):
        self.forge = SkillForge()  # No embedding engine — keyword fallback

    def test_conversational_returns_chat(self):
        """Conversational query returns (False, 'chat')."""
        should, reason = self.forge.should_create("cześć, jak się masz?", {})
        self.assertFalse(should)
        self.assertEqual(reason, "chat")

    def test_budget_exceeded(self):
        """Exhausted budget returns (False, 'budget_exceeded')."""
        self.forge._error_budget = ErrorBudget(max_errors_per_hour=2)
        self.forge._error_budget.record_error()
        self.forge._error_budget.record_error()
        should, reason = self.forge.should_create(
            "stwórz narzędzie do skanowania sieci", {"echo": ["v1"]})
        self.assertFalse(should)
        self.assertEqual(reason, "budget_exceeded")

    def test_new_skill_needed(self):
        """Novel query with no similar skills returns new_skill_needed."""
        should, reason = self.forge.should_create(
            "zbuduj skaner portów sieciowych TCP/UDP",
            {"echo": ["v1"], "shell": ["v1"]})
        self.assertTrue(should)
        self.assertEqual(reason, "new_skill_needed")

    @patch.object(SkillForge, 'search')
    def test_reuse_high_similarity(self, mock_search):
        """High similarity match returns reuse:<skill_name>."""
        mock_search.return_value = [
            SkillMatch(name="kalkulator", similarity=0.92, description="calculator")
        ]
        # Bypass conversational check by using an action-oriented query
        self.forge._skill_descriptions = {"kalkulator": "calculator"}
        should, reason = self.forge.should_create(
            "policz mi 2 razy 5", {"kalkulator": ["v1"]})
        self.assertFalse(should)
        self.assertEqual(reason, "reuse:kalkulator")

    def test_record_create_error(self):
        """record_create_error increments error budget."""
        self.forge.record_create_error()
        self.assertEqual(len(self.forge._error_budget.errors), 1)

    def test_stats(self):
        """stats() returns human-readable string."""
        s = self.forge.stats()
        self.assertIn("created=", s)
        self.assertIn("reused=", s)
        self.assertIn("budget=", s)

    def test_keyword_search_name_match(self):
        """Keyword search gives bonus for name substring match."""
        self.forge._skill_descriptions = {
            "web_search": "search the internet",
            "echo": "echo text back",
        }
        matches = self.forge._search_keyword("search the web", 3)
        self.assertTrue(len(matches) > 0)
        # web_search should be top match
        self.assertEqual(matches[0].name, "web_search")


# ═════════════════════════════════════════════════════════════════════
# Day 3: Pipeline Retry + Error Handling
# ═════════════════════════════════════════════════════════════════════

class MockSkillManager:
    """Mock SkillManager for pipeline tests."""

    def __init__(self):
        self._call_counts = {}
        self._results = {}  # skill_name → result or callable

    def set_result(self, skill_name, result):
        self._results[skill_name] = result

    def set_sequence(self, skill_name, results_list):
        """Set a sequence of results for successive calls."""
        self._results[skill_name] = iter(results_list)

    def exec_skill(self, name, version=None, inp=None):
        self._call_counts[name] = self._call_counts.get(name, 0) + 1
        result = self._results.get(name, {"success": True, "result": "ok"})
        if hasattr(result, '__next__'):
            try:
                return next(result)
            except StopIteration:
                return {"success": False, "error": "no more results"}
        if callable(result):
            return result(inp)
        return result

    def list_skills(self):
        return {}

    def call_count(self, name):
        return self._call_counts.get(name, 0)


class MockLLMForPipeline:
    def gen_pipeline(self, prompt, skills):
        return '{"name":"test","steps":[]}'


class TestPipelineRetry(unittest.TestCase):
    """Tests for pipeline retry, fallback, and on_error modes."""

    def setUp(self):
        self.sm = MockSkillManager()
        self.llm = MockLLMForPipeline()
        self.log = Logger("TEST")
        self.pm = PipelineManager(self.sm, self.llm, self.log)
        self.tmpdir = tempfile.mkdtemp()

    def _write_pipeline(self, name, steps):
        """Write a pipeline JSON file."""
        from cores.v1.config import PIPELINES_DIR
        PIPELINES_DIR.mkdir(parents=True, exist_ok=True)
        pf = PIPELINES_DIR / f"{name}.json"
        pf.write_text(json.dumps({"name": name, "steps": steps}))
        return pf

    def test_simple_success(self):
        """Basic pipeline with no retry — all steps succeed."""
        self.sm.set_result("echo", {"success": True, "result": "hello"})
        self._write_pipeline("test_simple", [
            {"skill": "echo", "input": {"text": "hello"}}
        ])
        result = self.pm.run_p("test_simple")
        self.assertTrue(result["success"])

    def test_step_failure_default(self):
        """Default on_error=fail stops pipeline."""
        self.sm.set_result("broken", {"success": False, "error": "boom"})
        self.sm.set_result("echo", {"success": True, "result": "hello"})
        self._write_pipeline("test_fail", [
            {"skill": "broken", "input": {}},
            {"skill": "echo", "input": {"text": "should not run"}},
        ])
        result = self.pm.run_p("test_fail")
        self.assertFalse(result["success"])
        self.assertEqual(result["failed"], 1)
        self.assertEqual(self.sm.call_count("echo"), 0)

    def test_retry_then_succeed(self):
        """Retry with eventual success."""
        self.sm.set_sequence("flaky", [
            {"success": False, "error": "try again"},
            {"success": True, "result": "ok"},
        ])
        self._write_pipeline("test_retry", [
            {"skill": "flaky", "input": {}, "retry": 2}
        ])
        result = self.pm.run_p("test_retry")
        self.assertTrue(result["success"])
        self.assertEqual(self.sm.call_count("flaky"), 2)

    def test_retry_all_fail(self):
        """Retry exhausted, all attempts fail."""
        self.sm.set_result("always_fail", {"success": False, "error": "nope"})
        self._write_pipeline("test_retry_fail", [
            {"skill": "always_fail", "input": {}, "retry": 2}
        ])
        result = self.pm.run_p("test_retry_fail")
        self.assertFalse(result["success"])
        # 1 initial + 2 retries = 3 attempts
        self.assertEqual(self.sm.call_count("always_fail"), 3)

    def test_on_error_skip(self):
        """on_error=skip continues pipeline after failure."""
        self.sm.set_result("broken", {"success": False, "error": "skip me"})
        self.sm.set_result("echo", {"success": True, "result": "continued"})
        self._write_pipeline("test_skip", [
            {"skill": "broken", "input": {}, "on_error": "skip"},
            {"skill": "echo", "input": {"text": "after skip"}},
        ])
        result = self.pm.run_p("test_skip")
        self.assertTrue(result["success"])
        self.assertEqual(self.sm.call_count("echo"), 1)
        # Check that skipped step is marked
        step1_key = "step_1"
        self.assertTrue(result["results"][step1_key].get("skipped", False))

    def test_fallback_skill(self):
        """fallback_skill used when primary fails."""
        self.sm.set_result("primary", {"success": False, "error": "dead"})
        self.sm.set_result("backup", {"success": True, "result": "fallback ok"})
        self._write_pipeline("test_fallback", [
            {"skill": "primary", "input": {}, "fallback_skill": "backup"}
        ])
        result = self.pm.run_p("test_fallback")
        self.assertTrue(result["success"])
        self.assertEqual(self.sm.call_count("backup"), 1)

    def test_fallback_also_fails(self):
        """When both primary and fallback fail, pipeline stops."""
        self.sm.set_result("primary", {"success": False, "error": "dead"})
        self.sm.set_result("backup", {"success": False, "error": "also dead"})
        self._write_pipeline("test_fb_fail", [
            {"skill": "primary", "input": {}, "fallback_skill": "backup"}
        ])
        result = self.pm.run_p("test_fb_fail")
        self.assertFalse(result["success"])

    def test_retry_plus_fallback(self):
        """Retry exhausted, then fallback succeeds."""
        self.sm.set_result("flaky", {"success": False, "error": "nope"})
        self.sm.set_result("stable", {"success": True, "result": "ok"})
        self._write_pipeline("test_retry_fb", [
            {"skill": "flaky", "input": {}, "retry": 1, "fallback_skill": "stable"}
        ])
        result = self.pm.run_p("test_retry_fb")
        self.assertTrue(result["success"])
        # 1 initial + 1 retry = 2 attempts of flaky, then 1 fallback
        self.assertEqual(self.sm.call_count("flaky"), 2)
        self.assertEqual(self.sm.call_count("stable"), 1)

    def test_output_key_propagation(self):
        """Output from one step is available in next step via template."""
        self.sm.set_result("search", {"success": True, "result": {"url": "http://example.com"}})
        self.sm.set_result("fetch", lambda inp: {
            "success": True, "result": {"text": f"fetched {inp.get('url', '')}"}
        })
        self._write_pipeline("test_chain", [
            {"skill": "search", "input": {"query": "test"},
             "output_key": "search_result"},
            {"skill": "fetch",
             "input": {"url": "{search_result.result.url}"},
             "output_key": "fetch_result"},
        ])
        result = self.pm.run_p("test_chain")
        self.assertTrue(result["success"])

    def test_backward_compat_no_retry_fields(self):
        """Old pipeline JSON without retry/on_error fields still works."""
        self.sm.set_result("echo", {"success": True, "result": "hello"})
        self._write_pipeline("test_compat", [
            {"skill": "echo", "input": {"text": "hello"}, "output_key": "step_1"}
        ])
        result = self.pm.run_p("test_compat")
        self.assertTrue(result["success"])
        self.assertIn("step_1", result["results"])

    def test_depends_on_validation(self):
        """depends_on with invalid reference logs warning but runs."""
        self.sm.set_result("echo", {"success": True, "result": "ok"})
        self._write_pipeline("test_deps", [
            {"skill": "echo", "input": {}, "id": "step_a"},
            {"skill": "echo", "input": {}, "id": "step_b",
             "depends_on": ["step_a", "nonexistent"]},
        ])
        # Should still run (warning only, not error)
        result = self.pm.run_p("test_deps")
        self.assertTrue(result["success"])

    def test_multiple_steps_mixed_errors(self):
        """Pipeline with skip and fail across multiple steps."""
        self.sm.set_result("ok_skill", {"success": True, "result": "fine"})
        self.sm.set_result("fail_skip", {"success": False, "error": "minor"})
        self.sm.set_result("fail_hard", {"success": False, "error": "critical"})
        self._write_pipeline("test_mixed", [
            {"skill": "ok_skill", "input": {}},
            {"skill": "fail_skip", "input": {}, "on_error": "skip"},
            {"skill": "ok_skill", "input": {}},
            {"skill": "fail_hard", "input": {}},  # default on_error=fail
        ])
        result = self.pm.run_p("test_mixed")
        self.assertFalse(result["success"])
        self.assertEqual(result["failed"], 4)
        # Steps 1-3 should have executed
        self.assertEqual(self.sm.call_count("ok_skill"), 2)


# ═════════════════════════════════════════════════════════════════════
# Integration: EvoEngine + SkillForge
# ═════════════════════════════════════════════════════════════════════

class TestEvoEngineForgeIntegration(unittest.TestCase):
    """Test SkillForge integration in EvoEngine.handle_request."""

    def setUp(self):
        from cores.v1.evo_engine import EvoEngine
        self.llm = MagicMock()
        self.llm.analyze_need = MagicMock(return_value={"action": "chat"})
        self.llm.chat = MagicMock(return_value="ok")
        self.sm = MagicMock()
        self.sm.list_skills.return_value = {"echo": ["v1"]}
        self.log = Logger("TEST")
        self.evo = EvoEngine(self.sm, self.llm, self.log)

    def test_forge_exists(self):
        """EvoEngine has forge attribute."""
        self.assertIsInstance(self.evo.forge, SkillForge)

    def test_chat_conversational_returns_none(self):
        """Conversational chat query returns None (no skill creation)."""
        result = self.evo.handle_request(
            "cześć, jak się masz?",
            {"echo": ["v1"]},
            analysis={"action": "chat"})
        self.assertIsNone(result)

    def test_chat_budget_exceeded_returns_none(self):
        """Budget exceeded returns None."""
        self.evo.forge._error_budget = ErrorBudget(max_errors_per_hour=0)
        # Record one error to exhaust the zero-budget
        # Actually with max=0, any query with an action intent would be blocked
        self.evo.forge._error_budget.max = 0
        result = self.evo.handle_request(
            "zbuduj skaner portów",
            {"echo": ["v1"]},
            analysis={"action": "chat"})
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
