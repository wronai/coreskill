#!/usr/bin/env python3
"""Echo Skill v1 - Base test skill for evo-engine."""
import json
from datetime import datetime, timezone
try:
    import nfo
    _logged = nfo.logged
    _log_call = nfo.log_call
except (ImportError, AttributeError):
    _logged = lambda cls: cls
    _log_call = lambda fn: fn

def get_info():
    return {"name": "echo", "version": "v1", "description": "Echo test skill"}

def health_check():
    return True

@_logged
class EchoSkill:
    def execute(self, input_data):
        return {
            "echo": input_data,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "skill": get_info(),
            "status": "ok",
        }

@_log_call
def execute(input_data):
    return EchoSkill().execute(input_data)

if __name__ == "__main__":
    print(json.dumps(execute({"message": "hello from evo-engine", "test": True}), indent=2))
