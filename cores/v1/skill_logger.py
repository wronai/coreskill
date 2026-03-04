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
