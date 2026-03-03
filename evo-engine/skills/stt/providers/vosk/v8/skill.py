import json
import os
import subprocess

def get_info():
    return {
        "name": "tts",
        "version": "v1",
        "description": "Text-to-Speech: convert text to speech using system tools (espeak, festival).",
    }

def health_check():
    has_espeak = shutil.which("espeak") is not None
    has_festival = shutil.which("festival") is not None
    return bool(has_espeak or has_festival)

class TTSkill:
    def __init__(self):
        self._has_espeak = shutil.which("espeak") is not None
        self._has_festival = shutil.which("festival") is not None

    def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        voice = params.get("voice", "default")

        if not text:
            return {"success": False, "error": "No text provided"}

        try:
            if self._has_espeak:
                cmd = ["espeak", "-v", voice, text]
                subprocess.run(cmd, check=True)
            elif self._has_festival:
                cmd = ["festival", "--tts", f'"{text}"']
                subprocess.run(cmd, check=True)
            else:
                return {"success": False, "error": "No TTS engine available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

def execute(input_data: dict) -> dict:
    return TTSkill().execute(input_data)

if __name__ == "__main__":
    import sys
    inp = {}
    if len(sys.argv) > 1:
        inp["text"] = sys.argv[1]
    else:
        inp["text"] = "pogadajmy głosowo"
    print(json.dumps(execute(inp), indent=2, ensure_ascii=False))