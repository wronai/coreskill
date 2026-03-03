import json
import os
import subprocess
from pathlib import Path
import shutil
import sys

def get_info():
    return {
        "name": "tts",
        "version": "v1",
        "description": "Text-to-Speech: convert text to speech using system tools (espeak).",
    }

def health_check():
    has_espeak = shutil.which("espeak") is not None
    return bool(has_espeak)

class TTSkill:
    def __init__(self):
        self._has_espeak = shutil.which("espeak") is not None

    def execute(self, params: dict) -> dict:
        text = params.get("text", "Hello, how can I assist you?")
        try:
            subprocess.run(["espeak", "-v", "en-us", text], check=True)
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

def execute(input_data: dict) -> dict:
    return TTSkill().execute(input_data)

if __name__ == "__main__":
    inp = {}
    if len(sys.argv) > 1:
        inp["text"] = sys.argv[1]
    else:
        inp["text"] = "czy mozemy pogadac glosowo?"
    print(json.dumps(execute(inp), indent=2, ensure_ascii=False))