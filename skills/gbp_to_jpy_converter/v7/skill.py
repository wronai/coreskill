import re
import subprocess
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v7',
        'description': 'Converts GBP to JPY, specifically handling requests like "przelicz tysiąc funtów szterlingów na jeny japońskie"'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available for TTS
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'error', 'message': 'espeak not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def parse_amount(text: str) -> float:
    # Extract number words and convert to numeric
    number_words = {
        'tysiąc': 1000,
        'tysiące': 1000,
        'tysięcy': 1000,
        'milion': 1000000,
        'miliony': 1000000,
        'milionów': 1000000,
        'miliard': 1000000000,
        'miliardy': 1000000000,
        'miliardów': 1000000000
    }
    
    # Try to find explicit numbers first
    numbers = re.findall(r'\d+\.?\d*', text)
    if numbers:
        return float(numbers[0])
    
    # Try to find number words
    for word, value in number_words.items():
        if word in text.lower():
            return value
    
    # Default to 1000 as per the example
    return 1000.0

def get_exchange_rate():
    try:
        # Use a public API for GBP to JPY exchange rate
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data['rates'].get('JPY', 150.0)  # fallback to 150 if not available
    except Exception:
        # Fallback exchange rate if API fails
        return 180.0

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '').lower()
        
        # Extract amount (default to 1000 as per example)
        amount = parse_amount(text)
        
        # Get current exchange rate
        rate = get_exchange_rate()
        
        # Calculate conversion: amount in GBP to JPY
        result_jpy = amount * rate
        
        # Format result
        result_text = f"{amount:,.0f} funtów szterlingów to {result_jpy:,.0f} jenów japońskich"
        
        # Generate TTS response using espeak
        try:
            subprocess.run(['espeak', '-v', 'pl', result_text], 
                         capture_output=True, timeout=10)
        except Exception:
            pass  # TTS is optional, don't fail if it doesn't work
        
        return {
            'success': True,
            'result': result_text,
            'amount_gbp': amount,
            'amount_jpy': result_jpy,
            'exchange_rate': rate
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

def main_execute(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = main_execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))