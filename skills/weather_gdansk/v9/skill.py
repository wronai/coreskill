import subprocess
import re
import urllib.request
import urllib.error
from html.parser import HTMLParser


class WeatherGdanskParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.in_location = False
        self.temp = None
        self.condition = None
        self.location = None
        self._current_tag = None
        self._data_buffer = ""

    def handle_starttag(self, tag, attrs):
        self._current_tag = tag
        attrs_dict = dict(attrs)
        # Look for temperature (e.g., <span class="temp">12°</span>)
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"]
            if "temp" in cls.lower():
                self.in_temp = True
            if "condition" in cls.lower() or "weather" in cls.lower():
                self.in_condition = True
        if tag == "h1" and "class" in attrs_dict:
            if "location" in attrs_dict["class"].lower() or "city" in attrs_dict["class"].lower():
                self.in_location = True

    def handle_endtag(self, tag):
        self._current_tag = None
        if tag == "span":
            self.in_temp = False
            self.in_condition = False
        if tag == "h1":
            self.in_location = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return
        if self.in_temp and self.temp is None:
            # Extract numeric temp (e.g., "12°", "12° C")
            match = re.search(r"-?\d+\.?\d*", data)
            if match:
                self.temp = match.group(0)
        elif self.in_condition and self.condition is None:
            self.condition = data
        elif self.in_location and self.location is None:
            self.location = data


def get_info() -> dict:
    return {
        "name": "weather_gdansk",
        "version": "v9",
        "description": "Searches the web for current weather in Gdańsk"
    }


def health_check() -> dict:
    try:
        # Test network connectivity with a HEAD request to a reliable host
        req = urllib.request.Request("https://www.google.com", method="HEAD")
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return {"status": "ok"}
            else:
                return {"status": "error", "message": f"Unexpected status: {response.status}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "").strip().lower()
            if "gdańsk" not in text and "gdansk" not in text:
                return {
                    "success": False,
                    "message": "Query does not mention Gdańsk"
                }

            # Use espeak to announce search
            try:
                subprocess.run(
                    ["espeak", "-v", "pl", "Wyszukuję pogodę w Gdańsku"],
                    check=True,
                    capture_output=True
                )
            except Exception:
                pass  # Non-critical if TTS fails

            # Search for weather using Google search (HTML parsing)
            query = "pogoda w Gdańsku"
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=pl"
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")
            
            parser = WeatherGdanskParser()
            parser.feed(html)
            
            # Extract weather info
            temp = parser.temp or "brak danych"
            condition = parser.condition or "brak danych"
            location = parser.location or "Gdańsk"
            
            # Construct response
            result_text = f"Pogoda w {location}: {condition}, temperatura {temp}°C"
            
            return {
                "success": True,
                "result": result_text,
                "raw_temp": temp,
                "raw_condition": condition,
                "raw_location": location
            }
            
        except urllib.error.URLError as e:
            return {
                "success": False,
                "message": f"Network error: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Unexpected error: {str(e)}"
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    print("Testing weather_gdansk skill...")
    
    # Test health check
    health = health_check()
    print(f"Health check: {health}")
    
    # Test info
    info = get_info()
    print(f"Skill info: {info}")
    
    # Test execution
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(f"Execution result: {result}")