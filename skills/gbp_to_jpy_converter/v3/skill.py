import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v3',
        'description': 'Converts GBP to JPY, specifically handling requests like "przelicz tysiąc funtów szterlingów na jeny japońskie"'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed later)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def fetch_exchange_rate():
    try:
        # Use a free exchange rate API
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data['rates'].get('JPY', None)
    except Exception:
        return None

def parse_amount_from_text(text):
    # Extract numbers from text (including "tysiąc" = thousand)
    text_lower = text.lower()
    
    # Handle Polish words for numbers
    if 'tysiąc' in text_lower:
        text_lower = text_lower.replace('tysiąc', '1000')
    
    # Match numbers (including decimals)
    numbers = re.findall(r'\d+\.?\d*', text_lower)
    if numbers:
        return float(numbers[0])
    return None

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '').lower()
        
        # Check if the request is about GBP to JPY conversion
        if 'funtów' in text and 'szterling' in text and 'jen' in text and 'japońsk' in text:
            # Extract amount
            amount = parse_amount_from_text(text)
            if amount is None:
                amount = 1000  # default to 1000 as per example
            
            # Get exchange rate
            rate = fetch_exchange_rate()
            if rate is None:
                return {
                    'success': False,
                    'message': 'Nie można pobrać kursu wymiany GBP do JPY',
                    'error': 'exchange_rate_unavailable'
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
                'response': response_text
            }
        else:
            return {
                'success': False,
                'message': 'Zapytanie nie dotyczy konwersji funtów szterlingów na jeny japońskie',
                'error': 'invalid_request'
            }
    except Exception as e:
        return {
            'success': False,
            'message': f'Błąd podczas przetwarzania zapytania: {str(e)}',
            'error': str(e)
        }

def execute_wrapper(params: dict) -> dict:
    return execute(params)

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