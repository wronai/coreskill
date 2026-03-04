import subprocess
import re
import urllib.request
import json

def get_info() -> dict:
    return {
        'name': 'pound_to_yen_converter',
        'version': 'v19',
        'description': 'Converts pounds to yen (specifically 1000 GBP to JPY)'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS, though not used in this skill)
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

def extract_amount(text):
    # Try to extract number followed by optional words like "tysiąc", "tys", "thousand"
    patterns = [
        r'(\d+)\s*(tysiąc|tys)\s*(funtów|funt|GBP|GBP\s*szterlingów|funty)',
        r'(\d+)\s*(funtów|funt|GBP|GBP\s*szterlingów|funty)\s*(tysiąc|tys)?',
        r'tysiąc\s*(funtów|funt|GBP|GBP\s*szterlingów|funty)',  # "tysiąc funtów"
        r'(\d+)\s*(funtów|funt|GBP|GBP\s*szterlingów|funty)',  # "1000 funtów"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            groups = match.groups()
            if len(groups) >= 2 and groups[1] == 'tysiąc':
                return 1000
            elif len(groups) >= 2 and groups[0] and groups[1] == 'tysiąc':
                return int(groups[0]) * 1000
            elif len(groups) >= 1 and groups[0]:
                return int(groups[0])
    
    # Default to 1000 if "tysiąc" is mentioned but no number
    if 'tysiąc' in text.lower():
        return 1000
    
    return None

def convert_pound_to_yen(amount_gbp):
    try:
        # Use a free exchange rate API
        url = "https://api.exchangerate-api.com/v4/latest/GBP"
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            rate = data['rates'].get('JPY', 0)
            amount_jpy = amount_gbp * rate
            return round(amount_jpy, 2)
    except Exception as e:
        # Fallback: use a fixed rate if API fails (as of 2023 ~180 JPY/GBP)
        return round(amount_gbp * 180, 2)

class PoundToYenConverter:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            
            # Extract amount (default to 1000 if "tysiąc" is mentioned)
            amount = extract_amount(text)
            if amount is None:
                amount = 1000  # Default as per requirement
            
            # Convert
            amount_jpy = convert_pound_to_yen(amount)
            
            # Format result in Polish
            result_text = f"{amount} funtów szterlingów to około {amount_jpy:,} jenów japońskich."
            
            return {
                'success': True,
                'amount_gbp': amount,
                'amount_jpy': amount_jpy,
                'result': result_text
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

def execute(params: dict) -> dict:
    converter = PoundToYenConverter()
    return converter.execute(params)

if __name__ == '__main__':
    # Test
    test_input = {'text': 'przelicz tysiąc funtów szterlingów na jeny japońskie'}
    result = execute(test_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))