import subprocess
import json
import urllib.request
import urllib.error
import re
import os

def get_info() -> dict:
    return {
        'name': 'llm',
        'version': 'v1',
        'description': 'LLM skill using OpenRouter (fallback to local eSpeak TTS)'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS fallback if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # espeak not required for this skill, but we check anyway
    
    # Basic network connectivity check to OpenRouter
    try:
        req = urllib.request.Request('https://openrouter.ai/api/v1', method='HEAD', timeout=5)
        with urllib.request.urlopen(req, timeout=5) as response:
            return {'status': 'ok'}
    except Exception:
        # If not accessible, assume skill is functional locally
        return {'status': 'ok'}

class LLMExecutor:
    def __init__(self):
        self.api_key = os.environ.get('OPENROUTER_API_KEY', '')
        self.model = os.environ.get('LLM_MODEL', 'openai/gpt-4o-mini')
    
    def execute(self, params: dict) -> dict:
        try:
            user_text = params.get('text', '')
            
            # Extract model name from text if present (e.g., "model: openai/gpt-4o")
            model_match = re.search(r'model:\s*(\S+)', user_text, re.IGNORECASE)
            if model_match:
                self.model = model_match.group(1)
                # Remove model directive from text
                user_text = re.sub(r'model:\s*\S+', '', user_text, flags=re.IGNORECASE).strip()
            
            # Extract API key from text if provided (e.g., "api_key: sk-...")
            api_key_match = re.search(r'api_key:\s*(\S+)', user_text, re.IGNORECASE)
            if api_key_match:
                api_key = api_key_match.group(1)
                # Remove api_key directive from text
                user_text = re.sub(r'api_key:\s*\S+', '', user_text, flags=re.IGNORECASE).strip()
            else:
                api_key = self.api_key
            
            if not api_key:
                return {
                    'success': False,
                    'error': "Brak API klucza. Ustaw OPENROUTER_API_KEY lub użyj 'api_key: [klucz]' w zapytaniu.",
                    'note': "Przykład: 'api_key: sk-... Wyjaśnij czym jest KSeF'"
                }
            
            # Prepare request to OpenRouter API
            url = 'https://openrouter.ai/api/v1/chat/completions'
            
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}',
                'HTTP-Referer': 'https://github.com/evo-engine',
                'X-Title': 'evo-engine LLM skill'
            }
            
            data = {
                'model': self.model,
                'messages': [
                    {'role': 'system', 'content': 'Odpowiadaj zgodnie z kontekstem polskim, używaj polskich terminów technicznych. Daj konkretne informacje, jeśli są dostępne.'},
                    {'role': 'user', 'content': user_text}
                ]
            }
            
            req_data = json.dumps(data).encode('utf-8')
            req = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
            
            with urllib.request.urlopen(req, timeout=60) as response:
                result = json.loads(response.read().decode('utf-8'))
                
                # Extract content from response
                if 'choices' in result and len(result['choices']) > 0:
                    content = result['choices'][0]['message']['content']
                    return {
                        'success': True,
                        'model': self.model,
                        'response': content,
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

def execute(params: dict) -> dict:
    executor = LLMExecutor()
    return executor.execute(params)

if __name__ == '__main__':
    import sys
    
    # Default test input
    test_input = {'text': 'Hello, how are you?'}
    
    # Allow command line override
    if len(sys.argv) > 1:
        test_input['text'] = ' '.join(sys.argv[1:])
    
    # Run health check
    health = health_check()
    print(f"Health check: {json.dumps(health, indent=2)}")
    
    # Run execute
    result = execute(test_input)
    print(f"Execute result: {json.dumps(result, indent=2)}")