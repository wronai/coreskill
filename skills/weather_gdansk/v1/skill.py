import subprocess
import re
import urllib.request
import json
from html.parser import HTMLParser


class WeatherGdanskSkill:
    def __init__(self):
        self.name = "weather_gdansk"
        self.version = "v1"
        self.description = "Searches for current weather in Gdańsk, Poland"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            if 'gda' in text and ('pogoda' in text or 'weather' in text):
                # Use Open-Meteo API for Gdańsk coordinates (54.3520°N, 18.6466°E)
                url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true"
                
                try:
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        current = data.get('current_weather', {})
                        temp = current.get('temperature', 'N/A')
                        wcode = current.get('weathercode', 'N/A')
                        
                        # Map WMO weather codes to descriptions
                        weather_descriptions = {
                            0: "jasno",
                            1: "głównie jasno",
                            2: "częściowo pochmurno",
                            3: "zachmurzenie całościowe",
                            45: "mgła",
                            48: "mgła",
                            51: "lekka mżawka",
                            53: "umiarkowana mżawka",
                            55: "gęsta mżawka",
                            56: "ledwo mroźna mżawka",
                            57: "ledwo mroźna gęsta mżawka",
                            61: "lekki deszcz",
                            63: "umiarkowany deszcz",
                            65: "silny deszcz",
                            66: "ledwo mroźny deszcz",
                            67: "ledwo mroźny silny deszcz",
                            71: "lekki śnieg",
                            73: "umiarkowany śnieg",
                            75: "silny śnieg",
                            77: "ziarna śniegu",
                            80: "lekka przelotna burza",
                            81: "umiarkowana przelotna burza",
                            82: "silna przelotna burza",
                            85: "lekka burza ze śniegiem",
                            86: "silna burza ze śniegiem",
                            95: "burza",
                            96: "burza z gradem",
                            99: "burza z silnym gradem"
                        }
                        desc = weather_descriptions.get(wcode, f"kod pogody {wcode}")
                        
                        result_text = f"Pogoda w Gdańsku: {temp}°C, {desc}."
                        
                        return {
                            'success': True,
                            'result': result_text,
                            'weather': {
                                'temperature': temp,
                                'description': desc,
                                'code': wcode
                            }
                        }
                except Exception as e:
                    return {
                        'success': False,
                        'error': f"Nie można pobrać danych pogodowych: {str(e)}"
                    }
            else:
                return {
                    'success': False,
                    'error': "Zapytanie nie dotyczy pogody w Gdańsku"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Błąd przetwarzania zapytania: {str(e)}"
            }


def get_info() -> dict:
    return {
        'name': 'weather_gdansk',
        'version': 'v1',
        'description': 'Searches for current weather in Gdańsk, Poland'
    }


def health_check() -> dict:
    try:
        # Test if espeak is available (for TTS) and if we can reach weather API
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=2)
        with urllib.request.urlopen("https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true", timeout=5) as response:
            if response.status == 200:
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'message': 'Weather API returned non-200 status'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))