#!/usr/bin/env python3
"""Echo Skill v1 - Base test skill"""
import json
from datetime import datetime, timezone

def get_info():
    return {"name":"echo","version":"v1","description":"Echo test skill",
            "capabilities":["echo","test","ping"]}

def health_check():
    return True

class EchoSkill:
    def execute(self, input_data):
        return {"echo": input_data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "ok"}

def execute(input_data):
    return EchoSkill().execute(input_data)

if __name__ == "__main__":
    print(json.dumps(execute({"msg": "hello"}), indent=2))
