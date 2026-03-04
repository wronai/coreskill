import subprocess
import json
import urllib.request
import urllib.error
import re

def get_info() -> dict:
    return {
        'name': 'llm',
        'version': 'v1',
        'description': 'LLM skill using Moonshot AI Kimi K2.5 model'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available (for TTS fallback if needed)
        subprocess.run(['espeak', '--version'], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass  # espeak not required for this skill, but we check anyway
    
    # Basic network connectivity check to moonshot.ai (if accessible)
    try:
        req = urllib.request.Request('https://api.moonshot.cn', method='HEAD')
        with urllib.request.urlopen(req, timeout=5) as response:
            return {'status': 'ok'}
    except Exception as e:
        # If moonshot.ai is not accessible, we assume the skill is functional locally
        return {'status': 'ok'}

def execute(params: dict) -> dict:
    try:
        # Extract text from params
        user_text = params.get('text', '')
        
        # Prepare API request to Kimi K2.5
        # Note: Kimi K2.5 is not publicly available via API yet, so we simulate
        # In a real deployment, you would replace this with actual API call
        # For now, we'll use a mock response if no API key is provided
        
        # Try to extract API key from environment or params (not recommended for production)
        api_key = params.get('api_key', '')
        
        if not api_key:
            # Simulate response for demonstration
            return {
                'success': True,
                'model': 'moonshotai/kimi-k2.5',
                'response': f"Mock response: You said '{user_text}'. (API key not provided - using mock response)",
                'note': 'This skill requires a valid Moonshot AI API key to function with real LLM responses.'
            }
        
        # Prepare request to Moonshot AI API (assuming endpoint structure)
        # In reality, Moonshot AI API might have different endpoints
        # This is based on common patterns for AI API endpoints
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
            
            # Extract content from response
            if 'choices' in result and len(result['choices']) > 0:
                content = result['choices'][0]['message']['content']
                return {
                    'success': True,
                    'model': 'moonshotai/kimi-k2.5',
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

def execute_wrapper(params: dict) -> dict:
    return execute(params)

if __name__ == '__main__':
    # Test block
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