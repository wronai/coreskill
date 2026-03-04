#!/usr/bin/env python3
"""
Weather skill - Sprawdza pogodę używając wttr.in (bez API key)
"""
import subprocess
import json
import re
from typing import Dict, Any


def get_info() -> Dict[str, Any]:
    """Zwraca metadane skilla."""
    return {
        "name": "weather",
        "version": "v1",
        "description": "Sprawdza aktualną pogodę dla podanej lokalizacji",
        "author": "CoreSkill AI",
        "actions": ["current", "forecast"],
        "parameters": {
            "location": {
                "type": "string",
                "description": "Nazwa miasta lub lokalizacji",
                "required": True,
                "example": "Warsaw, Krakow, London"
            },
            "format": {
                "type": "string",
                "description": "Format wyniku",
                "default": "text",
                "enum": ["text", "json"]
            }
        }
    }


def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sprawdza pogodę dla podanej lokalizacji.
    
    Args:
        params: {"location": "Warsaw", "format": "text"}
    
    Returns:
        {"success": True, "result": {"temp": "15°C", "condition": "Sunny", ...}}
    """
    location = params.get("location", "").strip()
    fmt = params.get("format", "text")
    
    if not location:
        return {
            "success": False,
            "error": "Missing required parameter: location",
            "suggestion": "Provide location: execute({'location': 'Warsaw'})"
        }
    
    try:
        # Use wttr.in API (free, no API key needed)
        # Format: j1 = JSON format
        url = f"wttr.in/{location}?format=j1"
        
        result = subprocess.run(
            ["curl", "-s", "--max-time", "10", url],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"Failed to fetch weather: {result.stderr}",
                "suggestion": "Check internet connection or try different location"
            }
        
        # Parse JSON response
        try:
            data = json.loads(result.stdout)
        except json.JSONDecodeError:
            # wttr.in returns HTML error page for unknown locations
            if "Unknown location" in result.stdout or "404" in result.stdout:
                return {
                    "success": False,
                    "error": f"Unknown location: {location}",
                    "suggestion": "Try city name in English, e.g., 'Warsaw', 'Krakow', 'London'"
                }
            return {
                "success": False,
                "error": "Invalid response from weather service",
                "suggestion": "Try again later or check if location name is correct"
            }
        
        # Extract current weather
        current = data.get("current_condition", [{}])[0]
        
        weather_data = {
            "location": location,
            "temperature_c": current.get("temp_C"),
            "temperature_f": current.get("temp_F"),
            "feels_like_c": current.get("FeelsLikeC"),
            "humidity": current.get("humidity"),
            "pressure": current.get("pressure"),
            "wind_speed_kmph": current.get("windspeedKmph"),
            "wind_direction": current.get("winddir16Point"),
            "description": current.get("weatherDesc", [{}])[0].get("value", "Unknown"),
            "visibility_km": current.get("visibility"),
            "uv_index": current.get("uvIndex"),
        }
        
        # Format output
        if fmt == "json":
            output = weather_data
        else:
            # Human-readable format in Polish
            temp = weather_data["temperature_c"]
            feels = weather_data["feels_like_c"]
            desc = weather_data["description"]
            humidity = weather_data["humidity"]
            wind = weather_data["wind_speed_kmph"]
            
            output = (
                f"🌡️ Temperatura: {temp}°C (odczuwalna: {feels}°C)\n"
                f"☁️ Warunki: {desc}\n"
                f"💧 Wilgotność: {humidity}%\n"
                f"💨 Wiatr: {wind} km/h {weather_data['wind_direction']}\n"
                f"📍 Lokalizacja: {location}"
            )
        
        return {
            "success": True,
            "result": weather_data,
            "formatted": output if fmt == "text" else None,
            "message": output if fmt == "text" else f"Weather in {location}: {weather_data['temperature_c']}°C, {weather_data['description']}"
        }
        
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Request timeout - weather service not responding",
            "suggestion": "Try again later"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestion": "Check location name and try again"
        }


def health_check() -> Dict[str, Any]:
    """Sprawdza health skilla."""
    try:
        # Test with a known location
        result = execute({"location": "London", "format": "json"})
        if result["success"]:
            return {
                "status": "ok",
                "message": "Weather skill is working"
            }
        else:
            return {
                "status": "degraded",
                "message": f"Weather API issue: {result.get('error')}"
            }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }


if __name__ == "__main__":
    # Test
    print("Testing weather skill...")
    result = execute({"location": "Warsaw", "format": "text"})
    print(f"Result: {result}")
