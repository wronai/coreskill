import subprocess
import sys
import json

def get_info():
    return {
        "name": "test_supervisor_probe",
        "version": "v10",
        "description": "A simple skill that echoes its input text"
    }

def health_check():
    try:
        # Check if espeak is available (common on Linux systems)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL, 
                      check=True)
        return {"status": "ok"}
    except (subprocess.CalledProcessError, FileNotFoundError):
        # espeak not available, but skill can still function for echo
        return {"status": "ok"}

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '')
        return {
            'success': True,
            'echo': text,
            'message': f"Echoed: {text}"
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

class TestSupervisorProbe:
    def execute(self, params: dict) -> dict:
        return execute(params)

if __name__ == '__main__':
    # Simple test block
    skill = TestSupervisorProbe()
    
    # Test with sample input
    test_input = {"text": "Hello, supervisor!"}
    result = skill.execute(test_input)
    
    print(json.dumps(result, indent=2))