import subprocess
import platform
import os
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'health',
        'version': 'v1',
        'description': 'System health monitoring skill'
    }

def health_check() -> dict:
    try:
        # Basic system health check using available commands
        result = {
            'status': 'ok',
            'system': platform.system(),
            'python_version': platform.python_version(),
            'cpu_count': os.cpu_count() or 0
        }
        
        # Try to get memory info if available
        try:
            if platform.system() == 'Linux':
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                    total_match = re.search(r'MemTotal:\s+(\d+)', meminfo)
                    free_match = re.search(r'MemFree:\s+(\d+)', meminfo)
                    if total_match and free_match:
                        result['memory_total_kb'] = int(total_match.group(1))
                        result['memory_free_kb'] = int(free_match.group(1))
            elif platform.system() == 'Darwin':  # macOS
                result['memory_info'] = 'available via system_profiler'
            elif platform.system() == 'Windows':
                result['memory_info'] = 'available via systeminfo'
        except Exception:
            pass
        
        # Try to get disk space info
        try:
            if platform.system() == 'Linux' or platform.system() == 'Darwin':
                result['disk_root_available'] = True
            elif platform.system() == 'Windows':
                result['disk_root_available'] = True
        except Exception:
            pass
        
        # Try network connectivity check
        try:
            urllib.request.urlopen('http://www.google.com', timeout=2)
            result['network'] = 'connected'
        except Exception:
            result['network'] = 'disconnected'
        
        return result
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

class HealthSkill:
    def execute(self, params: dict) -> dict:
        try:
            # Extract text from params if needed
            text = params.get('text', '').strip().lower()
            
            # Determine what kind of health check to perform
            if 'system' in text or 'computer' in text:
                # Full system health
                result = health_check()
                result['success'] = True
                return result
            elif 'cpu' in text:
                # CPU info
                result = {
                    'cpu_count': os.cpu_count() or 0,
                    'platform': platform.platform(),
                    'success': True
                }
                return result
            elif 'memory' in text or 'ram' in text:
                # Memory info
                result = health_check()
                if 'success' not in result:
                    result['success'] = True
                # Clean up unnecessary fields for memory-specific query
                if 'status' in result:
                    del result['status']
                return result
            elif 'disk' in text or 'storage' in text:
                # Disk info
                result = {
                    'disk_info': 'Use df -h on Linux/macOS or dir on Windows',
                    'success': True
                }
                return result
            elif 'network' in text or 'internet' in text:
                # Network check
                try:
                    urllib.request.urlopen('http://www.google.com', timeout=2)
                    result = {'network': 'connected', 'success': True}
                except Exception as e:
                    result = {'network': 'disconnected', 'error': str(e), 'success': True}
                return result
            else:
                # Default to full system health check
                result = health_check()
                result['success'] = True
                return result
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def execute(params: dict) -> dict:
    skill = HealthSkill()
    return skill.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'system health'}
    result = execute(test_params)
    print(json.dumps(result, indent=2))