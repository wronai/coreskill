import random
import string
import subprocess
import re

def get_info():
    return {
        "name": "password_generator",
        "version": "v1",
        "description": "Generates secure passwords of a specified length."
    }

def health_check():
    return {"status": "ok"}

class PasswordGenerator:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            password_length = 12  # Default length

            # Try to extract length from text using regex
            match = re.search(r'\b(\d+)\b', text)
            if match:
                password_length = int(match.group(1))

            # Clamp password length to sensible limits
            if password_length < 4:
                password_length = 4
            if password_length > 128:
                password_length = 128

            characters = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(random.choice(characters) for i in range(password_length))

            return {'success': True, 'password': password, 'spoken': f"Here is your password of {password_length} characters: {password}"}

        except Exception as e:
            return {'success': False, 'error': str(e), 'spoken': "Sorry, I could not generate a password."}

def execute(params: dict) -> dict:
    generator = PasswordGenerator()
    return generator.execute(params)

if __name__ == '__main__':
    # Example usage
    print(get_info())
    print(health_check())

    test_params_default = {'text': 'generate password'}
    result_default = execute(test_params_default)
    print(f"Test with default length: {result_default}")

    test_params_short = {'text': 'generate password of 8 characters'}
    result_short = execute(test_params_short)
    print(f"Test with 8 characters: {result_short}")

    test_params_long = {'text': 'create a password with 20 symbols'}
    result_long = execute(test_params_long)
    print(f"Test with 20 characters: {result_long}")

    test_params_very_long = {'text': 'generate password 150'}
    result_very_long = execute(test_params_very_long)
    print(f"Test with 150 characters (clamped to 128): {result_very_long}")

    test_params_too_short = {'text': 'generate password 2'}
    result_too_short = execute(test_params_too_short)
    print(f"Test with 2 characters (clamped to 4): {result_too_short}")