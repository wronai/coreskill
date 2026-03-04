import sys
import urllib.request
import subprocess

class TestSkill:
    def execute(self, params):
        try:
            if not params:
                return {"success": False, "error": "Params cannot be empty"}

            command = ["espeak", f"mowmy zawsze glosowo"]
            result = subprocess.run(command, capture_output=True, text=True)

            if result.returncode != 0:
                return {"success": False, "error": f"TTS error: {result.stderr}"}

            return {"success": True, "spoken": result.stdout}
        except Exception as e:
            return {"success": False, "error": str(e)}

def get_info():
    return {"name":"test"}

def health_check():
    return True

if __name__ == "__main__":
    skill = TestSkill()
    print(skill.execute({}))