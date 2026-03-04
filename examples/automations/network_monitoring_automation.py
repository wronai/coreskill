#!/usr/bin/env python3
"""
Pipeline 6: Network Monitoring & Diagnostics

Automatyzuje monitorowanie sieci:
1. Ping test do kluczowych serwerów
2. DNS lookup dla domen
3. Sprawdzanie portów
4. Generowanie raportu HTML

Użycie:
  python3 examples/automations/network_monitoring_automation.py
"""
import sys
import json
import subprocess
from datetime import datetime
from pathlib import Path


def run_skill(skill_name, action, params):
    """Execute a skill via subprocess."""
    input_data = {"action": action, **params}
    cmd = [
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, 'skills/{skill_name}/v1')
from skill import execute
result = execute({json.dumps(input_data)})
print(json.dumps(result))
"""
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd='/home/tom/github/wronai/coreskill')
        return json.loads(result.stdout.strip().split('\n')[-1])
    except Exception as e:
        return {"success": False, "error": str(e)}


def network_monitoring_automation():
    """Complete network monitoring workflow."""
    print("🌐 Network Monitoring Automation")
    print("=" * 60)
    
    targets = {
        "google": "google.com",
        "github": "github.com",
        "dns": "8.8.8.8",
        "gateway": "192.168.1.1"
    }
    
    results = {
        "ping": {},
        "dns": {},
        "ports": {},
        "timestamp": datetime.now().isoformat()
    }
    
    # Step 1: Ping tests
    print("\n📡 Step 1: Running ping tests...")
    for name, host in targets.items():
        print(f"   Pinging {name} ({host})...")
        ping_result = run_skill("network_tools", "ping", {
            "host": host,
            "count": 3
        })
        results["ping"][name] = ping_result
        
        if ping_result.get("success"):
            stats = ping_result.get("statistics", {})
            print(f"     ✅ {stats.get('packets_received', 0)}/{stats.get('packets_sent', 0)} packets")
        else:
            print(f"     ❌ Failed: {ping_result.get('error', 'Unknown')}")
    
    # Step 2: DNS lookups
    print("\n🔍 Step 2: Running DNS lookups...")
    domains = ["google.com", "github.com", "openai.com"]
    for domain in domains:
        print(f"   Resolving {domain}...")
        dns_result = run_skill("network_tools", "dns_lookup", {
            "domain": domain
        })
        results["dns"][domain] = dns_result
        
        if dns_result.get("success"):
            ips = dns_result.get("ip_addresses", [])
            print(f"     ✅ {', '.join(ips[:2])}")
        else:
            print(f"     ❌ Failed")
    
    # Step 3: Port checks
    print("\n🔌 Step 3: Checking common ports...")
    ports = [
        {"host": "google.com", "port": 443, "name": "HTTPS"},
        {"host": "github.com", "port": 22, "name": "SSH"},
        {"host": "8.8.8.8", "port": 53, "name": "DNS"}
    ]
    
    for check in ports:
        print(f"   Checking {check['name']} on {check['host']}:{check['port']}...")
        port_result = run_skill("network_tools", "check_port", {
            "host": check["host"],
            "port": check["port"]
        })
        results["ports"][f"{check['host']}:{check['port']}"] = port_result
        
        status = "✅ Open" if port_result.get("is_open") else "❌ Closed"
        print(f"     {status}")
    
    # Step 4: Generate report
    print("\n📊 Step 4: Generating HTML report...")
    report_html = generate_network_report(results)
    
    report_path = Path.home() / ".evo_network_reports"
    report_path.mkdir(exist_ok=True)
    
    report_file = report_path / f"network_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    report_file.write_text(report_html, encoding='utf-8')
    
    print(f"   Report saved to: {report_file}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📈 Network Monitoring Summary")
    print("=" * 60)
    
    total_pings = len(results["ping"])
    successful_pings = sum(1 for r in results["ping"].values() if r.get("success"))
    
    total_dns = len(results["dns"])
    successful_dns = sum(1 for r in results["dns"].values() if r.get("success"))
    
    total_ports = len(results["ports"])
    open_ports = sum(1 for r in results["ports"].values() if r.get("is_open"))
    
    print(f"\n✅ Ping tests: {successful_pings}/{total_pings} successful")
    print(f"✅ DNS lookups: {successful_dns}/{total_dns} successful")
    print(f"🔌 Open ports: {open_ports}/{total_ports}")
    print(f"📄 Report: {report_file}")
    
    return {
        "success": True,
        "timestamp": results["timestamp"],
        "ping_success": f"{successful_pings}/{total_pings}",
        "dns_success": f"{successful_dns}/{total_dns}",
        "open_ports": f"{open_ports}/{total_ports}",
        "report_file": str(report_file)
    }


def generate_network_report(results):
    """Generate HTML report from network results."""
    timestamp = results["timestamp"]
    
    # Build ping rows
    ping_rows = ""
    for name, result in results["ping"].items():
        stats = result.get("statistics", {})
        status = "✅" if result.get("success") else "❌"
        ping_rows += f"<tr><td>{name}</td><td>{status}</td><td>{stats.get('packets_received', 0)}/{stats.get('packets_sent', 0)}</td><td>{stats.get('packet_loss', 'N/A')}</td></tr>"
    
    # Build DNS rows
    dns_rows = ""
    for domain, result in results["dns"].items():
        ips = result.get("ip_addresses", [])
        status = "✅" if result.get("success") else "❌"
        dns_rows += f"<tr><td>{domain}</td><td>{status}</td><td>{', '.join(ips[:2])}</td></tr>"
    
    # Build port rows
    port_rows = ""
    for endpoint, result in results["ports"].items():
        status = "✅ Open" if result.get("is_open") else "❌ Closed"
        port_rows += f"<tr><td>{endpoint}</td><td>{status}</td><td>{result.get('response_time_ms', 'N/A')} ms</td></tr>"
    
    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Network Monitoring Report</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; max-width: 1000px; margin: 0 auto; padding: 2rem; }}
        h1 {{ color: #333; border-bottom: 2px solid #3498db; padding-bottom: 0.5rem; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; }}
        th, td {{ padding: 0.75rem; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f5f5f5; font-weight: 600; }}
        tr:hover {{ background: #f9f9f9; }}
        .success {{ color: #27ae60; }}
        .error {{ color: #e74c3c; }}
    </style>
</head>
<body>
    <h1>🌐 Network Monitoring Report</h1>
    <p>Generated: {timestamp}</p>
    
    <h2>Ping Tests</h2>
    <table>
        <tr><th>Target</th><th>Status</th><th>Packets</th><th>Loss</th></tr>
        {ping_rows}
    </table>
    
    <h2>DNS Lookups</h2>
    <table>
        <tr><th>Domain</th><th>Status</th><th>IP Addresses</th></tr>
        {dns_rows}
    </table>
    
    <h2>Port Checks</h2>
    <table>
        <tr><th>Endpoint</th><th>Status</th><th>Response Time</th></tr>
        {port_rows}
    </table>
</body>
</html>"""


if __name__ == "__main__":
    result = network_monitoring_automation()
    print(f"\n📊 Full result: {json.dumps(result, indent=2)}")
