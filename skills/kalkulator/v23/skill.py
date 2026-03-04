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
            expression = params.get('text', '')
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.', 'spoken': 'Brak wyrażenia do obliczenia.'}

            # Basic sanitization: allow numbers, operators, parentheses, and decimal points.
            # This is still a risky approach with eval(). A safer method would involve
            # a dedicated math expression parser.
            cleaned_expression = re.sub(r'[^-()\d/*+.\s]', '', expression)

            # Check for potentially harmful patterns (e.g., import, exec, eval)
            if re.search(r'import|exec|eval', cleaned_expression):
                return {'success': False, 'error': 'Niedozwolone słowa kluczowe w wyrażeniu.', 'spoken': 'Niedozwolone słowa kluczowe w wyrażeniu.'}

            # Use eval() cautiously.
            result = eval(cleaned_expression)

            spoken_result = f"Wynik to {result}"
            return {'success': True, 'result': str(result), 'spoken': spoken_result}

        except SyntaxError:
            return {'success': False, 'error': 'Nieprawidłowa składnia wyrażenia.', 'spoken': 'Nieprawidłowa składnia wyrażenia.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.', 'spoken': 'Dzielenie przez zero jest niedozwolone.'}
        except NameError as e:
            return {'success': False, 'error': f'Nieznany symbol w wyrażeniu: {e}', 'spoken': f'Nieznany symbol w wyrażeniu: {e}'}
        except TypeError as e:
            return {'success': False, 'error': f'Nieprawidłowy typ danych w wyrażeniu: {e}', 'spoken': f'Nieprawidłowy typ danych w wyrażeniu: {e}'}
        except Exception as e:
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
        "abc + 1", # Invalid syntax/name error
        "5 + (3 * 2)",
        "10.5 * 2",
        "sin(90)", # Example of a function not supported by basic eval
        "import os", # Malicious input
        "exec('print(1)')" # Malicious input
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