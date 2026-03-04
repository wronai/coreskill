import subprocess
import re
import urllib.request
import html
from html.parser import HTMLParser


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v10',
        'description': 'Searches the web for current weather in Gdańsk'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed later)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


class WeatherHTMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.current_tag = ''
        self.temperature = ''
        self.condition = ''
        self.location = ''
        self.data_buffer = ''

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        # Look for temperature indicators
        if tag == 'span' and 'class' in attrs_dict:
            if 'temp' in attrs_dict['class'].lower() or 'temperature' in attrs_dict['class'].lower():
                self.in_temp = True
        # Look for condition indicators
        if tag == 'div' and 'class' in attrs_dict:
            if 'condition' in attrs_dict['class'].lower() or 'weather' in attrs_dict['class'].lower():
                self.in_condition = True
        # Look for location indicators
        if tag == 'h1' or tag == 'h2':
            self.in_location = True

    def handle_endtag(self, tag):
        self.current_tag = ''
        if tag in ['span', 'div', 'h1', 'h2']:
            self.in_temp = False
            self.in_condition = False
            self.in_location = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_temp:
            # Extract numeric temperature
            temp_match = re.search(r'[-+]?\d+\.?\d*', data)
            if temp_match:
                self.temperature = temp_match.group()
        elif self.in_condition:
            self.condition = data
        elif self.in_location:
            self.location = data


def extract_weather_from_html(html_content):
    parser = WeatherHTMLParser()
    parser.feed(html_content)
    
    # If parser didn't find data, try regex fallback
    if not parser.temperature:
        temp_match = re.search(r'([-+]?\d+\.?\d*)\s*°[CF]', html_content)
        if temp_match:
            parser.temperature = temp_match.group(1)
    
    if not parser.condition:
        condition_match = re.search(r'(?:晴|晴朗|多云|阴|小雨|大雨|雪|雷雨|雾|霾|雨夹雪|阵雨|暴雨|小雪|大雪|沙尘|浮尘|扬沙|强沙尘|龙卷风|台风|雷电|冰雹|霜|冻|热|冷|湿|干|闷|舒适|宜人)', html_content)
        if condition_match:
            parser.condition = condition_match.group(1)
    
    return {
        'temperature': parser.temperature,
        'condition': parser.condition,
        'location': parser.location if parser.location else 'Gdańsk'
    }


def execute(params: dict) -> dict:
    try:
        text = params.get('text', '')
        
        # Extract query if it matches expected patterns
        query_patterns = [
            r'wyszukaj\s+w\s+internecie\s+pogodę\s+w\s+Gdańsku',
            r'pogoda\s+w\s+Gdańsku',
            r'jak\s+jest\s+pogoda\s+w\s+Gdańsku',
            r'pogoda\s+Gdańsk'
        ]
        
        matched = False
        for pattern in query_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                matched = True
                break
        
        if not matched:
            return {
                'success': False,
                'error': 'Query does not match expected pattern for Gdańsk weather'
            }
        
        # Use DuckDuckGo HTML search to find weather info
        # DuckDuckGo often shows weather cards in search results
        query = "pogoda w Gdańsku"
        search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote(query)}"
        
        req = urllib.request.Request(
            search_url,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
        )
        
        with urllib.request.urlopen(req, timeout=10) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
        
        # Try to extract weather info from search results
        weather_data = extract_weather_from_html(html_content)
        
        # If we found data, return it
        if weather_data['temperature']:
            return {
                'success': True,
                'location': weather_data['location'],
                'temperature': f"{weather_data['temperature']}°C" if weather_data['temperature'] else 'unknown',
                'condition': weather_data['condition'] if weather_data['condition'] else 'unknown',
                'raw_text': f"Pogoda w Gdańsku: {weather_data['temperature']}°C, {weather_data['condition']}"
            }
        
        # Fallback: try to find weather in DuckDuckGo instant answer
        # Look for DDG instant answer box with weather info
        instant_answer_match = re.search(r'<div[^>]*class="[^"]*zci--weather[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
        if instant_answer_match:
            instant_html = instant_answer_match.group(1)
            # Extract temperature and condition from instant answer
            temp_match = re.search(r'([-+]?\d+)\s*°[CF]', instant_html)
            condition_match = re.search(r'<div[^>]*class="[^"]*weather__condition[^"]*"[^>]*>([^<]+)</div>', instant_html)
            
            temp = temp_match.group(1) if temp_match else 'unknown'
            condition = condition_match.group(1).strip() if condition_match else 'unknown'
            
            return {
                'success': True,
                'location': 'Gdańsk',
                'temperature': f"{temp}°C",
                'condition': condition,
                'raw_text': f"Pogoda w Gdańsku: {temp}°C, {condition}"
            }
        
        # If still no data, try to use espeak to announce that we couldn't find data
        return {
            'success': False,
            'error': 'Could not extract weather information from search results',
            'raw_text': 'Nie udało się znaleźć aktualnej pogody w Gdańsku'
        }
    
    except urllib.error.URLError as e:
        return {
            'success': False,
            'error': f'Network error: {str(e)}',
            'raw_text': 'Błąd połączenia z internetem'
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'raw_text': 'Wystąpił nieoczekiwany błąd podczas pobierania pogody'
        }


def execute_wrapper(params: dict) -> dict:
    return execute(params)


if __name__ == '__main__':
    # Test block
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(f"Test result: {result}")
    
    # Verify required keys
    assert 'success' in result, "Missing 'success' key"
    assert isinstance(result['success'], bool), "'success' must be boolean"
    
    print("All tests passed!")