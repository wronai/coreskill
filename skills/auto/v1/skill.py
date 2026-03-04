import subprocess
import re
import json
import os
import urllib.request
import urllib.error
from pathlib import Path


def get_info() -> dict:
    return {
        'name': 'auto',
        'version': 'v1',
        'description': 'Auto skill builder | Capability/Provider architecture'
    }


def health_check() -> dict:
    try:
        # Check if espeak is available for TTS
        subprocess.run(['espeak', '--version'], capture_output=True, check=True)
        return {'status': 'ok'}
    except (subprocess.CalledProcessError, FileNotFoundError):
        return {'status': 'error', 'message': 'espeak not found'}


class AutoSkillBuilder:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            if not text:
                return {
                    'success': False,
                    'error': 'No text provided'
                }

            # Try to parse as JSON first
            try:
                data = json.loads(text)
                if isinstance(data, dict):
                    # If it's a dict, use it as params
                    text = data.get('text', text)
            except json.JSONDecodeError:
                pass

            # Detect capability type from text
            capability = self._detect_capability(text)
            if capability == 'tts':
                return self._execute_tts(text)
            elif capability == 'http_get':
                return self._execute_http_get(text)
            elif capability == 'system':
                return self._execute_system(text)
            elif capability == 'file':
                return self._execute_file(text)
            else:
                return {
                    'success': False,
                    'error': 'Unknown capability detected',
                    'detected': capability
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _detect_capability(self, text: str) -> str:
        text_lower = text.lower()
        if 'speak' in text_lower or 'say' in text_lower or 'tts' in text_lower:
            return 'tts'
        elif 'http' in text_lower and ('get' in text_lower or 'request' in text_lower):
            return 'http_get'
        elif 'run' in text_lower or 'execute' in text_lower or 'cmd' in text_lower:
            return 'system'
        elif 'read' in text_lower or 'write' in text_lower or 'file' in text_lower:
            return 'file'
        else:
            return 'unknown'

    def _execute_tts(self, text: str) -> dict:
        try:
            # Extract text to speak (remove command words)
            speak_text = re.sub(r'(speak|say|tts|text|to|say|:)', '', text, flags=re.IGNORECASE).strip()
            if not speak_text:
                return {
                    'success': False,
                    'error': 'No text to speak'
                }

            # Use espeak for TTS
            result = subprocess.run(
                ['espeak', speak_text],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'text_spoken': speak_text,
                    'output': 'Audio played via espeak'
                }
            else:
                return {
                    'success': False,
                    'error': f'espeak failed: {result.stderr.decode() if result.stderr else "Unknown error"}'
                }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'TTS operation timed out'
            }
        except FileNotFoundError:
            return {
                'success': False,
                'error': 'espeak not found. Please install espeak.'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _execute_http_get(self, text: str) -> dict:
        try:
            # Extract URL from text
            url_match = re.search(r'https?://[^\s]+', text)
            if not url_match:
                return {
                    'success': False,
                    'error': 'No URL found in command'
                }
            
            url = url_match.group(0)
            
            # Perform HTTP GET request
            req = urllib.request.Request(url, headers={'User-Agent': 'AutoSkillBuilder/1.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                content = response.read().decode('utf-8', errors='ignore')
                
                # Limit content size to avoid memory issues
                max_length = 1000
                truncated_content = content[:max_length] + '...' if len(content) > max_length else content
                
                return {
                    'success': True,
                    'url': url,
                    'status_code': response.getcode(),
                    'content': truncated_content,
                    'content_length': len(content)
                }
        except urllib.error.HTTPError as e:
            return {
                'success': False,
                'error': f'HTTP error: {e.code} {e.reason}',
                'url': url if 'url' in dir() else 'unknown'
            }
        except urllib.error.URLError as e:
            return {
                'success': False,
                'error': f'URL error: {e.reason}',
                'url': url if 'url' in dir() else 'unknown'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _execute_system(self, text: str) -> dict:
        try:
            # Extract command (remove command words)
            cmd_text = re.sub(r'(run|execute|cmd|system|command|to|execute|:)', '', text, flags=re.IGNORECASE).strip()
            if not cmd_text:
                return {
                    'success': False,
                    'error': 'No command provided'
                }

            # Execute command
            result = subprocess.run(
                cmd_text,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            output = result.stdout.strip() if result.stdout else ''
            error = result.stderr.strip() if result.stderr else ''
            
            return {
                'success': result.returncode == 0,
                'command': cmd_text,
                'return_code': result.returncode,
                'stdout': output[:1000] if output else '',  # Limit output size
                'stderr': error[:500] if error else ''  # Limit error output size
            }
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'error': 'Command execution timed out'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _execute_file(self, text: str) -> dict:
        try:
            # Detect file operation
            if 'read' in text.lower() or 'open' in text.lower():
                # Extract filename
                file_match = re.search(r'(?:read|open|file)\s+["\']?([^"\'\s]+)["\']?', text, re.IGNORECASE)
                if not file_match:
                    return {
                        'success': False,
                        'error': 'No filename provided'
                    }
                
                filename = file_match.group(1)
                if not os.path.exists(filename):
                    return {
                        'success': False,
                        'error': f'File not found: {filename}'
                    }
                
                with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                max_length = 1000
                truncated_content = content[:max_length] + '...' if len(content) > max_length else content
                
                return {
                    'success': True,
                    'operation': 'read',
                    'filename': filename,
                    'content': truncated_content,
                    'content_length': len(content)
                }
            
            elif 'write' in text.lower() or 'save' in text.lower():
                # Extract filename and content
                file_match = re.search(r'(?:write|save|file)\s+["\']?([^"\'\s]+)["\']?', text, re.IGNORECASE)
                if not file_match:
                    return {
                        'success': False,
                        'error': 'No filename provided'
                    }
                
                filename = file_match.group(1)
                
                # Extract content (everything after the filename)
                content_match = re.search(r'["\']?[^"\'\s]+["\']?\s+(.+)', text)
                if not content_match:
                    return {
                        'success': False,
                        'error': 'No content provided'
                    }
                
                content = content_match.group(1)
                
                # Ensure directory exists
                Path(filename).parent.mkdir(parents=True, exist_ok=True)
                
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                return {
                    'success': True,
                    'operation': 'write',
                    'filename': filename,
                    'content_length': len(content)
                }
            
            else:
                return {
                    'success': False,
                    'error': 'Unknown file operation'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


def execute(params: dict) -> dict:
    builder = AutoSkillBuilder()
    return builder.execute(params)


if __name__ == '__main__':
    # Test the skill
    test_cases = [
        {'text': 'speak Hello world'},
        {'text': 'http://example.com'},
        {'text': 'run echo Hello'},
        {'text': 'read test.txt'},
        {'text': 'write test.txt Hello from auto skill'},
        {'text': 'unknown operation'}
    ]
    
    for test in test_cases:
        print(f"Testing: {test['text']}")
        result = execute(test)
        print(json.dumps(result, indent=2))
        print("-" * 40)