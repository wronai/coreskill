import re
import subprocess
import sys
from datetime import datetime

def get_info() -> dict:
    return {
        'name': 'core_loader',
        'version': 'v1',
        'description': 'Handles core loading status messages like "[BOOT] Loading core v1 (active: A)"'
    }

def health_check() -> dict:
    try:
        # Basic health check: ensure espeak is available for TTS if needed
        result = subprocess.run(['which', 'espeak'], capture_output=True, text=True)
        if result.returncode != 0:
            return {'status': 'error', 'message': 'espeak not found'}
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class CoreLoaderSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            
            # Pattern to match: [BOOT] Loading core v1 (active: A)
            pattern = r'\[BOOT\]\s+Loading\s+core\s+v(\d+)\s+\(active:\s*([A-Z])\)'
            match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                version = match.group(1)
                active = match.group(2)
                
                # Prepare response
                response_text = f"Core v{version} is loading with active status {active}."
                
                # Optional: use TTS if espeak is available
                try:
                    subprocess.run(['espeak', response_text], 
                                 stdout=subprocess.DEVNULL, 
                                 stderr=subprocess.DEVNULL)
                except Exception:
                    pass  # TTS failure is not critical
                
                return {
                    'success': True,
                    'message': response_text,
                    'parsed': {
                        'version': version,
                        'active': active
                    }
                }
            else:
                return {
                    'success': False,
                    'message': "No core loading message detected in input.",
                    'parsed': None
                }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error processing core loader request: {str(e)}",
                'parsed': None
            }

def execute(params: dict) -> dict:
    skill = CoreLoaderSkill()
    return skill.execute(params)

if __name__ == '__main__':
    # Test block
    test_cases = [
        {'text': '[15:59:13] [BOOT] Loading core v1 (active: A)'},
        {'text': '[BOOT] Loading core v2 (active: B)'},
        {'text': 'Random text without core loading message'},
        {'text': '[boot] loading core v3 (active: X)'}
    ]
    
    for i, test in enumerate(test_cases):
        print(f"\nTest case {i+1}: {test['text']}")
        result = execute(test)
        print(f"Result: {result}")