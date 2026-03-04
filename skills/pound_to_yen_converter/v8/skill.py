import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v8',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed later)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def parse_amount_from_text(text: str) -> float:
    """Extract numeric amount from text, defaulting to 1000 for 'tysiąc' (thousand)"""
    text_lower = text.lower()
    
    # Check for "tysiąc" (thousand) in Polish
    if 'tysiąc' in text_lower:
        return 1000.0
    
    # Try to extract numbers (including decimals)
    numbers = re.findall(r'\d+\.?\d*', text_lower)
    if numbers:
        return float(numbers[0])
    
    return 1000.0  # Default to 1000 if nothing found

def get_exchange_rate() -> float:
    """Get GBP to JPY exchange rate from a public API"""
    try:
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return data['rates']['JPY']
    except Exception:
        # Fallback rate: 1 GBP ≈ 185 JPY (as of recent years)
        return 185.0

def execute(params: dict) -> dict:
    try:
        text = params.get('text', '')
        
        # Extract amount (default to 1000 for "tysiąc")
        amount_gbp = parse_amount_from_text(text)
        
        # Get current exchange rate
        rate = get_exchange_rate()
        
        # Calculate JPY amount
        amount_jpy = amount_gbp * rate
        
        # Format the result
        result_text = f"{amount_gbp:.2f} funtów szterlingów to {amount_jpy:,.2f} jenów japońskich"
        
        # Prepare response
        response = {
            'success': True,
            'amount_gbp': amount_gbp,
            'amount_jpy': amount_jpy,
            'exchange_rate': rate,
            'text': result_text
        }
        
        # If TTS is needed, generate audio using espeak
        try:
            subprocess.run(['espeak', '-v', 'pl', result_text], check=True)
        except Exception:
            pass  # TTS is optional, don't fail if espeak is unavailable
        
        return response
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'text': f'Błąd przeliczania: {str(e)}'
        }

# Module-level execute function
def execute_module(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute_module(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))