#!/usr/bin/env python3
"""
Weather skill - Sprawdza pogodę używając wttr.in (bez API key)
"""
import json
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any


def _fetch_weather(location: str) -> Dict:
    """Pobiera dane pogodowe z wttr.in."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    encoded_location = location.replace(" ", "%20")
    url = f"https://wttr.in/{encoded_location}?format=j1"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
    
    with urllib.request.urlopen(req, context=ctx, timeout=15) as response:
        return json.loads(response.read().decode('utf-8'))


def execute(input_data: Dict[str, Any]) -> Dict[str, Any]:
    """Główna funkcja wykonawcza skilla pogodowego."""
    try:
        location = input_data.get("location")
        if not location:
            return {"success": False, "error": "Brak lokalizacji"}
            
        data = _fetch_weather(location)
        
        return {
            "success": True,
            "data": data,
            "location": location,
            "status": "ok"
        }
    except Exception as e:
        return {"success": False, "error": str(e), "status": "error"}


def health_check() -> Dict[str, Any]:
    """Sprawdza health skilla (lightweight — bez wywołań sieciowych)."""
    try:
        # Verify core dependencies are importable
        import json as _j, ssl as _s, urllib.request as _u
        # Verify execute function exists and is callable
        if not callable(execute):
            return {"status": "error", "message": "execute not callable"}
        return {
            "status": "ok",
            "message": "Weather skill ready (deps OK)"
        }
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Missing dependency: {e}"
        }


if __name__ == "__main__":
    # Test
    print("Testing weather skill...")
    result = execute({"location": "Warsaw", "format": "text"})
    print(f"Result: {result}")


def get_info():
    return {"name": "weather", "version": "v1", "description": "weather skill"}

