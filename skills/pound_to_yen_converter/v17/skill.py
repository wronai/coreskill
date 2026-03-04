import subprocess
import re
import urllib.request
import json

def get_info():
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v17',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check():
    try:
        # Check if espeak is available (for TTS if needed later)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def execute(params: dict) -> dict:
    try:
        # Extract text from params
        text = params.get('text', '').lower()
        
        # Look for patterns like "tysiąc funtów szterlingów na jeny japońskie"
        # We'll extract the amount and currencies
        amount_match = re.search(r'(\d+)\s*(tysiąc)?\s*funtów?\s*(szterlingów?)?', text)
        if not amount_match:
            # Try alternative patterns
            amount_match = re.search(r'(\d+)\s*funtów?\s*(szterlingów?)?', text)
        
        if not amount_match:
            return {
                'success': False,
                'message': 'Nie rozpoznano kwoty do przeliczenia'
            }
        
        # Calculate the amount
        base_amount = int(amount_match.group(1))
        if amount_match.group(2):  # "tysiąc" was mentioned
            base_amount *= 1000
        
        # Get current exchange rate from a public API
        try:
            url = "https://api.exchangerate-api.com/v4/latest/GBP"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                gbp_to_jpy = data['rates']['JPY']
        except Exception:
            # Fallback: use a known approximate rate (as of 2023-2024)
            gbp_to_jpy = 185.0
        
        # Calculate result
        result_yen = base_amount * gbp_to_jpy
        
        # Format result
        result_text = f"{result_yen:,.0f} jenów japońskich"
        
        # Prepare response
        response_text = f"{base_amount:,} funtów szterlingów to {result_text} (kurs: 1 GBP = {gbp_to_jpy:.2f} JPY)"
        
        return {
            'success': True,
            'result': result_yen,
            'result_text': response_text,
            'amount_gbp': base_amount,
            'amount_jpy': result_yen,
            'exchange_rate': gbp_to_jpy
        }
    
    except Exception as e:
        return {
            'success': False,
            'message': f'Błąd podczas przeliczania: {str(e)}'
        }

def execute_wrapper(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))