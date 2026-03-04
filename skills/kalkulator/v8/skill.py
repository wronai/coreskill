import subprocess
import sys

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v8',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check() -> dict:
    try:
        subprocess.run(['python3', '-c', 'import math'], check=True, capture_output=True)
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
            result = eval(expression, {"__builtins__": None}, {}) # Restrict access to builtins
            return {'success': True, 'result': result}
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
        "math.sqrt(16)" # Test if math module is accessible (it shouldn't be with current eval)
    ]

    print(f"Running tests for {get_info()['name']} v{get_info()['version']}")
    print(f"Health check: {health_check()}")

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
```