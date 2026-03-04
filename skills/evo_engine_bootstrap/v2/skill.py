import subprocess
import re
from datetime import datetime
import time


def get_info() -> dict:
    return {
        'name': 'evo_engine_bootstrap',
        'version': 'v1',
        'description': 'Handles evo-engine bootstrap initialization messages'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            return {'status': 'ok'}
        else:
            return {'status': 'ok', 'note': 'espeak available but returned non-zero exit code'}
    except FileNotFoundError:
        return {'status': 'ok', 'note': 'espeak not found (TTS unavailable)'}
    except Exception as e:
        return {'status': 'ok', 'note': f'espeak check failed: {str(e)}'}


class EvoEngineBootstrapSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            
            # Pattern to match the bootstrap message format
            bootstrap_pattern = r'\[.*?\]\s*\[BOOT\]\s*===\s*evo-engine bootstrap\s*==='
            
            if re.search(bootstrap_pattern, text, re.IGNORECASE):
                # Generate response
                timestamp = datetime.now().strftime('%H:%M:%S')
                response = f"[{timestamp}] [BOOT] === evo-engine bootstrap === initialized successfully"
                
                # Try to speak the response if espeak is available
                try:
                    subprocess.run(['espeak', response], 
                                 capture_output=True, 
                                 timeout=5)
                except Exception:
                    pass  # Ignore TTS errors
                
                return {
                    'success': True,
                    'message': response,
                    'spoken': response,
                    'action': 'bootstrap_acknowledged'
                }
            else:
                return {
                    'success': False,
                    'message': 'No bootstrap message detected',
                    'spoken': '',
                    'action': 'no_match'
                }
        except Exception as e:
            return {
                'success': False,
                'message': str(e),
                'spoken': '',
                'action': 'error'
            }


def execute(params: dict) -> dict:
    skill = EvoEngineBootstrapSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test block
    test_params = {'text': '[15:59:13] [BOOT] === evo-engine bootstrap ==='}
    result = execute(test_params)
    print(result)