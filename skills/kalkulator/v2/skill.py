import subprocess
import sys

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v2',
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
            # Using eval is generally unsafe, but for a controlled environment and simple math expressions,
            # it can be used with caution. For a production system, a safer parser would be recommended.
            # We are restricting the environment for eval to only allow math functions.
            allowed_globals = {
                "__builtins__": None,
                "math": __import__('math')
            }
            result = eval(expression, allowed_globals)
            return {'success': True, 'result': result}
        except (SyntaxError, NameError, TypeError, ZeroDivisionError) as e:
            return {'success': False, 'error': f'Błąd składni lub wykonania: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Nieoczekiwany błąd: {e}'}

def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    print(f"Info: {get_info()}")
    print(f"Health Check: {health_check()}")

    test_expressions = [
        "2 + 2",
        "10 * 5",
        "(3 + 7) * 2",
        "10 / 2",
        "math.sqrt(16)",
        "2 ** 3",
        "10 / 0", # Test division by zero
        "invalid syntax", # Test syntax error
        "print('hello')" # Test disallowed function
    ]

    for expr in test_expressions:
        print(f"\nObliczanie: '{expr}'")
        result = execute({'expression': expr})
        print(f"Wynik: {result}")

    print("\nTest z pustym wyrażeniem:")
    result_empty = execute({})
    print(f"Wynik: {result_empty}")
```