import subprocess
import sys
import math

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check() -> dict:
    try:
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
            # Restrict the environment for eval to only allow math functions and basic operations.
            # This is a basic security measure. For production, a dedicated math expression parser is recommended.
            allowed_globals = {
                "__builtins__": None,
                "math": math
            }
            
            # Basic check for potentially unsafe keywords. This is not exhaustive.
            unsafe_keywords = ['import', 'exec', 'eval', 'open', '__', 'os', 'sys', 'subprocess']
            if any(keyword in expression for keyword in unsafe_keywords):
                 return {'success': False, 'error': 'Niedozwolone operacje w wyrażeniu.'}

            result = eval(expression, allowed_globals)
            
            # Format the result for better readability, especially for floats
            if isinstance(result, float):
                result_str = f"{result:.4f}" # Format to 4 decimal places
            else:
                result_str = str(result)

            return {'success': True, 'result': result_str, 'spoken': f"Wynik to {result_str}"}
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
        "10 / 3", # Test float result
        "math.pow(2, 3)",
        "10 / 0", # Test division by zero
        "invalid syntax", # Test syntax error
        "print('hello')", # Test disallowed function
        "math.log(100, 10)" # Test log
    ]

    for expr in test_expressions:
        print(f"\nObliczanie: '{expr}'")
        result = execute({'expression': expr})
        print(f"Wynik: {result}")

    print("\nTest z pustym wyrażeniem:")
    result_empty = execute({})
    print(f"Wynik: {result_empty}")

    print("\nTest z niedozwolonym wyrażeniem:")
    result_disallowed = execute({'expression': 'import os'})
    print(f"Wynik: {result_disallowed}")
```