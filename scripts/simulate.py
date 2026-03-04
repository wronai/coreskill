#!/usr/bin/env python3
"""
evo-engine Docker Simulation — automated text chat that triggers
evolutionary skill creation, repair, and reflection.

Runs multiple iterations of conversations with the bot, requesting
skills that don't exist yet, forcing the system to:
  1. Detect intent via IntentEngine
  2. Auto-create missing skills via EvoEngine
  3. Test & evolve until working
  4. Reflect on quality and speed
  5. Re-use evolved skills in subsequent requests

Outputs structured logs to logs/simulation/ for analysis.

Usage:
    python scripts/simulate.py [--iterations N] [--verbose]
"""
import os
import sys
import json
import time
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Ensure project root in path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

os.environ.setdefault("EVO_TEST_MODE", "1")
os.environ.setdefault("PYTHONUNBUFFERED", "1")


# ── Simulation Scenarios ─────────────────────────────────────────────
# Each scenario is a sequence of user messages that should trigger
# specific system behaviors (create, use, evolve, chat).

SCENARIOS = [
    # --- Iteration 1: Basic skill creation ---
    {
        "name": "create_kalkulator",
        "description": "Tworzenie nowego skilla kalkulatora",
        "messages": [
            "stwórz skill kalkulator który oblicza wyrażenia matematyczne",
            "policz mi 2 + 2 * 3",
            "a ile to 100 / 7?",
        ],
        "expect_skills": ["kalkulator"],
        "expect_actions": ["create", "use", "use"],
    },
    # --- Iteration 2: System info skill ---
    {
        "name": "create_system_info",
        "description": "Skill do informacji o systemie",
        "messages": [
            "potrzebuję skill który pokaże informacje o systemie operacyjnym",
            "pokaż info o systemie",
        ],
        "expect_skills": ["system_info"],
        "expect_actions": ["create", "use"],
    },
    # --- Iteration 3: Use existing shell skill ---
    {
        "name": "use_shell",
        "description": "Użycie istniejącego skilla shell",
        "messages": [
            "uruchom ls -la /tmp",
            "echo hello world",
        ],
        "expect_skills": [],
        "expect_actions": ["use", "use"],
    },
    # --- Iteration 4: File manager skill ---
    {
        "name": "create_file_manager",
        "description": "Tworzenie skilla do zarządzania plikami",
        "messages": [
            "stwórz skill do zarządzania plikami - listowanie, kopiowanie, info o pliku",
            "wylistuj pliki w /tmp",
        ],
        "expect_skills": ["file_manager"],
        "expect_actions": ["create", "use"],
    },
    # --- Iteration 5: JSON validator skill ---
    {
        "name": "create_json_validator",
        "description": "Skill do walidacji JSON",
        "messages": [
            'zbuduj skill json_validator który sprawdza poprawność JSON',
            'zwaliduj ten json: {"name": "test", "value": 42}',
        ],
        "expect_skills": ["json_validator"],
        "expect_actions": ["create", "use"],
    },
    # --- Iteration 6: Evolve existing skill ---
    {
        "name": "evolve_echo",
        "description": "Ewolucja istniejącego skilla echo",
        "messages": [
            "ulepsz skill echo żeby obsługiwał formatowanie tekstu (bold, uppercase)",
            "echo HELLO w formacie uppercase",
        ],
        "expect_skills": [],
        "expect_actions": ["evolve", "use"],
    },
    # --- Iteration 7: Text processing ---
    {
        "name": "create_text_processor",
        "description": "Skill do przetwarzania tekstu",
        "messages": [
            "stwórz skill text_processor: zliczanie słów, zdań, znaków",
            "policz słowa w tekście: Ala ma kota a kot ma Ale",
        ],
        "expect_skills": ["text_processor"],
        "expect_actions": ["create", "use"],
    },
    # --- Iteration 8: Chat quality test ---
    {
        "name": "chat_quality",
        "description": "Test jakości rozmowy",
        "messages": [
            "cześć, jak się masz?",
            "opowiedz mi coś ciekawego o Pythonie",
            "jakie masz umiejętności?",
        ],
        "expect_skills": [],
        "expect_actions": ["chat", "chat", "chat"],
    },
    # --- Iteration 9: Password generator ---
    {
        "name": "create_password_gen",
        "description": "Generator haseł",
        "messages": [
            "stwórz skill password_generator - generuje bezpieczne hasła o zadanej długości",
            "wygeneruj hasło o długości 16 znaków",
        ],
        "expect_skills": ["password_gen"],
        "expect_actions": ["create", "use"],
    },
    # --- Iteration 10: Reuse + multi-turn ---
    {
        "name": "multi_turn_reuse",
        "description": "Ponowne użycie skilli w kontekście rozmowy",
        "messages": [
            "policz 3.14 * 2.71",
            "a teraz pokaż info o systemie",
            "wygeneruj hasło 32 znaki",
            "jakie skille mam dostępne?",
        ],
        "expect_skills": [],
        "expect_actions": ["use", "use", "use", "chat"],
    },
]


