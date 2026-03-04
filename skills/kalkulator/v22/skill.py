import re
import subprocess

def get_info() -> dict:
    return {
        'name': 'kalkulator',
        'version': 'v22',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check() -> dict:
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        try:
            expression = params.get('text', '')
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

            # Remove any non-mathematical characters except for numbers, operators, and parentheses
            # This is a basic sanitization, more robust solutions might be needed for complex cases
            cleaned_expression = re.sub(r'[^-()\d/*+.]', '', expression)

            # Use eval() cautiously. For a production system, a safer parser would be recommended.
            # However, given the constraints (stdlib only) and the nature of the request,
            # we'll proceed with eval after basic sanitization.
            # A more secure approach would involve parsing the expression into an AST
            # and evaluating it node by node.
            result = eval(cleaned_expression)

            return {'success': True, 'result': str(result)}

        except SyntaxError:
            return {'success': False, 'error': 'Nieprawidłowa składnia wyrażenia.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.'}
        except NameError as e:
            return {'success': False, 'error': f'Nieznany symbol w wyrażeniu: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {e}'}

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
        "sin(90)" # Example of a function not supported by basic eval
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