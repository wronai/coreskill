import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v1',
        'description': 'Converts 1000 British Pounds to Japanese Yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def execute(params: dict) -> dict:
    try:
        # Extract text from params
        text = params.get('text', '').lower()
        
        # Check if the text contains the specific request pattern
        # Looking for phrases like "przelicz tysiąc funtów szterlingów na jeny japońskie"
        pattern = r'przelicz\s+(?:tysiąc|1000)\s+funtów\s+szterlingów\s+na\s+jeny\s+japońskie'
        if not re.search(pattern, text):
            # Try to find any mention of pounds to yen conversion
            pattern = r'(?:tysiąc|1000)\s+funtów\s+szterlingów'
            if not re.search(pattern, text):
                return {
                    'success': False,
                    'error': 'No valid conversion request found',
                    'message': 'The request does not match the expected pattern for converting 1000 British Pounds to Japanese Yen.'
                }
        
        # Fetch current exchange rates
        try:
            # Using ECB API (free, no key required)
            url = "https://api.exchangerate-api.com/v4/latest/GBP"
            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode())
                
            if 'rates' not in data:
                raise ValueError("No rates data in response")
                
            gbp_to_jpy = data['rates'].get('JPY', 0)
            
            if gbp_to_jpy == 0:
                raise ValueError("JPY rate not available")
                
            # Calculate 1000 GBP to JPY
            amount_gbp = 1000
            amount_jpy = amount_gbp * gbp_to_jpy
            
            result_text = f"{amount_gbp} funtów szterlingów to {amount_jpy:.2f} jenów japońskich"
            
            # Prepare response
            response_data = {
                'success': True,
                'amount_gbp': amount_gbp,
                'amount_jpy': round(amount_jpy, 2),
                'rate': gbp_to_jpy,
                'message': result_text,
                'text': result_text
            }
            
            # Try to speak the result if espeak is available
            try:
                subprocess.run(['espeak', result_text], capture_output=True, timeout=5)
            except Exception:
                pass  # Ignore TTS errors
            
            return response_data
            
        except Exception as e:
            # Fallback: use a hardcoded rate if API fails (for demo purposes)
            fallback_rate = 185.5  # Example fallback rate
            amount_jpy = 1000 * fallback_rate
            result_text = f"{1000} funtów szterlingów to {amount_jpy:.2f} jenów japońskich (kurs przybliżony)"
            
            return {
                'success': True,
                'amount_gbp': 1000,
                'amount_jpy': round(amount_jpy, 2),
                'rate': fallback_rate,
                'message': result_text,
                'text': result_text,
                'note': 'Użyto kursu przybliżonego (API niedostępne)'
            }
            
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'message': 'Wystąpił błąd podczas przeliczania walut'
        }

# Module-level execute function
def execute_module(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test block
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))