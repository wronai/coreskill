#!/usr/bin/env python3
"""
Weather skill - Sprawdza pogodę używając wttr.in (bez API key)
"""
import json
import re
import ssl
import urllib.request
import urllib.error
from typing import Dict, Any


def _extract_location(text: str) -> str:
    """Extract location from free text like 'jaka jest pogoda w Warszawie'."""
    if not text:
        return ""
    # Try Polish/English prepositions
    for pattern in [r'\bw\s+([A-Z\u0100-\u017E][\w\s-]{1,30})',
                    r'\bin\s+([A-Z][\w\s-]{1,30})',
                    r'\bdla\s+([A-Z\u0100-\u017E][\w\s-]{1,30})',
                    r'\bfor\s+([A-Z][\w\s-]{1,30})']:
        m = re.search(pattern, text)
        if m:
            return m.group(1).strip().rstrip('?.!')
    return ""


def _fetch_weather(location: str) -> Dict:
    """Pobiera dane pogodowe z wttr.in."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    encoded_location = location.replace(" ", "%20")
    url = f"https://wttr.in/{encoded_location}?format=j1"
    
    req = urllib.request.Request(url, headers={'User-Agent': 'curl/7.68.0'})
    
    with urllib.request.urlopen(req, context=ctx, timeout=10) as response:
        return json.loads(response.read().decode('utf-8'))


class WeatherSkill:
    def execute(self, params: dict) -> dict:
        """Główna funkcja wykonawcza skilla pogodowego."""
        try:
            location = params.get("location", "")
            if not location:
                # Parse location from free text (e.g. "jaka jest pogoda w Warszawie")
                text = params.get("text", "")
                location = _extract_location(text)
            # wttr.in auto-detects from IP when location is empty
            data = _fetch_weather(location)
            
            # Generate spoken response
            if data and "current_condition" in data and data["current_condition"]:
                condition = data["current_condition"][0].get("weatherDesc", [{}])[0].get("value", "nieznana")
                temp = data["current_condition"][0].get("temp_C", "nieznana")
                spoken = f"Pogoda to {condition}, temperatura {temp} stopni Celsjusza."
            else:
                spoken = "Nie mogę znaleźć aktualnych danych pogodowych."
            
            return {
                "success": True,
                "data": data,
                "location": location,
                "status": "ok",
                "spoken": spoken
            }
        except urllib.error.URLError as e:
            return {
                "success": False, 
                "error": f"Network error: {str(e.reason)}",
                "status": "error",
                "spoken": "Nie mogę połączyć się z serwisem pogodowym."
            }
        except Exception as e:
            return {
                "success": False, 
                "error": str(e),
                "status": "error",
                "spoken": "Wystąpił błąd podczas pobierania danych pogodowych."
            }


def execute(params: dict) -> dict:
    """Module-level execute function."""
    skill = WeatherSkill()
    return skill.execute(params)


def health_check() -> dict:
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


def get_info() -> dict:
    return {"name": "weather", "version": "v1", "description": "weather skill"}


if __name__ == "__main__":
    # Test
    print("Testing weather skill...")
    result = execute({"text": "jaka jest pogoda w Gdańsku"})
    print(f"Result: {result}")