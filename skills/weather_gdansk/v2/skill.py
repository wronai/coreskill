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
        self.current_tag = ""
        self.temperature = None
        self.condition = None
        self.location = "Gdańsk"
        self.data_buffer = ""

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag
        attrs_dict = dict(attrs)
        # Try to identify temperature (e.g., <span class="temp">20°</span>)
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"].lower()
            if "temp" in cls:
                self.in_temp = True
        # Try to identify weather condition
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"].lower()
            if "condition" in cls or "weather" in cls:
                self.in_condition = True
        # Try to identify location
        if tag == "span" and "class" in attrs_dict:
            cls = attrs_dict["class"].lower()
            if "location" in cls or "city" in cls:
                self.in_location = True

    def handle_endtag(self, tag):
        self.current_tag = ""
        if tag == "span":
            self.in_temp = False
            self.in_condition = False
            self.in_location = False

    def handle_data(self, data):
        data = data.strip()
        if not data:
            return

        if self.in_temp:
            # Extract numeric temperature (e.g., "20°", "20° C", "20°C")
            match = re.search(r"(-?\d+\.?\d*)\s*°?C?", data)
            if match:
                self.temperature = match.group(1) + "°C"
        elif self.in_condition:
            # Extract short condition (e.g., "Partly Cloudy")
            if len(data) < 50:  # avoid long descriptions
                self.condition = data
        elif self.in_location:
            self.location = data


def get_info() -> dict:
    return {
        "name": "weather_gdansk",
        "version": "v2",
        "description": "Searches for current weather in Gdańsk online"
    }


def health_check() -> dict:
    try:
        # Try to reach a weather service to verify connectivity
        req = urllib.request.Request(
            "https://www.google.com/search?q=pogoda+gdansk",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


def execute(params: dict) -> dict:
    try:
        text = params.get("text", "").strip().lower()
        # Check if the query is about weather in Gdańsk
        if not any(keyword in text for keyword in ["pogoda", "temperatura", "wietrzenie", "deszcz", "słońce"]) or "gdańsk" not in text:
            return {
                "success": False,
                "message": "Query does not match 'weather in Gdańsk' pattern"
            }

        # Use Google search for weather in Gdańsk
        query = "pogoda w Gdańsku"
        url = f"https://www.google.com/search?q={urllib.parse.quote(query)}&hl=pl"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
        
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as response:
            html = response.read().decode("utf-8", errors="ignore")

        # Parse HTML to extract weather info
        parser = WeatherGdanskParser()
        parser.feed(html)

        # Fallback: try to extract temperature and condition with regex
        if not parser.temperature:
            temp_match = re.search(r'(-?\d+\.?\d*)\s*°C', html)
            if temp_match:
                parser.temperature = temp_match.group(1) + "°C"

        if not parser.condition:
            # Try common weather condition patterns
            condition_match = re.search(r'class="BNeawe tAd85 AP7Wnd".*?>([^<]+)', html, re.IGNORECASE | re.DOTALL)
            if condition_match:
                parser.condition = condition_match.group(1).strip()

        # Build response
        if parser.temperature:
            response_text = f"Pogoda w Gdańsku: {parser.temperature}"
            if parser.condition:
                response_text += f", {parser.condition}"
        else:
            response_text = "Nie udało się pobrać aktualnej pogody w Gdańsku."

        return {
            "success": True,
            "text": response_text,
            "temperature": parser.temperature,
            "condition": parser.condition,
            "location": parser.location
        }

    except urllib.error.URLError as e:
        return {
            "success": False,
            "message": f"Network error: {str(e.reason)}"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Unexpected error: {str(e)}"
        }


def execute_wrapper(params: dict) -> dict:
    return execute(params)


if __name__ == "__main__":
    # Test block
    test_params = {"text": "wyszukaj w internecie pogodę w Gdańsku"}
    result = execute(test_params)
    print(result)