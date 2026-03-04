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
        # Check if espeak is available for potential TTS output
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
            # This is not a foolproof security measure against all possible attacks.
            # For a truly secure solution, a dedicated math expression parser library is recommended.
            if not re.match(r'^[\d\s\+\-\*\/\(\)\.\%]+$', expression):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Restrict access to builtins and only allow safe math functions if needed.
            # For this example, we'll keep it simple and restrict builtins.
            allowed_globals = {"__builtins__": None}
            allowed_locals = {}
            result = eval(expression, allowed_globals, allowed_locals)
            
            # Check if the result is a number to avoid returning arbitrary objects
            if isinstance(result, (int, float, complex)):
                # Prepare spoken output
                spoken_result = f"Wynik to {result}"
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
        "2 ** 3", # Test exponentiation
        "10 / 2.5",
        "10 % 3" # Test modulo
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
    else:
        print("Skipping tests due to health check failure.")