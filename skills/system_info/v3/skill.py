import subprocess
import platform
import os
import re

def get_info() -> dict:
    return {
        'name': 'system_info',
        'version': 'v1',
        'description': 'Provides information about the system and lists files in a directory.'
    }

def health_check() -> dict:
    try:
        subprocess.run(['uname', '-a'], check=True, capture_output=True)
        return {'status': 'ok'}
    except Exception:
        return {'status': 'error', 'message': 'uname command failed'}

class SystemInfoSkill:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '').lower()

        try:
            if 'info' in text or 'pokaż' in text or 'system' in text:
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
                return {'success': True, 'data': system_info, 'spoken': 'Here is the system information.'}

            file_list_match = re.search(r'wylistuj pliki w (.*)', text)
            if file_list_match:
                directory = file_list_match.group(1).strip()
                if not os.path.isdir(directory):
                    return {'success': False, 'message': f"Directory '{directory}' not found.", 'spoken': f"I could not find the directory {directory}."}

                files = os.listdir(directory)
                return {'success': True, 'data': {'directory': directory, 'files': files}, 'spoken': f"Here are the files in {directory}: {', '.join(files)}."}

            return {'success': False, 'message': "Unknown command. Try asking for 'system info' or 'list files in <directory>'."}
        except Exception as e:
            return {'success': False, 'message': f"An error occurred: {str(e)}", 'spoken': "An error occurred while processing your request."}

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

    # Test case 5: List files in /tmp
    test_params_list_files = {'text': 'wylistuj pliki w /tmp'}
    result_list_files = execute(test_params_list_files)
    print(f"Test Case 5 (List files in /tmp): {result_list_files}")

    # Test case 6: List files in a non-existent directory
    test_params_non_existent = {'text': 'wylistuj pliki w /non_existent_dir_12345'}
    result_non_existent = execute(test_params_non_existent)
    print(f"Test Case 6 (List files in non-existent dir): {result_non_existent}")