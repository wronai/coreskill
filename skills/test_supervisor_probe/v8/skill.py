import subprocess
import sys
import json

def get_info() -> dict:
    return {
        'name': 'test_supervisor_probe',
        'version': 'v8',
        'description': 'A simple skill that echoes its input text'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for potential future TTS)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return {'status': 'ok'}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # espeak not available, but skill can still work for echo functionality
        return {'status': 'ok'}

class TestSupervisorProbe:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            return {
                'success': True,
                'echo': text,
                'original_text': text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def execute(params: dict) -> dict:
    skill = TestSupervisorProbe()
    return skill.execute(params)

if __name__ == '__main__':
    # Simple test block
    test_params = {'text': 'Hello, supervisor!'}
    result = execute(test_params)
    print(json.dumps(result, indent=2))