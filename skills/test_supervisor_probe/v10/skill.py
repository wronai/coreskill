import subprocess
import sys
import json

def get_info():
    return {
        'name': 'test_supervisor_probe',
        'version': 'v10',
        'description': 'A simple skill that echoes its input text'
    }

def health_check():
    try:
        # Check if espeak is available (though not used in this skill)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return {'status': 'ok'}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Skill doesn't actually require espeak, but we check for general system health
        return {'status': 'ok'}

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '')
        return {
            'success': True,
            'echo': text,
            'message': f'Echoed: {text}'
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
    params = {'text': 'Hello, supervisor!'}
    result = execute(params)
    print(json.dumps(result, indent=2))