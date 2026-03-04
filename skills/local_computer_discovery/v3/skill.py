import subprocess
import re
import json
import platform
import socket
import struct
import fcntl
import os
import time

def get_info() -> dict:
    return {
        'name': 'local_computer_discovery',
        'version': 'v1',
        'description': 'Skill to discover local computers and cameras on the network'
    }

def health_check() -> dict:
    try:
        # Check if required system tools are available
        tools = ['nmap', 'arp-scan', 'ip', 'ifconfig', 'netstat', 'arp']
        available_tools = []
        for tool in tools:
            try:
                subprocess.run([tool, '--version'], capture_output=True, timeout=5)
                available_tools.append(tool)
            except (subprocess.SubprocessError, FileNotFoundError):
                pass
        
        # Try basic network operations
        try:
            # Get local IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return {
                'status': 'ok',
                'local_ip': local_ip,
                'available_tools': available_tools
            }
        except Exception as e:
            return {
                'status': 'error',
                'message': str(e)
            }
    except Exception as e:
        return {
            'status': 'error',
            'message': str(e)
        }

class LocalComputerDiscovery:
    def __init__(self):
        self.os_type = platform.system().lower()
    
    def get_local_ip(self):
        """Get local IP address of the machine"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return None
    
    def get_network_range(self, ip):
        """Get network range from IP address"""
        if not ip:
            return None
        parts = ip.split('.')
        if len(parts) != 4:
            return None
        # Assume /24 network for most home networks
        return f"{parts[0]}.{parts[1]}.{parts[2]}.0/24"
    
    def discover_with_arp(self):
        """Discover hosts using ARP table"""
        try:
            # Get ARP table
            result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                hosts = []
                for line in result.stdout.strip().split('\n'):
                    if line:
                        # Parse ARP output - format varies by OS
                        match = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F:]+)\s+(\w+)', line)
                        if match:
                            ip, mac, _ = match.groups()
                            hosts.append({'ip': ip, 'mac': mac, 'method': 'arp'})
                return hosts
        except Exception:
            pass
        return []
    
    def discover_with_nmap(self, network_range):
        """Discover hosts using nmap"""
        try:
            result = subprocess.run(['nmap', '-sn', network_range], capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                hosts = []
                # Parse nmap output
                for line in result.stdout.split('\n'):
                    if 'Nmap scan report for' in line:
                        ip_match = re.search(r'for\s+(\d+\.\d+\.\d+\.\d+)', line)
                        if ip_match:
                            ip = ip_match.group(1)
                            hosts.append({'ip': ip, 'method': 'nmap'})
                return hosts
        except Exception:
            pass
        return []
    
    def discover_with_arp_scan(self, interface=None):
        """Discover hosts using arp-scan"""
        try:
            cmd = ['arp-scan', '-l']
            if interface:
                cmd.extend(['-I', interface])
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if result.returncode == 0:
                hosts = []
                for line in result.stdout.split('\n'):
                    if re.match(r'\d+\.\d+\.\d+\.\d+', line.strip()):
                        parts = line.strip().split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            mac = parts[1] if len(parts) > 1 else 'unknown'
                            hosts.append({'ip': ip, 'mac': mac, 'method': 'arp-scan'})
                return hosts
        except Exception:
            pass
        return []
    
    def discover_with_netstat(self):
        """Discover hosts using netstat"""
        try:
            result = subprocess.run(['netstat', '-rn'], capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                # Parse routing table to get local network
                for line in result.stdout.split('\n'):
                    if re.match(r'\d+\.\d+\.\d+\.\d+', line.strip()):
                        parts = line.strip().split()
                        if len(parts) >= 2 and parts[0] != '0.0.0.0':
                            # This is a local network route
                            network = parts[0]
                            # Try to construct network range
                            if '/' not in network:
                                # Assume /24 for common cases
                                parts_net = network.split('.')
                                if len(parts_net) == 4:
                                    network_range = f"{parts_net[0]}.{parts_net[1]}.{parts_net[2]}.0/24"
                                    return self.discover_with_nmap(network_range)
        except Exception:
            pass
        return []
    
    def discover_with_ping(self, network_range):
        """Discover hosts using ping sweep"""
        try:
            # Get network range parts
            match = re.match(r'(\d+\.\d+\.\d+)\.(\d+)/(\d+)', network_range)
            if not match:
                return []
            
            base = match.group(1)
            start = int(match.group(2))
            prefix = f"{base}."
            
            hosts = []
            # Scan first 10 hosts for speed
            for i in range(start, min(start + 10, 255)):
                ip = f"{prefix}{i}"
                try:
                    # Use ping with timeout
                    if self.os_type == 'windows':
                        result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip], 
                                              capture_output=True, timeout=2)
                    else:
                        result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                              capture_output=True, timeout=2)
                    
                    if result.returncode == 0:
                        hosts.append({'ip': ip, 'method': 'ping'})
                except Exception:
                    continue
            return hosts
        except Exception:
            return []
    
    def get_hostname(self, ip):
        """Try to get hostname for IP"""
        try:
            return socket.gethostbyaddr(ip)[0]
        except Exception:
            return None
    
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Check if this is the right command
            if 'znajdź komputery' not in text and 'znajdź komputer' not in text and 'znajdź kamery' not in text:
                return {
                    'success': False,
                    'message': 'Command not recognized for local computer discovery',
                    'text': text
                }
            
            # Get local IP and network
            local_ip = self.get_local_ip()
            if not local_ip:
                return {
                    'success': False,
                    'message': 'Could not determine local IP address',
                    'local_ip': None
                }
            
            network_range = self.get_network_range(local_ip)
            if not network_range:
                return {
                    'success': False,
                    'message': 'Could not determine network range',
                    'local_ip': local_ip
                }
            
            # Try multiple discovery methods
            all_hosts = []
            
            # Method 1: ARP table (fastest, no external tools needed)
            arp_hosts = self.discover_with_arp()
            all_hosts.extend(arp_hosts)
            
            # Method 2: nmap if available
            nmap_hosts = self.discover_with_nmap(network_range)
            all_hosts.extend(nmap_hosts)
            
            # Method 3: arp-scan if available
            if not all_hosts:
                arp_scan_hosts = self.discover_with_arp_scan()
                all_hosts.extend(arp_scan_hosts)
            
            # Method 4: netstat routing table
            if not all_hosts:
                netstat_hosts = self.discover_with_netstat()
                all_hosts.extend(netstat_hosts)
            
            # Method 5: ping sweep as last resort
            if not all_hosts:
                ping_hosts = self.discover_with_ping(network_range)
                all_hosts.extend(ping_hosts)
            
            # Deduplicate hosts
            seen_ips = set()
            unique_hosts = []
            for host in all_hosts:
                if host['ip'] not in seen_ips:
                    seen_ips.add(host['ip'])
                    # Try to get hostname
                    hostname = self.get_hostname(host['ip'])
                    if hostname:
                        host['hostname'] = hostname
                    unique_hosts.append(host)
            
            # Prepare spoken response
            if not unique_hosts:
                spoken = "Nie znaleziono żadnych urządzeń w sieci lokalnej."
            else:
                count = len(unique_hosts)
                devices = ", ".join([h.get('hostname', h['ip']) for h in unique_hosts[:5]])
                if count > 5:
                    devices += f" i {count - 5} więcej"
                spoken = f"Znaleziono {count} urządzenie(-eń) w sieci lokalnej: {devices}."
            
            if not unique_hosts:
                return {
                    'success': True,
                    'message': 'No computers found on local network',
                    'local_ip': local_ip,
                    'network_range': network_range,
                    'hosts': [],
                    'spoken': spoken
                }
            
            return {
                'success': True,
                'message': f'Found {len(unique_hosts)} computer(s) on local network',
                'local_ip': local_ip,
                'network_range': network_range,
                'hosts': unique_hosts,
                'spoken': spoken
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Error during computer discovery: {str(e)}',
                'error': str(e),
                'spoken': 'Wystąpił błąd podczas wyszukiwania urządzeń w sieci.'
            }

def execute(params: dict) -> dict:
    """Module-level execute function"""
    skill = LocalComputerDiscovery()
    return skill.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'znajdź komputery się się lokalnych'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))