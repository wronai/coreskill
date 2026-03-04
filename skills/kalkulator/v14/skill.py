import subprocess
import sys

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
            expression = params.get('expression')
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

            # Bezpieczniejsze użycie eval() poprzez ograniczenie dostępnych globalnych i lokalnych zmiennych
            # Dopuszczamy tylko podstawowe funkcje matematyczne i stałe, jeśli są potrzebne
            allowed_globals = {
                "__builtins__": {
                    "abs": abs,
                    "round": round,
                    "pow": pow,
                    "max": max,
                    "min": min,
                    "sum": sum,
                    "divmod": divmod,
                    "float": float,
                    "int": int,
                    "True": True,
                    "False": False,
                    "None": None
                }
            }
            allowed_locals = {}
            result = eval(expression, allowed_globals, allowed_locals)

            # Sprawdzenie typu wyniku, aby uniknąć zwracania nieoczekiwanych typów
            if isinstance(result, (int, float, complex)):
                return {'success': True, 'result': result, 'spoken': f"Wynik to {result}"}
            else:
                return {'success': False, 'error': 'Wynik nie jest liczbą.'}

        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.', 'spoken': 'Nie można dzielić przez zero.'}
        except SyntaxError:
            return {'success': False, 'error': 'Nieprawidłowa składnia wyrażenia.', 'spoken': 'Nieprawidłowa składnia wyrażenia.'}
        except NameError as e:
            return {'success': False, 'error': f'Niedozwolona nazwa użyta w wyrażeniu: {e}', 'spoken': f'Użyto niedozwolonej nazwy: {e}'}
        except TypeError as e:
            return {'success': False, 'error': f'Nieprawidłowy typ argumentu dla operacji: {e}', 'spoken': f'Nieprawidłowy typ argumentu: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e), 'spoken': f'Wystąpił błąd: {e}'}

def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    # Test cases
    test_expressions = [
        "2 + 2",
        "10 * 5 - 3",
        "(4 + 6) / 2",
        "2 ** 3",
        "10 / 0", # Test division by zero
        "invalid expression", # Test invalid syntax
        "abs(-5)", # Test allowed function
        "math.sqrt(9)" # Test disallowed module
    ]

    for expr in test_expressions:
        print(f"Obliczanie: {expr}")
        result = execute({'expression': expr})
        print(f"Wynik: {result}\n")

    print("Test get_info():")
    print(get_info())
    print("\nTest health_check():")
    print(health_check())