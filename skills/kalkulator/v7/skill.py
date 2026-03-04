import subprocess
import sys

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check():
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        try:
            expression = params.get('expression')
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expression):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            if "__" in expression:
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone sekwencje znaków.'}

            # Używamy eval z ograniczonym zakresem, aby zminimalizować ryzyko.
            # Dopuszczamy tylko podstawowe operacje i liczby.
            # Dla pełnego bezpieczeństwa zalecane jest użycie dedykowanej biblioteki do parsowania wyrażeń.
            result = eval(expression, {"__builtins__": {}}, {})
            return {'success': True, 'result': result}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.'}
        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu.'}
        except NameError:
            return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone nazwy.'}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}'}

def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    test_expressions = [
        "2 + 2",
        "10 * 5 - 3",
        "(4 + 6) / 2",
        "10 / 2.5",
        "10 / 0",
        "invalid expression",
        "print('hello')",
        "2 ** 3" # Poprawiono błąd składniowy w tym miejscu
    ]

    print(f"Running Kalkulator skill tests (Version: {get_info()['version']})...")

    for expr in test_expressions:
        params = {'expression': expr}
        result = execute(params)
        print(f"Expression: '{expr}' -> Result: {result}")

    print("\nHealth Check:")
    print(health_check())

    print("\nInfo:")
    print(get_info())