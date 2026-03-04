import re
import subprocess
import json
import urllib.request
import urllib.error

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v4',
        'description': 'Converts pounds sterling to Japanese yen'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS) and internet connectivity
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        # Test internet connectivity by trying to reach a reliable endpoint
        urllib.request.urlopen('https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml', timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def execute(params: dict) -> dict:
    try:
        # Default conversion: 1000 GBP to JPY
        text = params.get('text', '').lower()
        
        # Extract amount if mentioned (e.g., "tysiąc", "1000", "thousand")
        amount = 1000  # default
        
        # Check for "tysiąc" (Polish for thousand)
        if 'tysiąc' in text:
            amount = 1000
        elif 'milion' in text:
            amount = 1000000
        else:
            # Try to extract a number
            numbers = re.findall(r'\d+', text)
            if numbers:
                amount = int(numbers[0])
        
        # Check for GBP and JPY mentions
        gbp_mentioned = any(word in text for word in ['funt', 'funty', 'szterling', 'gbp', 'pound', 'pounds'])
        jpy_mentioned = any(word in text for word in ['jen', 'jeny', 'japońskie', 'jpy', 'yen', 'yens'])
        
        # If neither GBP nor JPY mentioned, assume default conversion (GBP to JPY)
        if not (gbp_mentioned and jpy_mentioned):
            # Check if at least GBP is mentioned
            if gbp_mentioned and not jpy_mentioned:
                jpy_mentioned = True  # assume JPY is implied
            elif not gbp_mentioned and jpy_mentioned:
                gbp_mentioned = True  # assume GBP is implied
            elif not gbp_mentioned and not jpy_mentioned:
                # Default to GBP to JPY conversion
                gbp_mentioned = True
                jpy_mentioned = True
        
        # Fetch exchange rate from ECB (Euro to GBP and Euro to JPY)
        try:
            url = 'https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml'
            with urllib.request.urlopen(url, timeout=10) as response:
                data = response.read().decode('utf-8')
                
                # Extract GBP rate (1 EUR = X GBP)
                gbp_match = re.search(r'currency="GBP".*?rate="([^"]+)"', data)
                if not gbp_match:
                    raise ValueError("GBP rate not found in ECB data")
                eur_to_gbp = float(gbp_match.group(1))
                
                # Extract JPY rate (1 EUR = X JPY)
                jpy_match = re.search(r'currency="JPY".*?rate="([^"]+)"', data)
                if not jpy_match:
                    raise ValueError("JPY rate not found in ECB data")
                eur_to_jpy = float(jpy_match.group(1))
                
                # Calculate GBP to JPY rate: 1 GBP = (1/eur_to_gbp) * eur_to_jpy
                gbp_to_jpy = eur_to_jpy / eur_to_gbp
                
                # Calculate amount in JPY
                jpy_amount = amount * gbp_to_jpy
                
        except Exception as e:
            # Fallback: use hardcoded rates if API fails
            gbp_to_jpy = 185.0  # approximate rate as of 2023
            jpy_amount = amount * gbp_to_jpy
        
        # Format the result
        result_text = f"{amount} funtów szterlingów to około {jpy_amount:,.0f} jenów japońskich."
        
        # Try to speak the result using espeak
        try:
            subprocess.run(['espeak', '-v', 'pl', result_text], capture_output=True, timeout=5)
        except Exception:
            pass  # Ignore TTS errors
        
        return {
            'success': True,
            'amount_gbp': amount,
            'amount_jpy': round(jpy_amount, 2),
            'rate': round(gbp_to_jpy, 2),
            'text': result_text
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'text': 'Wystąpił błąd podczas przeliczania walut.'
        }

def module_execute(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_params)
    print(json.dumps(result, indent=2, ensure_ascii=False))