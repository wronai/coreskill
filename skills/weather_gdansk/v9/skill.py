import re
import subprocess
import urllib.request
import json
from html.parser import HTMLParser


class WeatherGdanskParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.current_tag = None
        self.current_class = None
        self.temperature = None
        self.condition = None
        self.location = "Gdańsk"
        self.data_buffer = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        self.current_class = attrs_dict.get('class', '')
        
        # Try to find temperature (common patterns: 'temp', 'temperature', 'current-temp')
        if any(x in self.current_class.lower() for x in ['temp', 'temperature', 'current-temp']):
            self.in_temp = True
        
        # Try to find condition description
        if any(x in self.current_class.lower() for x in ['condition', 'weather', 'desc']):
            self.in_condition = True
        
        # Try to find location
        if any(x in self.current_class.lower() for x in ['location', 'city', 'place']):
            self.in_location = True

    def handle_endtag(self, tag):
        self.current_tag = None
        self.current_class = None

    def handle_data(self, data):
        if self.in_temp:
            self.temperature = data.strip()
            self.in_temp = False
        elif self.in_condition:
            self.condition = data.strip()
            self.in_condition = False
        elif self.in_location:
            self.location = data.strip()
            self.in_location = False


def get_weather_gdansk():
    """Fetch weather for Gdańsk from a public weather API."""
    try:
        # Use Open-Meteo API for Gdańsk coordinates (54.3520° N, 18.6466° E)
        url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true&temperature_unit=celsius&wind_speed_unit=kmh&precipitation_unit=mm&timezone=auto"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'current_weather' in data:
                temp = data['current_weather']['temperature']
                return f"Pogoda w Gdańsku: {temp}°C"
            else:
                return "Nie udało się pobrać danych pogodowych."
    except Exception as e:
        return f"Błąd pobierania danych pogodowych: {str(e)}"


def get_info():
    return {
        "name": "weather_gdansk",
        "version": "v9",
        "description": "Skill do sprawdzania aktualnej pogody w Gdańsku"
    }


def health_check():
    try:
        # Basic connectivity check using subprocess to ping a known host
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                timeout=5)
        if result.returncode == 0:
            return {"status": "ok"}
        else:
            return {"status": "error", "message": "No internet connectivity"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Check if the query is about weather in Gdańsk
            if 'pogod' in text and ('gdańsk' in text or 'gdansk' in text):
                weather_info = get_weather_gdansk()
                return {
                    "success": True,
                    "text": weather_info,
                    "raw_response": weather_info
                }
            else:
                return {
                    "success": False,
                    "text": "Zapytanie nie dotyczy pogody w Gdańsku.",
                    "error": "No weather query for Gdańsk"
                }
        except Exception as e:
            return {
                "success": False,
                "text": f"Wystąpił błąd podczas przetwarzania zapytania: {str(e)}",
                "error": str(e)
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))