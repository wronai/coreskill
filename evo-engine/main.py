#!/usr/bin/env python3
"""
evo-engine Bootstrap - ensures core+skills exist, then runs core.
Usage: python3 main.py [--check|--reset]
"""
import os, sys, json, importlib.util, subprocess
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
CORES = ROOT / "cores"
SKILLS = ROOT / "skills"
LOGS = ROOT / "logs"
STATE = ROOT / ".evo_state.json"

DEFAULT = {"active_core":"A","core_a_version":1,"core_b_version":1,
           "model":"openrouter/stepfun/step-3.5-flash:free",
           "openrouter_api_key":"","tts_enabled":False,"iteration":0}

def log(msg, lvl="BOOT"):
    ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
    print(f"[{ts}] [{lvl}] {msg}")
    LOGS.mkdir(parents=True, exist_ok=True)
    with open(LOGS / "bootstrap.log", "a") as f:
        f.write(f"[{ts}] [{lvl}] {msg}\n")

def load_state():
    if STATE.exists(): return json.loads(STATE.read_text())
    return DEFAULT.copy()

def save_state(s):
    s["updated_at"] = datetime.now(timezone.utc).isoformat()
    STATE.write_text(json.dumps(s, indent=2))

def check(version=1):
    return (CORES / f"v{version}" / "core.py").exists()

def bootstrap():
    log("=== evo-engine bootstrap ===")
    for d in [CORES, SKILLS, LOGS, ROOT/"pipelines", ROOT/"registry"]:
        d.mkdir(parents=True, exist_ok=True)

    if not check(1):
        log("Core v1 missing, rebuilding...")
        b = ROOT / "build_core.py"
        if b.exists():
            subprocess.run([sys.executable, str(b)])
        if not check(1):
            log("FATAL: Cannot create core", "ERROR"); sys.exit(1)

    state = load_state()
    if not state.get("created_at"):
        state["created_at"] = datetime.now(timezone.utc).isoformat()
        save_state(state)

    active = state.get("active_core", "A")
    ver = state.get(f"core_{active.lower()}_version", 1)
    if not check(ver): ver = 1

    core_path = CORES / f"v{ver}" / "core.py"
    log(f"Loading core v{ver} (active: {active})")

    spec = importlib.util.spec_from_file_location("core", str(core_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.main()

if __name__ == "__main__":
    if "--check" in sys.argv:
        print("Core v1:", "OK" if check(1) else "MISSING")
        for s in ["tts","echo"]:
            print(f"Skill {s}:", "OK" if (SKILLS/s/"v1"/"skill.py").exists() else "MISSING")
    elif "--reset" in sys.argv:
        save_state(DEFAULT.copy())
        b = ROOT / "build_core.py"
        if b.exists(): subprocess.run([sys.executable, str(b)])
        print("Reset done")
    else:
        bootstrap()
