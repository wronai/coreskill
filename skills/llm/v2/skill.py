import subprocess
import json
import urllib.request
import urllib.error
import re
import os

class LLM:
    def execute(self, params: dict) -> dict:
        try:
            user_text = params.get('text', '')
            
            api_key = params.get('api_key', '') or os.environ.get('MOONSHOT_API_KEY', '')
            openrouter_key_present = bool(os.environ.get('OPENROUTER_API_KEY', ''))

            if not api_key:
                hint = ""
                if openrouter_key_present:
                    hint = " Wykryłem OPENROUTER_API_KEY, ale ten skill wymaga MOONSHOT_API_KEY (to inny provider)."
                return {
                    'success': False,
                    'error': "Brak MOONSHOT_API_KEY — nie mogę wykonać realnego zapytania do Moonshot API." + hint,
                    'note': "Ustaw zmienną środowiskową MOONSHOT_API_KEY albo podaj params['api_key']. Jeśli chcesz tylko przełączyć model evo-engine, użyj komendy /config llm model <nazwa_modelu>."
                }
            
            url = 'https://api.moonshot.cn/v1/chat/completions'
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            
            data = {
                'model': 'kimi-k2.5',
                'messages': [
                    {'role': 'user', 'content': user_text}
                ]
            }
            
            req_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=30) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    return {
                        'success': True,
                        'model': 'moonshotai/kimi-k2.5',
                        'response': content,
                        'spoken': content,
                        'raw_response': result
                    }
                else:
                    return {
                        'success': False,
                        'error': 'Invalid API response format',
                        'raw_response': result
                    }
                    
        except urllib.error.HTTPError as e:
            error_body = e.read().decode('utf-8')
            return {
                'success': False,
                'error': f'HTTP error {e.code}: {e.reason}',
                'details': error_body
            }
        except urllib.error.URLError as e:
            return {
                'success': False,
                'error': f'Network error: {str(e.reason)}'
            }
        except json.JSONDecodeError as e:
            return {
                'success': False,
                'error': 'Failed to parse API response as JSON',
                'details': str(e)
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unexpected error: {str(e)}'
            }

def get_info() -> dict:
    return {
        'name': 'llm',
        'version': 'v1',
        'description': 'LLM skill using Moonshot AI Kimi K2.5 model'
    }

def health_check() -> dict:
    try:
        subprocess.run(['espeak', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    
    try:
        req = urllib.request.Request('https://api.moonshot.cn', method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            return {'status': 'ok'}
    except Exception:
        return {'status': 'ok'}

def execute(params: dict) -> dict:
    return LLM().execute(params)

if __name__ == '__main__':
    import sys
    
    test_input = {'text': 'Hello, how are you?'}
    
    if len(sys.argv) > 1:
        test_input['text'] = ' '.join(sys.argv[1:])
    
    health = health_check()
    print(f"Health check: {json.dumps(health, indent=2)}")
    
    result = execute(test_input)
    print(f"Execute result: {json.dumps(result, indent=2)}")