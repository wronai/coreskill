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
        self.temp = None
        self.condition = None
        self._temp_buffer = ""
        self._condition_buffer = ""
        self._in_temp_div = False
        self._in_condition_div = False
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "div":
            if attrs_dict.get("class") and "current-temp" in attrs_dict["class"]:
                self._in_temp_div = True
                self._depth = 0
            elif attrs_dict.get("class") and "condition" in attrs_dict["class"]:
                self._in_condition_div = True
                self._depth = 0
        elif self._in_temp_div and tag == "span":
            self.in_temp = True
        elif self._in_condition_div and tag == "span":
            self.in_condition = True

    def handle_endtag(self, tag):
        if tag == "div":
            if self._in_temp_div:
                self._in_temp_div = False
            elif self._in_condition_div:
                self._in_condition_div = False
        elif tag == "span":
            if self.in_temp:
                self.in_temp = False
                self.temp = self._temp_buffer.strip()
                self._temp_buffer = ""
            elif self.in_condition:
                self.in_condition = False
                self.condition = self._condition_buffer.strip()
                self._condition_buffer = ""

    def handle_data(self, data):
        if self.in_temp:
            self._temp_buffer += data
        elif self.in_condition:
            self._condition_buffer += data


def get_info() -> dict:
    return {
        "name": "weather_gdansk",
        "version": "v1",
        "description": "Skill to search for current weather in Gdańsk online"
    }


def health_check() -> dict:
    try:
        req = urllib.request.Request(
            "https://www.google.com",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            if response.status == 200:
                return {"status": "ok"}
            else:
                return {"status": "error", "message": f"HTTP {response.status}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


class WeatherGdanskSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "")
            
            # Extract Gdańsk reference from text (case-insensitive)
            if not re.search(r"gda[ńn]sk", text, re.IGNORECASE):
                return {
                    "success": False,
                    "spoken": "Nie znaleziono wzmianki o Gdańsku w zapytaniu."
                }
            
            # Try to get weather from Google Weather
            url = "https://www.google.com/search?q=pogoda+gdansk&hl=pl"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as response:
                html_content = response.read().decode("utf-8", errors="ignore")
            
            # Parse the HTML to extract weather info
            parser = WeatherGdanskParser()
            parser.feed(html_content)
            
            # If parser didn't find data, try alternative extraction
            if not parser.temp or not parser.condition:
                # Try to find temperature using regex
                temp_match = re.search(r'(\d+°C)', html_content)
                if temp_match:
                    parser.temp = temp_match.group(1)
                
                # Try to find condition using regex
                condition_match = re.search(r'(<span[^>]*class="wob_t"[^>]*>.*?</span>)', html_content, re.IGNORECASE)
                if not condition_match:
                    condition_match = re.search(r'(<div[^>]*class="vk_bk wob-title"[^>]*>.*?</div>)', html_content, re.IGNORECASE)
                if condition_match:
                    # Extract text from the matched HTML
                    clean_match = re.sub(r'<[^>]+>', '', condition_match.group(1))
                    parser.condition = clean_match.strip()
            
            # If still no data, try espeak to announce no data found
            if not parser.temp:
                return {
                    "success": False,
                    "spoken": "Nie udało się pobrać danych pogodowych dla Gdańska."
                }
            
            # Prepare response
            weather_info = f"Pogoda w Gdańsku: {parser.condition}, temperatura {parser.temp}"
            
            # Use espeak for TTS if available
            try:
                subprocess.run(
                    ["espeak", "-v", "pl", weather_info],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                # espeak not available, continue without TTS
                pass
            
            return {
                "success": True,
                "weather": {
                    "condition": parser.condition,
                    "temperature": parser.temp
                },
                "spoken": weather_info
            }
        
        except urllib.error.URLError as e:
            return {
                "success": False,
                "spoken": f"Błąd sieci: {str(e)}"
            }
        except Exception as e:
            return {
                "success": False,
                "spoken": f"Błąd: {str(e)}"
            }


def execute(params: dict) -> dict:
    skill = WeatherGdanskSkill()
    return skill.execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(result)