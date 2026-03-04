import subprocess
import re
import json
import urllib.request
import urllib.error
from typing import Dict, Any


def get_info() -> dict:
    return {
        'name': 'invalid_input_handler',
        'version': 'v1',
        'description': 'Handles invalid input by providing helpful responses and alternative actions like finding cameras'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'error', 'message': 'espeak not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


class InvalidInputHandler:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip().lower()
            
            # Check if user wants to find cameras
            if 'kamery' in text or 'camera' in text or 'webcam' in text or 'monitoring' in text:
                # Try to detect available cameras using system commands
                camera_devices = []
                
                # Try to find video devices on Linux
                try:
                    result = subprocess.run(['ls', '/dev/video*'], capture_output=True, text=True, timeout=5)
                    if result.returncode == 0:
                        camera_devices = result.stdout.strip().split('\n')
                except Exception:
                    pass
                
                # Try to find video devices on macOS
                if not camera_devices:
                    try:
                        result = subprocess.run(['system_profiler', 'SPCameraDataType'], capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and 'Camera:' in result.stdout:
                            camera_devices = ['macOS camera detected']
                    except Exception:
                        pass
                
                # Try to find video devices on Windows
                if not camera_devices:
                    try:
                        result = subprocess.run(['wmic', 'path', 'Win32_PnPEntity', 'where', 'Caption like "%camera%"', 'get', 'Caption'], 
                                               capture_output=True, text=True, timeout=5)
                        if result.returncode == 0 and result.stdout.strip():
                            camera_devices = ['Windows camera detected']
                    except Exception:
                        pass
                
                if camera_devices:
                    return {
                        'success': True,
                        'message': f'Znaleziono kamery: {", ".join(camera_devices)}',
                        'cameras': camera_devices,
                        'action': 'cameras_found'
                    }
                else:
                    return {
                        'success': True,
                        'message': 'Nie udało się automatycznie wykryć kamer. Sprawdź, czy masz podłączone kamery i czy mają one odpowiednie uprawnienia.',
                        'cameras': [],
                        'action': 'cameras_not_found'
                    }
            
            # Default response for invalid input
            return {
                'success': True,
                'message': 'Nie rozumiem Twojego zapytania. Spróbuj sformułować inaczej lub zapytaj o coś konkretnego, np. "znajdź kamery".',
                'action': 'invalid_input_handled'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Wystąpił błąd podczas przetwarzania zapytania'
            }


def execute(params: dict) -> dict:
    handler = InvalidInputHandler()
    return handler.execute(params)


if __name__ == '__main__':
    # Test block
    test_cases = [
        {'text': 'sdafasd'},
        {'text': 'znajdź kamery'},
        {'text': 'kamery'},
        {'text': 'webcam'},
        {'text': 'co to jest kamera?'}
    ]
    
    for test in test_cases:
        print(f"Testing with: {test['text']}")
        result = execute(test)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("-" * 50)