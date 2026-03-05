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
            
            # Default amount
            amount = 1.0
            
            # Handle special cases for common amounts
            if 'tysiąc' in text or re.search(r'1\s*000|1,000', text):
                amount = 1000.0
            elif 'milion' in text or re.search(r'1\s*milion', text):
                amount = 1000000.0
            else:
                # Try to find any number in the text
                number_pattern = r'(\d+(?:[.,]\d+)?)'
                numbers = re.findall(number_pattern, text)
                
                # Find the number that appears before currency keywords
                for num_str in numbers:
                    # Find position of number in text
                    num_pos = text.find(num_str.replace(',', '.'))
                    if num_pos != -1:
                        # Look for currency keywords after the number
                        remaining_text = text[num_pos + len(num_str):num_pos + len(num_str) + 30]
                        if 'funt' in remaining_text or 'funty' in remaining_text:
                            amount = float(num_str.replace(',', '.'))
                            break
                
                # If no currency context found, use the first number found
                if amount == 1.0 and numbers:
                    amount = float(numbers[0].replace(',', '.'))
            
            # Get current exchange rate from a public API
            gbp_to_jpy = 185.0  # default fallback rate
            try:
                url = "https://api.exchangerate-api.com/v4/latest/GBP"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as response:
                    data = json.loads(response.read().decode())
                    gbp_to_jpy = data['rates'].get('JPY', 185.0)
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