import subprocess
import sys
import json
import os

def get_info():
    return {
        'name': 'test_supervisor_probe',
        'version': 'v10',
        'description': 'A simple skill that echoes its input text'
    }

def health_check():
    try:
        # Check if espeak is available (for potential TTS, though not used in this skill)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return {'status': 'ok'}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # Skill doesn't require espeak, so just warn but still report ok
        return {'status': 'ok'}

class TestSupervisorProbe:
    def execute(self, params: dict) -> dict:
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

def execute(params: dict) -> dict:
    skill = TestSupervisorProbe()
    return skill.execute(params)

if __name__ == '__main__':
    # Simple test block
    test_input = {'text': 'Hello, supervisor!'}
    result = execute(test_input)
    print(json.dumps(result, indent=2))