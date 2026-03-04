import subprocess
import re

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v17',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check():
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        try:
            expression = params.get('text', '')
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

            # Remove any non-mathematical characters except for numbers, operators, and parentheses
            # This is a basic sanitization, more robust parsing might be needed for complex cases
            cleaned_expression = re.sub(r'[^-()\d/*+.]', '', expression)

            # Use eval carefully, as it can be a security risk if the input is not trusted.
            # For this skill, we assume the input is from a trusted source or sufficiently sanitized.
            result = eval(cleaned_expression)

            return {'success': True, 'result': str(result)}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.'}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}'}

def execute(params: dict) -> dict:
    kalkulator_skill = Kalkulator()
    return kalkulator_skill.execute(params)

if __name__ == '__main__':
    # Test cases
    test_expressions = [
        "2 + 2",
        "10 * (5 - 3)",
        "100 / 4",
        "5 ** 2",
        "10 / 0", # Test division by zero
        "abc + 5", # Test invalid syntax
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "10.5 * 2",
        "2 +", # Test incomplete expression
        "", # Test empty input
        "2 + (3 * 4) - 1"
    ]

    for expr in test_expressions:
        params = {'text': expr}
        result = execute(params)
        print(f"Expression: '{expr}' -> Result: {result}")

    print("\nInfo:", get_info())
    print("Health Check:", health_check())
```