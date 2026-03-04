import subprocess
import re
import urllib.request
import html
from html.parser import HTMLParser


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            if 'pogod' in text and 'gda' in text:
                # Use espeak for TTS if available
                try:
                    subprocess.run(['espeak', '-v', 'pl'], input='Sprawdzam pogodę w Gdańsku...', 
                                   text=True, capture_output=True, timeout=5)
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    pass  # Ignore TTS errors

                # Fetch weather from a Polish weather website
                url = 'https://pogoda.onet.pl/prognoza/pogoda/Gdansk-123456789'
                try:
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=10) as response:
                        html_content = response.read().decode('utf-8')
                except Exception as e:
                    return {
                        'success': False,
                        'message': f'Nie udało się pobrać danych pogodowych: {str(e)}',
                        'text': 'Nie mogę pobrać danych pogodowych.'
                    }

                # Extract temperature and conditions using regex
                temp_match = re.search(r'(\d+°C|[-–]\d+°C)', html_content)
                condition_match = re.search(r'(Słonecznie|Pochmurnie|Zachmurzenie|Deszcz|Burza|Śnieg|Mgła)', html_content, re.IGNORECASE)
                
                if temp_match and condition_match:
                    temp = temp_match.group(1)
                    condition = condition_match.group(1)
                    result_text = f'W Gdańsku jest {temp}, {condition}.'
                else:
                    # Fallback: extract any weather-related info
                    weather_section = re.search(r'(?i)(pogoda|temperatura|warunki).{0,100}?(?:\d+°C|Słonecznie|Pochmurnie|Deszcz)', html_content)
                    if weather_section:
                        result_text = f'Sprawdź pogodę w Gdańsku: {weather_section.group(0)[:100]}'
                    else:
                        result_text = 'Nie mogę określić aktualnej pogody w Gdańsku.'

                return {
                    'success': True,
                    'text': result_text,
                    'weather': {
                        'location': 'Gdańsk',
                        'raw_info': result_text
                    }
                }
            else:
                return {
                    'success': False,
                    'message': 'Zapytanie nie dotyczy pogody w Gdańsku.',
                    'text': 'Nie rozumiem zapytania o pogodę w Gdańsku.'
                }
        except Exception as e:
            return {
                'success': False,
                'message': f'Błąd wykonania: {str(e)}',
                'text': 'Wystąpił błąd podczas sprawdzania pogody.'
            }


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v9',
        'description': 'Skill sprawdzający pogodę w Gdańsku'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=2)
        return {'status': 'ok'}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return {'status': 'ok', 'note': 'espeak nie jest zainstalowany, TTS może nie działać'}


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test block
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(result)