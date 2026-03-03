#!/usr/bin/env python3
"""
evo-engine: Evolutionary AI System Bootstrap
=============================================
Self-healing dual-core system with skill evolution and pipeline orchestration.

Architecture:
  main.py (bootstrap) -> cores/v{N}/core.py (A/B engine) -> skills/{name}/v{N}/skill.py

If everything fails, this script recreates core v1 and echo skill v1 from scratch.
"""

import os
import sys
import json
import importlib.util
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
CORES_DIR = ROOT / "cores"
SKILLS_DIR = ROOT / "skills"
LOGS_DIR = ROOT / "logs"
PIPELINES_DIR = ROOT / "pipelines"
STATE_FILE = ROOT / ".evo_state.json"

DEFAULT_STATE = {
    "active_core": "A",
    "core_a_version": 1,
    "core_b_version": 1,
    "last_healthy_core": "A",
    "model": "openrouter/stepfun/step-3.5-flash:free",
    "openrouter_api_key": "",
    "iteration": 0,
    "created_at": "",
    "updated_at": "",
}


def log(msg, level="INFO"):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] [{level}] {msg}"
    print(line)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOGS_DIR / "bootstrap.log", "a") as f:
        f.write(line + "\n")


def load_state():
    if STATE_FILE.exists():
        with open(STATE_FILE) as f:
            return json.load(f)
    return DEFAULT_STATE.copy()


def save_state(state):
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def ensure_directories():
    for d in [CORES_DIR, SKILLS_DIR, LOGS_DIR, PIPELINES_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def ensure_core_v1():
    core_dir = CORES_DIR / "v1"
    core_file = core_dir / "core.py"
    if not core_file.exists():
        log("Creating core v1 from seed...", "BOOTSTRAP")
        core_dir.mkdir(parents=True, exist_ok=True)
        seed = ROOT / "seeds" / "core_v1.py"
        if seed.exists():
            import shutil
            shutil.copy2(str(seed), str(core_file))
        else:
            core_file.write_text("# Core v1 placeholder\ndef main(): print('Core v1 needs seed')\n")
        log(f"Core v1 -> {core_file}", "BOOTSTRAP")
    return core_file


def ensure_echo_skill():
    skill_dir = SKILLS_DIR / "echo" / "v1"
    skill_file = skill_dir / "skill.py"
    if not skill_file.exists():
        log("Creating echo skill v1...", "BOOTSTRAP")
        skill_dir.mkdir(parents=True, exist_ok=True)
        seed = ROOT / "seeds" / "echo_skill_v1.py"
        if seed.exists():
            import shutil
            shutil.copy2(str(seed), str(skill_file))
        else:
            skill_file.write_text(_ECHO_FALLBACK)
        meta = {
            "name": "echo", "version": "v1",
            "description": "Echo skill - returns input with metadata",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        (skill_dir / "meta.json").write_text(json.dumps(meta, indent=2))
        (skill_dir / "Dockerfile").write_text(
            "FROM python:3.12-slim\nWORKDIR /app\nCOPY skill.py .\n"
            'CMD ["python", "skill.py"]\n'
        )
    return skill_file


_ECHO_FALLBACK = '''#!/usr/bin/env python3
"""Echo Skill v1"""
import json
from datetime import datetime, timezone

def get_info():
    return {"name": "echo", "version": "v1", "description": "Echo test skill"}

def health_check():
    return True

class EchoSkill:
    def execute(self, input_data):
        return {"echo": input_data, "ts": datetime.now(timezone.utc).isoformat(), "status": "ok"}

def execute(input_data):
    return EchoSkill().execute(input_data)

if __name__ == "__main__":
    print(json.dumps(execute({"msg": "hello"}), indent=2))
'''


def bootstrap():
    log("=== evo-engine Bootstrap ===", "BOOTSTRAP")
    ensure_directories()
    core_file = ensure_core_v1()
    ensure_echo_skill()

    state = load_state()
    if not state.get("created_at"):
        state["created_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

    log(f"Loading core from {core_file}", "BOOTSTRAP")
    spec = importlib.util.spec_from_file_location("core_v1", str(core_file))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()


if __name__ == "__main__":
    bootstrap()
