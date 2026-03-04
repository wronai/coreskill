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

            # Bezpieczniejsze użycie eval() poprzez ograniczenie dostępnych funkcji i modułów.
            # W tym przypadku dopuszczamy tylko podstawowe operacje arytmetyczne i liczby.
            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expression):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Dodatkowe sprawdzenie, aby uniknąć potencjalnych zagrożeń, np. podwójnych gwiazdek w nieoczekiwanych miejscach
            # lub innych niebezpiecznych konstrukcji, które mogłyby zostać zinterpretowane przez eval.
            # To jest nadal ograniczone i nie jest w 100% bezpieczne dla dowolnych danych wejściowych.
            # Dla pełnego bezpieczeństwa zalecane jest użycie dedykowanej biblioteki do parsowania wyrażeń.
            if "__" in expression:
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone sekwencje znaków.'}

            result = eval(expression, {"__builtins__": None}, {})
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
        "2 ** 3",
        "10 / 0",
        "invalid expression",
        "print('hello')", # Test niedozwolonej funkcji
        "10 / 2.5"
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