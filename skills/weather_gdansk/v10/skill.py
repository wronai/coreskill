import re
import subprocess
import json
import urllib.request
import urllib.error
from html.parser import HTMLParser


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v10',
        'description': 'Searches for current weather in Gdańsk, Poland'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available for TTS (optional, but used in other skills)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        # Test internet connectivity with a simple HTTP request
        req = urllib.request.Request(
            'https://www.google.com',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            if response.status == 200:
                return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}
    return {'status': 'ok'}


class WeatherParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.current_temp = None
        self.current_condition = None
        self.current_location = None
        self.temp_data = []
        self.condition_data = []
        self.location_data = []
        self._inside_span = False
        self._inside_div = False
        self._span_class = None
        self._div_class = None

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == 'span':
            self._inside_span = True
            self._span_class = attrs_dict.get('class', '')
            if 'CurrentConditions--tempValue--' in self._span_class:
                self.in_temp = True
        elif tag == 'div':
            self._inside_div = True
            self._div_class = attrs_dict.get('class', '')
            if 'CurrentConditions--phraseValue--' in self._div_class:
                self.in_condition = True
            elif 'CurrentConditions--location--' in self._div_class:
                self.in_location = True

    def handle_endtag(self, tag):
        if tag == 'span':
            self._inside_span = False
            self._span_class = None
            self.in_temp = False
        elif tag == 'div':
            self._inside_div = False
            self._div_class = None
            self.in_condition = False
            self.in_location = False

    def handle_data(self, data):
        if self.in_temp:
            self.temp_data.append(data.strip())
        elif self.in_condition:
            self.condition_data.append(data.strip())
        elif self.in_location:
            self.location_data.append(data.strip())


def extract_weather_data(html_content: str) -> dict:
    parser = WeatherParser()
    parser.feed(html_content)
    
    temp = ''.join(parser.temp_data).strip() if parser.temp_data else None
    condition = ' '.join(parser.condition_data).strip() if parser.condition_data else None
    location = ' '.join(parser.location_data).strip() if parser.location_data else None
    
    return {
        'temperature': temp,
        'condition': condition,
        'location': location
    }


def get_gdansk_weather() -> dict:
    """Fetch weather for Gdańsk from a weather website"""
    url = "https://weather.com/weather/today/l/Gdansk+Pomerania+Poland?unit=m"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html_content = response.read().decode('utf-8')
        
        weather_data = extract_weather_data(html_content)
        
        # If we didn't get data from the parser, try to find temperature with regex
        if not weather_data['temperature']:
            temp_match = re.search(r'(-?\d+°)', html_content)
            if temp_match:
                weather_data['temperature'] = temp_match.group(1)
        
        if not weather_data['condition']:
            condition_match = re.search(r'([A-Za-z\s]+)(?=\s*°)', html_content)
            if condition_match:
                weather_data['condition'] = condition_match.group(1).strip()
        
        return weather_data
    except Exception as e:
        return {'error': str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            
            # Check if the request is about weather in Gdańsk
            if not re.search(r'pogod[aeiu]?\s+w\s+gda[ńn]sku', text.lower()):
                return {
                    'success': False,
                    'message': 'Request not about weather in Gdańsk'
                }
            
            weather_data = get_gdansk_weather()
            
            if 'error' in weather_data:
                return {
                    'success': False,
                    'message': f"Failed to get weather data: {weather_data['error']}"
                }
            
            # Format the response
            temp = weather_data.get('temperature', 'nieznana')
            condition = weather_data.get('condition', 'nieznany')
            location = weather_data.get('location', 'Gdańsk')
            
            response_text = f"Pogoda w Gdańsku: {temp}, {condition}."
            
            # Try to speak the response using espeak
            try:
                subprocess.run(['espeak', '-v', 'pl', response_text], 
                             capture_output=True, timeout=5)
            except Exception:
                pass  # Skip TTS if not available
            
            return {
                'success': True,
                'response': response_text,
                'weather': {
                    'location': location,
                    'temperature': temp,
                    'condition': condition
                }
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f"Unexpected error: {str(e)}"
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))