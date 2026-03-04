import subprocess
import sys
import json

def get_info() -> dict:
    return {
        'name': 'test_supervisor_probe',
        'version': 'v10',
        'description': 'A simple skill that echoes its input text'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (though not used in this skill)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return {'status': 'ok'}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Skill doesn't actually require espeak, but we check for system commands availability
        return {'status': 'ok'}

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '')
        return {
            'success': True,
            'echo': text,
            'original_input': text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

class TestSupervisorProbe:
    def execute(self, input_data: dict) -> dict:
        return execute(input_data)

if __name__ == '__main__':
    # Simple test block
    test_params = {'text': 'Hello, supervisor!'}
    result = execute(test_params)
    print(json.dumps(result, indent=2))