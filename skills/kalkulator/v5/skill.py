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
            allowed_globals = {
                "__builtins__": None,
                "math": math
            }
            
            unsafe_keywords = ['import', 'exec', 'eval', 'open', '__', 'os', 'sys', 'subprocess', 'from']
            if any(keyword in expression for keyword in unsafe_keywords):
                 return {'success': False, 'error': 'Niedozwolone operacje w wyrażeniu.'}

            # Basic check for function calls that are not in math
            if '(' in expression and ')' in expression:
                function_calls = [call.split('(')[0] for call in expression.split() if '(' in call and ')' in call]
                for call in function_calls:
                    if call not in ['math.sqrt', 'math.pow', 'math.log', 'math.sin', 'math.cos', 'math.tan', 'math.floor', 'math.ceil', 'math.fabs', 'math.degrees', 'math.radians']: # Add more safe math functions if needed
                        return {'success': False, 'error': f'Niedozwolana funkcja: {call}'}

            result = eval(expression, allowed_globals)
            
            if isinstance(result, float):
                result_str = f"{result:.4f}"
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
        "10 / 3",
        "math.pow(2, 3)",
        "10 / 0",
        "invalid syntax",
        "print('hello')",
        "math.log(100, 10)",
        "math.sin(math.radians(90))"
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

    print("\nTest z niedozwolonym wywołaniem funkcji:")
    result_disallowed_func = execute({'expression': 'open("file.txt")'})
    print(f"Wynik: {result_disallowed_func}")
```