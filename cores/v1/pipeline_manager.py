#!/usr/bin/env python3
"""
evo-engine PipelineManager — multi-step skill pipelines.
"""
import json
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

    def run_p(self, name, ini=None):
        pf = PIPELINES_DIR / f"{name}.json"
        if not pf.exists(): return {"success": False, "error": "Not found"}
        pipe = json.loads(pf.read_text())
        res = {}; cur = ini or {}
        for i, st in enumerate(pipe.get("steps", [])):
            si = st.get("input", {})
            si.update(cur)
            cpr(C.DIM, f"  Step {i + 1}: {st.get('skill')}")
            r = self.sm.exec_skill(st.get("skill"), st.get("version"), si)
            res[st.get("output_key", f"step_{i + 1}")] = r
            if not r.get("success"):
                return {"success": False, "failed": i + 1, "results": res}
            if isinstance(r.get("result"), dict): cur.update(r["result"])
        return {"success": True, "results": res}
