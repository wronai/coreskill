import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v1',
        'description': 'Converts pounds sterling to Japanese yen with Polish TTS'
    }

def health_check() -> dict:
    try:
        # Test espeak availability
        result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        if result.returncode != 0:
            return {'status': 'error', 'message': 'espeak not available'}
        
        # Test internet connection by trying to fetch exchange rate data
        req = urllib.request.Request(
            'https://api.exchangerate-api.com/v4/latest/GBP',
            headers={'User-Agent': 'Mozilla/5.0'}
        )
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode())
            if 'rates' in data and 'JPY' in data['rates']:
                return {'status': 'ok'}
        return {'status': 'error', 'message': 'Exchange rate API not accessible'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class Converter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount if present, default to 1000 (thousand)
            amount = 1000.0  # Default
            
            # Try to match patterns like "tysiąc funtów", "1000 funtów", "tys. funtów"
            amount_match = re.search(r'(\d+)\s*(tysiąc|tys\.?)?\s*funtów|(\d+)\s*funtów', text)
            if amount_match:
                if amount_match.group(1):  # Has a number
                    if amount_match.group(2):  # Has "tysiąc" or "tys."
                        amount = float(amount_match.group(1)) * 1000
                    else:
                        amount = float(amount_match.group(1))
                elif 'tysiąc' in text or 'tys.' in text:
                    amount = 1000.0
                else:
                    amount = 1000.0
            else:
                # Check for "tysiąc" alone
                if 'tysiąc' in text or 'tys.' in text:
                    amount = 1000.0
            
            # Fetch current exchange rate
            try:
                req = urllib.request.Request(
                    'https://api.exchangerate-api.com/v4/latest/GBP',
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    if 'rates' in data and 'JPY' in data['rates']:
                        rate = data['rates']['JPY']
                    else:
                        raise ValueError("JPY rate not found")
            except Exception:
                # Fallback rate if API unavailable (as of 2023 ~180 JPY/GBP)
                rate = 180.0
            
            # Calculate conversion
            result_yen = amount * rate
            
            # Format result with proper Polish formatting (spaces instead of commas)
            result_text = f"{result_yen:,.0f}".replace(",", " ")
            
            # Prepare response
            amount_display = int(amount) if amount == int(amount) else amount
            response_text = f"{amount_display:,}".replace(",", " ") + " funtów szterlingów to około " + result_text + " jenów japońskich."
            
            # Use espeak for TTS if available
            try:
                subprocess.run(['espeak', '-v', 'pl', response_text], 
                              capture_output=True, timeout=5)
            except Exception:
                pass  # Ignore TTS errors
            
            return {
                'success': True,
                'amount_pounds': amount,
                'rate': rate,
                'amount_yen': result_yen,
                'text_response': response_text,
                'spoken': response_text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'spoken': "Wystąpił błąd podczas przeliczania."
            }

def execute(params: dict) -> dict:
    converter = Converter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))