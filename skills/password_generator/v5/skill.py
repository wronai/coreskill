import random
import string
import subprocess
import re

def get_info():
    return {
        'name': 'password_generator',
        'version': 'v1',
        'description': 'Generates secure passwords of a specified length.'
    }

def health_check():
    return {'status': 'ok'}

class PasswordGenerator:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            password_length = 12  # Default length

            # Try to extract length from text using regex
            match = re.search(r'\b(\d+)\b', text)
            if match:
                password_length = int(match.group(1))

            # Ensure length is within sensible bounds
            if password_length < 4:
                password_length = 4
            elif password_length > 128:
                password_length = 128

            characters = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(random.choice(characters) for i in range(password_length))

            return {'success': True, 'password': password, 'length': password_length}

        except Exception as e:
            return {'success': False, 'error': str(e)}

def execute(params: dict) -> dict:
    generator = PasswordGenerator()
    return generator.execute(params)

if __name__ == '__main__':
    # Test cases
    print("Testing password_generator skill...")

    # Test 1: Default length
    params1 = {'text': 'generate a password'}
    result1 = execute(params1)
    print(f"Test 1 (default length): {result1}")
    assert result1['success'] is True
    assert len(result1['password']) == 12

    # Test 2: Specific length
    params2 = {'text': 'generate a password of 16 characters'}
    result2 = execute(params2)
    print(f"Test 2 (specific length): {result2}")
    assert result2['success'] is True
    assert len(result2['password']) == 16
    assert result2['length'] == 16

    # Test 3: Another specific length
    params3 = {'text': 'create password 8'}
    result3 = execute(params3)
    print(f"Test 3 (another specific length): {result3}")
    assert result3['success'] is True
    assert len(result3['password']) == 8
    assert result3['length'] == 8

    # Test 4: Length too small
    params4 = {'text': 'password 2'}
    result4 = execute(params4)
    print(f"Test 4 (length too small): {result4}")
    assert result4['success'] is True
    assert len(result4['password']) == 4 # Should default to minimum
    assert result4['length'] == 4

    # Test 5: Length too large
    params5 = {'text': 'password 200'}
    result5 = execute(params5)
    print(f"Test 5 (length too large): {result5}")
    assert result5['success'] is True
    assert len(result5['password']) == 128 # Should default to maximum
    assert result5['length'] == 128

    # Test 6: No text
    params6 = {}
    result6 = execute(params6)
    print(f"Test 6 (no text): {result6}")
    assert result6['success'] is True
    assert len(result6['password']) == 12

    print("\nAll tests passed!")