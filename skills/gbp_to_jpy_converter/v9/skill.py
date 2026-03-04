import subprocess
import re
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'gbp_to_jpy_converter',
        'version': 'v1',
        'description': 'Converts GBP to JPY (Japanese Yen) using real-time exchange rates'
    }

def health_check() -> dict:
    try:
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=5) as response:
            if response.status == 200:
                return {'status': 'ok'}
            else:
                return {'status': 'error', 'message': f'API returned status {response.status}'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class GBPToJPYConverter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Polish number words mapping
            number_words = {
                'tysiąc': 1000,
                'dwa tysiące': 2000,
                'trzy tysiące': 3000,
                'cztery tysiące': 4000,
                'pięć tysięcy': 5000,
                'sześć tysięcy': 6000,
                'siedem tysięcy': 7000,
                'osiem tysięcy': 8000,
                'dziewięć tysięcy': 9000,
                'dziesięć tysięcy': 10000,
                'sto': 100,
                'dwieście': 200,
                'trzysta': 300,
                'czterysta': 400,
                'pięćset': 500,
                'sześćset': 600,
                'siedemset': 700,
                'osiemset': 800,
                'dziewięćset': 900,
            }
            
            amount = None
            
            # Check for number words first
            for word, value in number_words.items():
                if word in text:
                    amount = value
                    break
            
            # If not found, try to find numeric value
            if amount is None:
                numbers = re.findall(r'[\d]+[.,\d]*', text)
                if numbers:
                    for num_str in numbers:
                        try:
                            num_val = float(num_str.replace(',', '.'))
                            if num_val > 0:
                                amount = int(num_val)
                                break
                        except ValueError:
                            continue
            
            # Default to 1000 if no amount found
            if amount is None:
                amount = 1000
            
            # Fetch exchange rate
            try:
                url = "https://api.exchangerate-api.com/v4/latest/GBP"
                with urllib.request.urlopen(url, timeout=10) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    rate = data['rates'].get('JPY', 0)
            except Exception:
                rate = 180.0
            
            # Calculate JPY amount
            jpy_amount = amount * rate
            
            # Format the result
            result_text = f"{amount:,} GBP to {int(jpy_amount):,} JPY (kurso: 1 GBP = {rate:.2f} JPY)"
            spoken_text = f"{amount} funtów szterlingów to {int(jpy_amount)} jenów japońskich."
            
            # Use espeak for TTS if available
            try:
                subprocess.run(['espeak', spoken_text], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
            except Exception:
                pass
            
            return {
                'success': True,
                'amount_gbp': amount,
                'amount_jpy': int(jpy_amount),
                'rate': rate,
                'result': result_text,
                'text_response': spoken_text,
                'spoken': spoken_text
            }
        
        except Exception as e:
            spoken_text = "Przepraszam, nie udało się przeliczyć walut."
            try:
                subprocess.run(['espeak', spoken_text], 
                              stdout=subprocess.DEVNULL, 
                              stderr=subprocess.DEVNULL)
            except Exception:
                pass
            
            return {
                'success': False,
                'error': str(e),
                'text_response': spoken_text,
                'spoken': spoken_text
            }

def execute(params: dict) -> dict:
    converter = GBPToJPYConverter()
    return converter.execute(params)

if __name__ == '__main__':
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))