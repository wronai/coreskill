import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v10',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed later)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class PoundToYenConverter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount if present (e.g., "tysiąc" = 1000, "tysiące" = thousands)
            amount = 1000  # default as per requirement
            
            # Check for "tysiąc" (thousand) in Polish
            if 'tysiąc' in text:
                amount = 1000
            elif 'tysiące' in text or 'tysięcy' in text:
                # Try to extract number before "tysiące/tysięcy"
                match = re.search(r'(\d+)\s*tysiące?', text)
                if match:
                    amount = int(match.group(1)) * 1000
                else:
                    amount = 1000  # default
            
            # Extract currency names
            has_pound = any(word in text for word in ['funt', 'funty', 'szterling', 'gbp'])
            has_yen = any(word in text for word in ['jen', 'jeny', 'japońskie', 'jpy'])
            
            # If no explicit currencies mentioned but context suggests conversion
            if not (has_pound and has_yen):
                # Default to GBP to JPY conversion as per requirement
                has_pound = True
                has_yen = True
            
            if has_pound and has_yen:
                # Get current exchange rate from ECB API
                try:
                    url = "https://api.exchangerate-api.com/v4/latest/GBP"
                    with urllib.request.urlopen(url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        rate = data['rates'].get('JPY', 0)
                except Exception:
                    # Fallback rate if API fails (approximate)
                    rate = 185.0  # approximate rate as of 2023
                
                result_yen = amount * rate
                
                # Format result
                result_text = f"{amount} funtów szterlingów to {result_yen:,.0f} jenów japońskich"
                
                # Use espeak for TTS if available
                try:
                    subprocess.run(['espeak', result_text], capture_output=True, timeout=5)
                except Exception:
                    pass  # TTS is optional
                
                return {
                    'success': True,
                    'amount_pounds': amount,
                    'amount_yen': result_yen,
                    'exchange_rate': rate,
                    'text_response': result_text
                }
            else:
                return {
                    'success': False,
                    'error': 'Could not identify currency conversion request',
                    'text_response': 'Nie rozpoznałem prośby o przeliczenie funtów na jeny'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text_response': 'Wystąpił błąd podczas przeliczania'
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))