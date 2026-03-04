import subprocess
import sys
import json
import os
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def get_info():
    return {
        'name': 'test_supervisor_probe',
        'version': 'v3',
        'description': 'A skill to test supervisor probe functionality'
    }

def health_check():
    try:
        # Basic health check - verify espeak is available if needed
        result = subprocess.run(['which', 'espeak'], capture_output=True, text=True)
        if result.returncode != 0:
            return {'status': 'error', 'message': 'espeak not found'}
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class TestSupervisorProbe:
    def execute(self, input_data: dict) -> dict:
        try:
            # Extract text from input_data
            text = input_data.get('text', '')
            
            # Check if text contains probe-related commands
            if 'probe' in text.lower() or 'test' in text.lower():
                # Run a basic system probe
                probe_result = subprocess.run(['uname', '-a'], capture_output=True, text=True)
                probe_data = {
                    'system': probe_result.stdout.strip() if probe_result.stdout else 'unknown',
                    'probe_command': 'uname -a',
                    'probe_status': 'success' if probe_result.returncode == 0 else 'failed'
                }
                
                # Try to get supervisor status if available
                supervisor_status = 'unknown'
                try:
                    supervisor_result = subprocess.run(['supervisorctl', 'status'], 
                                                     capture_output=True, text=True, timeout=5)
                    supervisor_status = supervisor_result.stdout.strip() if supervisor_result.stdout else 'no output'
                except Exception:
                    supervisor_status = 'supervisor not available'
                
                return {
                    'success': True,
                    'probe_data': probe_data,
                    'supervisor_status': supervisor_status,
                    'message': 'Probe completed successfully',
                    'text': text
                }
            else:
                # Default response for non-probe text
                return {
                    'success': True,
                    'message': 'No probe command detected in text',
                    'text': text,
                    'probe_data': {'status': 'skipped', 'reason': 'no probe command found'}
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Probe execution failed'
            }

def execute(params: dict) -> dict:
    skill = TestSupervisorProbe()
    return skill.execute(params)

if __name__ == '__main__':
    # Test block
    print("Running test for test_supervisor_probe...")
    
    # Test health check
    health = health_check()
    print(f"Health check: {health}")
    
    # Test get_info
    info = get_info()
    print(f"Skill info: {info}")
    
    # Test execute with probe command
    test_input = {'text': 'run supervisor probe test'}
    result = execute(test_input)
    print(f"Test result: {json.dumps(result, indent=2)}")
    
    # Test execute with non-probe command
    test_input2 = {'text': 'hello world'}
    result2 = execute(test_input2)
    print(f"Test result2: {json.dumps(result2, indent=2)}")
    
    print("All tests completed.")