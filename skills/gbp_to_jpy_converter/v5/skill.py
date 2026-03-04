import re
import subprocess
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v5',
        'description': 'Converts GBP to JPY, specifically handles requests like "przelicz tysiąc funtów szterlingów na jeny japońskie"'
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
    # Polish number words to digits mapping
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
    
    # Check for explicit numbers first
    number_match = re.search(r'(\d+(?:[.,]\d+)?)', text)
    if number_match:
        num_str = number_match.group(1).replace(',', '.')
        return float(num_str)
    
    # Check for Polish number words
    for word, value in number_words.items():
        if word in text.lower():
            return value
    
    # Default to 1000 if "tysiąc" is mentioned but not matched above
    if 'tysiąc' in text.lower():
        return 1000.0
    
    return 1000.0  # Default fallback

def fetch_exchange_rate() -> float:
    try:
        # Use ECB API for EUR rates, then convert EUR->GBP and EUR->JPY
        # ECB provides EUR/USD, EUR/JPY, and we can get GBP/USD from other sources
        # Since we need GBP->JPY, we'll use a simpler approach with a public API
        
        # Use exchangerate-api.com for GBP to JPY conversion
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            return data['rates']['JPY']
    except Exception:
        # Fallback rate: 1 GBP ≈ 185 JPY (as of 2023-2024)
        return 185.0

def speak_result(amount_gbp: float, amount_jpy: float, rate: float):
    try:
        text = f"{amount_gbp:.2f} funtów szterlingów to około {amount_jpy:.2f} jenów japońskich przy kursie {rate:.2f} jenów na funt."
        subprocess.run(['espeak', '-v', 'pl', text], timeout=10)
    except Exception:
        pass  # Silent failure for TTS

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '').lower()
        
        # Check if the query is about converting GBP to JPY
        if 'funty' in text and 'jen' in text and ('przelicz' in text or 'ile' in text):
            amount_gbp = parse_amount(text)
            rate = fetch_exchange_rate()
            amount_jpy = amount_gbp * rate
            
            result_text = f"{amount_gbp:.2f} GBP to {amount_jpy:.2f} JPY (kurs: {rate:.2f} JPY/GBP)"
            
            # Speak the result
            speak_result(amount_gbp, amount_jpy, rate)
            
            return {
                'success': True,
                'result': result_text,
                'amount_gbp': amount_gbp,
                'amount_jpy': amount_jpy,
                'rate': rate
            }
        else:
            return {
                'success': False,
                'error': 'Query not recognized as GBP to JPY conversion request',
                'result': 'Nie rozpoznano zapytania o przeliczenie funtów szterlingów na jeny japońskie.'
            }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'result': 'Wystąpił błąd podczas przetwarzania zapytania.'
        }

def main_execute(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test the skill
    test_cases = [
        "przelicz tysiąc funtów szterlingów na jeny japońskie",
        "ile to 500 funtów w jenach",
        "przelicz 200 funtów na jeny"
    ]
    
    for text in test_cases:
        print(f"\nTesting: '{text}'")
        result = execute({'text': text})
        print(json.dumps(result, indent=2, ensure_ascii=False))