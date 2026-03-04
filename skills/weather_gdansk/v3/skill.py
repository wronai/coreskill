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
        self.temp = None
        self.condition = None
        self.location = None
        self.current_tag = None
        self.current_attrs = None
        self.temp_buffer = ""
        self.condition_buffer = ""
        self.location_buffer = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = attrs
        attrs_dict = dict(attrs)
        
        # Look for temperature (e.g., <span class="temp">12°</span>)
        if tag == 'span' and any('temp' in v.lower() for _, v in attrs if v):
            self.in_temp = True
            self.temp_buffer = ""
        # Look for weather condition (e.g., <div class="condition">Clear</div>)
        elif tag == 'div' and any('cond' in v.lower() for _, v in attrs if v):
            self.in_condition = True
            self.condition_buffer = ""
        # Look for location (e.g., <h1 class="location">Gdańsk</h1>)
        elif tag == 'h1' and any('loc' in v.lower() for _, v in attrs if v):
            self.in_location = True
            self.location_buffer = ""

    def handle_endtag(self, tag):
        if tag == 'span' and self.in_temp:
            self.temp = self.temp_buffer.strip()
            self.in_temp = False
        elif tag == 'div' and self.in_condition:
            self.condition = self.condition_buffer.strip()
            self.in_condition = False
        elif tag == 'h1' and self.in_location:
            self.location = self.location_buffer.strip()
            self.in_location = False

    def handle_data(self, data):
        if self.in_temp:
            self.temp_buffer += data
        elif self.in_condition:
            self.condition_buffer += data
        elif self.in_location:
            self.location_buffer += data


def get_weather_gdansk():
    """Fetch weather for Gdańsk from a public weather site."""
    # Use Open-Meteo API (no API key needed) for Gdańsk coordinates
    # Gdańsk: 54.3520° N, 18.6466° E
    url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = response.read().decode('utf-8')
            # Extract current weather info
            import json
            weather_data = json.loads(data)
            current = weather_data.get('current_weather', {})
            temp = current.get('temperature')
            windspeed = current.get('windspeed')
            return {
                'success': True,
                'temperature': temp,
                'windspeed': windspeed,
                'location': 'Gdańsk',
                'source': 'Open-Meteo API'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'location': 'Gdańsk'
        }


def get_info():
    return {
        'name': 'weather_gdansk',
        'version': 'v3',
        'description': 'Skill to fetch current weather in Gdańsk, Poland'
    }


def health_check():
    try:
        # Test network connectivity by attempting to reach a known endpoint
        req = urllib.request.Request(
            "https://www.google.com",
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Check if the query is about weather in Gdańsk
            if 'pogod' in text and 'gdańsk' in text:
                result = get_weather_gdansk()
                if result['success']:
                    temp = result.get('temperature')
                    windspeed = result.get('windspeed')
                    location = result.get('location', 'Gdańsk')
                    
                    # Construct response
                    response_text = f"Pogoda w Gdańsku: temperatura {temp}°C, prędkość wiatru {windspeed} km/h."
                    
                    # Try TTS if espeak is available
                    try:
                        subprocess.run(
                            ['espeak', '-v', 'pl', response_text],
                            capture_output=True,
                            timeout=5
                        )
                    except Exception:
                        pass  # Ignore TTS errors
                    
                    return {
                        'success': True,
                        'text': response_text,
                        'temperature': temp,
                        'windspeed': windspeed,
                        'location': location,
                        'source': result.get('source', 'Open-Meteo API')
                    }
                else:
                    return {
                        'success': False,
                        'text': f"Błąd pobierania pogody dla Gdańska: {result.get('error', 'nieznany błąd')}",
                        'error': result.get('error')
                    }
            else:
                return {
                    'success': False,
                    'text': "Zapytanie nie dotyczy pogody w Gdańsku.",
                    'error': 'no_match'
                }
        except Exception as e:
            return {
                'success': False,
                'text': f"Błąd wykonania: {str(e)}",
                'error': str(e)
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test block
    print("Testing weather_gdansk skill...")
    
    # Test health check
    health = health_check()
    print(f"Health check: {health}")
    
    # Test info
    info = get_info()
    print(f"Skill info: {info}")
    
    # Test execution
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(f"Execution result: {result}")