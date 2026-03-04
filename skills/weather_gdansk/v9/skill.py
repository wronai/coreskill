import re
import subprocess
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser


class WeatherGdanskParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.current_data = ""
        self.temperature = None
        self.condition = None
        self.location = "Gdańsk"
        self.data_buffer = []

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        # Try to find temperature (e.g., <span class="temp">15°</span>)
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"].lower()
            if any(x in cls for x in ["temp", "temperature"]):
                self.in_temp = True
        # Try to find weather condition (e.g., <div class="condition">Clear</div>)
        if tag == "div" and "class" in attrs_dict:
            cls = attrs_dict["class"].lower()
            if any(x in cls for x in ["condition", "weather", "status"]):
                self.in_condition = True
        # Try to find location (e.g., <h1 class="location">Gdańsk</h1>)
        if tag == "h1" and "class" in attrs_dict:
            cls = attrs_dict["class"].lower()
            if any(x in cls for x in ["location", "city"]):
                self.in_location = True

    def handle_endtag(self, tag):
        if tag == "span" and self.in_temp:
            self.in_temp = False
        if tag == "div" and self.in_condition:
            self.in_condition = False
        if tag == "h1" and self.in_location:
            self.in_location = False

    def handle_data(self, data):
        if self.in_temp:
            self.temperature = data.strip()
        elif self.in_condition:
            self.condition = data.strip()
        elif self.in_location:
            self.location = data.strip()


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
            if wmo_code in [0]:
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
        "version": "v9",
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
            # Check if the user asked for weather in Gdańsk
            if not any(keyword in text for keyword in ["pogoda", "temperatura", "warunki pogodowe"]):
                return {
                    "success": False,
                    "message": "Zapytanie nie dotyczy pogody.",
                    "text": "Nie rozpoznano zapytania o pogodę."
                }
            if "gdańsk" not in text and "gdansk" not in text:
                return {
                    "success": False,
                    "message": "Zapytanie nie dotyczy Gdańska.",
                    "text": "Zapytanie dotyczy innej lokalizacji niż Gdańsk."
                }

            weather_data = get_weather_gdansk()
            if "error" in weather_data:
                return {
                    "success": False,
                    "message": f"Błąd pobierania danych: {weather_data['error']}",
                    "text": "Nie udało się pobrać danych pogodowych."
                }

            temp = weather_data.get("temperature", "N/A")
            condition = weather_data.get("condition", "nieznane")
            response_text = f"W Gdańsku obecnie {temp} stopni Celsjusza, {condition}."
            return {
                "success": True,
                "temperature": temp,
                "condition": condition,
                "text": response_text
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Błąd wykonania: {str(e)}",
                "text": "Wystąpił błąd podczas przetwarzania zapytania."
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