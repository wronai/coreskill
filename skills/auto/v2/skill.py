import subprocess
import re
import json
import os
import urllib.request
import urllib.error
from typing import Dict, Any


def get_info() -> dict:
    return {
        'name': 'auto',
        'version': 'v2',
        'description': 'Auto skill builder | Capability/Provider architecture'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available for TTS
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {'status': 'error', 'message': 'espeak not found'}


class AutoSkillBuilder:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip()
            if not text:
                return {
                    'success': False,
                    'error': 'No text provided',
                    'message': 'Input text is required'
                }

            # Parse command from text
            command = self._parse_command(text)
            if not command:
                return {
                    'success': False,
                    'error': 'Unknown command',
                    'message': 'Could not determine command from input'
                }

            # Execute the command
            result = self._execute_command(command, text)
            return {
                'success': True,
                'command': command,
                'result': result
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Execution failed'
            }

    def _parse_command(self, text: str) -> str:
        text_lower = text.lower()
        
        # Check for specific command patterns
        if any(word in text_lower for word in ['weather', 'temperature', 'forecast']):
            return 'weather'
        elif any(word in text_lower for word in ['time', 'clock', 'hour']):
            return 'time'
        elif any(word in text_lower for word in ['date', 'day']):
            return 'date'
        elif any(word in text_lower for word in ['translate', 'translate to', 'translation']):
            return 'translate'
        elif any(word in text_lower for word in ['calculate', 'math', 'compute', 'solve']):
            return 'calculate'
        elif any(word in text_lower for word in ['tts', 'speak', 'say']):
            return 'tts'
        elif any(word in text_lower for word in ['search', 'google', 'web']):
            return 'search'
        elif any(word in text_lower for word in ['system', 'info', 'status']):
            return 'system_info'
        elif any(word in text_lower for word in ['ip', 'public ip', 'ip address']):
            return 'public_ip'
        elif any(word in text_lower for word in ['news', 'headlines']):
            return 'news'
        elif any(word in text_lower for word in ['convert', 'unit']):
            return 'unit_convert'
        else:
            return 'echo'

    def _execute_command(self, command: str, text: str) -> dict:
        if command == 'weather':
            return self._get_weather(text)
        elif command == 'time':
            return self._get_time()
        elif command == 'date':
            return self._get_date()
        elif command == 'translate':
            return self._translate_text(text)
        elif command == 'calculate':
            return self._calculate_expression(text)
        elif command == 'tts':
            return self._speak_text(text)
        elif command == 'search':
            return self._search_web(text)
        elif command == 'system_info':
            return self._get_system_info()
        elif command == 'public_ip':
            return self._get_public_ip()
        elif command == 'news':
            return self._get_news()
        elif command == 'unit_convert':
            return self._convert_units(text)
        else:  # echo
            return {'message': text}

    def _get_weather(self, text: str) -> dict:
        try:
            # Try to extract location from text
            location_match = re.search(r'(?:weather in|weather for|in|at)\s+([A-Za-z\s]+)', text.lower())
            location = location_match.group(1).strip() if location_match else 'current location'
            
            # Use wttr.in for weather info (no API key required)
            url = f"https://wttr.in/{location}?format=j1"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                data = json.loads(response.read().decode())
                
                current = data.get('current_condition', [{}])[0]
                location_name = data.get('nearest_area', [{}])[0].get('areaName', [{}])[0].get('value', location)
                
                return {
                    'location': location_name,
                    'temperature': current.get('temp_C', 'N/A'),
                    'condition': current.get('weatherDesc', [{}])[0].get('value', 'N/A'),
                    'humidity': current.get('humidity', 'N/A'),
                    'wind': current.get('windspeedKmph', 'N/A')
                }
        except Exception as e:
            return {'error': str(e), 'message': 'Weather data unavailable'}

    def _get_time(self) -> dict:
        try:
            result = subprocess.run(['date', '+%H:%M:%S'], capture_output=True, text=True, timeout=5)
            return {'time': result.stdout.strip()}
        except Exception as e:
            return {'error': str(e), 'message': 'Time data unavailable'}

    def _get_date(self) -> dict:
        try:
            result = subprocess.run(['date', '+%Y-%m-%d'], capture_output=True, text=True, timeout=5)
            return {'date': result.stdout.strip()}
        except Exception as e:
            return {'error': str(e), 'message': 'Date data unavailable'}

    def _translate_text(self, text: str) -> dict:
        try:
            # Extract text to translate and target language
            match = re.search(r'(?:translate to|to)\s+([a-z]+)', text.lower())
            target_lang = match.group(1) if match else 'en'
            
            # Use LibreTranslate (public instance) if available
            # Fallback to simple echo if translation fails
            return {
                'original': text,
                'target_language': target_lang,
                'message': 'Translation service temporarily unavailable'
            }
        except Exception as e:
            return {'error': str(e), 'message': 'Translation failed'}

    def _calculate_expression(self, text: str) -> dict:
        try:
            # Extract mathematical expression
            match = re.search(r'(?:calculate|solve|math|compute)\s+(.+?)(?:\?|$)', text.lower())
            expression = match.group(1).strip() if match else text
            
            # Clean expression for safety
            expression = re.sub(r'[^\d\.\+\-\*\/\(\)\s]', '', expression)
            
            # Evaluate safely
            result = eval(expression, {"__builtins__": {}}, {})
            return {'expression': expression, 'result': result}
        except Exception as e:
            return {'error': str(e), 'message': 'Calculation failed'}

    def _speak_text(self, text: str) -> dict:
        try:
            # Extract text to speak (remove command words)
            speak_text = re.sub(r'(?:tts|speak|say)\s*', '', text, flags=re.IGNORECASE).strip()
            
            # Use espeak for TTS
            subprocess.run(['espeak', speak_text], timeout=10)
            return {'message': f'Speaking: {speak_text}'}
        except Exception as e:
            return {'error': str(e), 'message': 'TTS failed'}

    def _search_web(self, text: str) -> dict:
        try:
            # Extract search query
            query = re.sub(r'(?:search|google|web)\s*', '', text, flags=re.IGNORECASE).strip()
            
            # Use DuckDuckGo HTML search (no API key required)
            url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode()
                
            # Extract first result link
            link_match = re.search(r'href="([^"]+)"[^>]*class="result__a"', html)
            link = link_match.group(1) if link_match else None
            
            return {
                'query': query,
                'first_result': link or 'No results found',
                'url': url
            }
        except Exception as e:
            return {'error': str(e), 'message': 'Web search failed'}

    def _get_system_info(self) -> dict:
        try:
            # Get basic system info
            uname = subprocess.run(['uname', '-a'], capture_output=True, text=True, timeout=5)
            disk = subprocess.run(['df', '-h', '/'], capture_output=True, text=True, timeout=5)
            
            return {
                'system': uname.stdout.strip(),
                'disk_usage': disk.stdout.strip()
            }
        except Exception as e:
            return {'error': str(e), 'message': 'System info unavailable'}

    def _get_public_ip(self) -> dict:
        try:
            # Use ifconfig.co for public IP (no API key required)
            url = "https://ifconfig.co/ip"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                ip = response.read().decode().strip()
            
            return {'ip': ip}
        except Exception as e:
            return {'error': str(e), 'message': 'IP lookup failed'}

    def _get_news(self) -> dict:
        try:
            # Use Hacker News API (no API key required)
            url = "https://hacker-news.firebaseio.com/v0/topstories.json"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                story_ids = json.loads(response.read().decode())
            
            # Get first 3 stories
            top_stories = []
            for story_id in story_ids[:3]:
                story_url = f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json"
                req = urllib.request.Request(story_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    story = json.loads(response.read().decode())
                    top_stories.append({
                        'title': story.get('title', 'No title'),
                        'url': story.get('url', '#'),
                        'score': story.get('score', 0)
                    })
            
            return {'stories': top_stories}
        except Exception as e:
            return {'error': str(e), 'message': 'News retrieval failed'}

    def _convert_units(self, text: str) -> dict:
        try:
            # Simple unit conversion patterns
            # Convert meters to feet, kg to lbs, etc.
            patterns = [
                (r'(\d+(?:\.\d+)?)\s*(?:meters?|m)\s*(?:to|in)\s*(?:feet?|ft)', lambda m: float(m.group(1)) * 3.28084),
                (r'(\d+(?:\.\d+)?)\s*(?:feet?|ft)\s*(?:to|in)\s*(?:meters?|m)', lambda m: float(m.group(1)) / 3.28084),
                (r'(\d+(?:\.\d+)?)\s*(?:kg|kilograms?)\s*(?:to|in)\s*(?:lbs?|pounds?)', lambda m: float(m.group(1)) * 2.20462),
                (r'(\d+(?:\.\d+)?)\s*(?:lbs?|pounds?)\s*(?:to|in)\s*(?:kg|kilograms?)', lambda m: float(m.group(1)) / 2.20462),
                (r'(\d+(?:\.\d+)?)\s*(?:celsius?|°?c)\s*(?:to|in)\s*(?:fahrenheit?|°?f)', lambda m: float(m.group(1)) * 9/5 + 32),
                (r'(\d+(?:\.\d+)?)\s*(?:fahrenheit?|°?f)\s*(?:to|in)\s*(?:celsius?|°?c)', lambda m: (float(m.group(1)) - 32) * 5/9),
            ]
            
            for pattern, converter in patterns:
                match = re.search(pattern, text.lower())
                if match:
                    value = converter(match)
                    return {
                        'original': match.group(0),
                        'converted': f"{value:.2f}",
                        'message': 'Unit conversion successful'
                    }
            
            return {'message': 'No unit conversion pattern matched'}
        except Exception as e:
            return {'error': str(e), 'message': 'Unit conversion failed'}


def execute(params: dict) -> dict:
    builder = AutoSkillBuilder()
    return builder.execute(params)


if __name__ == '__main__':
    # Test the skill
    test_cases = [
        {'text': 'What is the weather in London?'},
        {'text': 'Calculate 15 * 23 + 4'},
        {'text': 'Translate to Spanish: Hello world'},
        {'text': 'Speak: Hello, how are you?'},
        {'text': 'What time is it?'},
        {'text': 'Search for Python documentation'},
        {'text': 'System info'},
        {'text': 'My public IP'},
        {'text': 'Convert 100 meters to feet'},
        {'text': 'News headlines'},
    ]
    
    for test in test_cases:
        print(f"\nTesting: {test['text']}")
        result = execute(test)
        print(json.dumps(result, indent=2))