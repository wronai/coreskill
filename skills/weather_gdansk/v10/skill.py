import subprocess
import re
import urllib.request
import json
from html.parser import HTMLParser


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v10',
        'description': 'Searches for current weather in Gdańsk, Poland'
    }


def health_check() -> dict:
    try:
        # Test basic internet connectivity
        req = urllib.request.Request(
            'https://www.google.com',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return {'status': 'ok'}
    except Exception as e:
        pass
    
    return {'status': 'error', 'message': 'No internet connectivity'}


class WeatherHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.temperature = None
        self.condition = None
        self.location = None
        self.current_tag = None
        self.current_attrs = None
        self.temp_buffer = ""
        self.condition_buffer = ""
        self.location_buffer = ""
        self.found_temp = False
        self.found_condition = False
        self.found_location = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        self.current_attrs = attrs
        
        # Look for temperature (common patterns)
        if not self.found_temp:
            for attr in attrs:
                if isinstance(attr, tuple) and len(attr) >= 2:
                    if attr[0] in ['class', 'id', 'itemprop'] and any(x in str(attr[1]).lower() for x in ['temp', 'temperature', 'current-temp']):
                        self.in_temp = True
                        self.temp_buffer = ""
                        break
        
        # Look for condition
        if not self.found_condition:
            for attr in attrs:
                if isinstance(attr, tuple) and len(attr) >= 2:
                    if attr[0] in ['class', 'id', 'itemprop'] and any(x in str(attr[1]).lower() for x in ['condition', 'weather', 'description']):
                        self.in_condition = True
                        self.condition_buffer = ""
                        break
        
        # Look for location
        if not self.found_location:
            for attr in attrs:
                if isinstance(attr, tuple) and len(attr) >= 2:
                    if attr[0] in ['class', 'id', 'itemprop'] and any(x in str(attr[1]).lower() for x in ['location', 'city', 'place']):
                        self.in_location = True
                        self.location_buffer = ""
                        break

    def handle_endtag(self, tag):
        if self.in_temp and tag in ['span', 'div', 'p', 'h1', 'h2', 'h3']:
            if self.temp_buffer and not self.found_temp:
                # Try to extract temperature value
                temp_match = re.search(r'(-?\d+\.?\d*)\s*[°CcFf]', self.temp_buffer)
                if temp_match:
                    self.temperature = temp_match.group(1)
                    self.found_temp = True
            self.in_temp = False
            self.temp_buffer = ""
        
        if self.in_condition and tag in ['span', 'div', 'p', 'h1', 'h2', 'h3']:
            if self.condition_buffer and not self.found_condition:
                self.condition = self.condition_buffer.strip()
                self.found_condition = True
            self.in_condition = False
            self.condition_buffer = ""
        
        if self.in_location and tag in ['span', 'div', 'p', 'h1', 'h2', 'h3']:
            if self.location_buffer and not self.found_location:
                self.location = self.location_buffer.strip()
                self.found_location = True
            self.in_location = False
            self.location_buffer = ""

    def handle_data(self, data):
        if self.in_temp:
            self.temp_buffer += data
        if self.in_condition:
            self.condition_buffer += data
        if self.in_location:
            self.location_buffer += data


def extract_weather_from_html(html_content):
    parser = WeatherHTMLParser()
    parser.feed(html_content)
    
    # If parser didn't find data, try regex fallback
    if not parser.temperature:
        temp_match = re.search(r'(-?\d+\.?\d*)\s*[°CcFf]', html_content)
        if temp_match:
            parser.temperature = temp_match.group(1)
    
    if not parser.condition:
        # Look for common weather condition patterns
        condition_patterns = [
            r'(晴|晴れ|clear|sunny|cloudy|rainy|snowy|stormy|overcast|partly cloudy)',
            r'(wet|drizzly|foggy|hail|thunder|light rain|heavy rain)'
        ]
        for pattern in condition_patterns:
            cond_match = re.search(pattern, html_content, re.IGNORECASE)
            if cond_match:
                parser.condition = cond_match.group(1).strip()
                break
    
    if not parser.location:
        # Look for Gdańsk specifically
        gdansk_match = re.search(r'(Gdańsk|Gdansk|Gdánsk)', html_content, re.IGNORECASE)
        if gdansk_match:
            parser.location = "Gdańsk"
    
    return {
        'temperature': parser.temperature,
        'condition': parser.condition,
        'location': parser.location or "Gdańsk"
    }


def get_weather_from_weather_com():
    """Get weather data from weather.com for Gdańsk"""
    try:
        url = "https://weather.com/weather/today/l/54.5167,18.5333"
        req = urllib.request.Request(
            url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8')
            return extract_weather_from_html(html_content)
    except Exception as e:
        return None


def get_weather_from_open_meteo():
    """Get weather data from Open-Meteo API for Gdańsk coordinates"""
    try:
        # Gdańsk coordinates: 54.5167° N, 18.5333° E
        url = "https://api.open-meteo.com/v1/forecast?latitude=54.5167&longitude=18.5333&current_weather=true"
        req = urllib.request.Request(
            url,
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            if 'current_weather' in data:
                temp = data['current_weather'].get('temperature', 'N/A')
                # Get weather code description
                weather_codes = {
                    0: "Clear sky",
                    1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
                    45: "Fog", 48: "Depositing rime fog",
                    51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
                    56: "Light freezing drizzle", 57: "Dense freezing drizzle",
                    61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
                    66: "Light freezing rain", 67: "Heavy freezing rain",
                    71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow",
                    77: "Snow grains",
                    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
                    85: "Slight snow showers", 86: "Heavy snow showers",
                    95: "Thunderstorm", 96: "Thunderstorm with hail", 99: "Thunderstorm with heavy hail"
                }
                condition = weather_codes.get(data['current_weather'].get('weathercode', 0), "Unknown")
                return {
                    'temperature': str(temp),
                    'condition': condition,
                    'location': "Gdańsk"
                }
    except Exception as e:
        return None


def execute(params: dict) -> dict:
    try:
        text = params.get('text', '').lower()
        
        # Check if this is a weather query for Gdańsk
        if not any(keyword in text for keyword in ['pogod', 'weather', 'temperature', 'temp']):
            return {
                'success': False,
                'message': 'Not a weather query',
                'data': {}
            }
        
        if 'gdansk' not in text and 'gdańsk' not in text:
            return {
                'success': False,
                'message': 'Not about Gdańsk',
                'data': {}
            }
        
        # Try multiple sources
        weather_data = None
        
        # Try Open-Meteo first (more reliable)
        weather_data = get_weather_from_open_meteo()
        
        # Fallback to weather.com if Open-Meteo fails
        if not weather_data:
            weather_data = get_weather_from_weather_com()
        
        if weather_data and weather_data.get('temperature'):
            # Format response
            response_text = f"Pogoda w Gdańsku: {weather_data['temperature']}°C, {weather_data['condition']}"
            
            # Use espeak for TTS if available
            try:
                subprocess.run(['espeak', response_text], check=False)
            except Exception:
                pass  # TTS is optional
            
            return {
                'success': True,
                'message': response_text,
                'data': weather_data
            }
        else:
            return {
                'success': False,
                'message': 'Nie udało się pobrać danych pogodowych dla Gdańska',
                'data': {}
            }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Błąd: {str(e)}',
            'data': {}
        }


def execute_wrapper(params: dict) -> dict:
    return execute(params)


if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))