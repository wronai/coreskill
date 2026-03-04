import subprocess
import re
import urllib.request
import json
from html.parser import HTMLParser


class WeatherGdanskSkill:
    def __init__(self):
        self.name = "weather_gdansk"
        self.version = "v10"
        self.description = "Searches for current weather in Gdańsk, Poland"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Check if the request is about weather in Gdańsk
            if 'pogod' in text and 'gda' in text:
                # Use Open-Meteo API (no API key required)
                # Gdańsk coordinates: 54.3520° N, 18.6466° E
                weather_url = (
                    "https://api.open-meteo.com/v1/forecast?"
                    "latitude=54.3520&longitude=18.6466"
                    "&current_weather=true"
                )
                
                try:
                    with urllib.request.urlopen(weather_url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        
                        if 'current_weather' in data:
                            cw = data['current_weather']
                            temp = cw.get('temperature', 'N/A')
                            ws = cw.get('windspeed', 'N/A')
                            wd = cw.get('winddirection', 'N/A')
                            weather_code = cw.get('weathercode', '')
                            
                            # Map WMO weather codes to descriptions
                            weather_descriptions = {
                                0: "jasno",
                                1: "głównie jasno",
                                2: "częściowo pochmurno",
                                3: "zachmurzenie całkowite",
                                45: "mgła",
                                48: "mgła z osadami",
                                51: "lekka mżawka",
                                53: "umiarkowana mżawka",
                                55: "silna mżawka",
                                56: "zimna mżawka, lekka",
                                57: "zimna mżawka, silna",
                                61: "lekki deszcz",
                                63: "umiarkowany deszcz",
                                65: "silny deszcz",
                                66: "zimny deszcz, lekki",
                                67: "zimny deszcz, silny",
                                71: "lekki śnieg",
                                73: "umiarkowany śnieg",
                                75: "silny śnieg",
                                77: "ziarna śniegu",
                                80: "lekkie ulewy",
                                81: "umiarkowane ulewy",
                                82: "silne ulewy",
                                85: "lekki deszcz ze śniegiem",
                                86: "silny deszcz ze śniegiem",
                                95: "burza",
                                96: "burza z gradem",
                                99: "burza z silnym gradem"
                            }
                            
                            description = weather_descriptions.get(weather_code, "nieznane warunki")
                            
                            result_text = f"W Gdańsku jest obecnie {temp}°C, {description}, wiatr {wd}° z prędkością {ws} km/h."
                            
                            return {
                                'success': True,
                                'text': result_text,
                                'weather_data': data
                            }
                        else:
                            return {
                                'success': False,
                                'text': "Nie udało się pobrać danych pogodowych.",
                                'error': 'No weather data in response'
                            }
                            
                except urllib.error.URLError as e:
                    return {
                        'success': False,
                        'text': "Błąd połączenia z serwerem pogodowym.",
                        'error': str(e.reason)
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'text': "Wystąpił nieoczekiwany błąd podczas pobierania danych pogodowych.",
                        'error': str(e)
                    }
            else:
                return {
                    'success': False,
                    'text': "To zapytanie nie dotyczy pogody w Gdańsku.",
                    'error': 'No weather request detected'
                }
                
        except Exception as e:
            return {
                'success': False,
                'text': "Wystąpił błąd podczas przetwarzania zapytania.",
                'error': str(e)
            }


def get_info() -> dict:
    skill = WeatherGdanskSkill()
    return {
        'name': skill.name,
        'version': skill.version,
        'description': skill.description
    }


def health_check() -> dict:
    try:
        # Test connectivity to Open-Meteo API
        test_url = "https://api.open-meteo.com/v1/health"
        with urllib.request.urlopen(test_url, timeout=5) as response:
            if response.status == 200:
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'message': f'Health check returned status {response.status}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == '__main__':
    # Test execution
    test_params = {'text': 'wyszukaj w internecie pogodę w Gdańsku'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))