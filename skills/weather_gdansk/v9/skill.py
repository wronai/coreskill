import subprocess
import re
import urllib.request
import html
from html.parser import HTMLParser


class WeatherGdanskSkill:
    def __init__(self):
        self.name = "weather_gdansk"
        self.version = "v9"
        self.description = "Searches for current weather in Gdańsk online"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip().lower()
            if 'gda' in text and ('pogo' in text or 'pogoda' in text or 'pogod' in text):
                # Search for weather in Gdańsk using DuckDuckGo HTML search
                query = "pogoda w Gdańsku"
                url = f"https://duckduckgo.com/html/?q={urllib.parse.quote(query)}"
                
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                req = urllib.request.Request(url, headers=headers)
                
                with urllib.request.urlopen(req, timeout=10) as response:
                    html_content = response.read().decode('utf-8', errors='ignore')
                
                # Extract weather info using regex patterns
                # Look for weather widget or result snippet
                weather_patterns = [
                    r'class="[^"]*weather[^"]*"[^>]*>([^<]*?)(?:<|&nbsp;)',
                    r'data-text="([^"]*?pogoda[^"]*?)"',
                    r'class="[^"]*result__snippet[^"]*"[^>]*>([^<]*?pogoda[^<]*?)<',
                    r'<div[^>]*class="[^"]*[^"]*weather[^"]*[^"]*"[^>]*>([^<]*?)(?:<|&nbsp;)',
                    r'<span[^>]*class="[^"]*[^"]*temp[^"]*[^"]*"[^>]*>([^<]*?)</span>',
                ]
                
                # Try to find weather info in the page
                weather_info = ""
                for pattern in weather_patterns:
                    match = re.search(pattern, html_content, re.IGNORECASE)
                    if match:
                        weather_info = match.group(1)
                        break
                
                # If no direct weather found, try to find a link to a weather site
                if not weather_info:
                    # Look for links to weather services
                    links = re.findall(r'<a[^>]*href="([^"]*gda[^"]*pogo[^"]*|pogo[^"]*gda[^"]*)"[^>]*>', html_content, re.IGNORECASE)
                    if links:
                        # Try first link that seems relevant
                        weather_info = "Znaleziono link do pogody w Gdańsku: " + html.unescape(links[0])
                    else:
                        # Use espeak to say we're searching for weather
                        weather_info = "Nie znaleziono bezpośrednich wyników pogody w Gdańsku. Sprawdź https://www.meteo.pl"
                
                # Clean up the result
                weather_info = re.sub(r'<[^>]+>', '', weather_info)
                weather_info = html.unescape(weather_info).strip()
                
                if not weather_info:
                    weather_info = "Nie udało się pobrać aktualnej pogody w Gdańsku. Sprawdź https://www.meteo.pl"
                
                # Speak the result
                try:
                    subprocess.run(['espeak', '-v', 'pl', f"Pogoda w Gdańsku: {weather_info[:150]}"], 
                                 capture_output=True, timeout=5)
                except Exception:
                    pass  # Ignore TTS errors
                
                return {
                    'success': True,
                    'text': f"Pogoda w Gdańsku: {weather_info[:200]}",
                    'result': weather_info[:200]
                }
            else:
                return {
                    'success': False,
                    'text': "To nie jest zapytanie o pogodę w Gdańsku.",
                    'error': 'No weather query for Gdańsk'
                }
        except Exception as e:
            return {
                'success': False,
                'text': f"Błąd podczas pobierania pogody: {str(e)}",
                'error': str(e)
            }

    def get_info(self) -> dict:
        return {
            'name': self.name,
            'version': self.version,
            'description': self.description
        }

    def health_check(self) -> dict:
        try:
            # Test if espeak is available
            result = subprocess.run(['espeak', '--version'], 
                                  capture_output=True, timeout=2)
            return {'status': 'ok', 'espeak_available': True}
        except FileNotFoundError:
            return {'status': 'ok', 'espeak_available': False, 'message': 'espeak not installed, TTS will be disabled'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}


def get_info() -> dict:
    skill = WeatherGdanskSkill()
    return skill.get_info()


def health_check() -> dict:
    skill = WeatherGdanskSkill()
    return skill.health_check()


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(f"Result: {result}")
    
    # Test info
    info = get_info()
    print(f"Info: {info}")
    
    # Test health
    health = health_check()
    print(f"Health: {health}")