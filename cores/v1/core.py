#!/usr/bin/env python3
"""evo-engine Core v1 - Evolutionary Chat Engine

REFACTORED: Modular architecture with core split into 3 files:
- core_boot.py: System initialization and boot sequence
- core_dispatch.py: Command handlers and chat processing  
- core_loop.py: Main event loop and intent handlers

This file is now a thin wrapper that delegates to the modular components.
"""
import json
from pathlib import Path
from .config import ROOT

# Re-export all public APIs for backward compatibility
from .core_boot import boot as _boot
from .core_dispatch import (
    HELP, QUICK_HELP,
    get_commands, _handle_chat, _handle_outcome,
    _check_proactive_learning,
)
from .core_loop import main

# Docker Compose Generator (needed by _cmd_compose)
def gen_compose(skills, state):
    """Generate docker-compose.yml for dual-core setup."""
    svc = {}
    for side in ["a", "b"]:
        svc[f"core-{side}"] = {
            "build": {"context": ".", "dockerfile": "Dockerfile.core"},
            "container_name": f"evo-core-{side}",
            "environment": {
                "CORE_ID": side.upper(),
                "CORE_VERSION": str(state.get(f"core_{side}_version", 1)),
                "OPENROUTER_API_KEY": "${OPENROUTER_API_KEY}",
                "MODEL": state.get("model", "")},
            "volumes": ["./cores:/app/cores:ro", "./skills:/app/skills",
                        "./logs:/app/logs", "./pipelines:/app/pipelines"],
            "restart": "unless-stopped"}
    for sn, vs in skills.items():
        svc[f"skill-{sn}"] = {
            "build": {"context": f"./skills/{sn}/{vs[-1]}"},
            "container_name": f"evo-skill-{sn}",
            "restart": "unless-stopped"}
    out = ROOT / "docker-compose.yml"
    out.write_text(json.dumps({"version": "3.8", "services": svc}, indent=2))
    return str(out)


# Backward compatibility alias
def boot():
    """Backward-compatible wrapper that calls boot() from core_boot."""
    return _boot()


