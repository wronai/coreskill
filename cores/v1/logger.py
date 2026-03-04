#!/usr/bin/env python3
"""
evo-engine Logger — per-skill, per-core structured logging with learning.
"""
import json
from datetime import datetime, timezone

from .config import LOGS_DIR


class Logger:
    """Per-skill, per-core structured logging with learning."""

    def __init__(self, core_id="A"):
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        self.core_id = core_id

    def _write(self, path, entry):
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def _entry(self, event, data=None):
        return {"ts": datetime.now(timezone.utc).isoformat(),
                "core": self.core_id, "event": event, "data": data or {}}

    def core(self, event, data=None):
        e = self._entry(event, data)
        self._write(LOGS_DIR / f"core_{self.core_id}.log", e)
        self._write(LOGS_DIR / "core.log", e)

    def skill(self, skill_name, event, data=None):
        e = self._entry(event, data)
        self._write(LOGS_DIR / "skills" / f"{skill_name}.log", e)
        self._write(LOGS_DIR / "core.log", e)

    def read_skill_log(self, skill_name, last_n=20):
        p = LOGS_DIR / "skills" / f"{skill_name}.log"
        if not p.exists(): return []
        lines = p.read_text().strip().split("\n")[-last_n:]
        return [json.loads(l) for l in lines if l.strip()]

    def read_core_log(self, last_n=30):
        p = LOGS_DIR / f"core_{self.core_id}.log"
        if not p.exists(): return []
        lines = p.read_text().strip().split("\n")[-last_n:]
        return [json.loads(l) for l in lines if l.strip()]

    def learn_summary(self, skill_name=None):
        """Build a summary of past errors and successes for learning."""
        logs = self.read_skill_log(skill_name, 50) if skill_name else self.read_core_log(50)
        errors = [l for l in logs if "error" in l.get("event","")]
        successes = [l for l in logs if "success" in l.get("event","") or "created" in l.get("event","")]
        summary = []
        if errors:
            summary.append(f"Past errors ({len(errors)}): " +
                           "; ".join(set(str(e.get("data",{}).get("error",""))[:80] for e in errors[-5:])))
        if successes:
            summary.append(f"Successes: {len(successes)}")
        return " | ".join(summary) if summary else "No history"
