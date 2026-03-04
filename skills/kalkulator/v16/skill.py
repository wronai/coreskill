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
    test_expressions = [
        "2 + 2",
        "10 * 5 - 3",
        "(4 + 6) / 2",
        "2 ** 3",
        "10 / 0",
        "invalid expression",
        "abs(-5)",
        "math.sqrt(9)"
    ]

    for expr in test_expressions:
        print(f"Obliczanie: {expr}")
        result = execute({'expression': expr})
        print(f"Wynik: {result}\n")

    print("Test get_info():")
    print(get_info())
    print("\nTest health_check():")
    print(health_check())

    print("Test user query: a ile to 100 / 7?")
    user_query = "a ile to 100 / 7?"
    # Simple parsing to extract the mathematical expression
    expression_to_calculate = None
    parts = user_query.split(" ile to ")
    if len(parts) > 1:
        expression_to_calculate = parts[1].strip('?')

    if expression_to_calculate:
        print(f"Wyrażenie do obliczenia: {expression_to_calculate}")
        result = execute({'expression': expression_to_calculate})
        print(f"Wynik: {result}\n")
    else:
        print("Nie udało się wyodrębnić wyrażenia matematycznego z zapytania.")