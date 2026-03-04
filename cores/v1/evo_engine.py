#!/usr/bin/env python3
"""
evo-engine EvoEngine — evolutionary skill building with diagnosis loop.
"""
import sys

try:
    import nfo
    _logged = nfo.logged
except (ImportError, AttributeError):
    _logged = lambda cls: cls

import time

from .config import MAX_EVO_ITERATIONS, cpr, C
from .preflight import EvolutionGuard
from .evo_journal import EvolutionJournal


@_logged
class EvoEngine:
    """
    Generic evolutionary algorithm:
    1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
       diagnose (devops) → find alternatives (deps) → evolve with smart prompt
    5. Loop until goal achieved or max iterations → 6. Report to user
    """
    def __init__(self, sm, llm, logger, provider_chain=None):
        self.sm = sm
        self.llm = llm
        self.log = logger
        self.evo_guard = EvolutionGuard()
        self.provider_chain = provider_chain  # ProviderChain instance (optional)
        self.journal = EvolutionJournal()

    def handle_request(self, user_msg, skills, analysis=None):
        """Full pipeline: analyze → execute/create/evolve → validate. No user prompts."""
        if analysis is None:
            analysis = self.llm.analyze_need(user_msg, skills)
        action = analysis.get("action", "chat")
        goal = analysis.get("goal", "")
        inp = analysis.get("input", {})
        if not isinstance(inp, dict): inp = {}

        if action == "chat":
            return None

        skill_or_name = analysis.get('skill', analysis.get('name', '?'))
        cpr(C.DIM, f"[PIPE] Intent: {action} → {skill_or_name} | goal: {goal[:60]}")
        self.log.core("pipeline_intent", {"action": action, "skill": skill_or_name, "goal": goal})

        if action == "use":
            skill_name = analysis.get("skill")
            if skill_name and skill_name in skills:
                result = self._execute_with_validation(
                    skill_name, inp, goal, user_msg)
                # On failure, try fallback providers
                if (result and result.get("type") == "failed"
                        and self.provider_chain):
                    fallback = self._try_fallback_providers(
                        skill_name, inp, goal, user_msg)
                    if fallback:
                        return fallback
                return result
            # Skill not found - auto-create it
            if skill_name:
                cpr(C.CYAN, f"[EVO] Skill '{skill_name}' not found. Auto-creating...")
                ok, msg = self.evolve_skill(skill_name, analysis.get("description", user_msg))
                if ok:
                    return self._execute_with_validation(skill_name, inp, goal, user_msg)
                return {"type": "evo_failed", "message": msg}

        if action == "evolve":
            skill_name = analysis.get("skill", "")
            feedback = analysis.get("feedback", user_msg)
            if skill_name and skill_name in skills:
                cpr(C.CYAN, f"[EVO] Evolving '{skill_name}'...")
                ok, msg = self.sm.smart_evolve(skill_name, feedback, user_msg)
                if ok:
                    cpr(C.GREEN, f"[EVO] {msg}")
                    return self._execute_with_validation(skill_name, inp, goal, user_msg)
                return {"type": "evo_failed", "message": msg}

        if action == "create":
            name = analysis.get("name", "").replace(" ", "_").lower()
            desc = analysis.get("description", user_msg)
            if not name:
                return None
            cpr(C.CYAN, f"[EVO] Auto-creating skill '{name}'...")
            ok, msg = self.evolve_skill(name, desc)
            if ok:
                return self._execute_with_validation(name, inp, goal, user_msg)
            return {"type": "evo_failed", "message": msg}

        return None

    def _execute_with_validation(self, skill_name, inp, goal, user_msg):
        """Pipeline: preflight → execute → validate result → reflect → retry if needed.
        Now with journal tracking and quality reflection."""
        max_retries = 2
        seen_errors = set()
        start_version = self.sm.latest_v(skill_name)

        # Journal: consult history for avoid-patterns before starting
        history_avoid = []
        prev_history = self.journal.get_skill_history(skill_name, 5)
        if prev_history:
            failed = [h for h in prev_history if not h.get("success") and h.get("error")]
            history_avoid = [h["error"][:60] for h in failed[-2:]]
            if history_avoid:
                cpr(C.DIM, f"[JOURNAL] Znane problemy: {'; '.join(history_avoid[:2])}")

        # Journal: start tracking
        j_entry = self.journal.start_evolution(skill_name, goal)

        for attempt in range(max_retries + 1):
            version = self.sm.latest_v(skill_name) or "?"

            # Step 1+2: Execute (includes preflight + auto-fix inside exec_skill)
            cpr(C.CYAN, f"[PIPE] Execute: {skill_name} {version} "
                         f"(attempt {attempt + 1}/{max_retries + 1})")
            if inp:
                inp_preview = str(inp)[:80]
                cpr(C.DIM, f"[PIPE]   input: {inp_preview}")
            result = self.sm.exec_skill(skill_name, inp=inp)

            # Log preflight failure if that's what stopped execution
            if result.get("preflight"):
                cpr(C.RED, f"[PIPE] Preflight FAIL: {result.get('error', '?')[:100]}")
            self.log.core("pipeline_exec", {
                "skill": skill_name, "attempt": attempt + 1,
                "success": result.get("success"), "goal": goal})

            # Step 3: Validate result (always run normal validation first)
            validation = self._validate_result(skill_name, result, goal, user_msg)

            # Step 3b: On first attempt, check for stub code (not output — code only)
            if attempt == 0 and validation["verdict"] in ("success", "partial"):
                skill_path = self.sm.skill_path(skill_name)
                stub_check = self.evo_guard.check_execution_result(
                    skill_name, result, skill_path)
                if stub_check.get("is_stub"):
                    cpr(C.YELLOW, f"[PIPE] ⚠ Stub code: {stub_check['issue']}")
                    error_info = (f"Stub skill: {stub_check['issue']}. "
                                  f"{stub_check['suggestion']}")
                    self.evo_guard.record_error(skill_name, error_info, version)
                    validation = {"verdict": "fail", "reason": error_info}

            cpr(C.DIM, f"[PIPE] Validate: {validation['verdict']} "
                       f"(reason: {validation['reason'][:60]})")
            self.log.core("pipeline_validate", {
                "skill": skill_name, "verdict": validation["verdict"],
                "reason": validation["reason"]})

            if validation["verdict"] == "success":
                cpr(C.GREEN, f"[PIPE] ✓ Goal achieved: {goal or 'OK'}")
                self.log.skill(skill_name, "goal_achieved", {"goal": goal})
                # Journal: reflect + record success
                refl = self.journal.reflect(skill_name, result)
                self.journal.finish_evolution(
                    skill_name, success=True,
                    quality_score=refl["quality_score"],
                    reflection=refl["reflection"],
                    attempts=attempt + 1)
                if refl["improvement"] > 0.05:
                    cpr(C.DIM, f"[JOURNAL] Jakość: {refl['quality_score']:.2f} "
                               f"(+{refl['improvement']:.2f}) | {refl['speed_assessment']}")
                return {"type": "success", "skill": skill_name,
                        "result": result, "goal": goal}

            if validation["verdict"] == "partial":
                cpr(C.YELLOW, f"[PIPE] ~ Partial: {validation['reason'][:100]}")
                self.log.skill(skill_name, "goal_partial", {
                    "goal": goal, "reason": validation["reason"]})
                
                # Autonomous repair for STT empty transcription
                # Skip repair in voice_conversation mode — silence is normal
                if (skill_name == "stt" and "empty transcription" in validation["reason"]
                        and goal != "voice_conversation"):
                    cpr(C.CYAN, "[AUTO] Próbuję autonomicznej naprawy STT...")
                    fixed, msg, new_result = self._autonomous_stt_repair(skill_name, result, user_msg)
                    if fixed:
                        cpr(C.GREEN, f"[AUTO] Naprawione! {msg[:100]}")
                        self.journal.finish_evolution(
                            skill_name, success=True, quality_score=0.6,
                            reflection="Auto-repair STT", attempts=attempt + 1)
                        return {"type": "success", "skill": skill_name,
                                "result": new_result, "goal": goal}
                    else:
                        cpr(C.YELLOW, f"[AUTO] Nie udało się naprawić: {msg}")
                
                # Journal: partial = moderate quality
                refl = self.journal.reflect(skill_name, result)
                self.journal.finish_evolution(
                    skill_name, success=True,
                    quality_score=max(refl["quality_score"], 0.3),
                    reflection=f"Partial: {validation['reason'][:80]}",
                    attempts=attempt + 1)
                return {"type": "success", "skill": skill_name,
                        "result": result, "goal": goal}

            # Failed
            error_info = validation["reason"]
            cpr(C.YELLOW, f"[PIPE] ✗ Failed: {error_info[:100]}")

            # Step 4: Reflect — can we fix without evolving?
            err_key = error_info[:80]
            if err_key in seen_errors:
                cpr(C.RED, f"[PIPE] Same error repeated, stopping.")
                break
            seen_errors.add(err_key)

            if attempt >= max_retries:
                break

            # Record in guard
            self.evo_guard.record_error(skill_name, error_info, version)

            # Journal-enhanced reflection: use history to pick strategy
            j_refl = self.journal.reflect(skill_name, result, error=error_info)
            suggested = j_refl.get("suggested_strategy", "")
            avoid = j_refl.get("avoid_patterns", [])
            cpr(C.DIM, f"[JOURNAL] Sugestia: {suggested} | "
                       f"Unikaj: {'; '.join(avoid[:2]) if avoid else 'brak'}")

            # Auto-fix path (prefer journal suggestion over guard)
            strategy = self.evo_guard.suggest_strategy(skill_name, error_info)
            effective_strategy = suggested if suggested and suggested != "normal_evolve" else strategy["strategy"]
            cpr(C.DIM, f"[PIPE] Reflect: strategy={effective_strategy}")

            if effective_strategy == "auto_fix_imports":
                sp = self.sm.skill_path(skill_name)
                if sp and sp.exists():
                    code = sp.read_text()
                    fixed = self.sm.preflight.auto_fix_imports(code)
                    if fixed != code:
                        sp.write_text(fixed)
                        cpr(C.GREEN, f"[PIPE] Auto-fixed imports, retrying...")
                        self.log.skill(skill_name, "auto_fix_imports", {})
                        continue

            # Diagnose → auto-install deps → evolve
            cpr(C.DIM, f"[PIPE] Diagnose + evolve '{skill_name}'...")
            diag = self.sm.diagnose_skill(skill_name)
            phase = diag.get("phase", "?")
            missing = diag.get("missing", [])
            if missing:
                cpr(C.YELLOW, f"[PIPE] Missing deps: {', '.join(missing)}")
                # Auto-install missing Python packages
                import subprocess as _sp
                for pkg in missing:
                    cpr(C.DIM, f"[PIPE] Auto-install: pip install {pkg}...")
                    try:
                        r = _sp.run(
                            [sys.executable, "-m", "pip", "install", pkg, "-q"],
                            capture_output=True, text=True, timeout=60)
                        if r.returncode == 0:
                            cpr(C.GREEN, f"[PIPE] ✓ Installed {pkg}")
                            self.log.skill(skill_name, "auto_install_dep", {"pkg": pkg})
                        else:
                            cpr(C.DIM, f"[PIPE] pip install {pkg} failed: {r.stderr[:80]}")
                    except Exception as e:
                        cpr(C.DIM, f"[PIPE] pip install {pkg} error: {e}")

            # Include avoid-patterns in evolve prompt
            evolve_ctx = error_info
            if avoid:
                evolve_ctx += f"\nWAŻNE: unikaj tych błędów z poprzednich iteracji: {'; '.join(avoid[:3])}"

            ok, msg = self.sm.smart_evolve(skill_name, evolve_ctx, user_msg)
            if ok:
                cpr(C.DIM, f"[PIPE] {msg}")
            else:
                cpr(C.RED, f"[PIPE] Evolution failed: {msg}")
                break

        # Journal: record failure
        self.journal.finish_evolution(
            skill_name, success=False, quality_score=0.0,
            error=error_info if 'error_info' in dir() else "unknown",
            reflection=f"Failed after {attempt + 1} attempts",
            attempts=attempt + 1)

        # Rollback if evolution created broken versions
        cur_version = self.sm.latest_v(skill_name)
        if cur_version != start_version:
            cpr(C.DIM, f"[PIPE] Rolling back {skill_name} to {start_version}")
            self.sm.rollback(skill_name)

        # Record failure for provider chain auto-degradation
        if self.provider_chain and self.sm.provider_selector:
            provider = self.sm._active_provider(skill_name)
            if provider:
                self.provider_chain.record_failure(skill_name, provider,
                                                   error_info if 'error_info' in dir() else "")

        cpr(C.RED, f"[PIPE] Could not achieve goal after {attempt + 1} attempts")
        self.log.core("goal_failed", {"skill": skill_name, "goal": goal})
        return {"type": "failed", "skill": skill_name, "goal": goal}

    def _try_fallback_providers(self, skill_name, inp, goal, user_msg):
        """Try alternative providers from the chain when primary fails."""
        if not self.provider_chain or not self.sm.provider_selector:
            return None

        chain = self.provider_chain.select_with_fallback(skill_name)
        if len(chain) < 2:
            return None  # no alternatives

        # Skip first (already tried as primary)
        current = self.sm._active_provider(skill_name)
        alternatives = [p for p in chain if p != current]
        if not alternatives:
            return None

        cpr(C.CYAN, f"[CHAIN] Trying {len(alternatives)} fallback provider(s) "
                    f"for {skill_name}: {' → '.join(alternatives)}")

        for alt_provider in alternatives:
            cpr(C.DIM, f"[CHAIN] Trying {skill_name}/{alt_provider}...")
            # Get skill path for this provider
            sp = self.sm.provider_selector.get_skill_path(skill_name, alt_provider)
            if not sp or not sp.exists():
                cpr(C.DIM, f"[CHAIN] {alt_provider}: no skill file, skipping")
                continue

            try:
                # Load and run directly
                import importlib.util
                spec = importlib.util.spec_from_file_location(
                    f"chain_{skill_name}_{alt_provider}", str(sp))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                for attr in dir(mod):
                    obj = getattr(mod, attr)
                    if isinstance(obj, type) and hasattr(obj, "execute") and attr != "type":
                        result = obj().execute(inp or {})
                        validation = self._validate_result(skill_name, 
                            {"success": True, "result": result}, goal, user_msg)
                        if validation["verdict"] in ("success", "partial"):
                            self.provider_chain.record_success(skill_name, alt_provider)
                            cpr(C.GREEN, f"[CHAIN] ✓ {alt_provider} succeeded")
                            self.log.core("chain_fallback_success", {
                                "skill": skill_name, "provider": alt_provider})
                            return {"type": "success", "skill": skill_name,
                                    "result": {"success": True, "result": result},
                                    "goal": goal, "provider": alt_provider}
                        break
            except Exception as e:
                cpr(C.DIM, f"[CHAIN] {alt_provider} failed: {str(e)[:60]}")
                self.provider_chain.record_failure(skill_name, alt_provider, str(e))

        cpr(C.YELLOW, f"[CHAIN] All fallback providers exhausted for {skill_name}")
        return None

    def _validate_result(self, skill_name, result, goal, user_msg):
        """Validate whether the skill result actually achieved the goal.
        Returns {verdict: success|partial|fail, reason: str}."""
        if not result.get("success"):
            return {"verdict": "fail",
                    "reason": result.get("error", "skill returned success=False")}

        inner = result.get("result", {})
        if not isinstance(inner, dict):
            return {"verdict": "success", "reason": "non-dict result, trusting skill"}

        # Inner explicitly failed
        if inner.get("success") is False:
            return {"verdict": "fail",
                    "reason": inner.get("error", "inner result success=False")}

        # Skill-specific validation
        if skill_name == "stt":
            spoken = inner.get("spoken") or inner.get("text") or ""
            if not spoken.strip():
                return {"verdict": "partial",
                        "reason": "STT returned empty transcription (silence or mic issue)"}

        if skill_name == "shell":
            exit_code = inner.get("exit_code", 0)
            if exit_code != 0:
                stderr = inner.get("stderr", "")[:200]
                return {"verdict": "partial",
                        "reason": f"exit_code={exit_code}: {stderr}"}

        if skill_name == "tts":
            if inner.get("error"):
                return {"verdict": "fail", "reason": inner["error"]}

        return {"verdict": "success", "reason": "skill reports success"}

    def _autonomous_stt_repair(self, skill_name, result, user_msg):
        """Autonomous diagnosis and repair for STT empty transcription.
        Returns (fixed, message, new_result)."""
        import shutil, subprocess, os
        from pathlib import Path

        cpr(C.CYAN, "[AUTO] Diagnozuję problem ze STT...")

        # Check 1: vosk-transcriber exists
        if not shutil.which("vosk-transcriber"):
            cpr(C.YELLOW, "[AUTO] Brak vosk-transcriber")
            return False, "Brak vosk-transcriber. Zainstaluj: pip install vosk", result

        # Check 2: Model exists
        model_paths = [
            Path.home() / ".cache" / "vosk" / "vosk-model-small-pl-0.22",
            Path.home() / ".cache" / "vosk" / "model",
            Path("/usr/share/vosk/model"),
        ]
        has_model = any(p.exists() for p in model_paths)

        if not has_model:
            cpr(C.YELLOW, "[AUTO] Brak modelu Vosk dla PL")
            cpr(C.DIM, "[AUTO] Próbuję pobrać model...")
            try:
                # Try to download model via shell skill
                cmd = ("mkdir -p ~/.cache/vosk && cd ~/.cache/vosk && "
                       "curl -L -o model.zip 'https://alphacephei.com/vosk/models/vosk-model-small-pl-0.22.zip' && "
                       "unzip -q model.zip && rm model.zip")
                r = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
                if r.returncode == 0:
                    cpr(C.GREEN, "[AUTO] Model pobrany ✓")
                    has_model = True
                else:
                    cpr(C.YELLOW, "[AUTO] Nie udało się pobrać modelu")
            except Exception as e:
                cpr(C.YELLOW, f"[AUTO] Błąd pobierania: {e}")

        # Check 3: Microphone test
        cpr(C.DIM, "[AUTO] Testuję mikrofon...")
        try:
            test_cmd = ["arecord", "-d", "1", "-f", "S16_LE", "-r", "16000", "-c", "1", "/tmp/stt_test.wav"]
            r = subprocess.run(test_cmd, capture_output=True, timeout=5)
            if r.returncode != 0:
                cpr(C.YELLOW, "[AUTO] Mikrofon nie działa - sprawdź permissions")
                return False, "Mikrofon niedostępny. Sprawdź: arecord -l", result
            # Check if recorded file has content
            if Path("/tmp/stt_test.wav").exists():
                size = Path("/tmp/stt_test.wav").stat().st_size
                if size < 1000:
                    cpr(C.YELLOW, f"[AUTO] Mikrofon nagrywa ciszę ({size}b)")
                    return False, "Mikrofon działa ale nagrywa ciszę - sprawdź ustawienia", result
            cpr(C.GREEN, "[AUTO] Mikrofon OK ✓")
        except Exception as e:
            cpr(C.YELLOW, f"[AUTO] Test mikrofonu nieudany: {e}")

        # Check 4: Try alternative provider (whisper)
        if not has_model:
            cpr(C.CYAN, "[AUTO] Próbuję alternatywnego providera (whisper)...")
            # Check whisper availability
            if shutil.which("whisper") or Path.home().joinpath(".local/bin/whisper").exists():
                # Force whisper provider
                result = self.sm.exec_skill(skill_name, inp={"duration_s": 4, "lang": "pl", "_provider": "whisper"})
                if result.get("success"):
                    inner = result.get("result", {})
                    text = inner.get("spoken") or inner.get("text", "")
                    if text.strip():
                        cpr(C.GREEN, "[AUTO] Whisper działa! Przełączam...")
                        return True, f"Używam alternatywnego providera (whisper): {text[:50]}", result

        if has_model:
            cpr(C.GREEN, "[AUTO] Wszystko sprawdzone. Ponawiam z nowym modelem...")
            # Retry with explicit model path
            result = self.sm.exec_skill(skill_name, inp={"duration_s": 4, "lang": "pl"})
            if result.get("success"):
                inner = result.get("result", {})
                text = inner.get("spoken") or inner.get("text", "")
                if text.strip():
                    return True, f"Teraz działa: {text[:100]}", result

        return False, "Nie udało się automatycznie naprawić. Sprawdź: /diagnose stt", result

    def evolve_skill(self, name, desc):
        """Create + evolutionary test loop for new skills.
        Enhanced with journal tracking and cross-iteration reflection."""
        cpr(C.CYAN, f"\n[EVO] === Building '{name}' ===")
        self.log.core("evo_start", {"skill": name, "desc": desc})
        j_entry = self.journal.start_evolution(name, desc, strategy="create_new")
        t0 = time.time()

        cpr(C.DIM, f"[EVO] 1/{MAX_EVO_ITERATIONS}: Generating...")
        ok, msg = self.sm.create_skill(name, desc)
        if not ok:
            cpr(C.RED, f"[EVO] Create failed: {msg}")
            self.journal.finish_evolution(
                name, success=False, error=msg, reflection="Create failed")
            return False, msg
        cpr(C.GREEN, f"[EVO] {msg}")

        # Collect errors across iterations for smarter evolve prompts
        all_errors = []

        for i in range(MAX_EVO_ITERATIONS):
            cpr(C.DIM, f"[EVO] Testing '{name}'...")
            test_ok, test_out = self.sm.test_skill(name)

            if test_ok:
                elapsed = (time.time() - t0) * 1000
                cpr(C.GREEN, f"[EVO] ✓ '{name}' works! ({i + 1} iter, {elapsed:.0f}ms)")
                self.log.core("evo_success", {"skill": name, "iterations": i + 1})
                # Journal: compute quality from test + code
                sp = self.sm.skill_path(name)
                code_size = sp.stat().st_size if sp and sp.exists() else 0
                self.journal.finish_evolution(
                    name, success=True, quality_score=0.8,
                    reflection=f"Created in {i+1} iter, {elapsed:.0f}ms",
                    code_size=code_size, test_passed=True, attempts=i + 1)
                return True, f"Skill '{name}' ready ({i + 1} iter)"

            if i < MAX_EVO_ITERATIONS - 1:
                cpr(C.YELLOW, f"[EVO] ✗ iter {i+1}: {test_out[:100]}")
                all_errors.append(test_out[:200])
                cpr(C.DIM, f"[EVO] Diagnosing + evolving...")

                # Build evolve context with history of errors
                evolve_feedback = test_out[:300]
                if len(all_errors) > 1:
                    evolve_feedback += (f"\n\nPREVIOUS ERRORS (do NOT repeat):\n" +
                                        "\n".join(f"- {e[:100]}" for e in all_errors[:-1]))

                ok, msg = self.sm.smart_evolve(name, evolve_feedback)
                if not ok:
                    cpr(C.RED, f"[EVO] Evolve failed: {msg}")
                    break
                cpr(C.DIM, f"[EVO] {msg}")
            else:
                cpr(C.RED, f"[EVO] Max iterations. Error: {test_out[:100]}")

        self.log.core("evo_failed", {"skill": name})
        self.journal.finish_evolution(
            name, success=False, error=all_errors[-1][:200] if all_errors else "max_iterations",
            reflection=f"Failed {MAX_EVO_ITERATIONS} iter. Errors: {len(all_errors)}",
            attempts=MAX_EVO_ITERATIONS)
        self.sm.rollback(name)
        return False, f"Skill '{name}' failed after {MAX_EVO_ITERATIONS} iter"
