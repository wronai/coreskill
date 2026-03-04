import re
import subprocess
import json
import os

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v1',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class PoundToYenConverter:
    def __init__(self):
        # Approximate exchange rate (as of 2023-10-01: ~1 GBP = 185 JPY)
        # Using a fixed rate since we can't use external APIs
        self.exchange_rate = 185.0
    
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount and currencies from the text
            amount = 1  # default
            
            if 'milion' in text or 'miliony' in text:
                amount = 1000000
                # Adjust for multiple millions
                match = re.search(r'(\d+)\s*milion', text)
                if match:
                    amount = int(match.group(1)) * 1000000
            elif 'tysiąc' in text or 'tysiące' in text:
                amount = 1000
                # Adjust for multiple thousands
                match = re.search(r'(\d+)\s*tysiąc', text)
                if match:
                    amount = int(match.group(1)) * 1000
            else:
                # Try to extract a number from the text
                numbers = re.findall(r'\d+', text)
                if numbers:
                    amount = int(numbers[0])
            
            # Check if it's GBP to JPY conversion
            if ('funt' in text and 'jen' in text) or ('funt' in text and 'jenów' in text):
                # Convert pounds to yen
                result_yen = amount * self.exchange_rate
                
                # Format the result for display and speech
                result_text = f"{amount} funtów szterlingów to około {result_yen:,.0f} jenów japońskich"
                spoken_text = f"{amount} funtów szterlingów to około {result_yen:,.0f} jenów japońskich"
                
                # Use espeak for TTS if available
                try:
                    subprocess.run(['espeak', spoken_text], capture_output=True, timeout=10)
                except Exception:
                    pass  # TTS is optional
                
                return {
                    'success': True,
                    'result': result_yen,
                    'text': result_text,
                    'spoken': spoken_text,
                    'amount_pounds': amount,
                    'amount_yen': result_yen,
                    'exchange_rate': self.exchange_rate
                }
            else:
                return {
                    'success': False,
                    'error': 'Not a valid pound to yen conversion request',
                    'text': 'Proszę zapytać o przeliczenie funtów szterlingów na jeny japońskie',
                    'spoken': 'Proszę zapytać o przeliczenie funtów szterlingów na jeny japońskie'
                }
                
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': 'Wystąpił błąd podczas przeliczania',
                'spoken': 'Wystąpił błąd podczas przeliczania'
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))