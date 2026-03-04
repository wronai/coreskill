#!/usr/bin/env python3
"""
network_info - Pobiera informacje o sieci (IP, MAC)
"""
import subprocess
import json
import re
from typing import Dict, Any


def get_info():
    return {
        "name": "network_info",
        "version": "v1", 
        "description": "Pokazuje adres IP i MAC urządzenia",
        "actions": ["show_ip", "show_mac", "show_all"]
    }


def execute(params: dict) -> dict:
    action = params.get("action", "show_all")
    
    try:
        if action in ("show_ip", "show_all"):
            # Get IP
            ip_result = subprocess.run(
                ["hostname", "-I"],
                capture_output=True, text=True, timeout=5
            )
            ip = ip_result.stdout.strip().split()[0] if ip_result.stdout else "N/A"
        else:
            ip = "N/A"
        
        if action in ("show_mac", "show_all"):
            # Get MAC from ip link
            mac_result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True, text=True, timeout=5
            )
            mac_match = re.search(r"link/ether\s+([0-9a-f:]{17})", mac_result.stdout)
            mac = mac_match.group(1) if mac_match else "N/A"
        else:
            mac = "N/A"
        
        result = {"ip": ip, "mac": mac}
        
        if action == "show_all":
            msg = f"📡 IP: {ip}\n🔗 MAC: {mac}"
        elif action == "show_ip":
            msg = f"📡 Adres IP: {ip}"
        else:
            msg = f"🔗 Adres MAC: {mac}"
        
        return {
            "success": True,
            "result": result,
            "message": msg
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestion": "Sprawdź czy masz zainstalowane polecenia: ip, hostname"
        }


def health_check():
    result = execute({"action": "show_all"})
    return {
        "status": "ok" if result["success"] else "error",
        "message": "Network info working" if result["success"] else result.get("error")
    }
