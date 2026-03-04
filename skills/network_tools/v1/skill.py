#!/usr/bin/env python3
"""
network_tools skill - Network diagnostics (ping, DNS lookup, port check).
Uses subprocess for system tools and socket for port checks.
"""
import subprocess
import socket
import json
import re
from urllib.parse import urlparse


def get_info():
    return {
        "name": "network_tools",
        "version": "v1",
        "description": "Network diagnostics: ping, DNS lookup, port check, HTTP status check.",
        "capabilities": ["network", "diagnostics", "ping", "dns", "port"],
        "actions": ["ping", "dns_lookup", "check_port", "check_http", "my_ip", "info"]
    }


def health_check():
    return True


class NetworkToolsSkill:
    """Network diagnostic tools."""

    def ping(self, host, count=4, timeout=5):
        """Ping a host and return statistics."""
        try:
            # Clean host (remove protocol if present)
            host = host.replace("http://", "").replace("https://", "").split("/")[0]

            # Use system ping command
            result = subprocess.run(
                ["ping", "-c", str(count), "-W", str(timeout), host],
                capture_output=True,
                text=True,
                timeout=timeout * count + 5
            )

            output = result.stdout + result.stderr

            # Parse ping output
            if result.returncode != 0 and "unknown host" in output.lower():
                return {"success": False, "error": f"Unknown host: {host}"}

            # Extract packets info
            packets_match = re.search(r'(\d+) packets transmitted, (\d+) received', output)
            if packets_match:
                transmitted = int(packets_match.group(1))
                received = int(packets_match.group(2))
                loss_percent = ((transmitted - received) / transmitted) * 100 if transmitted > 0 else 0
            else:
                transmitted = received = loss_percent = None

            # Extract timing info
            time_match = re.search(r'min/avg/max.*?=\s*([\d.]+)/([\d.]+)/([\d.]+)', output)
            if time_match:
                min_time = float(time_match.group(1))
                avg_time = float(time_match.group(2))
                max_time = float(time_match.group(3))
            else:
                min_time = avg_time = max_time = None

            return {
                "success": result.returncode == 0,
                "host": host,
                "packets_transmitted": transmitted,
                "packets_received": received,
                "packet_loss_percent": round(loss_percent, 1) if loss_percent is not None else None,
                "time_min_ms": min_time,
                "time_avg_ms": avg_time,
                "time_max_ms": max_time,
                "output_preview": output[:200] if output else None
            }

        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Ping to {host} timed out"}
        except FileNotFoundError:
            return {"success": False, "error": "ping command not available"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def dns_lookup(self, hostname):
        """Lookup DNS records for hostname."""
        try:
            # Try to resolve hostname
            addr_info = socket.getaddrinfo(hostname, None)

            ips = []
            for info in addr_info:
                family, _, _, _, sockaddr = info
                ip = sockaddr[0]
                if ip not in ips:
                    ips.append(ip)

            # Get canonical name
            try:
                canonical = socket.getfqdn(hostname)
            except:
                canonical = hostname

            return {
                "success": True,
                "hostname": hostname,
                "canonical_name": canonical,
                "ip_addresses": ips,
                "ip_count": len(ips),
                "ipv4": [ip for ip in ips if "." in ip],
                "ipv6": [ip for ip in ips if ":" in ip]
            }

        except socket.gaierror:
            return {"success": False, "error": f"Could not resolve {hostname}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def check_port(self, host, port, timeout=5):
        """Check if a port is open on a host."""
        try:
            # Clean host
            host = host.replace("http://", "").replace("https://", "").split("/")[0]

            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)

            result = sock.connect_ex((host, int(port)))
            sock.close()

            if result == 0:
                return {
                    "success": True,
                    "host": host,
                    "port": port,
                    "open": True,
                    "service": self._common_port_service(port)
                }
            else:
                return {
                    "success": True,
                    "host": host,
                    "port": port,
                    "open": False,
                    "error_code": result
                }

        except socket.gaierror:
            return {"success": False, "error": f"Could not resolve {host}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _common_port_service(self, port):
        """Get common service name for port."""
        common = {
            20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "TELNET",
            25: "SMTP", 53: "DNS", 80: "HTTP", 110: "POP3",
            143: "IMAP", 443: "HTTPS", 3306: "MySQL", 5432: "PostgreSQL",
            27017: "MongoDB", 6379: "Redis", 8080: "HTTP-ALT", 8443: "HTTPS-ALT"
        }
        return common.get(int(port), "Unknown")

    def check_http(self, url, timeout=10):
        """Check HTTP/HTTPS URL status."""
        try:
            # Try using curl first (more reliable)
            result = subprocess.run(
                ["curl", "-s", "-o", "/dev/null", "-w",
                 "%{http_code}|%{content_type}|%{time_total}",
                 "-L", "--max-time", str(timeout), url],
                capture_output=True,
                text=True,
                timeout=timeout + 5
            )

            if result.returncode == 0:
                parts = result.stdout.strip().split("|")
                status_code = parts[0] if len(parts) > 0 else "000"
                content_type = parts[1] if len(parts) > 1 else "unknown"
                time_total = parts[2] if len(parts) > 2 else "0"

                try:
                    response_time = float(time_total) * 1000  # Convert to ms
                except:
                    response_time = None

                return {
                    "success": True,
                    "url": url,
                    "status_code": int(status_code) if status_code.isdigit() else 0,
                    "accessible": status_code.startswith("2") or status_code.startswith("3"),
                    "content_type": content_type if content_type != "" else None,
                    "response_time_ms": round(response_time, 2) if response_time else None
                }

            # Fallback to urllib
            try:
                import urllib.request
                req = urllib.request.Request(url, method='HEAD')
                req.add_header('User-Agent', 'Mozilla/5.0 (NetworkTools)')
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.getcode(),
                        "accessible": True,
                        "content_type": response.headers.get('Content-Type')
                    }
            except ImportError:
                pass

            return {"success": False, "error": f"Could not check URL (curl returned {result.returncode})"}

        except subprocess.TimeoutExpired:
            return {"success": False, "error": "HTTP check timed out"}
        except FileNotFoundError:
            # curl not available, try urllib
            try:
                import urllib.request
                req = urllib.request.Request(url, method='HEAD')
                req.add_header('User-Agent', 'Mozilla/5.0 (NetworkTools)')
                with urllib.request.urlopen(req, timeout=timeout) as response:
                    return {
                        "success": True,
                        "url": url,
                        "status_code": response.getcode(),
                        "accessible": True
                    }
            except Exception as e:
                return {"success": False, "error": f"curl not available and urllib failed: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def my_ip(self):
        """Get local and public IP information."""
        try:
            # Get local IP
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(2)
                # Connect to a public DNS server to determine local IP
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()
            except:
                local_ip = "127.0.0.1"

            # Try to get public IP using curl
            public_ip = None
            try:
                result = subprocess.run(
                    ["curl", "-s", "--max-time", "5", "https://api.ipify.org"],
                    capture_output=True,
                    text=True,
                    timeout=7
                )
                if result.returncode == 0:
                    public_ip = result.stdout.strip()
            except:
                pass

            # Hostname
            try:
                hostname = socket.gethostname()
            except:
                hostname = "unknown"

            return {
                "success": True,
                "hostname": hostname,
                "local_ip": local_ip,
                "public_ip": public_ip,
                "has_internet": public_ip is not None
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def network_info(self):
        """Get network interface information."""
        try:
            info = {
                "hostname": socket.gethostname(),
                "fqdn": socket.getfqdn(),
                "platform": None
            }

            # Try to get more info using system commands
            try:
                result = subprocess.run(["hostname", "-I"], capture_output=True, text=True)
                if result.returncode == 0:
                    ips = result.stdout.strip().split()
                    info["all_ips"] = ips
            except:
                pass

            return {
                "success": True,
                **info
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "ping")

        if action == "ping":
            return self.ping(
                input_data.get("host", ""),
                input_data.get("count", 4),
                input_data.get("timeout", 5)
            )
        elif action == "dns_lookup":
            return self.dns_lookup(input_data.get("hostname", ""))
        elif action == "check_port":
            return self.check_port(
                input_data.get("host", ""),
                input_data.get("port", 80),
                input_data.get("timeout", 5)
            )
        elif action == "check_http":
            return self.check_http(
                input_data.get("url", ""),
                input_data.get("timeout", 10)
            )
        elif action == "my_ip":
            return self.my_ip()
        elif action == "info":
            return self.network_info()
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return NetworkToolsSkill().execute(input_data)


if __name__ == "__main__":
    skill = NetworkToolsSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    tests = [
        {"action": "ping", "host": "8.8.8.8", "count": 2},
        {"action": "dns_lookup", "hostname": "google.com"},
        {"action": "check_port", "host": "google.com", "port": 443},
        {"action": "my_ip"},
    ]

    for test in tests:
        print(f"\n{test}:")
        result = skill.execute(test)
        print(json.dumps(result, indent=2))
        if not result.get("success"):
            print(f"  Note: {result.get('error')}")
