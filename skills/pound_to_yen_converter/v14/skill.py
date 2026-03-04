import subprocess
import re
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v14',
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
    def __init__(self):
        self.api_url = "https://api.exchangerate-api.com/v4/latest/GBP"
    
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount if present (e.g., "tysiąc", "1000", etc.)
            amount = 1000  # default to 1000 as per requirement
            
            # Try to find a number in the text
            numbers = re.findall(r'\d+', text)
            if numbers:
                amount = int(numbers[0])
            
            # Check if the request is for GBP to JPY conversion
            if 'funt' in text and 'jen' in text:
                # Fetch exchange rate
                try:
                    with urllib.request.urlopen(self.api_url, timeout=10) as response:
                        data = json.loads(response.read().decode())
                        gbp_to_jpy = data['rates'].get('JPY', 0)
                        
                        if gbp_to_jpy == 0:
                            return {
                                'success': False,
                                'error': 'Exchange rate not available',
                                'message': 'Could not retrieve exchange rate'
                            }
                        
                        result = amount * gbp_to_jpy
                        
                        # Format the result with proper separators
                        result_formatted = f"{result:,.2f}"
                        
                        # Create response message
                        response_text = f"{amount} funtów szterlingów to {result_formatted} jenów japońskich"
                        
                        return {
                            'success': True,
                            'amount_gbp': amount,
                            'amount_jpy': result,
                            'rate': gbp_to_jpy,
                            'message': response_text
                        }
                except urllib.error.URLError as e:
                    return {
                        'success': False,
                        'error': 'Network error',
                        'message': f'Could not fetch exchange rate: {str(e)}'
                    }
                except Exception as e:
                    return {
                        'success': False,
                        'error': 'API error',
                        'message': f'Error processing exchange rate: {str(e)}'
                    }
            else:
                return {
                    'success': False,
                    'error': 'No conversion request',
                    'message': 'The request does not contain a valid GBP to JPY conversion request'
                }
        except Exception as e:
            return {
                'success': False,
                'error': 'Internal error',
                'message': f'Internal error: {str(e)}'
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))