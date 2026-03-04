#!/usr/bin/env python3
"""
evo-engine skill_logger — nfo-based decorator logging for all skills.

Captures all skill events (execute, health_check, errors, timing)
via nfo decorators for anomaly analysis and quick diagnosis.

Usage in skills:
    import nfo
    @nfo.logged
    class MySkill:
        def execute(self, params): ...

Auto-injection (all skills, no code changes needed):
    Called from skill_manager._load_and_run() via inject_logging(mod)
"""
try:
    import nfo
except ImportError:
    nfo = None
from pathlib import Path

from .config import LOGS_DIR

# ─── Paths ────────────────────────────────────────────────────────────
_NFO_DIR = LOGS_DIR / "nfo"
_NFO_DIR.mkdir(parents=True, exist_ok=True)
_SQLITE_PATH = _NFO_DIR / "skills.db"
_JSON_PATH = _NFO_DIR / "skills.jsonl"

# ─── Singleton: configure once ────────────────────────────────────────
_configured = False


def init_nfo():
    """Configure nfo logging for the entire evo-engine.
    Call once at startup. Idempotent."""
    global _configured
    if nfo is None:
        return None
    if _configured:
        return nfo.get_logger("evo")
    _configured = True

    logger = nfo.configure(
        name="evo",
        level="DEBUG",
        sinks=[
            f"sqlite:{_SQLITE_PATH}",
            f"json:{_JSON_PATH}",
        ],
        propagate_stdlib=False,
    )
    return logger


def inject_logging(mod, skill_name=None):
    """Inject nfo decorator logging into a dynamically loaded skill module.
    Wraps all public functions with @nfo.log_call automatically.
    Safe to call on any module — skips already-wrapped functions."""
    if nfo is None:
        return
    init_nfo()
    try:
        nfo.auto_log(mod, level="DEBUG", include_private=False)
    except Exception:
        pass


def get_skill_logger(skill_name):
    """Get a named nfo logger for a specific skill."""
    if nfo is None:
        return None
    init_nfo()
    return nfo.get_logger(f"evo.skill.{skill_name}")


