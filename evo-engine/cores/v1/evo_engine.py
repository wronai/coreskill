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

        cpr(C.DIM, f"[EVO] {action}: {analysis.get('skill', analysis.get('name', '?'))}")

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
        """Execute skill → validate → retry (max 2 evolves for existing skills)."""
        max_retries = 2  # conservative: don't destroy working skills
        seen_errors = set()
        start_version = self.sm.latest_v(skill_name)

        for attempt in range(max_retries + 1):
            cpr(C.CYAN, f"[EVO] Running '{skill_name}' (attempt {attempt + 1}/{max_retries + 1})...")
            result = self.sm.exec_skill(skill_name, inp=inp)
            self.log.core("skill_exec", {
                "skill": skill_name, "attempt": attempt + 1,
                "success": result.get("success"), "goal": goal})

            # Success from skill → accept immediately, no over-validation
            if result.get("success"):
                inner = result.get("result", {})
                # Only reject if inner explicitly says failure
                if isinstance(inner, dict) and inner.get("success") is False:
                    error_info = inner.get("error", "inner failure")
                    cpr(C.YELLOW, f"[EVO] ✗ Partial fail: {error_info[:100]}")
                else:
                    cpr(C.GREEN, f"[EVO] ✓ Goal achieved: {goal or 'OK'}")
                    self.log.skill(skill_name, "goal_achieved", {"goal": goal})
                    return {"type": "success", "skill": skill_name,
                            "result": result, "goal": goal}
            else:
                error_info = result.get("error", "unknown error")
                cpr(C.YELLOW, f"[EVO] ✗ Failed: {error_info[:100]}")

            # Stop if max retries or same error repeats
            err_key = error_info[:80] if 'error_info' in dir() else "?"
            if err_key in seen_errors:
                cpr(C.RED, f"[EVO] Same error repeated, stopping.")
                break
            seen_errors.add(err_key)

            if attempt >= max_retries:
                break

            # Record error in evolution guard
            self.evo_guard.record_error(skill_name, error_info,
                                         self.sm.latest_v(skill_name) or "?")

            # Check if guard suggests auto-fix instead of LLM
            strategy = self.evo_guard.suggest_strategy(skill_name, error_info)
            if strategy["strategy"] == "auto_fix_imports":
                p = self.sm.skill_path(skill_name)
                if p and p.exists():
                    code = p.read_text()
                    fixed = self.sm.preflight.auto_fix_imports(code)
                    if fixed != code:
                        p.write_text(fixed)
                        cpr(C.GREEN, f"[EVO] Auto-fixed imports in {skill_name}")
                        self.log.skill(skill_name, "auto_fix_imports", {})
                        continue  # retry with fixed code

            # Diagnose → evolve (conservative)
            cpr(C.DIM, f"[EVO] Diagnosing '{skill_name}'...")
            diag = self.sm.diagnose_skill(skill_name)
            phase = diag.get("phase", "?")
            missing = diag.get("missing", [])
            alts = diag.get("alternatives", {})

            if missing:
                cpr(C.YELLOW, f"[EVO] Missing deps: {', '.join(missing)}")
                for mod, alt in alts.items():
                    hint = alt.get("code_hint", alt.get("hint", ""))
                    if hint:
                        cpr(C.DIM, f"  {mod} → {hint}")

            cpr(C.DIM, f"[EVO] Evolving '{skill_name}' (phase: {phase})...")
            ok, msg = self.sm.smart_evolve(skill_name, error_info, user_msg)
            if ok:
                cpr(C.DIM, f"[EVO] {msg}")
            else:
                cpr(C.RED, f"[EVO] Evolution failed: {msg}")
                break

        # Rollback to original version if evolution created broken ones
        cur_version = self.sm.latest_v(skill_name)
        if cur_version != start_version:
            cpr(C.DIM, f"[EVO] Rolling back {skill_name} to {start_version}")
            self.sm.rollback(skill_name)

        cpr(C.RED, f"[EVO] Could not achieve goal after {attempt + 1} attempts")
        self.log.core("goal_failed", {"skill": skill_name, "goal": goal})
        return {"type": "failed", "skill": skill_name, "goal": goal}

    def _validate_goal(self, skill_name, result, goal):
        """Validate goal from result metadata."""
        r = result.get("result", {})
        if not isinstance(r, dict):
            return True
        if r.get("spoken") is True:
            return True
        if r.get("success") is False:
            return False
        if r.get("error"):
            return False
        if r.get("success") is True:
            return True
        return True

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
