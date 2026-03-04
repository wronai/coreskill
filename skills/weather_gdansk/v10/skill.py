import re
import subprocess
import urllib.request
import json


def get_weather_gdansk():
    """Fetch weather for Gdańsk from a public weather API."""
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=54.3520&longitude=18.6466&current_weather=true&temperature_unit=celsius&wind_speed_unit=kmh&precipitation_unit=mm&timezone=auto"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'current_weather' in data:
                temp = data['current_weather']['temperature']
                return f"Pogoda w Gdańsku: {temp}°C"
            else:
                return "Nie udało się pobrać danych pogodowych."
    except Exception as e:
        return f"Błąd pobierania danych pogodowych: {str(e)}"


def get_info():
    return {
        "name": "weather_gdansk",
        "version": "v1",
        "description": "Skill do sprawdzania aktualnej pogody w Gdańsku"
    }


def health_check():
    try:
        result = subprocess.run(['ping', '-c', '1', '8.8.8.8'], 
                                stdout=subprocess.DEVNULL, 
                                stderr=subprocess.DEVNULL,
                                timeout=5)
        if result.returncode == 0:
            return {"status": "ok"}
        else:
            return {"status": "error", "message": "No internet connectivity"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Check if the query is about weather in Gdańsk (including variations)
            if ('pogod' in text and ('gdańsk' in text or 'gdansk' in text)) or \
               ('gdańsk' in text or 'gdansk' in text) and ('pogod' in text or 'temperatura' in text or 'deszcz' in text or 'śnieg' in text or 'chmury' in text):
                weather_info = get_weather_gdansk()
                return {
                    "success": True,
                    "text": weather_info,
                    "spoken": weather_info,
                    "raw_response": weather_info
                }
            else:
                return {
                    "success": False,
                    "text": "Zapytanie nie dotyczy pogody w Gdańsku.",
                    "spoken": "Zapytanie nie dotyczy pogody w Gdańsku.",
                    "error": "No weather query for Gdańsk"
                }
        except Exception as e:
            return {
                "success": False,
                "text": f"Wystąpił błąd podczas przetwarzania zapytania: {str(e)}",
                "spoken": f"Wystąpił błąd podczas przetwarzania zapytania: {str(e)}",
                "error": str(e)
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "jaka w ogóle na wgdańsku?"}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))