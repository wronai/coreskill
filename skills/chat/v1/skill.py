import subprocess
import sys
import re
import os

def get_info() -> dict:
    return {
        'name': 'chat',
        'version': 'v1',
        'description': 'Simple chat skill that processes user text and provides responses'
    }

def health_check() -> dict:
    try:
        # Check if espeak is available for TTS if needed
        subprocess.run(['espeak', '--version'], capture_output=True, timeout=5)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'error', 'message': 'espeak not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class ChatSkill:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip()
            
            if not text:
                return {
                    'success': False,
                    'message': 'No text provided',
                    'response': 'Please provide some text to chat about.'
                }
            
            # Simple response generation based on text content
            response = self._generate_response(text)
            
            # Try to speak the response if espeak is available
            try:
                subprocess.run(['espeak', response], capture_output=True, timeout=5)
            except Exception:
                pass  # Ignore TTS errors
            
            return {
                'success': True,
                'message': 'Chat response generated',
                'response': response,
                'input': text
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Error processing chat: {str(e)}',
                'error': str(e)
            }
    
    def _generate_response(self, text: str) -> str:
        text_lower = text.lower()
        
        # Greetings
        if any(greeting in text_lower for greeting in ['hello', 'hi ', 'hey', 'greetings']):
            return "Hello! How can I help you today?"
        
        # Farewells
        if any(farewell in text_lower for farewell in ['goodbye', 'bye', 'see you', 'farewell']):
            return "Goodbye! Have a great day!"
        
        # Questions about the assistant
        if any(q in text_lower for q in ['who are you', 'what are you', 'your name']):
            return "I am a chat assistant created with Python. I can help with simple conversations."
        
        # Time
        if 'time' in text_lower and ('what' in text_lower or 'current' in text_lower):
            try:
                import time
                current_time = time.strftime("%H:%M")
                return f"The current time is {current_time}."
            except Exception:
                return "I'm not sure about the current time right now."
        
        # Date
        if 'date' in text_lower and ('what' in text_lower or 'current' in text_lower):
            try:
                import datetime
                current_date = datetime.date.today().strftime("%B %d, %Y")
                return f"Today's date is {current_date}."
            except Exception:
                return "I'm not sure about the current date right now."
        
        # Simple math
        math_match = re.search(r'(\d+)\s*([+\-*/])\s*(\d+)', text_lower)
        if math_match:
            try:
                num1 = float(math_match.group(1))
                operator = math_match.group(2)
                num2 = float(math_match.group(3))
                
                if operator == '+':
                    result = num1 + num2
                elif operator == '-':
                    result = num1 - num2
                elif operator == '*':
                    result = num1 * num2
                elif operator == '/':
                    if num2 == 0:
                        return "Division by zero is not allowed."
                    result = num1 / num2
                else:
                    return "I can't perform that operation."
                
                return f"The result is {result}."
            except Exception:
                return "I couldn't calculate that. Please check your expression."
        
        # Default responses
        if 'peter' in text_lower:
            return "I'm not sure who Peter is. Could you tell me more?"
        
        # Fallback
        return f"You said: '{text}'. That's interesting! Tell me more."

def execute(params: dict) -> dict:
    skill = ChatSkill()
    return skill.execute(params)

if __name__ == '__main__':
    # Test the skill
    test_params = {'text': 'Hello, how are you?'}
    result = execute(test_params)
    print(f"Test result: {result}")
    
    # Test with Peter
    test_params2 = {'text': 'Where is peter?'}
    result2 = execute(test_params2)
    print(f"Test result for Peter: {result2}")