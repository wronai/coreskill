import subprocess
import re
import urllib.request
import json
from html.parser import HTMLParser


class WeatherGdanskSkill:
    def __init__(self):
        self.name = "weather_gdansk"
        self.version = "v5"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip().lower()
            
            # Check if the query is about weather in Gdansk
            if 'pogod' in text and ('gdansk' in text or 'gdańsk' in text or 'gda' in text):
                # Use Open-Meteo API (no API key required)
                # Gdansk coordinates: 54.3520° N, 18.6466° E
                url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true&daily=weathercode,temperature_2m_max,temperature_2m_min&timezone=auto"
                
                try:
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        
                        if 'current_weather' in data:
                            current = data['current_weather']
                            temp = current.get('temperature', 'N/A')
                            code = current.get('weathercode', 'N/A')
                            # Convert WMO weather code to description
                            weather_desc = self._get_weather_description(code)
                            
                            result_text = f"W Gdańsku obecnie {temp}°C, {weather_desc}."
                            
                            return {
                                'success': True,
                                'result': result_text,
                                'raw_data': data
                            }
                        else:
                            return {
                                'success': False,
                                'error': 'Nie udało się pobrać danych pogodowych.',
                                'result': 'Nie udało się pobrać danych pogodowych.'
                            }
                except Exception as e:
                    # Fallback: try to use espeak to announce the error
                    return {
                        'success': False,
                        'error': str(e),
                        'result': 'Nie udało się połączyć z serwisem pogodowym.'
                    }
            else:
                return {
                    'success': False,
                    'error': 'Zapytanie nie dotyczy pogody w Gdańsku.',
                    'result': 'Nie rozpoznano zapytania o pogodę w Gdańsku.'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'result': 'Wystąpił błąd podczas przetwarzania zapytania.'
            }

    def _get_weather_description(self, code):
        """Convert WMO weather code to Polish description"""
        descriptions = {
            0: "bezchmurnie",
            1: "głównie bezchmurnie",
            2: "częściowo pochmurnie",
            3: "pochmurnie",
            45: "mgła",
            48: "mgła z szelągami",
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
            80: "lekka przelotna burza",
            81: "umiarkowana przelotna burza",
            82: "silna przelotna burza",
            85: "lekki deszcz ze śniegiem",
            86: "silny deszcz ze śniegiem",
            95: "burza",
            96: "burza z gradem",
            99: "burza z silnym gradem"
        }
        return descriptions.get(code, f"kod {code}")


def get_info() -> dict:
    return {
        "name": "weather_gdansk",
        "version": "v5",
        "description": "Skill do sprawdzania aktualnej pogody w Gdańsku"
    }


def health_check() -> dict:
    try:
        # Test connectivity to Open-Meteo API
        url = "https://api.open-meteo.com/v1/health"
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                return {"status": "ok"}
            else:
                return {"status": "error", "message": f"API returned status {response.status}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))