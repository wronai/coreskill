import subprocess
import sys

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v13',
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

            # Używamy eval() ostrożnie, zakładając, że dane wejściowe są zaufane
            # W rzeczywistym zastosowaniu należałoby dodać walidację lub użyć bezpieczniejszego parsera
            result = eval(expression)
            return {'success': True, 'result': result}
        except Exception as e:
            return {'success': False, 'error': str(e)}

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
        "invalid expression" # Test invalid syntax
    ]

    for expr in test_expressions:
        print(f"Obliczanie: {expr}")
        result = execute({'expression': expr})
        print(f"Wynik: {result}\n")

    print("Test get_info():")
    print(get_info())
    print("\nTest health_check():")
    print(health_check())