import subprocess
import sys
import json
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError


def get_info() -> dict:
    return {
        'name': 'test_supervisor_probe',
        'version': 'v1',
        'description': 'Tests supervisor probe functionality by checking system health and responding with status'
    }


def health_check() -> dict:
    try:
        # Basic system health check: try to run a simple command
        result = subprocess.run(['echo', 'health_check'], 
                                capture_output=True, 
                                text=True, 
                                timeout=5)
        if result.returncode == 0:
            return {'status': 'ok'}
        else:
            return {'status': 'error', 'message': 'System command failed'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


class TestSupervisorProbe:
    def execute(self, params: dict) -> dict:
        try:
            # Extract text from params
            text = params.get('text', '')
            
            # Check for supervisor-related commands in the text
            if re.search(r'supervisor|probe|health|status', text, re.IGNORECASE):
                # Run health check
                health_result = health_check()
                
                if health_result['status'] == 'ok':
                    return {
                        'success': True,
                        'message': 'Supervisor probe completed successfully',
                        'probe_result': health_result,
                        'text': text
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Supervisor probe failed',
                        'probe_result': health_result,
                        'text': text
                    }
            else:
                # Default response for non-supervisor related text
                return {
                    'success': True,
                    'message': 'Supervisor probe executed (no supervisor-related command detected)',
                    'probe_result': {'status': 'ok'},
                    'text': text
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Error during probe execution: {str(e)}',
                'error': str(e)
            }


def execute(params: dict) -> dict:
    """Module-level execute function that creates class instance and calls .execute(params)."""
    probe = TestSupervisorProbe()
    return probe.execute(params)


if __name__ == '__main__':
    # Test block
    print("Testing test_supervisor_probe skill...")
    
    # Test get_info
    info = get_info()
    print(f"get_info(): {json.dumps(info, indent=2)}")
    
    # Test health_check
    health = health_check()
    print(f"health_check(): {json.dumps(health, indent=2)}")
    
    # Test execute function
    test_cases = [
        {'text': 'check supervisor status'},
        {'text': 'run probe'},
        {'text': 'hello world'},
        {'text': 'health check'}
    ]
    
    for i, test_case in enumerate(test_cases):
        print(f"\nTest case {i+1}: {test_case['text']}")
        result = execute(test_case)
        print(f"Result: {json.dumps(result, indent=2)}")
    
    print("\nAll tests completed.")