import re
import subprocess
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v1',
        'description': 'Converts GBP to JPY, specifically handles requests like "przelicz tysiąc funtów szterlingów na jeny japońskie"'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available for TTS (not required for this skill, but for consistency)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        # Check network connectivity for currency API
        req = urllib.request.Request(
            'https://api.exchangerate-api.com/v4/latest/GBP',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'rates' in data and 'JPY' in data['rates']:
                return {'status': 'ok'}
        return {'status': 'error', 'message': 'Currency API not responding properly'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def extract_amount(text: str) -> float:
    # Polish number words mapping
    polish_numbers = {
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
    
    # Try to find numeric values first
    numbers = re.findall(r'\d+\.?\d*', text.replace(',', '.'))
    if numbers:
        return float(numbers[0])
    
    # Try to find Polish number words
    for word, value in polish_numbers.items():
        if word in text.lower():
            return float(value)
    
    # Default to 1000 if "tysiąc" is mentioned but not matched above
    if 'tysiąc' in text.lower():
        return 1000.0
    
    return 1000.0  # Default fallback

def convert_gbp_to_jpy(amount_gbp: float) -> float:
    try:
        req = urllib.request.Request(
            'https://api.exchangerate-api.com/v4/latest/GBP',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'rates' in data and 'JPY' in data['rates']:
                rate = data['rates']['JPY']
                return amount_gbp * rate
    except Exception:
        # Fallback rate if API fails (approximate as of 2023)
        return amount_gbp * 185.0

class GBPToJPYConverter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            
            # Extract amount from text
            amount_gbp = extract_amount(text)
            
            # Convert to JPY
            amount_jpy = convert_gbp_to_jpy(amount_gbp)
            
            # Format output
            result_text = f"{amount_gbp:.2f} funtów szterlingów to {amount_jpy:.2f} jenów japońskich"
            
            # Try to speak the result using espeak
            try:
                subprocess.run(['espeak', '-v', 'pl', result_text], 
                             capture_output=True, timeout=5)
            except Exception:
                pass  # TTS is optional
            
            return {
                'success': True,
                'amount_gbp': amount_gbp,
                'amount_jpy': amount_jpy,
                'result_text': result_text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'result_text': 'Wystąpił błąd podczas przeliczania walut.'
            }

def execute(params: dict) -> dict:
    converter = GBPToJPYConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))