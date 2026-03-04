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
        # Check if espeak is available for TTS
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class Converter:
    def execute(self, params: dict) -> dict:
        try:
            # Extract text from params
            text = params.get('text', '').lower()
            
            # Convert Polish number words to digits (basic support)
            number_words = {
                'tysiąc': 1000, 'tysiące': 1000, 'tysięcy': 1000,
                'dwa tysiące': 2000, 'trzy tysiące': 3000, 'cztery tysiące': 4000,
                'pięć tysięcy': 5000, 'sześć tysięcy': 6000, 'siedem tysięcy': 7000,
                'osiem tysięcy': 8000, 'dziewięć tysięcy': 9000, 'dziesięć tysięcy': 10000,
                'sto': 100, 'dwieście': 200, 'trzysta': 300, 'czterysta': 400,
                'pięćset': 500, 'sześćset': 600, 'siedemset': 700, 'osiemset': 800,
                'dziewięćset': 900
            }
            
            # Replace Polish number words with digits
            for word, value in number_words.items():
                text = text.replace(word, str(value))
            
            # Pattern to match "przelicz [amount] funtów szterlingów na jeny japońskie"
            pattern = r'przelicz\s+(\d+)\s+funtów\s+szterlingów\s+na\s+jeny\s+japońskie'
            match = re.search(pattern, text)
            
            if not match:
                # Try alternative patterns
                alt_patterns = [
                    r'przelicz\s+(\d+)\s+funtów\s+szterlingów\s+na\s+jeny',
                    r'przelicz\s+(\d+)\s+funtów\s+na\s+jeny\s+japońskie',
                    r'przelicz\s+(\d+)\s+funtów\s+szterlingów\s+na\s+jeny',
                    r'ile\s+to\s+(\d+)\s+funtów\s+szterlingów\s+w\s+jenach',
                    r'ile\s+to\s+(\d+)\s+funtów\s+w\s+jenach'
                ]
                for alt_pattern in alt_patterns:
                    match = re.search(alt_pattern, text)
                    if match:
                        break
            
            if not match:
                return {
                    'success': False,
                    'error': 'Nie rozpoznano zapytania o przeliczenie funtów szterlingów na jeny japońskie',
                    'spoken': 'Nie rozpoznano zapytania o przeliczenie funtów szterlingów na jeny japońskie'
                }
            
            amount_pounds = int(match.group(1))
            
            # Fetch current exchange rate from NBP API (Polish National Bank)
            try:
                url = "https://api.nbp.pl/api/exchangerates/rates/a/gbp/?format=json"
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    gbp_to_pln = data['rates'][0]['mid']
            except Exception:
                # Fallback: use a default rate if API fails
                gbp_to_pln = 5.30
            
            # Fetch JPY exchange rate from NBP API
            try:
                url = "https://api.nbp.pl/api/exchangerates/rates/a/jpy/?format=json"
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    jpy_to_pln = data['rates'][0]['mid']
            except Exception:
                # Fallback: use a default rate if API fails
                jpy_to_pln = 0.035
            
            # Calculate: GBP -> PLN -> JPY
            amount_pln = amount_pounds * gbp_to_pln
            amount_yen = amount_pln / jpy_to_pln
            
            # Round to 2 decimal places
            amount_yen_rounded = round(amount_yen, 2)
            
            # Prepare response
            response_text = f"{amount_pounds} funtów szterlingów to około {amount_yen_rounded} jenów japońskich."
            
            return {
                'success': True,
                'amount_pounds': amount_pounds,
                'amount_yen': amount_yen_rounded,
                'response': response_text,
                'spoken': response_text
            }
        
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'spoken': 'Wystąpił błąd podczas przeliczania walut'
            }

def execute(params: dict) -> dict:
    converter = Converter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test cases
    test_cases = [
        {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'},
        {'text': 'przelicz 500 funtów szterlingów na jeny japońskie'},
        {'text': 'ile to 2000 funtów w jenach'}
    ]
    
    for test in test_cases:
        result = execute(test)
        print(f"Input: {test['text']}")
        print(f"Result: {result}")
        print("-" * 50)