import subprocess
import sys
import json
import re

def get_info() -> dict:
    return {
        'name': 'test_supervisor_probe',
        'version': 'v9',
        'description': 'A simple skill that echoes its input text'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for potential future TTS)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      timeout=5)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'ok', 'message': 'espeak not installed (optional)'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class TestSupervisorProbe:
    def execute(self, params: dict) -> dict:
        try:
            # Extract text from params, default to empty string if not present
            text = params.get('text', '')
            
            # Echo the input text back
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
    """Module-level function that creates class instance and calls .execute(params)"""
    skill = TestSupervisorProbe()
    return skill.execute(params)

if __name__ == '__main__':
    # Simple test block
    test_input = {'text': 'Hello, supervisor probe!'}
    result = execute(test_input)
    print(json.dumps(result, indent=2))