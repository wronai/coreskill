#!/usr/bin/env python3
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
