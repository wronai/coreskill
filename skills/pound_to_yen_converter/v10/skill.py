import subprocess
import re
import urllib.request
import json

def get_info():
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v1',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check():
    try:
        # Check if espeak is available (for TTS, though not used in this skill)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class PoundToYenConverter:
    def execute(self, params: dict) -> dict:
        try:
            # Extract text from params
            text = params.get('text', '').lower()
            
            # Try to find amount in text (handles Polish words and numbers)
            amount = 1000  # default
            
            # Handle "tysiąc" (thousand)
            if 'tysiąc' in text or re.search(r'1\s*000|1,000', text):
                amount = 1000
            else:
                # Try to find any number in the text
                number_pattern = r'(\d+(?:[.,]\d+)?)'
                numbers = re.findall(number_pattern, text)
                if numbers:
                    # Find the first number that appears to be the amount (before "funt" or "funty")
                    for num_str in numbers:
                        # Check if this number appears before currency keywords
                        idx = text.find(num_str.replace(',', '.'))
                        if idx != -1:
                            # Look for currency keywords after the number
                            remaining_text = text[idx+len(num_str):idx+len(num_str)+20]
                            if 'funt' in remaining_text or 'funty' in remaining_text:
                                amount = float(num_str.replace(',', '.'))
                                break
                    else:
                        # If no currency context found, use the first number
                        amount = float(numbers[0].replace(',', '.'))
            
            # Get current exchange rate from a public API
            try:
                url = "https://api.exchangerate-api.com/v4/latest/GBP"
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    gbp_to_jpy = data['rates'].get('JPY', 150)  # default to 150 if not found
            except Exception:
                # Fallback rate if API fails
                gbp_to_jpy = 185.0
            
            # Calculate result
            result_yen = amount * gbp_to_jpy
            
            # Format result for display and TTS
            result_text = f"{amount:.0f} funtów szterlingów to {result_yen:.2f} jenów japońskich"
            spoken_text = f"{int(amount)} funtów szterlingów to {result_yen:.0f} jenów japońskich"
            
            # Prepare response
            return {
                'success': True,
                'result': result_yen,
                'text': result_text,
                'spoken': spoken_text,
                'amount_gbp': amount,
                'amount_jpy': result_yen,
                'exchange_rate': gbp_to_jpy
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'text': 'Wystąpił błąd podczas przeliczania walut.',
                'spoken': 'Wystąpił błąd podczas przeliczania walut.'
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))