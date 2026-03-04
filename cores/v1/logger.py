#!/usr/bin/env python3
"""
CoreSkill Logger — per-skill, per-core structured logging with markdown output.

Logi są zapisywane w formacie JSON dla maszyn oraz w formacie markdown dla LLM.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

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

    def _write_markdown(self, path, entry):
        """Write log entry in markdown format for LLM consumption."""
        path.parent.mkdir(parents=True, exist_ok=True)
        md = self._format_markdown(entry)
        with open(path, "a") as f:
            f.write(md + "\n---\n\n")

    def _format_markdown(self, entry):
        """Format entry as markdown with code blocks."""
        ts = entry.get("ts", datetime.now(timezone.utc).isoformat())
        event = entry.get("event", "unknown")
        core = entry.get("core", self.core_id)
        data = entry.get("data", {})
        
        lines = [
            f"## [{ts}] Event: `{event}`",
            "",
            f"**Core:** `{core}`  ",
            f"**Timestamp:** `{ts}`",
            "",
        ]
        
        # Add data as formatted JSON in code block
        if data:
            lines.append("### Data")
            lines.append("```json")
            lines.append(json.dumps(data, indent=2, ensure_ascii=False))
            lines.append("```")
        
        return "\n".join(lines)

    def _entry(self, event, data=None):
        return {"ts": datetime.now(timezone.utc).isoformat(),
                "core": self.core_id, "event": event, "data": data or {}}

    def core(self, event, data=None):
        e = self._entry(event, data)
        # JSON format for programmatic access
        self._write(LOGS_DIR / f"core_{self.core_id}.log", e)
        self._write(LOGS_DIR / "core.log", e)
        # Markdown format for LLM consumption
        self._write_markdown(LOGS_DIR / f"core_{self.core_id}.md", e)
        self._write_markdown(LOGS_DIR / "core.md", e)

    def skill(self, skill_name, event, data=None):
        e = self._entry(event, data)
        # JSON format
        self._write(LOGS_DIR / "skills" / f"{skill_name}.log", e)
        self._write(LOGS_DIR / "core.log", e)
        # Markdown format
        self._write_markdown(LOGS_DIR / "skills" / f"{skill_name}.md", e)
        self._write_markdown(LOGS_DIR / "core.md", e)

    def read_skill_log(self, skill_name, last_n=20, format="json"):
        """Read skill logs. Format: 'json' or 'markdown'."""
        if format == "markdown":
            p = LOGS_DIR / "skills" / f"{skill_name}.md"
            if not p.exists(): return ""
            content = p.read_text()
            entries = content.split("\n---\n")
            return "\n---\n".join(entries[-last_n:])
        else:
            p = LOGS_DIR / "skills" / f"{skill_name}.log"
            if not p.exists(): return []
            lines = p.read_text().strip().split("\n")[-last_n:]
            return [json.loads(l) for l in lines if l.strip()]

    def read_core_log(self, last_n=30, format="json"):
        """Read core logs. Format: 'json' or 'markdown'."""
        if format == "markdown":
            p = LOGS_DIR / f"core_{self.core_id}.md"
            if not p.exists(): return ""
            content = p.read_text()
            entries = content.split("\n---\n")
            return "\n---\n".join(entries[-last_n:])
        else:
            p = LOGS_DIR / f"core_{self.core_id}.log"
            if not p.exists(): return []
            lines = p.read_text().strip().split("\n")[-last_n:]
            return [json.loads(l) for l in lines if l.strip()]

    def get_markdown_logs(self, skill_name=None, last_n=10):
        """Get logs formatted as markdown ready for LLM."""
        if skill_name:
            header = f"# Skill Logs: `{skill_name}` (last {last_n} entries)\n\n"
            logs = self.read_skill_log(skill_name, last_n, format="markdown")
        else:
            header = f"# Core Logs (last {last_n} entries)\n\n"
            logs = self.read_core_log(last_n, format="markdown")
        
        return header + logs if logs else header + "*No logs available*"

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
