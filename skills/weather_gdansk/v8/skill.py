import subprocess
import re
import urllib.request
import urllib.error
import urllib.parse
from html.parser import HTMLParser


class WeatherGdanskParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_temp = False
        self.in_condition = False
        self.current_tag = ""
        self.temperature = None
        self.condition = None
        self.buffer = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        # Look for temperature (e.g., <span class="temp">12°</span>)
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"]
            if any(x in cls for x in ["temp", "temperature"]):
                self.in_temp = True
        # Look for condition (e.g., <div class="condition">Cloudy</div>)
        if tag == "div" and "class" in attrs_dict:
            cls = attrs_dict["class"]
            if any(x in cls for x in ["condition", "weather"]):
                self.in_condition = True

    def handle_endtag(self, tag):
        self.current_tag = ""
        if tag == "span" and self.in_temp:
            self.in_temp = False
        if tag == "div" and self.in_condition:
            self.in_condition = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_temp and self.temperature is None:
            # Extract numeric temperature with optional sign and unit
            match = re.search(r"([+-]?\d+)", data)
            if match:
                self.temperature = match.group(1) + "°C"
        if self.in_condition and self.condition is None:
            # Keep only first meaningful word(s), avoid numbers
            if not re.search(r"\d", data) and len(data) > 2:
                self.condition = data


def get_info() -> dict:
    return {
        "name": "weather_gdansk",
        "version": "v8",
        "description": "Searches for current weather in Gdańsk online"
    }


def health_check() -> dict:
    try:
        # Test network connectivity with a lightweight request
        req = urllib.request.Request(
            "https://www.google.com",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return {"status": "ok"}
            else:
                return {"status": "error", "message": "Google returned non-200 status"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "").strip().lower()
            if not text or "gdańsk" not in text and "gdansk" not in text:
                return {
                    "success": False,
                    "message": "No Gdańsk reference found in input text",
                    "spoken": "Nie znaleziono odniesienia do Gdańska"
                }

            # Use Google search with weather site
            query = "pogoda w Gdańsku"
            search_url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=pl"
            
            req = urllib.request.Request(
                search_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                }
            )
            
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode("utf-8", errors="ignore")
            
            parser = WeatherGdanskParser()
            parser.feed(html)
            
            # Fallback: try to extract from Google's weather card directly
            if parser.temperature is None:
                temp_match = re.search(r'(\d+)\s*°C', html)
                if temp_match:
                    parser.temperature = temp_match.group(1) + "°C"
            
            if parser.condition is None:
                condition_match = re.search(r'<div[^>]*class="vk_gy vk_sh"[^>]*>([^<]+)</div>', html)
                if condition_match:
                    parser.condition = condition_match.group(1).strip()
            
            if parser.temperature:
                result_text = f"Pogoda w Gdańsku: {parser.temperature}"
                if parser.condition:
                    result_text += f", {parser.condition}"
                
                # Use espeak for TTS if available
                try:
                    subprocess.run(
                        ["espeak", "-v", "pl", result_text],
                        check=True,
                        capture_output=True
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    pass  # TTS is optional
                
                return {
                    "success": True,
                    "message": result_text,
                    "temperature": parser.temperature,
                    "condition": parser.condition or "brak danych",
                    "spoken": result_text
                }
            else:
                fallback_text = "Nie udało się pobrać danych o pogodzie w Gdańsku"
                return {
                    "success": False,
                    "message": fallback_text,
                    "spoken": fallback_text
                }

        except urllib.error.URLError as e:
            error_msg = f"Błąd połączenia: {str(e.reason)}"
            return {
                "success": False,
                "message": error_msg,
                "spoken": error_msg
            }
        except Exception as e:
            error_msg = f"Błąd systemu: {str(e)}"
            return {
                "success": False,
                "message": error_msg,
                "spoken": error_msg
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(result)