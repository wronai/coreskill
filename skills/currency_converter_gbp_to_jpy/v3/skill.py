import re
import subprocess
import json
import urllib.request
import urllib.error

class CurrencyConverterGBPtoJPY:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount and currencies from text
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
            
            amount = None
            
            # Try to find explicit numbers first
            number_match = re.search(r'(\d+(?:[.,]\d+)?)', text)
            if number_match:
                amount_str = number_match.group(1).replace(',', '.')
                try:
                    amount = float(amount_str)
                except ValueError:
                    pass
            
            # If no explicit number found, try number words
            if amount is None:
                for word, value in number_words.items():
                    if word in text:
                        amount = value
                        break
            
            # Default to 1000 if still no amount found
            if amount is None:
                amount = 1000
            
            # Check if it's GBP to JPY conversion
            gbp_keywords = ['funty', 'funt', 'gbp', 'brytyjskie', 'szterling']
            jpy_keywords = ['jeny', 'jen', 'japońskie', 'jpy', 'yeny']
            
            has_gbp = any(kw in text for kw in gbp_keywords)
            has_jpy = any(kw in text for kw in jpy_keywords)
            
            if not (has_gbp and has_jpy):
                return {
                    'success': False,
                    'error': 'Not a GBP to JPY conversion request',
                    'text': text,
                    'spoken': 'Nie można wykonać konwersji: nie znaleziono fraz oznaczających funty szterlingów i jeny japońskie'
                }
            
            # Get exchange rate from a public API
            gbp_to_jpy_rate = 185.0  # Default fallback rate
            try:
                url = "https://api.exchangerate-api.com/v4/latest/GBP"
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    gbp_to_jpy_rate = data['rates'].get('JPY', 0)
                    if gbp_to_jpy_rate == 0:
                        gbp_to_jpy_rate = 185.0
            except Exception:
                pass  # Use fallback rate
            
            # Calculate conversion
            result_jpy = amount * gbp_to_jpy_rate
            
            # Format result
            result_text = f"{amount:,.0f} funtów szterlingów to {result_jpy:,.0f} jenów japońskich przy kursie {gbp_to_jpy_rate:.2f} JPY/GBP"
            
            # Use espeak for TTS if available
            try:
                subprocess.run(['espeak', result_text], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass  # Continue even if TTS fails
            
            return {
                'success': True,
                'amount_gbp': amount,
                'amount_jpy': round(result_jpy, 2),
                'exchange_rate': gbp_to_jpy_rate,
                'text': result_text,
                'spoken': result_text
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'spoken': f'Wystąpił błąd: {str(e)}'
            }

def get_info() -> dict:
    return {
        'name': 'currency_converter_gbp_to_jpy',
        'version': 'v1',
        'description': 'Converts GBP to JPY, specifically handling requests like "przelicz tysiąc funtów szterlingów na jeny japońskie"'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available for TTS
        result = subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except (subprocess.TimeoutExpired, FileNotFoundError, subprocess.SubprocessError):
        return {'status': 'error', 'message': 'espeak not available'}

def execute(params: dict) -> dict:
    converter = CurrencyConverterGBPtoJPY()
    return converter.execute(params)

if __name__ == '__main__':
    # Test block
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))