# ── Simulation Engine ────────────────────────────────────────────────

class SimulationResult:
    """Result of a single scenario execution."""
    def __init__(self, scenario_name):
        self.scenario_name = scenario_name
        self.started_at = time.time()
        self.finished_at = None
        self.messages = []  # [{msg, analysis, outcome, duration_ms}]
        self.skills_created = []
        self.skills_used = []
        self.errors = []
        self.intent_accuracy = 0.0  # % of correct intent detections
        self.success = False

    def finish(self):
        self.finished_at = time.time()

    @property
    def duration_ms(self):
        if self.finished_at:
            return (self.finished_at - self.started_at) * 1000
        return 0

    def to_dict(self):
        return {
            "scenario": self.scenario_name,
            "duration_ms": round(self.duration_ms, 1),
            "messages_count": len(self.messages),
            "skills_created": self.skills_created,
            "skills_used": self.skills_used,
            "errors": self.errors[:5],
            "intent_accuracy": round(self.intent_accuracy, 2),
            "success": self.success,
            "messages": self.messages,
        }


class Simulator:
    """Runs automated chat scenarios against the evo-engine system."""

    def __init__(self, verbose=False):
        self.verbose = verbose
        self.results = []
        self.log_dir = ROOT / "logs" / "simulation"
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Initialize core components
        self._init_system()

    def _init_system(self):
        """Initialize all evo-engine components."""
        from cores.v1.config import load_state, save_state, LOGS_DIR
        from cores.v1.logger import Logger
        from cores.v1.llm_client import LLMClient, _detect_ollama_models
        from cores.v1.intent_engine import IntentEngine
        from cores.v1.skill_manager import SkillManager
        from cores.v1.evo_engine import EvoEngine
        from cores.v1.pipeline_manager import PipelineManager
        from cores.v1.resource_monitor import ResourceMonitor
        from cores.v1.provider_selector import ProviderSelector, ProviderChain
        from cores.v1.system_identity import SystemIdentity
        from cores.v1.config import SKILLS_DIR
        from cores.v1.skill_logger import init_nfo
        from cores.v1.self_reflection import SelfReflection

        init_nfo()

        self.state = load_state()
        self.logger = Logger("SIM")

        # Resolve API key
        ak = self.state.get("openrouter_api_key") or os.environ.get("OPENROUTER_API_KEY", "")
        if not ak:
            print("[SIM] WARNING: No API key. Will use local models only.")
            ak = "sim-dummy-key"

        # Resolve model
        from cores.v1.config import get_models_from_config, DEFAULT_MODEL
        models = get_models_from_config(self.state)
        mdl = os.environ.get("EVO_MODEL") or self.state.get("model") or (
            models[0] if models else DEFAULT_MODEL)

        # Init components
        self.llm = LLMClient(ak, mdl, self.logger, models=models)
        resource_mon = ResourceMonitor()
        provider_sel = ProviderSelector(SKILLS_DIR, resource_mon)
        self.sm = SkillManager(self.llm, self.logger, provider_selector=provider_sel)
        chain = ProviderChain(provider_sel)
        self.evo = EvoEngine(self.sm, self.llm, self.logger, provider_chain=chain)
        self.intent = IntentEngine(self.llm, self.logger, self.state)
        self.identity = SystemIdentity(skill_manager=self.sm, resource_monitor=resource_mon)

        # Wire SelfReflection for auto-diagnosis on 3 consecutive failures
        reflection = SelfReflection(self.llm, self.sm, self.logger, self.state)
        self.evo.set_reflection(reflection)

        self.conv = []

        print(f"[SIM] System initialized. Model: {self.llm.model}")
        print(f"[SIM] Tiers: {self.llm.tier_info()}")
        print(f"[SIM] SelfReflection: active (auto-reflection after 3 failures)")
        sk = self.sm.list_skills()
        print(f"[SIM] Skills: {', '.join(sk.keys()) if sk else 'none'}")

    def run_scenario(self, scenario: dict) -> SimulationResult:
        """Run a single scenario."""
        name = scenario["name"]
        desc = scenario.get("description", "")
        messages = scenario["messages"]
        expect_actions = scenario.get("expect_actions", [])

        print(f"\n{'='*60}")
        print(f"[SIM] Scenariusz: {name} — {desc}")
        print(f"{'='*60}")

        result = SimulationResult(name)
        correct_intents = 0
        total_intents = 0

        for i, msg in enumerate(messages):
            print(f"\n[SIM] [{i+1}/{len(messages)}] you> {msg}")
            t0 = time.time()

            # Analyze intent
            sk = self.sm.list_skills()
            analysis = self.intent.analyze(msg, sk, self.conv)
            action = analysis.get("action", "chat")
            skill = analysis.get("skill", analysis.get("name", ""))
            goal = analysis.get("goal", "")

            # Check intent accuracy
            if i < len(expect_actions):
                expected = expect_actions[i]
                total_intents += 1
                if action == expected:
                    correct_intents += 1
                    print(f"[SIM] Intent: {action} → {skill or 'chat'} ✓")
                else:
                    print(f"[SIM] Intent: {action} → {skill or 'chat'} "
                          f"(expected: {expected}) ✗")

            # Execute through EvoEngine
            self.conv.append({"role": "user", "content": msg})
            outcome = None
            outcome_type = "chat"
            error = ""

            try:
                if action != "chat":
                    outcome = self.evo.handle_request(msg, sk, analysis=analysis)
                    if outcome:
                        outcome_type = outcome.get("type", "unknown")
                        if outcome.get("skill"):
                            result.skills_used.append(outcome["skill"])
                        if outcome_type == "success":
                            # Track created skills
                            if action == "create" and outcome.get("skill"):
                                result.skills_created.append(outcome["skill"])
                            self.conv.append({
                                "role": "assistant",
                                "content": f"Executed {outcome.get('skill', '?')} OK"
                            })
                        elif outcome_type == "evo_failed":
                            error = outcome.get("message", "")[:200]
                            result.errors.append(error)
                        elif outcome_type == "failed":
                            error = f"Failed: {outcome.get('goal', '?')}"
                            result.errors.append(error)

                if action == "chat" or not outcome:
                    # LLM chat response
                    sp = self.identity.build_system_prompt()
                    r = self.llm.chat(
                        [{"role": "system", "content": sp}] + self.conv[-12:])
                    if r:
                        self.conv.append({"role": "assistant", "content": r})
                        if self.verbose:
                            print(f"[SIM] evo> {r[:200]}")
                    outcome_type = "chat"

            except Exception as e:
                error = str(e)[:200]
                result.errors.append(error)
                print(f"[SIM] ERROR: {error}")
                outcome_type = "error"

            elapsed = (time.time() - t0) * 1000

            result.messages.append({
                "msg": msg,
                "action": action,
                "skill": skill,
                "outcome_type": outcome_type,
                "error": error,
                "duration_ms": round(elapsed, 1),
            })

            print(f"[SIM] Result: {outcome_type} ({elapsed:.0f}ms)")

        result.intent_accuracy = (
            correct_intents / total_intents * 100 if total_intents else 100)
        result.success = len(result.errors) == 0
        result.finish()

        # Save intent state
        self.intent.save()

        print(f"\n[SIM] Scenariusz '{name}' zakończony: "
              f"{'OK' if result.success else 'ERRORS'} | "
              f"{result.duration_ms:.0f}ms | "
              f"Intent accuracy: {result.intent_accuracy:.0f}% | "
              f"Skills created: {result.skills_created}")

        return result

    def run_all(self, scenarios=None, iterations=1):
        """Run all scenarios for N iterations."""
        scenarios = scenarios or SCENARIOS
        all_results = []

        for iteration in range(1, iterations + 1):
            print(f"\n{'#'*60}")
            print(f"# ITERACJA {iteration}/{iterations}")
            print(f"{'#'*60}")

            iter_results = []
            for scenario in scenarios:
                result = self.run_scenario(scenario)
                iter_results.append(result)
                self.results.append(result)

            # Save iteration results
            iter_data = {
                "iteration": iteration,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "results": [r.to_dict() for r in iter_results],
                "summary": self._iter_summary(iter_results),
            }
            out_file = self.log_dir / f"iteration_{iteration:03d}.json"
            out_file.write_text(json.dumps(iter_data, indent=2, ensure_ascii=False))
            print(f"\n[SIM] Wyniki iteracji {iteration} zapisane: {out_file}")

            # Print iteration summary
            summary = iter_data["summary"]
            print(f"\n[SIM] === Podsumowanie iteracji {iteration} ===")
            print(f"  Scenariuszy: {summary['total_scenarios']}")
            print(f"  Sukces: {summary['successful']}/{summary['total_scenarios']}")
            print(f"  Skills stworzonych: {summary['skills_created']}")
            print(f"  Średni czas: {summary['avg_duration_ms']:.0f}ms")
            print(f"  Średnia dokładność intencji: {summary['avg_intent_accuracy']:.0f}%")
            print(f"  Błędy: {summary['total_errors']}")

            all_results.extend(iter_results)

        # Final report
        self._final_report(all_results, iterations)

        # Save journal report
        journal_report = self.evo.journal.get_global_stats()
        journal_file = self.log_dir / "journal_summary.json"
        journal_file.write_text(json.dumps(journal_report, indent=2))
        print(f"\n[SIM] Journal ewolucji zapisany: {journal_file}")

        return all_results

    def _iter_summary(self, results):
        total = len(results)
        successful = sum(1 for r in results if r.success)
        all_created = []
        for r in results:
            all_created.extend(r.skills_created)
        all_errors = []
        for r in results:
            all_errors.extend(r.errors)
        durations = [r.duration_ms for r in results if r.duration_ms > 0]
        accuracies = [r.intent_accuracy for r in results]
        return {
            "total_scenarios": total,
            "successful": successful,
            "skills_created": len(all_created),
            "skills_created_names": all_created,
            "total_errors": len(all_errors),
            "errors": all_errors[:10],
            "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
            "avg_intent_accuracy": sum(accuracies) / len(accuracies) if accuracies else 0,
        }

    def _final_report(self, results, iterations):
        print(f"\n{'='*60}")
        print(f"[SIM] === RAPORT KOŃCOWY ({iterations} iteracji) ===")
        print(f"{'='*60}")

        total = len(results)
        successful = sum(1 for r in results if r.success)
        all_created = []
        for r in results:
            all_created.extend(r.skills_created)
        unique_created = list(set(all_created))
        all_errors = []
        for r in results:
            all_errors.extend(r.errors)
        durations = [r.duration_ms for r in results if r.duration_ms > 0]

        print(f"  Scenariuszy łącznie: {total}")
        print(f"  Sukces: {successful}/{total} ({successful/total*100:.0f}%)")
        print(f"  Unikalne skille stworzone: {len(unique_created)} ({unique_created})")
        print(f"  Błędy łącznie: {len(all_errors)}")
        if durations:
            print(f"  Średni czas scenariusza: {sum(durations)/len(durations):.0f}ms")
            print(f"  Najszybszy: {min(durations):.0f}ms")
            print(f"  Najwolniejszy: {max(durations):.0f}ms")

        # Speed trend across iterations
        if iterations > 1:
            iter_durations = []
            batch_size = len(SCENARIOS)
            for i in range(iterations):
                batch = results[i*batch_size:(i+1)*batch_size]
                avg = sum(r.duration_ms for r in batch) / len(batch) if batch else 0
                iter_durations.append(avg)
            if len(iter_durations) >= 2:
                improvement = (
                    (iter_durations[0] - iter_durations[-1]) / iter_durations[0] * 100
                    if iter_durations[0] > 0 else 0)
                print(f"\n  Trend prędkości:")
                for i, d in enumerate(iter_durations):
                    print(f"    Iteracja {i+1}: {d:.0f}ms")
                print(f"  Poprawa: {improvement:.1f}%")

        # Journal stats
        print(f"\n  Journal ewolucji:")
        print(f"    {self.evo.journal.format_report()}")

        # Common errors
        if all_errors:
            from collections import Counter
            common = Counter(all_errors).most_common(3)
            print(f"\n  Najczęstsze błędy:")
            for err, count in common:
                print(f"    [{count}x] {err[:80]}")

        # Recommendations
        print(f"\n  Rekomendacje:")
        if successful / total < 0.7:
            print(f"    ⚠ Niska skuteczność ({successful/total*100:.0f}%) — "
                  f"sprawdź model LLM i konfigurację")
        if all_errors:
            print(f"    ⚠ {len(all_errors)} błędów — przejrzyj logi w logs/simulation/")
        if not all_errors and successful == total:
            print(f"    ✓ Wszystkie scenariusze zakończone sukcesem!")

        # Save final report
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "iterations": iterations,
            "total_scenarios": total,
            "successful": successful,
            "success_rate": round(successful / total * 100, 1),
            "unique_skills_created": unique_created,
            "total_errors": len(all_errors),
            "avg_duration_ms": round(sum(durations) / len(durations), 0) if durations else 0,
        }
        report_file = self.log_dir / "final_report.json"
        report_file.write_text(json.dumps(report, indent=2, ensure_ascii=False))
        print(f"\n[SIM] Raport końcowy: {report_file}")


def main():
    parser = argparse.ArgumentParser(description="evo-engine simulation")
    parser.add_argument("--iterations", "-n", type=int, default=2,
                        help="Number of iteration rounds (default: 2)")
    parser.add_argument("--verbose", "-v", action="store_true",
                        help="Show LLM responses")
    parser.add_argument("--scenario", "-s", type=str, default=None,
                        help="Run only specific scenario by name")
    args = parser.parse_args()

    sim = Simulator(verbose=args.verbose)

    if args.scenario:
        scenarios = [s for s in SCENARIOS if s["name"] == args.scenario]
        if not scenarios:
            print(f"Unknown scenario: {args.scenario}")
            print(f"Available: {', '.join(s['name'] for s in SCENARIOS)}")
            sys.exit(1)
    else:
        scenarios = SCENARIOS

    results = sim.run_all(scenarios=scenarios, iterations=args.iterations)
    sys.exit(0 if all(r.success for r in results) else 1)


if __name__ == "__main__":
    main()
