Here is the corrected version of your code, using standard library and available system tools:

```python
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
    has_espeak = os.system("which espeak > /dev/null") == 0
    has_festival = os.system("which festival > /dev/null") == 0
    return bool(has_espeak or has_festival)

class TTSkill:
    def __init__(self):
        self._has_espeak = os.system("which espeak > /dev/null") == 0
        self._has_festival = os.system("which festival > /dev/null") == 0

    def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        voice = params.get("voice", "default")

        if not text:
            return {"success": False, "error": "No text provided"}

        try:
            if self._has_espeak:
                cmd = ["espeak", "-v", voice, text]
                subprocess.run(cmd, check=True)
                spoken = f'"{text}"'
            elif self._has_festival:
                cmd = ["festival", "--tts", f'"{text}"']
                subprocess.run(cmd, check=True)
                spoken = f'"{text}"' spoken with festival
            else:
                return {"success": False, "error": "No TTS engine available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

        return {"success": True, "spoken": spoken}

def execute(input_data: dict) -> dict:
    return TTSkill().execute(input_data)

if __name__ == "__main__":
    import sys
    inp = {}
    if len(sys.argv) > 1:
        inp["text"] = sys.argv[1]
    else:
        inp["text"] = "mozemy pogadac glosowo?"
    print(json.dumps(execute(inp), indent=2, ensure_ascii=False))
```

This code fixes the NameError for 'shutil' and uses standard library functions instead of shutil.which(). It also follows your requirements for the class structure and execute() method return format. The execute() function now returns a dictionary with 'success' and 'spoken' keys, as requested.