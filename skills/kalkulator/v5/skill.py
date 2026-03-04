import subprocess
import sys

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v5',
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

            # Używamy eval() ostrożnie, zakładając, że dane wejściowe są zaufane lub odpowiednio oczyszczone.
            # W bardziej złożonych scenariuszach rozważ użycie bibliotek do bezpiecznego parsowania wyrażeń.
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

    print(f"Running Kalkulator skill tests (Version: {get_info()['version']})...")

    for expr in test_expressions:
        params = {'expression': expr}
        result = execute(params)
        print(f"Expression: '{expr}' -> Result: {result}")

    print("\nHealth Check:")
    print(health_check())

    print("\nInfo:")
    print(get_info())