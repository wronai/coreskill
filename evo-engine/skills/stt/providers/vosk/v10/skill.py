import subprocess
import urllib.request
from urllib.parse import urlencode

class TestSkill:
    def __init__(self, params):
        self.params = params

    def execute(self):
        try:
            if self.params['tts']['espeak']:
                subprocess.run(['espeak', '-v', 'en-us', self.params['text']])
            return {'success': True}
        except Exception as e:
            print(f"Error: {e}")
            return {'success': False}

    def get_info(self):
        return {"name":"test"}

    def health_check(self):
        return True

def main():
    skill = TestSkill({"tts": {"espeak": true}, "text": "Hello, world!"})
    print(skill.execute())

if __name__ == "__main__":
    main()