# ─── Anomaly queries ─────────────────────────────────────────────────
def query_skill_errors(skill_name=None, last_n=20):
    """Query recent errors from nfo SQLite sink for anomaly analysis."""
    import sqlite3
    if not _SQLITE_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(_SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        if skill_name:
            rows = conn.execute(
                "SELECT * FROM logs WHERE level >= 40 AND function LIKE ? "
                "ORDER BY timestamp DESC LIMIT ?",
                (f"%{skill_name}%", last_n)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM logs WHERE level >= 40 "
                "ORDER BY timestamp DESC LIMIT ?",
                (last_n,)
            ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def query_slow_calls(threshold_ms=2000, last_n=10):
    """Find slow skill calls (potential performance anomalies)."""
    import sqlite3
    if not _SQLITE_PATH.exists():
        return []
    try:
        conn = sqlite3.connect(str(_SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM logs WHERE duration_ms > ? "
            "ORDER BY duration_ms DESC LIMIT ?",
            (threshold_ms, last_n)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []


def skill_health_summary(skill_name):
    """Build a health summary from nfo logs for a specific skill."""
    import sqlite3
    if not _SQLITE_PATH.exists():
        return {"skill": skill_name, "status": "no_data"}
    try:
        conn = sqlite3.connect(str(_SQLITE_PATH))
        total = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE function LIKE ?",
            (f"%{skill_name}%",)
        ).fetchone()[0]
        errors = conn.execute(
            "SELECT COUNT(*) FROM logs WHERE function LIKE ? AND level >= 40",
            (f"%{skill_name}%",)
        ).fetchone()[0]
        avg_ms = conn.execute(
            "SELECT AVG(duration_ms) FROM logs WHERE function LIKE ? "
            "AND duration_ms IS NOT NULL",
            (f"%{skill_name}%",)
        ).fetchone()[0]
        conn.close()
        error_rate = errors / total if total > 0 else 0
        return {
            "skill": skill_name,
            "total_calls": total,
            "errors": errors,
            "error_rate": round(error_rate, 3),
            "avg_duration_ms": round(avg_ms, 1) if avg_ms else None,
            "status": "unhealthy" if error_rate > 0.3 else "healthy",
        }
    except Exception as e:
        return {"skill": skill_name, "status": "error", "detail": str(e)}


# ─── Markdown Export Functions ───────────────────────────────────────
def get_markdown_logs(last_n: int = 50, skill_name: str = None) -> str:
    """Get logs formatted as markdown ready for LLM with code blocks."""
    import sqlite3
    if not _SQLITE_PATH.exists():
        return "# Skill Logs\n\n*No logs available*"
    
    try:
        conn = sqlite3.connect(str(_SQLITE_PATH))
        conn.row_factory = sqlite3.Row
        
        if skill_name:
            rows = conn.execute(
                "SELECT * FROM logs WHERE function LIKE ? ORDER BY timestamp DESC LIMIT ?",
                (f"%{skill_name}%", last_n)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM logs ORDER BY timestamp DESC LIMIT ?",
                (last_n,)
            ).fetchall()
        conn.close()
        
        if not rows:
            return "# Skill Logs\n\n*No logs found*"
        
        lines = [f"# Skill Logs (last {len(rows)} entries)\n"]
        
        for row in rows:
            r = dict(row)
            ts = r.get("timestamp", "unknown")
            func = r.get("function_name", "unknown")
            level = r.get("level", "INFO")
            
            lines.append(f"## [{ts}] `{func}` - Level {level}")
            lines.append("")
            
            # Exception as code block
            if r.get("exception"):
                lines.append("### Exception")
                lines.append("```")
                lines.append(r["exception"][:500])
                lines.append("```")
                lines.append("")
            
            # Arguments as JSON code block
            if r.get("args") or r.get("kwargs"):
                lines.append("### Arguments")
                lines.append("```json")
                args_data = {"args": r.get("args", []), "kwargs": r.get("kwargs", {})}
                lines.append(json.dumps(args_data, indent=2, ensure_ascii=False))
                lines.append("```")
                lines.append("")
            
            # Return value as JSON
            if r.get("return_value"):
                lines.append("### Return")
                lines.append("```json")
                lines.append(json.dumps(r["return_value"], indent=2, ensure_ascii=False)[:500])
                lines.append("```")
                lines.append("")
            
            if r.get("duration_ms"):
                lines.append(f"**Duration:** {r['duration_ms']}ms")
                lines.append("")
            
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"# Skill Logs\n\nError loading logs: {e}"


def get_errors_markdown(skill_name=None, last_n=20) -> str:
    """Get errors formatted as markdown for LLM analysis."""
    errors = query_skill_errors(skill_name, last_n)
    
    header = f"# Error Log"
    if skill_name:
        header += f": `{skill_name}`"
    header += f" ({len(errors)} errors)\n"
    
    if not errors:
        return header + "\n*No errors found*"
    
    lines = [header]
    for err in errors:
        ts = err.get("timestamp", "unknown")
        func = err.get("function_name", "unknown")
        exc = err.get("exception", "No details")
        
        lines.append(f"## [{ts}] `{func}`")
        lines.append("")
        lines.append("```python")
        lines.append(exc[:500])
        lines.append("```")
        lines.append("")
    
    return "\n".join(lines)


def get_health_markdown() -> str:
    """Get health summary for all skills as markdown."""
    import sqlite3
    
    if not _SQLITE_PATH.exists():
        return "# Health Summary\n\n*No data available*"
    
    try:
        conn = sqlite3.connect(str(_SQLITE_PATH))
        rows = conn.execute(
            "SELECT DISTINCT function FROM logs WHERE function LIKE '%'"
        ).fetchall()
        conn.close()
        
        skills = set()
        for (func,) in rows:
            skill = func.split('.')[0] if '.' in func else func
            skills.add(skill)
        
        lines = ["# Health Summary\n"]
        
        for skill_name in sorted(skills):
            health = skill_health_summary(skill_name)
            
            status = health.get("status", "unknown")
            if status == "healthy":
                emoji = "✅"
            elif status == "degraded":
                emoji = "⚠️"
            else:
                emoji = "❌"
            
            lines.append(f"## {emoji} `{skill_name}`")
            lines.append("")
            lines.append(f"- **Status:** {status}")
            lines.append(f"- **Calls:** {health.get('total_calls', 0)}")
            lines.append(f"- **Errors:** {health.get('errors', 0)}")
            lines.append(f"- **Error Rate:** {health.get('error_rate', 0):.1%}")
            lines.append(f"- **Avg Duration:** {health.get('avg_duration_ms', 'N/A')}ms")
            lines.append("")
        
        return "\n".join(lines)
    except Exception as e:
        return f"# Health Summary\n\nError: {e}"
