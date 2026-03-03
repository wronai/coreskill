#!/usr/bin/env python3
"""
evo-engine EvoEngine — evolutionary skill building with diagnosis loop.
"""
from .config import MAX_EVO_ITERATIONS, cpr, C
from .preflight import EvolutionGuard


class EvoEngine:
    """
    Generic evolutionary algorithm:
    1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
       diagnose (devops) → find alternatives (deps) → evolve with smart prompt
    5. Loop until goal achieved or max iterations → 6. Report to user
    """
    def __init__(self, sm, llm, logger):
        self.sm = sm
        self.llm = llm
        self.log = logger
        self.evo_guard = EvolutionGuard()

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
                return self._execute_with_validation(
                    skill_name, inp, goal, user_msg)
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
        """Pipeline: preflight → execute → validate result → reflect → retry if needed."""
        max_retries = 2
        seen_errors = set()
        start_version = self.sm.latest_v(skill_name)

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

            # Step 3: Validate result
            validation = self._validate_result(skill_name, result, goal, user_msg)
            cpr(C.DIM, f"[PIPE] Validate: {validation['verdict']} "
                       f"(reason: {validation['reason'][:60]})")
            self.log.core("pipeline_validate", {
                "skill": skill_name, "verdict": validation["verdict"],
                "reason": validation["reason"]})

            if validation["verdict"] == "success":
                cpr(C.GREEN, f"[PIPE] ✓ Goal achieved: {goal or 'OK'}")
                self.log.skill(skill_name, "goal_achieved", {"goal": goal})
                return {"type": "success", "skill": skill_name,
                        "result": result, "goal": goal}

            if validation["verdict"] == "partial":
                cpr(C.YELLOW, f"[PIPE] ~ Partial: {validation['reason'][:100]}")
                self.log.skill(skill_name, "goal_partial", {
                    "goal": goal, "reason": validation["reason"]})
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

            # Auto-fix path
            strategy = self.evo_guard.suggest_strategy(skill_name, error_info)
            cpr(C.DIM, f"[PIPE] Reflect: strategy={strategy['strategy']}")

            if strategy["strategy"] == "auto_fix_imports":
                sp = self.sm.skill_path(skill_name)
                if sp and sp.exists():
                    code = sp.read_text()
                    fixed = self.sm.preflight.auto_fix_imports(code)
                    if fixed != code:
                        sp.write_text(fixed)
                        cpr(C.GREEN, f"[PIPE] Auto-fixed imports, retrying...")
                        self.log.skill(skill_name, "auto_fix_imports", {})
                        continue

            # Diagnose → evolve
            cpr(C.DIM, f"[PIPE] Diagnose + evolve '{skill_name}'...")
            diag = self.sm.diagnose_skill(skill_name)
            phase = diag.get("phase", "?")
            missing = diag.get("missing", [])
            if missing:
                cpr(C.YELLOW, f"[PIPE] Missing deps: {', '.join(missing)}")

            ok, msg = self.sm.smart_evolve(skill_name, error_info, user_msg)
            if ok:
                cpr(C.DIM, f"[PIPE] {msg}")
            else:
                cpr(C.RED, f"[PIPE] Evolution failed: {msg}")
                break

        # Rollback if evolution created broken versions
        cur_version = self.sm.latest_v(skill_name)
        if cur_version != start_version:
            cpr(C.DIM, f"[PIPE] Rolling back {skill_name} to {start_version}")
            self.sm.rollback(skill_name)

        cpr(C.RED, f"[PIPE] Could not achieve goal after {attempt + 1} attempts")
        self.log.core("goal_failed", {"skill": skill_name, "goal": goal})
        return {"type": "failed", "skill": skill_name, "goal": goal}

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

    def evolve_skill(self, name, desc):
        """Create + evolutionary test loop for new skills."""
        cpr(C.CYAN, f"\n[EVO] === Building '{name}' ===")
        self.log.core("evo_start", {"skill": name, "desc": desc})

        cpr(C.DIM, f"[EVO] 1/{MAX_EVO_ITERATIONS}: Generating...")
        ok, msg = self.sm.create_skill(name, desc)
        if not ok:
            cpr(C.RED, f"[EVO] Create failed: {msg}")
            return False, msg
        cpr(C.GREEN, f"[EVO] {msg}")

        for i in range(MAX_EVO_ITERATIONS):
            cpr(C.DIM, f"[EVO] Testing '{name}'...")
            test_ok, test_out = self.sm.test_skill(name)

            if test_ok:
                cpr(C.GREEN, f"[EVO] ✓ '{name}' works!")
                self.log.core("evo_success", {"skill": name, "iterations": i + 1})
                return True, f"Skill '{name}' ready ({i + 1} iter)"

            if i < MAX_EVO_ITERATIONS - 1:
                cpr(C.YELLOW, f"[EVO] ✗ iter {i+1}: {test_out[:100]}")
                cpr(C.DIM, f"[EVO] Diagnosing + evolving...")
                ok, msg = self.sm.smart_evolve(name, test_out[:300])
                if not ok:
                    cpr(C.RED, f"[EVO] Evolve failed: {msg}")
                    break
                cpr(C.DIM, f"[EVO] {msg}")
            else:
                cpr(C.RED, f"[EVO] Max iterations. Error: {test_out[:100]}")

        self.log.core("evo_failed", {"skill": name})
        self.sm.rollback(name)
        return False, f"Skill '{name}' failed after {MAX_EVO_ITERATIONS} iter"
