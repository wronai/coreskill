import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v1',
        'description': 'Converts GBP to JPY, specifically handling Polish requests like "przelicz tysiąc funtów szterlingów na jeny japońskie"'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        if result.returncode == 0:
            return {'status': 'ok'}
        else:
            return {'status': 'error', 'message': 'espeak not working properly'}
    except FileNotFoundError:
        return {'status': 'error', 'message': 'espeak not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def fetch_exchange_rate():
    try:
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data['rates'].get('JPY', None)
    except Exception:
        return None

def parse_amount_from_text(text):
    text_lower = text.lower()
    
    # Handle Polish words for numbers
    replacements = {
        'tysiąc': '1000',
        'tys': '1000',
        'milion': '1000000',
        'mln': '1000000'
    }
    
    for word, value in replacements.items():
        text_lower = text_lower.replace(word, value)
    
    # Match numbers (including decimals)
    numbers = re.findall(r'\d+\.?\d*', text_lower)
    if numbers:
        return float(numbers[0])
    return None

class GBPToJPYConverter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Check if the request is about GBP to JPY conversion
            if ('funt' in text and 'szterling' in text and 
                ('jen' in text or 'japońsk' in text)):
                # Extract amount
                amount = parse_amount_from_text(text)
                if amount is None:
                    amount = 1000  # default to 1000 as per example
                
                # Get exchange rate
                rate = fetch_exchange_rate()
                if rate is None:
                    response_text = "Nie można pobrać kursu wymiany GBP do JPY"
                    return {
                        'success': False,
                        'message': response_text,
                        'error': 'exchange_rate_unavailable',
                        'spoken': response_text
                    }
                
                # Calculate conversion
                result = amount * rate
                
                # Prepare response
                response_text = f"{amount:.2f} funtów szterlingów to {result:.2f} jenów japońskich przy kursie 1 GBP = {rate:.2f} JPY"
                
                # Try to speak the result using espeak
                try:
                    subprocess.run(['espeak', response_text], capture_output=True, timeout=5)
                except Exception:
                    pass  # Ignore TTS errors
                
                return {
                    'success': True,
                    'result': result,
                    'amount_gbp': amount,
                    'rate': rate,
                    'response': response_text,
                    'spoken': response_text
                }
            else:
                response_text = "Zapytanie nie dotyczy konwersji funtów szterlingów na jeny japońskie"
                return {
                    'success': False,
                    'message': response_text,
                    'error': 'invalid_request',
                    'spoken': response_text
                }
        except Exception as e:
            response_text = f"Błąd podczas przetwarzania zapytania: {str(e)}"
            return {
                'success': False,
                'message': response_text,
                'error': str(e),
                'spoken': response_text
            }

def execute(params: dict) -> dict:
    converter = GBPToJPYConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_cases = [
        "przelicz tysiąc funtów szterlingów na jeny japońskie",
        "ile to 500 funtów w jenach",
        "przelicz 200 funtów na jeny japońskie"
    ]
    
    for test in test_cases:
        print(f"\nTesting: '{test}'")
        result = execute({'text': test})
        print(f"Result: {json.dumps(result, indent=2, ensure_ascii=False)}")