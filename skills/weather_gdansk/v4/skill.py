import subprocess
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser


class WeatherGdanskParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.current_tag = ""
        self.temp = None
        self.condition = None
        self.location = "Gdańsk"
        self.data_buffer = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        # Try to identify temperature (e.g., <span class="temp">22°</span>)
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"]
            if any(x in cls.lower() for x in ["temp", "temperature"]):
                self.in_temp = True
        # Try to identify weather condition (e.g., <div class="condition">Clear</div>)
        if tag == "div" and "class" in attrs_dict:
            cls = attrs_dict["class"]
            if any(x in cls.lower() for x in ["condition", "weather"]):
                self.in_condition = True
        # Try to identify location (e.g., <h1 class="location">Gdańsk</h1>)
        if tag == "h1" and "class" in attrs_dict:
            cls = attrs_dict["class"]
            if any(x in cls.lower() for x in ["location", "city"]):
                self.in_location = True

    def handle_endtag(self, tag):
        self.current_tag = ""
        if tag == "span" and self.in_temp:
            self.in_temp = False
        if tag == "div" and self.in_condition:
            self.in_condition = False
        if tag == "h1" and self.in_location:
            self.in_location = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_temp and self.temp is None:
            # Extract numeric temp with unit
            match = re.search(r"(-?\d+\.?\d*)\s*°?C?", data)
            if match:
                self.temp = match.group(0)
        elif self.in_condition and self.condition is None:
            self.condition = data
        elif self.in_location and self.location == "Gdańsk":
            # Prefer the parsed location if found, but default to Gdańsk
            if data and len(data) > 2:
                self.location = data


def get_weather_gdansk():
    """Fetch weather for Gdańsk using a public weather API."""
    # Use Open-Meteo API (no key required, free, no CORS)
    # Coordinates for Gdańsk: 54.3520° N, 18.6466° E
    url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true&temperature_unit=celsius&timezone=auto"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read().decode('utf-8')
            # Simple JSON parsing using regex for stdlib-only
            temp_match = re.search(r'"temperature":\s*([-0-9.]+)', data)
            condition_match = re.search(r'"weathercode":\s*(\d+)', data)
            
            if temp_match:
                temp = temp_match.group(1)
                condition = "unknown"
                if condition_match:
                    code = int(condition_match.group(1))
                    # WMO weather interpretation codes
                    if code in [0, 1]:
                        condition = "clear sky"
                    elif code in [2, 3]:
                        condition = "partly cloudy"
                    elif code in [45, 48]:
                        condition = "foggy"
                    elif code in [51, 53, 55, 56, 57]:
                        condition = "drizzle"
                    elif code in [61, 63, 65, 66, 67]:
                        condition = "rain"
                    elif code in [71, 73, 75, 77, 85, 86]:
                        condition = "snow"
                    elif code in [80, 81, 82]:
                        condition = "showers"
                    elif code in [95, 96, 99]:
                        condition = "thunderstorm"
                return {"temperature": temp, "condition": condition}
            else:
                return None
    except Exception as e:
        return None


def get_info():
    return {
        "name": "weather_gdansk",
        "version": "v4",
        "description": "Searches for current weather in Gdańsk"
    }


def health_check():
    try:
        result = get_weather_gdansk()
        if result is not None:
            return {"status": "ok"}
        else:
            return {"status": "error", "message": "Weather API unreachable"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "").lower()
            
            # Check if the user is asking about weather in Gdańsk
            if "pogod" in text and ("gdańsk" in text or "gdansk" in text):
                weather_data = get_weather_gdansk()
                if weather_data:
                    temp = weather_data.get("temperature", "unknown")
                    condition = weather_data.get("condition", "unknown")
                    response_text = f"Pogoda w Gdańsku: {temp}°C, {condition}."
                    return {
                        "success": True,
                        "result": {
                            "text": response_text,
                            "weather": weather_data
                        }
                    }
                else:
                    return {
                        "success": False,
                        "error": "Nie udało się pobrać danych pogodowych."
                    }
            else:
                # Not a weather query for Gdańsk
                return {
                    "success": False,
                    "error": "Zapytanie nie dotyczy pogody w Gdańsku."
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Błąd wykonania: {str(e)}"
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(result)