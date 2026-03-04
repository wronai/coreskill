import subprocess
import sys
import os
import re
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'test_supervisor_probe',
        'version': 'v2',
        'description': 'Tests supervisor probe functionality by checking system health and responding to probe requests'
    }

def health_check() -> dict:
    try:
        # Basic system health check
        result = subprocess.run(['echo', 'ok'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            return {'status': 'ok'}
        else:
            return {'status': 'error', 'message': 'System health check failed'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class TestSupervisorProbe:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            
            # Check if it's a supervisor probe request
            if 'probe' in text.lower() or 'health' in text.lower():
                health = health_check()
                if health['status'] == 'ok':
                    return {
                        'success': True,
                        'message': 'Supervisor probe successful',
                        'probe_result': health
                    }
                else:
                    return {
                        'success': False,
                        'message': 'Supervisor probe failed',
                        'probe_result': health
                    }
            
            # Default response for test purposes
            return {
                'success': True,
                'message': 'Test supervisor probe executed',
                'input_received': text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def execute(params: dict) -> dict:
    """Module-level execute function that creates class instance and calls .execute(params)"""
    return TestSupervisorProbe().execute(params)

if __name__ == '__main__':
    # Simple test block
    print("Testing test_supervisor_probe skill...")
    
    # Test get_info
    info = get_info()
    print(f"Info: {json.dumps(info, indent=2)}")
    
    # Test health_check
    health = health_check()
    print(f"Health: {json.dumps(health, indent=2)}")
    
    # Test execute function
    test_params = {'text': 'probe'}
    result = execute(test_params)
    print(f"Execute result: {json.dumps(result, indent=2)}")
    
    # Test execute method directly
    probe = TestSupervisorProbe()
    result2 = probe.execute({'text': 'health check'})
    print(f"Direct method result: {json.dumps(result2, indent=2)}")
    
    print("All tests completed.")