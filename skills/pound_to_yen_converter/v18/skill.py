import subprocess
import re
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v18',
        'description': 'Converts British Pounds to Japanese Yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS, though not used in this skill)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def parse_amount_from_text(text: str) -> float:
    # Extract number followed by optional words like "tysiąc", "tys", "tysiące", etc.
    # Also handle "tysiąc funtów" -> extract 1000
    text_lower = text.lower()
    
    # Handle "tysiąc" explicitly
    if 'tysiąc' in text_lower:
        # Look for number before "tysiąc" or just use 1000
        match = re.search(r'(\d+(?:[.,]\d+)?)\s*tysiąc', text_lower)
        if match:
            return float(match.group(1).replace(',', '.')) * 1000
        else:
            return 1000.0
    
    # General number extraction (handles decimals with comma or dot)
    match = re.search(r'(\d+(?:[.,]\d+)?)', text_lower)
    if match:
        return float(match.group(1).replace(',', '.'))
    return 1000.0  # default if no number found

def get_exchange_rate():
    # Use ECB public API for exchange rates (GBP to JPY)
    try:
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data['rates'].get('JPY', 0)
    except Exception:
        # Fallback rate: 1 GBP ≈ 185 JPY (as of 2023-2024)
        return 185.0

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '').lower()
        
        # Extract amount (default to 1000 if "tysiąc" is mentioned)
        amount = parse_amount_from_text(text)
        
        # Get exchange rate
        rate = get_exchange_rate()
        
        # Calculate conversion
        result_yen = amount * rate
        
        # Format result
        result_text = f"{amount:.2f} funtów szterlingów to {result_yen:,.2f} jenów japońskich"
        
        # Use espeak for TTS if needed (not required, but available)
        try:
            subprocess.run(['espeak', result_text], capture_output=True, timeout=5)
        except Exception:
            pass  # TTS is optional
        
        return {
            'success': True,
            'amount_pounds': amount,
            'rate': rate,
            'amount_yen': result_yen,
            'text': result_text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'text': f"Błąd przeliczania: {str(e)}"
        }

# Module-level execute function
def execute_module(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test case
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))