import subprocess
import sys
import re

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check() -> dict:
    try:
        subprocess.run(['espeak', '--version'], check=True, capture_output=True)
        return {'status': 'ok'}
    except FileNotFoundError:
        return {'status': 'error', 'message': 'espeak not found'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        expression = params.get('expression')
        if not expression:
            return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

        try:
            # Basic sanitization to prevent obvious code injection attempts
            # Allowed characters: digits, whitespace, +, -, *, /, (, ), ., %, ^ (for power)
            if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%\^\,]+$', expression):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Replace ^ with ** for exponentiation
            expression = expression.replace('^', '**')

            # Restrict access to builtins and only allow safe math functions if needed.
            # For this example, we'll keep it simple and restrict builtins.
            # eval is generally unsafe, but with the regex and restricted globals/locals,
            # it's made slightly safer for this specific use case.
            allowed_globals = {"__builtins__": None}
            allowed_locals = {}
            result = eval(expression, allowed_globals, allowed_locals)
            
            # Check if the result is a number to avoid returning arbitrary objects
            if isinstance(result, (int, float, complex)):
                # Prepare spoken output
                # Use Polish number formatting for spoken output if possible, otherwise default
                try:
                    # Attempt to format as integer if it's a whole number
                    if result == int(result):
                        spoken_result = f"Wynik to {int(result)}"
                    else:
                        spoken_result = f"Wynik to {result:.2f}" # Format to 2 decimal places
                except:
                    spoken_result = f"Wynik to {result}" # Fallback

                return {'success': True, 'result': result, 'spoken': spoken_result}
            else:
                return {'success': False, 'error': 'Wyrażenie zwróciło nieoczekiwany typ wyniku.'}
                
        except (SyntaxError, NameError, TypeError, ZeroDivisionError) as e:
            return {'success': False, 'error': f'Błąd składni lub wykonania: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Nieoczekiwany błąd: {e}'}

def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    # Test cases
    test_expressions = [
        "2 + 2",
        "10 * 5 / 2",
        "(3 + 7) * (10 - 5)",
        "10 / 0", # Test division by zero
        "10 / 2.5",
        "10 % 3", # Test modulo
        "2^3", # Test power operator
        "100 / 7",
        "5 + 3 * 2",
        "(5 + 3) * 2"
    ]

    print(f"Running tests for {get_info()['name']} v{get_info()['version']}")
    health_status = health_check()
    print(f"Health check: {health_status}")

    if health_status['status'] == 'ok':
        for expr in test_expressions:
            print(f"\nCalculating: {expr}")
            params = {'expression': expr}
            result = execute(params)
            print(f"Result: {result}")
            if result.get('success') and 'spoken' in result:
                try:
                    subprocess.run(['espeak', result['spoken']], check=True)
                except Exception as e:
                    print(f"Error during TTS: {e}")

        # Test with missing expression
        print("\nTesting with missing expression:")
        params_missing = {}
        result_missing = execute(params_missing)
        print(f"Result: {result_missing}")

        # Test with disallowed characters
        print("\nTesting with disallowed characters:")
        params_disallowed = {'expression': "import os"}
        result_disallowed = execute(params_disallowed)
        print(f"Result: {result_disallowed}")

        # Test with disallowed characters in a more complex expression
        print("\nTesting with disallowed characters in complex expression:")
        params_disallowed_complex = {'expression': "2 + print('hello')"}
        result_disallowed_complex = execute(params_disallowed_complex)
        print(f"Result: {result_disallowed_complex}")
    else:
        print("Skipping tests due to health check failure.")