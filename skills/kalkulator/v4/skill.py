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
            # Using eval is generally unsafe, but for a controlled environment and simple math expressions,
            # it can be used with caution. For a production system, a safer parser would be recommended.
            # We are restricting the environment for eval to only allow math functions.
            allowed_globals = {
                "__builtins__": None,
                "math": math
            }
            # Basic check for potentially harmful keywords. A more robust solution would involve AST parsing.
            disallowed_keywords = ['import', 'exec', 'eval', 'open', '__', 'os', 'sys']
            if any(keyword in expression for keyword in disallowed_keywords):
                 return {'success': False, 'error': 'Niedozwolone operacje w wyrażeniu.'}

            # Evaluate the expression
            result = eval(expression, allowed_globals)

            # Format the result for potential TTS
            if isinstance(result, (int, float)):
                spoken_result = f"Wynik to {result}"
            else:
                spoken_result = f"Wynik to {str(result)}"

            return {'success': True, 'result': result, 'spoken': spoken_result}
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
        "math.pow(2, 3)",
        "10 / 0", # Test division by zero
        "invalid syntax", # Test syntax error
        "print('hello')", # Test disallowed function
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