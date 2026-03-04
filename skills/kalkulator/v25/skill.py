import re
import subprocess

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check() -> dict:
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        try:
            expression = params.get('text', '').strip()
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.', 'spoken': 'Brak wyrażenia do obliczenia.'}

            # More robust sanitization: allow numbers, operators, parentheses, decimal points, and whitespace.
            # This regex specifically targets characters that are NOT allowed.
            # Allowed: 0-9, ., +, -, *, /, (, ), whitespace
            if re.search(r'[^0-9\.\+\-\*\/\(\)\s]', expression):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.', 'spoken': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Prevent execution of potentially harmful commands by checking for keywords
            # that might be used in conjunction with eval or other execution methods.
            # This is a basic safeguard; a full parser would be more secure.
            if re.search(r'\b(import|exec|eval|__\w+__)\b', expression):
                return {'success': False, 'error': 'Niedozwolone słowa kluczowe w wyrażeniu.', 'spoken': 'Niedozwolone słowa kluczowe w wyrażeniu.'}

            # Use eval() cautiously. It's still a security risk if sanitization is not perfect.
            # For a production system, a dedicated math expression parser library would be safer.
            result = eval(expression)

            # Format the result for spoken output
            if isinstance(result, float):
                spoken_result = f"Wynik to {result:.2f}"
            else:
                spoken_result = f"Wynik to {result}"

            return {'success': True, 'result': str(result), 'spoken': spoken_result}

        except SyntaxError:
            return {'success': False, 'error': 'Nieprawidłowa składnia wyrażenia.', 'spoken': 'Nieprawidłowa składnia wyrażenia.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.', 'spoken': 'Dzielenie przez zero jest niedozwolone.'}
        except NameError as e:
            # Catching NameError is important for cases like 'sin(90)' if sin is not defined.
            return {'success': False, 'error': f'Nieznany symbol w wyrażeniu: {e}', 'spoken': f'Nieznany symbol w wyrażeniu: {e}'}
        except TypeError as e:
            return {'success': False, 'error': f'Nieprawidłowy typ danych w wyrażeniu: {e}', 'spoken': f'Nieprawidłowy typ danych w wyrażeniu: {e}'}
        except Exception as e:
            # Catch all other unexpected errors
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {e}', 'spoken': f'Wystąpił nieoczekiwany błąd: {e}'}

def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    # Test cases
    test_expressions = [
        "1 + 1",
        "10 * (5 - 2)",
        "100 / 4",
        "2 ** 3",
        "10 / 0", # Zero division
        "abc + 1", # Name error
        "5 + (3 * 2)",
        "10.5 * 2",
        "sin(90)", # Name error (sin is not defined in basic eval)
        "import os", # Malicious input (should be caught by regex)
        "exec('print(1)')", # Malicious input (should be caught by regex)
        "10 + 'a'", # Type error
        "", # Empty input
        "  ", # Whitespace input
        "10 + 5.5",
        "100 / (2 * 5)"
    ]

    print("Running Kalkulator tests:")
    for expr in test_expressions:
        params = {'text': expr}
        result = execute(params)
        print(f"Expression: '{expr}' -> Result: {result}")

    print("\nTesting get_info():")
    print(get_info())

    print("\nTesting health_check():")
    print(health_check())
```