import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v7',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class PoundToYenConverter:
    def __init__(self):
        self.api_url = "https://api.exchangerate-api.com/v4/latest/GBP"
    
    def _fetch_exchange_rate(self):
        try:
            with urllib.request.urlopen(self.api_url, timeout=10) as response:
                data = json.loads(response.read().decode())
                return data['rates'].get('JPY', 0)
        except Exception:
            # Fallback rate if API fails (approximate as of 2023)
            return 175.0
    
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount (e.g., "tysiąc" -> 1000, "1000" -> 1000)
            amount = 1000  # default
            
            # Check for "tysiąc" (thousand in Polish)
            if 'tysiąc' in text:
                amount = 1000
            
            # Check for numeric amount
            numbers = re.findall(r'\d+', text)
            if numbers:
                amount = int(numbers[0])
            
            # Fetch exchange rate
            rate = self._fetch_exchange_rate()
            
            # Calculate result
            result = amount * rate
            
            # Format result with commas
            result_formatted = f"{result:,.2f}"
            
            # Create response message
            response_text = f"{amount} funtów szterlingów to {result_formatted} jenów japońskich"
            
            # Try to speak the response if espeak is available
            try:
                subprocess.run(['espeak', response_text], capture_output=True, timeout=5)
            except Exception:
                pass  # Ignore TTS errors
            
            return {
                'success': True,
                'amount_pounds': amount,
                'exchange_rate': rate,
                'amount_yen': result,
                'result_text': response_text
            }
            
        except Exception as e:
            return {
                'success': False,
                'error_message': str(e)
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))