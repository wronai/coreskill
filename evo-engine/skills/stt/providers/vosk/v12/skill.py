import subprocess
import urllib.request
from urllib.parse import urlencode

class TestSkill:
    def __init__(self, params):
        self.params = params

    def execute(self):
        try:
            if 'stt' in self.params and self.params['stt']['arecord']:
                subprocess.run(['arecord', '-l'], check=True)
                return {'success': True}
            else:
                return {'success': False, 'error': 'STT command not found'}
        except Exception as e:
            print(f"Error: {e}")
            return {'success': False}

    def get_info(self):
        return {"name":"test"}

    def health_check(self):
        return True

def main():
    skill = TestSkill({"stt": {"arecord": True}})
    print(skill.execute())

if __name__ == "__main__":
    main()