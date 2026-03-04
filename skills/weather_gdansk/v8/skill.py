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
        self.temp_buffer = ""
        self.condition_buffer = ""
        self.location_buffer = ""
        self.found_temp = False
        self.found_condition = False
        self.found_location = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        
        # Try to find temperature (common patterns)
        if tag == 'span' or tag == 'div' or tag == 'p':
            classes = attrs_dict.get('class', '')
            if any(x in classes.lower() for x in ['temp', 'temperature', 'current-temp', 'degree']):
                self.in_temp = True
                self.temp_buffer = ""
            if any(x in classes.lower() for x in ['condition', 'weather', 'status', 'description']):
                self.in_condition = True
                self.condition_buffer = ""
            if any(x in classes.lower() for x in ['location', 'city', 'place']):
                self.in_location = True
                self.location_buffer = ""

    def handle_endtag(self, tag):
        if tag == self.current_tag:
            if self.in_temp:
                if self.temp_buffer and not self.found_temp:
                    self.temperature = self.temp_buffer.strip()
                    self.found_temp = True
                self.in_temp = False
            if self.in_condition:
                if self.condition_buffer and not self.found_condition:
                    self.condition = self.condition_buffer.strip()
                    self.found_condition = True
                self.in_condition = False
            if self.in_location:
                if self.location_buffer and not self.found_location:
                    self.location = self.location_buffer.strip()
                    self.found_location = True
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
    """Fetch current weather for Gdańsk using a weather website."""
    url = "https://www.accuweather.com/en/pl/gdansk/274664/weather-forecast/274664"
    
    try:
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html = response.read().decode('utf-8', errors='ignore')
        
        parser = WeatherGdanskParser()
        parser.feed(html)
        
        return {
            'temperature': parser.temperature,
            'condition': parser.condition,
            'location': parser.location or 'Gdańsk'
        }
    except urllib.error.URLError as e:
        return {'error': f"Network error: {str(e)}"}
    except Exception as e:
        return {'error': f"Unexpected error: {str(e)}"}


def speak_weather(weather_data):
    """Speak weather using espeak if available."""
    try:
        if 'error' in weather_data:
            text = f"Błąd: {weather_data['error']}"
        else:
            location = weather_data.get('location', 'Gdańsk')
            temp = weather_data.get('temperature', 'nieznana')
            condition = weather_data.get('condition', 'nieznana')
            text = f"Pogoda w {location}: {temp}, {condition}."
        
        subprocess.run(['espeak', '-v', 'pl', text], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        # espeak not available, silently continue
        return False
    except Exception:
        return False


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            # Extract text from params (as required)
            user_text = params.get('text', '')
            
            # Check if the user is asking about weather in Gdańsk
            # Accept various formulations
            text_lower = user_text.lower()
            if 'gdańsk' not in text_lower and 'gdansk' not in text_lower:
                return {
                    'success': False,
                    'error': "Zapytanie nie dotyczy Gdańska",
                    'text': user_text
                }
            
            # Fetch weather data
            weather_data = get_weather_gdansk()
            
            # Speak the weather if possible
            speak_weather(weather_data)
            
            # Prepare response
            if 'error' in weather_data:
                return {
                    'success': False,
                    'error': weather_data['error'],
                    'text': user_text
                }
            
            # Format response
            location = weather_data.get('location', 'Gdańsk')
            temp = weather_data.get('temperature', 'nieznana')
            condition = weather_data.get('condition', 'nieznana')
            response_text = f"Pogoda w {location}: {temp}, {condition}."
            
            return {
                'success': True,
                'location': location,
                'temperature': temp,
                'condition': condition,
                'text': response_text,
                'raw_data': weather_data
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': params.get('text', '')
            }


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v8',
        'description': 'Skill to fetch and announce current weather in Gdańsk'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS)
        subprocess.run(['espeak', '--version'], 
                      stdout=subprocess.DEVNULL, 
                      stderr=subprocess.DEVNULL)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'ok', 'note': 'espeak not found, TTS will be disabled'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


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