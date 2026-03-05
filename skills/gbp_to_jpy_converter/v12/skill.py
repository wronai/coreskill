import subprocess
import re
import json
import urllib.request
import sys

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v1',
        'description': 'Converts GBP to JPY, specifically handling Polish language requests'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed later)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def parse_amount(text: str) -> float:
    text_lower = text.lower()
    
    # Handle Polish number words
    number_words = {
        'tysiąc': 1000,
        'tys': 1000,
        'milion': 1000000,
        'mln': 1000000,
        'miliard': 1000000000,
        'mld': 1000000000
    }
    
    # Check for explicit numbers first
    number_match = re.search(r'(\d+(?:[.,]\d+)?)', text)
    if number_match:
        try:
            return float(number_match.group(0).replace(',', '.'))
        except ValueError:
            pass
    
    # Check for Polish number words
    for word, value in number_words.items():
        if word in text_lower:
            return float(value)
    
    # Default to 1000 if no amount found but context suggests GBP->JPY conversion
    return 1000.0

def get_exchange_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data['rates'].get('JPY', 0)
    except Exception:
        return 175.0

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '')
        
        # Check if the request is about GBP to JPY conversion
        text_lower = text.lower()
        is_gbp_jpy_request = (
            ('funt' in text_lower and 'jen' in text_lower) or 
            ('gbp' in text_lower and 'jen' in text_lower) or
            ('funt' in text_lower and 'yen' in text_lower) or
            ('gbp' in text_lower and 'yen' in text_lower)
        )
        
        if is_gbp_jpy_request:
            amount_gbp = parse_amount(text)
            rate = get_exchange_rate()
            amount_jpy = amount_gbp * rate
            
            # Format the result for display and speech
            result_text = f"{amount_gbp:.2f} funtów szterlingów to {amount_jpy:.2f} jenów japońskich"
            
            return {
                'success': True,
                'amount_gbp': amount_gbp,
                'amount_jpy': amount_jpy,
                'exchange_rate': rate,
                'spoken': result_text,
                'result': result_text
            }
        else:
            return {
                'success': False,
                'error': 'Not a GBP to JPY conversion request',
                'message': 'The request does not match the expected pattern for GBP to JPY conversion',
                'spoken': 'Nie rozpoznano prośby o przeliczenie funtów na jeny'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'An error occurred during conversion',
            'spoken': 'Wystąpił błąd podczas przeliczania'
        }

class GBPToJPYConverter:
    def execute(self, params: dict) -> dict:
        return execute(params)

def execute_wrapper(params: dict) -> dict:
    converter = GBPToJPYConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_cases = [
        "przelicz tysiąc funtów szterlingów na jeny japońskie",
        "ile to 500 funtów w jenach",
        "przelicz 100 funtów na jeny japońskie"
    ]
    
    for test in test_cases:
        print(f"\nTesting: '{test}'")
        result = execute({'text': test})
        print(json.dumps(result, indent=2, ensure_ascii=False))