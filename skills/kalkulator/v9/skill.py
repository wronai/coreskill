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
        # Check if python3 is available and can import math
        subprocess.run([sys.executable, '-c', 'import math'], check=True, capture_output=True)
        return {'status': 'ok'}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        expression = params.get('expression')
        if not expression:
            return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

        try:
            # Using eval is generally unsafe, but for a controlled environment like this
            # and with the assumption that input is from a trusted source or sanitized,
            # it's the most straightforward way to evaluate mathematical expressions.
            # In a real-world application, a safer parsing library would be preferred.
            # Restrict access to builtins and only allow safe math functions if needed.
            # For this example, we'll keep it simple and restrict builtins.
            allowed_globals = {"__builtins__": None}
            allowed_locals = {}
            result = eval(expression, allowed_globals, allowed_locals)
            
            # Check if the result is a number to avoid returning arbitrary objects
            if isinstance(result, (int, float, complex)):
                return {'success': True, 'result': result}
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
        "abs(-5)", # Test a safe built-in if allowed (not allowed with __builtins__: None)
        "print('hello')", # Test disallowed operation
        "10 / 2.5"
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

        # Test with missing expression
        print("\nTesting with missing expression:")
        params_missing = {}
        result_missing = execute(params_missing)
        print(f"Result: {result_missing}")
    else:
        print("Skipping tests due to health check failure.")