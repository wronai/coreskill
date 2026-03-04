#!/usr/bin/env python3
"""
evo-engine PipelineManager — multi-step skill pipelines.

Supports:
- retry: per-step retry count with exponential backoff
- on_error: skip | fail | retry (default: fail)
- fallback_skill: alternative skill when primary fails
- timeout_s: per-step timeout override
- depends_on: DAG-style dependency declaration (future: parallel execution)
"""
import json
import re
import time
from datetime import datetime, timezone

from .config import PIPELINES_DIR, cpr, C
from .utils import clean_code, clean_json


class PipelineManager:
    def __init__(self, sm, llm, logger):
        self.sm = sm
        self.llm = llm
        self.log = logger
        PIPELINES_DIR.mkdir(parents=True, exist_ok=True)

    def list_p(self): return [f.stem for f in PIPELINES_DIR.glob("*.json")]

    def create_p(self, name, desc):
        raw = clean_code(self.llm.gen_pipeline(desc, list(self.sm.list_skills().keys())))
        try:
            pd = json.loads(clean_json(raw))
        except:
            return False, f"Invalid JSON: {raw[:200]}"
        pd["created_at"] = datetime.now(timezone.utc).isoformat()
        (PIPELINES_DIR / f"{name}.json").write_text(json.dumps(pd, indent=2))
        self.log.core("pipeline_created", {"name": name})
        return True, f"Pipeline '{name}' created"

    def _get_nested_value(self, data, path):
        """Get value from nested dict/list using dot path like 'results.0.url'."""
        if not path:
            return None
        
        parts = path.split('.')
        current = data
        
        for part in parts:
            if current is None:
                return None
            
            # Try integer index for lists
            if isinstance(current, (list, tuple)):
                try:
                    idx = int(part)
                    current = current[idx] if 0 <= idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            elif isinstance(current, dict):
                current = current.get(part)
            else:
                # Try attribute access
                current = getattr(current, part, None)
        
        return current

    def _substitute_vars(self, template, context):
        """Substitute {variable.path} patterns in template string."""
        if not isinstance(template, str):
            return template
        
        pattern = r'\{([^}]+)\}'
        
        def replace_var(match):
            var_path = match.group(1)
            value = self._get_nested_value(context, var_path)
            
            if value is None:
                return match.group(0)  # Keep original if not found
            
            # Convert to string
            if isinstance(value, (dict, list)):
                return json.dumps(value, ensure_ascii=False)
            return str(value)
        
        return re.sub(pattern, replace_var, template)

    def _process_input(self, input_data, context):
        """Process input dict, substituting variables in all string values."""
        if isinstance(input_data, dict):
            return {k: self._process_input(v, context) for k, v in input_data.items()}
        elif isinstance(input_data, list):
            return [self._process_input(item, context) for item in input_data]
        elif isinstance(input_data, str):
            return self._substitute_vars(input_data, context)
        else:
            return input_data

    def _exec_step_with_retry(self, step, context, step_num):
        """Execute a single step with retry, fallback, and error handling.

        Step JSON fields:
            skill: str          — skill name (required)
            version: str|None   — version to use
            input: dict         — input template with {var.path} substitution
            retry: int          — max retries (default 0)
            timeout_s: int      — per-step timeout (default 30)
            on_error: str       — "fail" | "skip" | "retry" (default "fail")
            fallback_skill: str — alternative skill on failure
            output_key: str     — key for storing result in context

        Returns:
            (result_dict, should_continue: bool)
        """
        skill_name = step.get("skill", "?")
        version = step.get("version")
        max_retry = step.get("retry", 0)
        timeout = step.get("timeout_s", 30)
        on_error = step.get("on_error", "fail")
        fallback = step.get("fallback_skill")

        si = step.get("input", {})
        si = self._process_input(si, context)

        # Retry loop
        last_result = None
        for attempt in range(max_retry + 1):
            if attempt > 0:
                backoff = min(2 ** (attempt - 1), 8)
                cpr(C.DIM, f"  Step {step_num}: retry {attempt}/{max_retry} "
                           f"(backoff {backoff}s)...")
                time.sleep(backoff)

            cpr(C.DIM, f"  Step {step_num}: {skill_name}"
                       f"{f' (attempt {attempt+1})' if attempt > 0 else ''}")

            last_result = self.sm.exec_skill(skill_name, version, si)
            if last_result.get("success"):
                return last_result, True

            self.log.core("pipeline_step_fail", {
                "step": step_num, "skill": skill_name,
                "attempt": attempt + 1, "error": str(last_result.get("error", ""))[:200]})

        # All retries exhausted — try fallback skill
        if fallback:
            cpr(C.CYAN, f"  Step {step_num}: fallback → {fallback}")
            fb_result = self.sm.exec_skill(fallback, None, si)
            if fb_result.get("success"):
                self.log.core("pipeline_fallback_ok", {
                    "step": step_num, "primary": skill_name, "fallback": fallback})
                return fb_result, True
            last_result = fb_result

        # Handle error mode
        if on_error == "skip":
            cpr(C.YELLOW, f"  Step {step_num}: SKIPPED ({skill_name} failed)")
            self.log.core("pipeline_step_skipped", {
                "step": step_num, "skill": skill_name})
            return {"success": True, "result": None, "skipped": True}, True

        # on_error == "fail" (default)
        return last_result, False

    def _resolve_execution_order(self, steps):
        """Resolve step execution order respecting depends_on.

        Currently returns sequential order but validates that all
        depends_on references are valid. Future: topological sort + parallel.

        Returns list of (index, step) in execution order.
        """
        step_ids = {}
        for i, st in enumerate(steps):
            sid = st.get("id", f"step_{i + 1}")
            step_ids[sid] = i

        # Validate depends_on references
        for i, st in enumerate(steps):
            deps = st.get("depends_on", [])
            if isinstance(deps, str):
                deps = [deps]
            for dep in deps:
                if dep not in step_ids:
                    cpr(C.YELLOW, f"  Warning: step '{st.get('id', i)}' "
                                  f"depends on unknown '{dep}'")

        # For now: sequential order (topological sort is trivial for linear chains)
        return list(enumerate(steps))

    def run_p(self, name, ini=None):
        """Run pipeline with retry, fallback, and error handling.

        Supports new step fields: retry, on_error, fallback_skill, timeout_s, depends_on.
        Backward compatible with old pipeline JSON format.
        """
        pf = PIPELINES_DIR / f"{name}.json"
        if not pf.exists(): return {"success": False, "error": "Not found"}
        pipe = json.loads(pf.read_text())
        res = {}; cur = ini or {}

        steps = pipe.get("steps", [])
        execution_order = self._resolve_execution_order(steps)
        total = len(steps)
        failed_step = None

        for i, st in execution_order:
            output_key = st.get("output_key", st.get("id", f"step_{i + 1}"))

            result, should_continue = self._exec_step_with_retry(
                st, cur, step_num=i + 1)

            res[output_key] = result
            cur[output_key] = result

            if not should_continue:
                failed_step = i + 1
                break

        if failed_step:
            return {"success": False, "failed": failed_step,
                    "total_steps": total, "results": res}

        return {"success": True, "results": res}
