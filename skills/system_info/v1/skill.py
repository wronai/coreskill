import subprocess
import platform
import os

def get_info() -> dict:
    return {
        'name': 'system_info',
        'version': 'v1',
        'description': 'Provides information about the system.'
    }

def health_check() -> dict:
    try:
        subprocess.run(['uname', '-a'], check=True, capture_output=True)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class SystemInfoSkill:
    def execute(self, params: dict) -> dict:
        try:
            command = params.get('text', '').lower()
            if 'info' in command or 'pokaż' in command or 'system' in command:
                system_info = {
                    'system': platform.system(),
                    'node_name': platform.node(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'python_version': platform.python_version(),
                    'os_name': os.name,
                    'cwd': os.getcwd()
                }
                return {'success': True, 'data': system_info}
            else:
                return {'success': False, 'message': "Unknown command. Try asking for 'system info'."}
        except Exception as e:
            return {'success': False, 'message': f"An error occurred: {str(e)}"}

def execute(params: dict) -> dict:
    skill = SystemInfoSkill()
    return skill.execute(params)

if __name__ == '__main__':
    print("System Info Skill Test")

    # Test case 1: Get system info
    test_params_info = {'text': 'pokaż info o systemie'}
    result_info = execute(test_params_info)
    print(f"Test Case 1 (System Info): {result_info}")

    # Test case 2: Unknown command
    test_params_unknown = {'text': 'hello there'}
    result_unknown = execute(test_params_unknown)
    print(f"Test Case 2 (Unknown Command): {result_unknown}")

    # Test case 3: Health check
    health_status = health_check()
    print(f"Health Check: {health_status}")

    # Test case 4: Get info function
    info = get_info()
    print(f"Get Info: {info}")