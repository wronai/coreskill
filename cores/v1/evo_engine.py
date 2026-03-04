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
from .self_reflection import SelfReflection


# ─── Failure Tracker ─────────────────────────────────────────────────
class FailureTracker:
    """Tracks consecutive failures and unhandled events.
    Triggers auto-reflection after THRESHOLD consecutive occurrences."""
    THRESHOLD = 3

    def __init__(self):
        self.consecutive_failures: list = []   # recent failure descriptions
        self.unhandled_events: list = []        # events with no reaction
        self._reflection_count = 0

    def record_failure(self, skill: str, error: str, goal: str = ""):
        """Record a failure event. Returns True if threshold reached."""
        self.consecutive_failures.append({
            "skill": skill, "error": error[:200], "goal": goal,
            "ts": time.time(),
        })
        return len(self.consecutive_failures) >= self.THRESHOLD

    def record_unhandled(self, user_msg: str, analysis: dict = None):
        """Record an unhandled event (no reaction). Returns True if threshold reached."""
        self.unhandled_events.append({
            "msg": user_msg[:200],
            "analysis": str(analysis)[:100] if analysis else "",
            "ts": time.time(),
        })
        return len(self.unhandled_events) >= self.THRESHOLD

    def record_success(self):
        """Reset failure streak on success."""
        self.consecutive_failures.clear()

    def should_reflect(self) -> bool:
        """Check if auto-reflection should trigger."""
        return (len(self.consecutive_failures) >= self.THRESHOLD
                or len(self.unhandled_events) >= self.THRESHOLD)

    def consume_failures(self) -> dict:
        """Return accumulated failure context and reset counters."""
        ctx = {
            "failures": list(self.consecutive_failures),
            "unhandled": list(self.unhandled_events),
            "reflection_number": self._reflection_count + 1,
        }
        self._reflection_count += 1
        self.consecutive_failures.clear()
        self.unhandled_events.clear()
        return ctx

    def summary(self) -> str:
        return (f"failures={len(self.consecutive_failures)}/"
                f"{self.THRESHOLD}, unhandled={len(self.unhandled_events)}/"
                f"{self.THRESHOLD}, reflections={self._reflection_count}")


