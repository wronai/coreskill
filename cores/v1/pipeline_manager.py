#!/usr/bin/env python3
"""
evo-engine PipelineManager — multi-step skill pipelines.
"""
import json
import re
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

    def run_p(self, name, ini=None):
        """Run pipeline with proper variable scoping via output_key paths only."""
        pf = PIPELINES_DIR / f"{name}.json"
        if not pf.exists(): return {"success": False, "error": "Not found"}
        pipe = json.loads(pf.read_text())
        res = {}; cur = ini or {}
        
        for i, st in enumerate(pipe.get("steps", [])):
            si = st.get("input", {})
            
            # Process template variables in input
            si = self._process_input(si, cur)
            
            cpr(C.DIM, f"  Step {i + 1}: {st.get('skill')}")
            r = self.sm.exec_skill(st.get("skill"), st.get("version"), si)
            
            output_key = st.get("output_key", f"step_{i + 1}")
            res[output_key] = r
            
            if not r.get("success"):
                return {"success": False, "failed": i + 1, "results": res}
            
            # Store result under output_key for template access
            # Templates use: {output_key.result.field} or {output_key.result.results.0.field}
            cur[output_key] = r
        
        return {"success": True, "results": res}
