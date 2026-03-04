import subprocess
import sys
import platform
import os
import re
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def get_info() -> dict:
    return {
        'name': '_health_',
        'version': 'v1',
        'description': 'Basic system health monitoring and status reporting skill'
    }

def health_check() -> dict:
    try:
        # Check if essential system commands are available
        commands = ['espeak', 'uname', 'hostname']
        for cmd in commands:
            try:
                subprocess.run([cmd, '--version'], capture_output=True, timeout=5)
            except FileNotFoundError:
                if cmd == 'espeak':
                    # espeak is optional, skip if not found
                    continue
                return {'status': 'error', 'message': f'Missing required system command: {cmd}'}
        
        # Check network connectivity with a simple DNS lookup
        try:
            req = Request('http://www.google.com', headers={'User-Agent': 'Mozilla/5.0'})
            with urlopen(req, timeout=5) as response:
                if response.status != 200:
                    return {'status': 'error', 'message': 'Network connectivity issue'}
        except (URLError, HTTPError):
            return {'status': 'error', 'message': 'Network connectivity issue'}
        
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class HealthSkill:
    def execute(self, input_data: dict) -> dict:
        try:
            text = input_data.get('text', '').lower()
            
            # Default to full health report if no specific request
            if not text or 'health' in text:
                return self._get_full_health_report()
            
            # Check for specific health metrics
            if 'cpu' in text:
                return self._get_cpu_usage()
            elif 'memory' in text or 'ram' in text:
                return self._get_memory_usage()
            elif 'disk' in text:
                return self._get_disk_usage()
            elif 'uptime' in text:
                return self._get_system_uptime()
            elif 'process' in text:
                return self._get_process_count()
            elif 'network' in text:
                return self._get_network_status()
            else:
                return {
                    'success': False,
                    'message': 'Unknown health query. Try "health", "cpu", "memory", "disk", "uptime", "processes", or "network".'
                }
                
        except Exception as e:
            return {'success': False, 'message': f'Error executing health check: {str(e)}'}
    
    def _get_full_health_report(self) -> dict:
        try:
            report = {
                'success': True,
                'health_report': {
                    'system': platform.system(),
                    'node': platform.node(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                }
            }
            
            # Add CPU info
            try:
                report['health_report']['cpu'] = self._get_cpu_info()
            except Exception:
                report['health_report']['cpu'] = {'error': 'Unable to retrieve CPU info'}
            
            # Add memory info
            try:
                report['health_report']['memory'] = self._get_memory_info()
            except Exception:
                report['health_report']['memory'] = {'error': 'Unable to retrieve memory info'}
            
            # Add disk info
            try:
                report['health_report']['disk'] = self._get_disk_info()
            except Exception:
                report['health_report']['disk'] = {'error': 'Unable to retrieve disk info'}
            
            # Add uptime
            try:
                report['health_report']['uptime'] = self._get_system_uptime_info()
            except Exception:
                report['health_report']['uptime'] = {'error': 'Unable to retrieve uptime info'}
            
            # Add network info
            try:
                report['health_report']['network'] = self._get_network_info()
            except Exception:
                report['health_report']['network'] = {'error': 'Unable to retrieve network info'}
            
            return report
        except Exception as e:
            return {'success': False, 'message': f'Error generating health report: {str(e)}'}
    
    def _get_cpu_usage(self) -> dict:
        try:
            # Try to get CPU usage from /proc/stat on Linux
            if platform.system() == 'Linux':
                with open('/proc/stat', 'r') as f:
                    line = f.readline()
                    if line.startswith('cpu '):
                        values = line.split()[1:]
                        total = sum(int(v) for v in values)
                        idle = int(values[3])
                        usage = (1 - idle / total) * 100 if total > 0 else 0
                        return {
                            'success': True,
                            'cpu_usage_percent': round(usage, 2)
                        }
            
            # Fallback for other systems
            return {
                'success': True,
                'cpu_usage_percent': 'N/A',
                'message': 'CPU usage calculation not available on this system'
            }
        except Exception as e:
            return {'success': False, 'message': f'Error getting CPU usage: {str(e)}'}
    
    def _get_memory_usage(self) -> dict:
        try:
            # Try to get memory info from /proc/meminfo on Linux
            if platform.system() == 'Linux':
                meminfo = {}
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value_parts = parts[1].strip().split()
                            meminfo[key] = int(value_parts[0]) * 1024  # Convert to bytes
                
                if 'MemTotal' in meminfo and 'MemAvailable' in meminfo:
                    total = meminfo['MemTotal']
                    available = meminfo['MemAvailable']
                    used = total - available
                    usage_percent = (used / total) * 100 if total > 0 else 0
                    return {
                        'success': True,
                        'memory_total_bytes': total,
                        'memory_used_bytes': used,
                        'memory_available_bytes': available,
                        'memory_usage_percent': round(usage_percent, 2)
                    }
            
            # Fallback for other systems
            return {
                'success': True,
                'memory_usage_percent': 'N/A',
                'message': 'Memory usage calculation not available on this system'
            }
        except Exception as e:
            return {'success': False, 'message': f'Error getting memory usage: {str(e)}'}
    
    def _get_disk_usage(self) -> dict:
        try:
            # Try to get disk usage using df command
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    # Parse the output (skip header line)
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        return {
                            'success': True,
                            'disk_total': parts[1],
                            'disk_used': parts[2],
                            'disk_available': parts[3],
                            'disk_usage_percent': parts[4]
                        }
            
            # Fallback for other systems
            return {
                'success': True,
                'disk_usage_percent': 'N/A',
                'message': 'Disk usage calculation not available on this system'
            }
        except Exception as e:
            return {'success': False, 'message': f'Error getting disk usage: {str(e)}'}
    
    def _get_system_uptime(self) -> dict:
        try:
            uptime_info = self._get_system_uptime_info()
            return {
                'success': True,
                **uptime_info
            }
        except Exception as e:
            return {'success': False, 'message': f'Error getting system uptime: {str(e)}'}
    
    def _get_system_uptime_info(self) -> dict:
        # Try to get uptime from /proc/uptime on Linux
        if platform.system() == 'Linux':
            try:
                with open('/proc/uptime', 'r') as f:
                    uptime_seconds = float(f.readline().split()[0])
                    days = int(uptime_seconds // 86400)
                    hours = int((uptime_seconds % 86400) // 3600)
                    minutes = int((uptime_seconds % 3600) // 60)
                    seconds = int(uptime_seconds % 60)
                    return {
                        'uptime_seconds': int(uptime_seconds),
                        'uptime_formatted': f'{days}d {hours}h {minutes}m {seconds}s'
                    }
            except Exception:
                pass
        
        # Try to get uptime from uptime command
        try:
            result = subprocess.run(['uptime'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                return {
                    'uptime_formatted': result.stdout.strip(),
                    'uptime_seconds': 'N/A'
                }
        except Exception:
            pass
        
        return {
            'uptime_seconds': 'N/A',
            'uptime_formatted': 'N/A'
        }
    
    def _get_process_count(self) -> dict:
        try:
            # Try to count processes from /proc on Linux
            if platform.system() == 'Linux':
                process_count = len([d for d in os.listdir('/proc') if d.isdigit()])
                return {
                    'success': True,
                    'process_count': process_count
                }
            
            # Fallback using ps command
            result = subprocess.run(['ps', '-e'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                process_count = len(lines) - 1  # Subtract header line
                return {
                    'success': True,
                    'process_count': process_count
                }
            
            return {
                'success': True,
                'process_count': 'N/A',
                'message': 'Process count not available on this system'
            }
        except Exception as e:
            return {'success': False, 'message': f'Error getting process count: {str(e)}'}
    
    def _get_network_status(self) -> dict:
        try:
            # Try to get network interfaces info
            interfaces = []
            if platform.system() == 'Linux':
                try:
                    result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # Simple parsing of interface names
                        for line in result.stdout.split('\n'):
                            if line.strip().startswith('inet ') or line.strip().startswith('inet6 '):
                                parts = line.strip().split()
                                if len(parts) >= 2:
                                    interfaces.append({
                                        'address': parts[1],
                                        'type': 'IPv4' if 'inet ' in line else 'IPv6'
                                    })
                except Exception:
                    pass
            
            # Check network connectivity
            connectivity = 'unknown'
            try:
                req = Request('http://www.google.com', headers={'User-Agent': 'Mozilla/5.0'})
                with urlopen(req, timeout=5) as response:
                    connectivity = 'connected' if response.status == 200 else 'disconnected'
            except Exception:
                connectivity = 'disconnected'
            
            return {
                'success': True,
                'connectivity': connectivity,
                'interfaces': interfaces[:5]  # Limit to 5 interfaces
            }
        except Exception as e:
            return {'success': False, 'message': f'Error getting network status: {str(e)}'}
    
    def _get_cpu_info(self) -> dict:
        # Try to get CPU info from /proc/cpuinfo on Linux
        if platform.system() == 'Linux':
            try:
                with open('/proc/cpuinfo', 'r') as f:
                    cpuinfo = {}
                    for line in f:
                        if ':' in line:
                            key, value = line.split(':', 1)
                            key = key.strip()
                            value = value.strip()
                            if key not in cpuinfo:
                                cpuinfo[key] = value
                    return {
                        'model': cpuinfo.get('model name', cpuinfo.get('Processor', 'Unknown')),
                        'cores': int(cpuinfo.get('processor', 0)) + 1 if 'processor' in cpuinfo else 'N/A',
                        'architecture': platform.machine()
                    }
            except Exception:
                pass
        
        return {
            'model': platform.processor() or 'Unknown',
            'cores': 'N/A',
            'architecture': platform.machine()
        }
    
    def _get_memory_info(self) -> dict:
        # Try to get memory info from /proc/meminfo on Linux
        if platform.system() == 'Linux':
            try:
                meminfo = {}
                with open('/proc/meminfo', 'r') as f:
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            key = parts[0].strip()
                            value_parts = parts[1].strip().split()
                            meminfo[key] = int(value_parts[0]) * 1024  # Convert to bytes
                
                if 'MemTotal' in meminfo:
                    return {
                        'total_bytes': meminfo.get('MemTotal', 0),
                        'available_bytes': meminfo.get('MemAvailable', 0),
                        'free_bytes': meminfo.get('MemFree', 0),
                        'buffers_bytes': meminfo.get('Buffers', 0),
                        'cached_bytes': meminfo.get('Cached', 0)
                    }
            except Exception:
                pass
        
        return {
            'total_bytes': 'N/A',
            'available_bytes': 'N/A',
            'free_bytes': 'N/A',
            'buffers_bytes': 'N/A',
            'cached_bytes': 'N/A'
        }
    
    def _get_disk_info(self) -> dict:
        # Try to get disk info using df command
        try:
            result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                if len(lines) >= 2:
                    parts = lines[1].split()
                    if len(parts) >= 5:
                        return {
                            'total': parts[1],
                            'used': parts[2],
                            'available': parts[3],
                            'usage_percent': parts[4],
                            'mount_point': '/'
                        }
        except Exception:
            pass
        
        return {
            'total': 'N/A',
            'used': 'N/A',
            'available': 'N/A',
            'usage_percent': 'N/A',
            'mount_point': '/'
        }
    
    def _get_network_info(self) -> dict:
        # Try to get network interfaces info
        interfaces = []
        if platform.system() == 'Linux':
            try:
                result = subprocess.run(['ip', 'addr'], capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # Simple parsing of interface names
                    current_interface = None
                    for line in result.stdout.split('\n'):
                        if line.strip().startswith('inet ') or line.strip().startswith('inet6 '):
                            parts = line.strip().split()
                            if len(parts) >= 2:
                                interfaces.append({
                                    'address': parts[1],
                                    'type': 'IPv4' if 'inet ' in line else 'IPv6'
                                })
            except Exception:
                pass
        
        return {
            'interfaces': interfaces[:5],  # Limit to 5 interfaces
            'connectivity': 'unknown'
        }

def execute(params: dict) -> dict:
    skill = HealthSkill()
    return skill.execute(params)

if __name__ == '__main__':
    # Test the skill
    print("Testing health skill...")
    
    # Test health_check function
    health = health_check()
    print(f"Health check: {health}")
    
    # Test execute function with different inputs
    test_cases = [
        {'text': 'health'},
        {'text': 'cpu'},
        {'text': 'memory'},
        {'text': 'disk'},
        {'text': 'uptime'},
        {'text': 'processes'},
        {'text': 'network'},
        {'text': 'unknown query'}
    ]
    
    for test in test_cases:
        print(f"\nTesting with input: {test['text']}")
        result = execute(test)
        print(f"Result: {result}")