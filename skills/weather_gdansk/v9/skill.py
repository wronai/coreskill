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
        self.temperature = None
        self.condition = None
        self.location = None
        self.current_tag = None
        self.current_attrs = []
        self.temp_buffer = ""
        self.condition_buffer = ""
        self.location_buffer = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = attrs
        attrs_dict = dict(attrs)
        
        # Look for temperature (common patterns: span with class containing 'temp', div with 'temp')
        if tag == 'span' or tag == 'div':
            class_attr = attrs_dict.get('class', '')
            if any(keyword in class_attr.lower() for keyword in ['temp', 'temperature']):
                self.in_temp = True
                self.temp_buffer = ""
            if any(keyword in class_attr.lower() for keyword in ['condition', 'weather', 'status']):
                self.in_condition = True
                self.condition_buffer = ""
            if any(keyword in class_attr.lower() for keyword in ['location', 'city', 'place']):
                self.in_location = True
                self.location_buffer = ""

    def handle_endtag(self, tag):
        if self.in_temp and tag == ('span' if self.current_tag == 'span' else 'div'):
            self.temperature = self.temp_buffer.strip()
            self.in_temp = False
        if self.in_condition and tag == ('span' if self.current_tag == 'span' else 'div'):
            self.condition = self.condition_buffer.strip()
            self.in_condition = False
        if self.in_location and tag == ('span' if self.current_tag == 'span' else 'div'):
            self.location = self.location_buffer.strip()
            self.in_location = False
        self.current_tag = None

    def handle_data(self, data):
        if self.in_temp:
            self.temp_buffer += data
        if self.in_condition:
            self.condition_buffer += data
        if self.in_location:
            self.location_buffer += data


def get_weather_gdansk():
    """Fetch weather for Gdańsk using a weather API or web scraping."""
    # Try Open-Meteo API (no API key required)
    try:
        # Gdańsk coordinates: 54.3520° N, 18.6466° E
        url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read().decode('utf-8')
            import json
            weather_data = json.loads(data)
            current = weather_data.get("current_weather", {})
            temp = current.get("temperature")
            windspeed = current.get("windspeed")
            return {
                "success": True,
                "temperature": f"{temp}°C",
                "windspeed": f"{windspeed} km/h",
                "location": "Gdańsk",
                "source": "Open-Meteo API"
            }
    except Exception as e:
        # Fallback to web scraping (e.g., YR.no or AccuWeather)
        try:
            # Try YR.no (Norwegian Meteorological Institute) which has English weather for Gdańsk
            url = "https://www.yr.no/en/place/Poland/Pomeranian_Gvo/Gdansk/"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
                parser = WeatherGdanskParser()
                parser.feed(html)
                if parser.temperature and parser.condition:
                    return {
                        "success": True,
                        "temperature": parser.temperature,
                        "condition": parser.condition,
                        "location": parser.location or "Gdańsk",
                        "source": "YR.no"
                    }
        except Exception as e2:
            return {
                "success": False,
                "error": f"Failed to fetch weather: {str(e)}; fallback failed: {str(e2)}"
            }
    return {"success": False, "error": "Unknown weather fetch failure"}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            if 'pogod' in text and 'gdańsk' in text:
                result = get_weather_gdansk()
                if result['success']:
                    response_text = f"Pogoda w Gdańsku: {result['temperature']}, {result.get('condition', 'nieznana')}. Źródło: {result['source']}."
                    # Use espeak for TTS
                    try:
                        subprocess.run(['espeak', response_text], check=True, capture_output=True)
                    except Exception:
                        pass  # TTS is optional
                    return {
                        'success': True,
                        'text': response_text,
                        'weather': {
                            'temperature': result['temperature'],
                            'condition': result.get('condition', 'nieznana'),
                            'location': result['location'],
                            'source': result['source']
                        }
                    }
                else:
                    return {
                        'success': False,
                        'text': "Nie udało się pobrać danych pogodowych dla Gdańska.",
                        'error': result.get('error', 'Unknown error')
                    }
            else:
                return {
                    'success': False,
                    'text': "Zapytanie nie dotyczy pogody w Gdańsku.",
                    'error': "No match"
                }
        except Exception as e:
            return {
                'success': False,
                'text': "Wystąpił błąd podczas przetwarzania zapytania.",
                'error': str(e)
            }


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v9',
        'description': 'Skill do sprawdzania aktualnej pogody w Gdańsku'
    }


def health_check() -> dict:
    try:
        # Minimal health check: ensure espeak is available (optional) and urllib works
        urllib.request.urlopen("https://www.yr.no", timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test block
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(result)