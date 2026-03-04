import random
import string
import subprocess

def get_info() -> dict:
    return {
        'name': 'password_generator',
        'version': 'v3',
        'description': 'Generates secure passwords of a specified length.'
    }

def health_check() -> dict:
    return {'status': 'ok'}

class PasswordGenerator:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').lower()
            length = 12  # Default length

            words = text.split()
            for i, word in enumerate(words):
                if word.isdigit():
                    length = int(word)
                    break
                elif word.startswith("długość") and i + 1 < len(words) and words[i+1].isdigit():
                    length = int(words[i+1])
                    break
                elif word.startswith("length") and i + 1 < len(words) and words[i+1].isdigit():
                    length = int(words[i+1])
                    break

            if length < 4:
                return {'success': False, 'message': 'Password length must be at least 4.'}
            if length > 128:
                return {'success': False, 'message': 'Password length cannot exceed 128.'}

            characters = string.ascii_letters + string.digits + string.punctuation
            password = ''.join(random.choice(characters) for i in range(length))

            return {'success': True, 'password': password}

        except Exception as e:
            return {'success': False, 'message': str(e)}

def execute(params: dict) -> dict:
    generator = PasswordGenerator()
    return generator.execute(params)

if __name__ == '__main__':
    # Example usage
    print(get_info())
    print(health_check())

    test_params1 = {'text': 'generate a password of 16 characters'}
    result1 = execute(test_params1)
    print(f"Test 1: {result1}")

    test_params2 = {'text': 'stwórz hasło o długości 8'}
    result2 = execute(test_params2)
    print(f"Test 2: {result2}")

    test_params3 = {'text': 'password length 20'}
    result3 = execute(test_params3)
    print(f"Test 3: {result3}")

    test_params4 = {'text': 'generate a password'} # default length
    result4 = execute(test_params4)
    print(f"Test 4: {result4}")

    test_params5 = {'text': 'password length 2'} # too short
    result5 = execute(test_params5)
    print(f"Test 5: {result5}")

    test_params6 = {'text': 'password length 200'} # too long
    result6 = execute(test_params6)
    print(f"Test 6: {result6}")