@_logged
class EvoEngine:
    """
    Generic evolutionary algorithm:
    1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
       diagnose (devops) → find alternatives (deps) → evolve with smart prompt
    5. Loop until goal achieved or max iterations → 6. Report to user
    
    Auto-reflection: after 3 consecutive failures or 3 unhandled events,
    triggers SelfReflection diagnostic + auto-fix cycle.
    """
    def __init__(self, sm, llm, logger, provider_chain=None, state=None):
        self.sm = sm
        self.llm = llm
        self.log = logger
        self.evo_guard = EvolutionGuard()
        self.provider_chain = provider_chain  # ProviderChain instance (optional)
        self.journal = EvolutionJournal()
        self.reflection = None  # Injected via set_reflection()
        self.failure_tracker = FailureTracker()

    def set_reflection(self, reflection: SelfReflection):
        """Inject SelfReflection instance for stall/timeout detection."""
        self.reflection = reflection

    def handle_request(self, user_msg, skills, analysis=None):
        """Full pipeline: analyze → execute/create/evolve → validate. No user prompts."""
        if analysis is None:
            analysis = self.llm.analyze_need(user_msg, skills)
        action = analysis.get("action", "chat")
        goal = analysis.get("goal", "")
        inp = analysis.get("input", {})
        if not isinstance(inp, dict): inp = {}

        if action == "chat":
            # AUTO-CREATE SKILL: when intent is unknown/chat - create skill to answer this query
            new_skill_name = self._generate_skill_name(user_msg)
            skill_desc = f"Skill odpowiadający na zapytanie: '{user_msg}'. " \
                          f"Zadanie: odpowiedzieć na to pytanie/potrzebę użytkownika. " \
                          f"Funkcjonalność: {goal or 'obsługa tego typu zapytań'}"
            
            cpr(C.CYAN, f"[AUTO-CREATE] Nieznane zapytanie - tworzę skill '{new_skill_name}'...")
            
            # Auto-create the skill
            ok, msg = self.evolve_skill(new_skill_name, skill_desc)
            if ok:
                cpr(C.GREEN, f"[AUTO-CREATE] ✓ Skill '{new_skill_name}' stworzony!")
                cpr(C.DIM, f"[AUTO-CREATE] Wykonuję nowy skill...")
                # Execute the newly created skill with the original input
                inp = {"text": user_msg}
                return self._execute_with_validation(new_skill_name, inp, user_msg, user_msg)
            else:
                cpr(C.YELLOW, f"[AUTO-CREATE] ✗ Nie udało się stworzyć: {msg}")
                return None  # Fallback to normal chat if creation fails

        # Check if we should trigger auto-reflection before proceeding
        if self.failure_tracker.should_reflect() and self.reflection:
            self._run_auto_reflection("pre_request")

        skill_or_name = analysis.get('skill', analysis.get('name', '?'))
        cpr(C.DIM, f"[PIPE] Intent: {action} → {skill_or_name} | goal: {goal[:60]}")
        self.log.core("pipeline_intent", {"action": action, "skill": skill_or_name, "goal": goal})

        if action == "use":
            skill_name = analysis.get("skill")
            provider = analysis.get("provider")  # Get provider from analysis if specified
            if skill_name and skill_name in skills:
                result = self._execute_with_validation(
                    skill_name, inp, goal, user_msg, provider=provider)
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
                    return self._execute_with_validation(skill_name, inp, goal, user_msg, provider=provider)
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

        # Track unhandled — no action taken for non-chat request
        self.failure_tracker.record_unhandled(user_msg, analysis)
        if self.failure_tracker.should_reflect() and self.reflection:
            self._run_auto_reflection("unhandled")
        return None

    def _run_auto_reflection(self, trigger_skill: str):
        """Run auto-reflection after 3 consecutive failures or unhandled events.
        Diagnoses system, attempts auto-fixes, logs results to journal."""
        ctx = self.failure_tracker.consume_failures()
        n_fail = len(ctx["failures"])
        n_unhandled = len(ctx["unhandled"])
        reflection_num = ctx["reflection_number"]

        cpr(C.YELLOW, f"\n[REFLECT] === Auto-refleksja #{reflection_num} ===")
        cpr(C.YELLOW, f"[REFLECT] Powód: {n_fail} błędów, {n_unhandled} nieobsłużonych")
        self.log.core("auto_reflection_trigger", {
            "reflection_num": reflection_num,
            "failures": n_fail, "unhandled": n_unhandled,
            "trigger": trigger_skill,
        })

        # Determine which skill to focus diagnostics on
        focus_skill = ""
        last_error = ""
        if ctx["failures"]:
            # Most recent failing skill
            focus_skill = ctx["failures"][-1].get("skill", "")
            last_error = ctx["failures"][-1].get("error", "")
            # Show failure summary
            skill_counts = {}
            for f in ctx["failures"]:
                s = f.get("skill", "?")
                skill_counts[s] = skill_counts.get(s, 0) + 1
            for s, c in skill_counts.items():
                cpr(C.DIM, f"[REFLECT]   {s}: {c}x failed")

        if ctx["unhandled"]:
            cpr(C.DIM, f"[REFLECT]   {n_unhandled} wiadomości bez reakcji")
            for u in ctx["unhandled"][-2:]:
                cpr(C.DIM, f"[REFLECT]     ‘{u['msg'][:60]}’")

        # Try event bus path first (decoupled)
        overall_status = "unknown"
        fixes_applied = []
        requires_user = []
        bus_handled = False
        try:
            from .event_bus import reflection_needed, ReflectionNeededEvent, _HAS_BLINKER
            if _HAS_BLINKER and reflection_needed.receivers:
                evt = ReflectionNeededEvent(
                    trigger=trigger_skill,
                    failures=ctx["failures"],
                    unhandled=ctx["unhandled"],
                    reflection_number=reflection_num,
                )
                results = reflection_needed.send(self, event=evt)
                for _, diag_result in results:
                    if diag_result:
                        overall_status = diag_result.overall_status
                        fixes_applied = diag_result.fixes_applied
                        requires_user = diag_result.requires_user
                        bus_handled = True
                        break
        except ImportError:
            pass

        # Fallback: direct call (backward compat when bus not wired)
        if not bus_handled and self.reflection:
            report = self.reflection.run_diagnostic(focus_skill, last_error)
            overall_status = report.overall_status
            requires_user = report.requires_user
            if report.auto_fixable:
                cpr(C.CYAN, "[REFLECT] Próbuję automatycznych napraw...")
                fixes_applied = self.reflection.attempt_auto_fix(report)
                for fix in fixes_applied:
                    cpr(C.GREEN, f"[REFLECT] ✓ {fix}")

        # Log reflection to journal
        self.journal.start_evolution(
            focus_skill or "system",
            f"auto_reflection_{reflection_num}",
            strategy="reflection")
        self.journal.finish_evolution(
            focus_skill or "system",
            success=bool(fixes_applied),
            quality_score=0.5 if fixes_applied else 0.1,
            reflection=f"Auto-reflection #{reflection_num}: "
                       f"{overall_status}, "
                       f"{len(fixes_applied)} fixes applied",
            error=last_error[:200] if not fixes_applied else "")

        cpr(C.CYAN, f"[REFLECT] Status: {overall_status} | "
                    f"Naprawy: {len(fixes_applied)} | "
                    f"Do zrobienia: {len(requires_user)}")
        cpr(C.DIM, f"[REFLECT] === Koniec auto-refleksji #{reflection_num} ===\n")

        self.log.core("auto_reflection_done", {
            "reflection_num": reflection_num,
            "status": overall_status,
            "fixes": len(fixes_applied),
            "requires_user": len(requires_user),
        })

    def _execute_with_validation(self, skill_name, inp, goal, user_msg, provider=None):
        """Pipeline: preflight → execute → validate → reflect → retry.
        Now split into focused sub-methods for maintainability."""
        max_retries = 2
        seen_errors = set()
        start_version = self.sm.latest_v(skill_name)

        # Phase 1: Setup
        j_entry, history_avoid = self._exec_prepare(skill_name, goal)

        # Phase 2: Retry loop
        for attempt in range(max_retries + 1):
            version = self.sm.latest_v(skill_name) or "?"
            effective_inp = inp if inp else {"text": user_msg}

            # Execute single attempt
            result, validation = self._exec_attempt(
                skill_name, effective_inp, goal, user_msg, attempt, max_retries, version, provider)

            # Handle outcomes
            if validation["verdict"] == "success":
                return self._exec_handle_success(
                    skill_name, result, goal, attempt, start_version)

            if validation["verdict"] == "partial":
                outcome = self._exec_handle_partial(
                    skill_name, result, validation, goal, user_msg, attempt, start_version)
                if outcome:
                    return outcome
                # If partial handler returns None, continue to failure handling

            # Failed - attempt recovery
            error_info = validation["reason"]
            retry = self._exec_handle_failure(
                skill_name, error_info, seen_errors, attempt, max_retries,
                effective_inp, user_msg, history_avoid, version)
            if not retry:
                break

        # Phase 3: Finalize failure
        return self._exec_finalize_failure(
            skill_name, goal, attempt, start_version, seen_errors)

    def _exec_prepare(self, skill_name, goal):
        """Phase 1: Journal consultation and setup."""
        # Journal: consult history for avoid-patterns before starting
        history_avoid = []
        prev_history = self.journal.get_skill_history(skill_name, 5)
        if prev_history:
            import time as _t
            cutoff = _t.time() - 3600
            failed = [h for h in prev_history
                      if not h.get("success") and h.get("error")
                      and h.get("timestamp", 0) > cutoff]
            history_avoid = [h["error"][:60] for h in failed[-2:]]
            if history_avoid:
                cpr(C.DIM, f"[JOURNAL] Znane problemy: {'; '.join(history_avoid[:2])}")

        # Journal: start tracking
        j_entry = self.journal.start_evolution(skill_name, goal)
        return j_entry, history_avoid

    def _exec_attempt(self, skill_name, effective_inp, goal, user_msg,
                      attempt, max_retries, version, provider=None):
        """Execute single attempt with validation."""
        cpr(C.CYAN, f"[PIPE] Execute: {skill_name} {version} "
                     f"(attempt {attempt + 1}/{max_retries + 1})")
        if effective_inp:
            inp_preview = str(effective_inp)[:80]
            cpr(C.DIM, f"[PIPE]   input: {inp_preview}")

        # Start reflection tracking for stall/timeout detection
        if self.reflection:
            self.reflection.start_operation(f"{skill_name}:{goal}")

        result = self.sm.exec_skill(skill_name, inp=effective_inp, provider=provider)

        # End reflection tracking
        if self.reflection:
            exec_success = result.get("success", False) and not result.get("preflight")
            self.reflection.end_operation(success=exec_success, error=result.get("error", ""))

        # Log preflight failure if that's what stopped execution
        if result.get("preflight"):
            cpr(C.RED, f"[PIPE] Preflight FAIL: {result.get('error', '?')[:100]}")
        self.log.core("pipeline_exec", {
            "skill": skill_name, "attempt": attempt + 1,
            "success": result.get("success"), "goal": goal})

        # Validate result
        validation = self._validate_result(skill_name, result, goal, user_msg)

        # On first attempt, check for stub code
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

        # Track consecutive outcomes for auto-reflection
        if self.reflection and not (
                skill_name == "stt" and goal == "voice_conversation"
                and validation["verdict"] == "partial"):
            is_success = validation["verdict"] == "success"
            is_partial = validation["verdict"] == "partial"
            self.reflection.record_skill_outcome(
                skill_name, success=is_success, partial=is_partial,
                error=validation.get("reason", ""))

        return result, validation

    def _exec_handle_success(self, skill_name, result, goal, attempt, start_version):
        """Handle successful execution outcome."""
        cpr(C.GREEN, f"[PIPE] ✓ Goal achieved: {goal or 'OK'}")
        self.log.skill(skill_name, "goal_achieved", {"goal": goal})
        self.failure_tracker.record_success()

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

    def _exec_handle_partial(self, skill_name, result, validation, goal,
                            user_msg, attempt, start_version):
        """Handle partial success outcome. May auto-create skill or repair."""
        cpr(C.YELLOW, f"[PIPE] ~ Partial: {validation['reason'][:100]}")
        self.log.skill(skill_name, "goal_partial", {
            "goal": goal, "reason": validation["reason"]})

        # AUTO-CREATE: web_search empty results → create dedicated skill
        if skill_name == "web_search" and "empty results" in validation["reason"]:
            new_skill_name = self._generate_skill_name(user_msg)
            skill_desc = f"Skill odpowiadający na zapytanie: '{user_msg}'. " \
                          f"Poprzedni skill '{skill_name}' zwrócił puste wyniki. " \
                          f"Wymagana funkcjonalność: {goal}"

            cpr(C.CYAN, f"[AUTO-CREATE] Brak wyników z '{skill_name}'.")
            cpr(C.CYAN, f"[AUTO-CREATE] Automatycznie tworzę skill '{new_skill_name}'...")

            ok, msg = self.evolve_skill(new_skill_name, skill_desc)
            if ok:
                cpr(C.GREEN, f"[AUTO-CREATE] ✓ Skill '{new_skill_name}' stworzony!")
                cpr(C.DIM, f"[AUTO-CREATE] Wykonuję nowy skill...")
                return self._execute_with_validation(new_skill_name,
                    {"text": user_msg}, goal, user_msg)
            else:
                cpr(C.YELLOW, f"[AUTO-CREATE] ✗ Nie udało się stworzyć: {msg}")

        # Autonomous repair for STT empty transcription
        if (skill_name == "stt" and "empty transcription" in validation["reason"]
                and goal != "voice_conversation"):
            cpr(C.CYAN, "[AUTO] Próbuję autonomicznej naprawy STT...")
            fixed, msg, new_result = self._autonomous_stt_repair(
                skill_name, result, user_msg)
            if fixed:
                cpr(C.GREEN, f"[AUTO] Naprawione! {msg[:100]}")
                self.journal.finish_evolution(
                    skill_name, success=True, quality_score=0.6,
                    reflection="Auto-repair STT", attempts=attempt + 1)
                return {"type": "success", "skill": skill_name,
                        "result": new_result, "goal": goal}
            else:
                cpr(C.YELLOW, f"[AUTO] Nie udało się naprawić: {msg}")

        # Return partial as success (with moderate quality)
        refl = self.journal.reflect(skill_name, result)
        self.journal.finish_evolution(
            skill_name, success=True,
            quality_score=max(refl["quality_score"], 0.3),
            reflection=f"Partial: {validation['reason'][:80]}",
            attempts=attempt + 1)
        return {"type": "success", "skill": skill_name,
                "result": result, "goal": goal}

    def _exec_handle_failure(self, skill_name, error_info, seen_errors,
                            attempt, max_retries, effective_inp, user_msg,
                            history_avoid, version):
        """Handle failure outcome. Returns True if should retry."""
        cpr(C.YELLOW, f"[PIPE] ✗ Failed: {error_info[:100]}")

        # Check for repeated errors
        err_key = error_info[:80]
        if err_key in seen_errors:
            cpr(C.RED, f"[PIPE] Same error repeated, stopping.")
            return False
        seen_errors.add(err_key)

        if attempt >= max_retries:
            return False

        # Record in guard
        self.evo_guard.record_error(skill_name, error_info, version)

        # Journal-enhanced reflection
        j_refl = self.journal.reflect(skill_name, {"error": error_info}, error=error_info)
        suggested = j_refl.get("suggested_strategy", "")
        avoid = j_refl.get("avoid_patterns", [])
        cpr(C.DIM, f"[JOURNAL] Sugestia: {suggested} | "
                   f"Unikaj: {'; '.join(avoid[:2]) if avoid else 'brak'}")

        # Determine strategy
        strategy = self.evo_guard.suggest_strategy(skill_name, error_info)
        effective_strategy = suggested if suggested and suggested != "normal_evolve" else strategy["strategy"]
        cpr(C.DIM, f"[PIPE] Reflect: strategy={effective_strategy}")

        # Auto-fix imports
        if effective_strategy == "auto_fix_imports":
            sp = self.sm.skill_path(skill_name)
            if sp and sp.exists():
                code = sp.read_text()
                fixed = self.sm.preflight.auto_fix_imports(code)
                if fixed != code:
                    sp.write_text(fixed)
                    cpr(C.GREEN, f"[PIPE] Auto-fixed imports, retrying...")
                    self.log.skill(skill_name, "auto_fix_imports", {})
                    return True

        # Diagnose and evolve
        cpr(C.DIM, f"[PIPE] Diagnose + evolve '{skill_name}'...")
        diag = self.sm.diagnose_skill(skill_name)

        # Check if diagnostic tool itself failed
        if diag.get("phase") in ("diagnostic_tool_failed", "diagnostic_validation_error"):
            cpr(C.YELLOW, f"[PIPE] Diagnostic tool failed: {diag.get('error', 'unknown')}")
            cpr(C.CYAN, f"[PIPE] Attempting to repair devops diagnostic tool...")
            # Try to repair devops itself
            ok, msg = self.sm.smart_evolve("devops", "Fix validation error - add proper input validation for empty path parameter")
            if ok:
                cpr(C.GREEN, f"[PIPE] Repaired devops: {msg}")
            # Retry original skill with fallback diagnosis
            cpr(C.DIM, f"[PIPE] Retrying '{skill_name}' with fallback diagnosis...")
            # Use raw test as fallback
            diag = {"phase": "runtime", "error": error_info}

        missing = diag.get("missing", [])

        # Auto-install missing deps
        if missing:
            cpr(C.YELLOW, f"[PIPE] Missing deps: {', '.join(missing)}")
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

        # Build evolve context
        evolve_ctx = error_info
        evolve_ctx += f"\nActual input: {str(effective_inp)[:200]}"
        evolve_ctx += ("\nIMPORTANT: params always has 'text' key. "
                       "Extract using regex/parsing. "
                       "Do NOT require specific param names.")
        if avoid:
            evolve_ctx += f"\nWAŻNE: unikaj tych błędów: {'; '.join(avoid[:3])}"

        ok, msg = self.sm.smart_evolve(skill_name, evolve_ctx, user_msg)
        if ok:
            cpr(C.DIM, f"[PIPE] {msg}")
            return True
        else:
            cpr(C.RED, f"[PIPE] Evolution failed: {msg}")
            return False

    def _exec_finalize_failure(self, skill_name, goal, attempt,
                               start_version, seen_errors):
        """Phase 3: Finalize failure - rollback, record, reflect."""
        # Get error info from seen_errors (last added)
        error_info = list(seen_errors)[-1] if seen_errors else "unknown"

        # Journal: record failure
        self.journal.finish_evolution(
            skill_name, success=False, quality_score=0.0,
            error=error_info,
            reflection=f"Failed after {attempt + 1} attempts",
            attempts=attempt + 1)

        # Rollback if evolution created broken versions
        cur_version = self.sm.latest_v(skill_name)
        if cur_version != start_version:
            cpr(C.DIM, f"[PIPE] Rolling back {skill_name} to {start_version}")
            self.sm.rollback(skill_name)

        # Record failure for provider chain
        if self.provider_chain and self.sm.provider_selector:
            provider = self.sm._active_provider(skill_name)
            if provider:
                self.provider_chain.record_failure(skill_name, provider, error_info)

        cpr(C.RED, f"[PIPE] Could not achieve goal after {attempt + 1} attempts")
        self.log.core("goal_failed", {"skill": skill_name, "goal": goal})

        # Track failure for auto-reflection
        threshold_hit = self.failure_tracker.record_failure(skill_name, error_info, goal)
        if threshold_hit and self.reflection:
            self._run_auto_reflection(skill_name)
        elif self.reflection:
            cpr(C.DIM, f"[REFLECT] Failures: {self.failure_tracker.summary()}")

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
            
            # STT v2: hardware check failed
            if inner.get("hardware_ok") is False:
                error_msg = inner.get("error", "Unknown hardware error")
                return {"verdict": "fail",
                        "reason": f"STT hardware error: {error_msg}"}
            
            # STT v2: no sound detected
            if inner.get("has_sound") is False:
                db_level = inner.get("audio_level_db", -999)
                warning = inner.get("warning", "No sound detected")
                return {"verdict": "partial",
                        "reason": f"STT silence detected ({db_level:.1f}dB). Check microphone and speak louder."}
            
            # Legacy: empty transcription (should not happen with v2, but keep for compatibility)
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

        # web_search: empty results for local network queries should trigger new skill suggestion
        if skill_name == "web_search":
            results = inner.get("results", [])
            query = inner.get("query", "").lower()
            # Check if query is about local network (cameras, devices, scanning)
            _local_net_keywords = (
                "kamer", "camera", "rtsp", "onvif", "sieć lokal", "local network",
                "lan ", "lan:", "skanuj", "scan", "urządzenia w sieci", "devices in network",
                "ip w sieci", "ip in network", "drukark", "printer", "router",
            )
            is_local_net_query = any(kw in query for kw in _local_net_keywords)
            if is_local_net_query and (not results or len(results) == 0):
                return {
                    "verdict": "partial",
                    "reason": f"web_search: no results for local network query '{query[:50]}'. "
                              f"Requires dedicated network scanner skill."
                }
            # Generic empty results - still partial but less urgent
            if not results or len(results) == 0:
                return {
                    "verdict": "partial",
                    "reason": f"web_search: empty results for '{query[:50]}'"
                }

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

    def _generate_skill_name(self, user_msg: str) -> str:
        """Generate snake_case skill name from user query using LLM or fallback to simple extraction."""
        import re
        
        # Try to use LLM to generate a good name
        try:
            prompt = f"""Generate a short, descriptive snake_case skill name for this user request:
"{user_msg}"

Rules:
- Use only lowercase letters, numbers, and underscores
- Max 30 characters
- Should describe WHAT the skill does
- No verbs like "get", "find", "search" - just the topic
- Examples: "camera_scanner", "weather_forecast", "currency_converter", "ip_geolocation"

Return ONLY the name, nothing else:"""
            
            response = self.llm.chat([
                {"role": "system", "content": "You generate short snake_case skill names."},
                {"role": "user", "content": prompt}
            ], temperature=0.3, max_tokens=50)
            
            # Clean up the response
            name = response.strip().lower()
            # Remove any non-alphanumeric except underscore
            name = re.sub(r'[^a-z0-9_]', '', name)
            # Remove leading/trailing underscores
            name = name.strip('_')
            
            if name and len(name) >= 3:
                return name[:30]
        except Exception:
            pass
        
        # Fallback: simple keyword extraction
        # Remove common stop words and extract key terms
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 
                      'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had',
                      'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might',
                      'co', 'jest', 'są', 'w', 'na', 'z', 'do', 'dla', 'i', 'lub', 'ale', 
                      'który', 'która', 'jak', 'co', 'tym', 'tych', 'te', 'ta', 'to'}
        
        words = re.findall(r'\b[a-zA-Z_]+\b', user_msg.lower())
        key_words = [w for w in words if w not in stop_words and len(w) > 2]
        
        if key_words:
            # Take first 2-3 significant words
            name = '_'.join(key_words[:3])
            name = re.sub(r'[^a-z0-9_]', '', name)
            return name[:30] if name else "custom_skill"
        
        return "custom_skill"
