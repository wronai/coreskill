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

            # Użycie eval z ograniczonymi globals i locals dla bezpieczeństwa
            # Dopuszczamy tylko podstawowe operacje arytmetyczne i liczby.
            # Nie dopuszczamy żadnych wbudowanych funkcji ani obiektów.
            result = eval(expression, {"__builtins__": {}}, {})

            # Sprawdzenie typu wyniku, aby upewnić się, że jest to liczba
            if not isinstance(result, (int, float)):
                return {'success': False, 'error': 'Wynik wyrażenia nie jest liczbą.'}

            return {'success': True, 'result': result}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.'}
        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu.'}
        except NameError:
            return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone nazwy.'}
        except TypeError:
            return {'success': False, 'error': 'Błąd typu w wyrażeniu.'}
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
        "2 ** 3", # Test potęgowania, które jest dozwolone przez eval
        "abs(-5)" # Test niedozwolonej funkcji
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
```