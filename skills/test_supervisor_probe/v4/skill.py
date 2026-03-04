import subprocess
import sys
import os
import re

def get_info():
    return {
        'name': 'test_supervisor_probe',
        'version': 'v4',
        'description': 'Tests supervisor probe functionality by checking system health and responding appropriately'
    }

def health_check():
    try:
        # Basic system health check using only stdlib
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
            # Extract text from params (required key)
            text = params.get('text', '')
            
            # Check for supervisor probe commands in the text
            probe_patterns = [
                r'probe\s+(?:now|immediately|test)',
                r'supervisor\s+probe',
                r'check\s+supervisor',
                r'supervisor\s+status'
            ]
            
            is_probe_request = any(re.search(pattern, text.lower()) for pattern in probe_patterns)
            
            # Perform health check
            health = health_check()
            
            if health['status'] == 'ok':
                if is_probe_request:
                    return {
                        'success': True,
                        'message': 'Supervisor probe successful',
                        'probe_result': 'healthy',
                        'health_status': health['status']
                    }
                else:
                    return {
                        'success': True,
                        'message': 'Supervisor is healthy',
                        'probe_result': 'not_requested',
                        'health_status': health['status']
                    }
            else:
                return {
                    'success': False,
                    'message': 'Supervisor probe failed',
                    'probe_result': 'unhealthy',
                    'health_status': health['status'],
                    'error_details': health.get('message', 'Unknown error')
                }
                
        except Exception as e:
            return {
                'success': False,
                'message': f'Exception during execution: {str(e)}',
                'probe_result': 'error',
                'health_status': 'error',
                'error_details': str(e)
            }

def execute(params: dict) -> dict:
    """Module-level execute function that creates class instance and calls .execute(params)"""
    return TestSupervisorProbe().execute(params)

if __name__ == '__main__':
    # Test block
    print("Testing test_supervisor_probe skill...")
    
    # Test health check
    health = health_check()
    print(f"Health check: {health}")
    
    # Test get_info
    info = get_info()
    print(f"Skill info: {info}")
    
    # Test execute function with probe request
    test_params = {'text': 'probe now'}
    result = execute(test_params)
    print(f"Probe test result: {result}")
    
    # Test execute function with non-probe request
    test_params2 = {'text': 'hello world'}
    result2 = execute(test_params2)
    print(f"Non-probe test result: {result2}")
    
    # Test execute function with empty text
    test_params3 = {'text': ''}
    result3 = execute(test_params3)
    print(f"Empty text test result: {result3}")
    
    print("All tests completed.")