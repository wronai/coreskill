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
        # Check if espeak is available (for TTS capability, though not used in this skill)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'error', 'message': 'espeak not found (optional dependency)'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

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
    test_params = {'text': 'Hello, supervisor!'}
    result = execute(test_params)
    print(json.dumps(result, indent=2))