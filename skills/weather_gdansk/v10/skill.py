import re
import subprocess
import json
import urllib.request
import urllib.error


def get_weather_gdansk():
    """Fetch weather for Gdańsk from a public weather API."""
    try:
        # Use Open-Meteo API (no API key required)
        # Coordinates for Gdańsk: 54.3520° N, 18.6466° E
        url = (
            "https://api.open-meteo.com/v1/forecast?"
            "latitude=54.3520&longitude=18.6466"
            "&current_weather=true&temperature_unit=celsius"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
            current = data.get("current_weather", {})
            temp = current.get("temperature", "N/A")
            # Try to get weather condition from additional fields if available
            # Open-Meteo doesn't provide condition string directly, so we'll infer
            # from wmo_code (https://open-meteo.com/en/docs)
            wmo_code = current.get("weathercode", 0)
            condition = "Nieznany"
            if wmo_code == 0:
                condition = "Bezchmurnie"
            elif wmo_code in [1, 2, 3]:
                condition = "Pochmurnie"
            elif wmo_code in [45, 48]:
                condition = "Mgła"
            elif wmo_code in [51, 53, 55, 56, 57]:
                condition = "Mżawka"
            elif wmo_code in [61, 63, 65, 66, 67]:
                condition = "Deszcz"
            elif wmo_code in [71, 73, 75, 77, 80, 81, 82]:
                condition = "Śnieg"
            elif wmo_code in [85, 86]:
                condition = "Zamieć śnieżna"
            elif wmo_code in [95, 96, 99]:
                condition = "Burza"
            return {"temperature": str(temp), "condition": condition}
    except Exception as e:
        return {"error": str(e)}


def get_info() -> dict:
    return {
        "name": "weather_gdansk",
        "version": "v1",
        "description": "Skill do pobierania aktualnej pogody w Gdańsku"
    }


def health_check() -> dict:
    try:
        # Simple connectivity check to Open-Meteo
        req = urllib.request.Request(
            "https://api.open-meteo.com/health",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return {"status": "ok"}
            else:
                return {"status": "error", "message": "Unexpected health check response"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "").lower()
            
            # Extract location (default to Gdańsk)
            location = "Gdańsk"
            location_match = re.search(r'(?:w|w\s+gdańsku|gdzieś\s+w|gdzieś\s+w\s+gdańsku)\s*(\w+)', text)
            if location_match:
                location = location_match.group(1).capitalize()
            elif "gdansk" in text or "gdańsk" in text:
                location = "Gdańsk"
            
            # Check if the user asked for weather-related info
            weather_keywords = ["pogoda", "temperatura", "warunki pogodowe", "temperaturę", "czy pada"]
            if not any(keyword in text for keyword in weather_keywords):
                return {
                    "success": False,
                    "message": "Zapytanie nie dotyczy pogody.",
                    "text": "Nie rozpoznano zapytania o pogodę.",
                    "spoken": "Nie rozpoznano zapytania o pogodę."
                }
            
            # For Gdańsk specifically
            if location == "Gdańsk":
                weather_data = get_weather_gdansk()
                if "error" in weather_data:
                    return {
                        "success": False,
                        "message": f"Błąd pobierania danych: {weather_data['error']}",
                        "text": "Nie udało się pobrać danych pogodowych.",
                        "spoken": "Nie udało się pobrać danych pogodowych."
                    }

                temp = weather_data.get("temperature", "N/A")
                condition = weather_data.get("condition", "nieznane")
                response_text = f"W Gdańsku obecnie {temp} stopni Celsjusza, {condition}."
                return {
                    "success": True,
                    "temperature": temp,
                    "condition": condition,
                    "text": response_text,
                    "spoken": response_text
                }
            else:
                # For other locations, fallback to generic message
                return {
                    "success": False,
                    "message": "Obsługujemy obecnie tylko Gdańsk.",
                    "text": "Obecnie obsługujemy tylko pogodę w Gdańsku.",
                    "spoken": "Obecnie obsługujemy tylko pogodę w Gdańsku."
                }
        except Exception as e:
            return {
                "success": False,
                "message": f"Błąd wykonania: {str(e)}",
                "text": "Wystąpił błąd podczas przetwarzania zapytania.",
                "spoken": "Wystąpił błąd podczas przetwarzania zapytania."
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    print("Testing weather_gdansk skill...")
    print("Health check:", health_check())
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print("Test result:", json.dumps(result, indent=2, ensure_ascii=False))