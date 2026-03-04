import subprocess
import re

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
            expression = params.get('text', '')
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

            # Basic sanitization: allow numbers, operators, parentheses, and decimal points.
            # This regex is more restrictive to prevent potential injection.
            # It allows: digits, +, -, *, /, ., (, )
            # It disallows: letters, other symbols.
            # It also ensures that operators are not at the beginning or end,
            # and that there are no consecutive operators (except for unary minus).
            # This is still a simplified approach and a full parser would be more robust.
            
            # Remove whitespace
            expression = expression.replace(" ", "")

            # Check for invalid characters
            if not re.fullmatch(r'^[0-9+\-*/().]+$', expression):
                 return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Further validation for syntax (simplified)
            # Check for unbalanced parentheses
            if expression.count('(') != expression.count(')'):
                return {'success': False, 'error': 'Niezrównoważone nawiasy.'}
            
            # Check for invalid operator placement (basic)
            if re.search(r'[+\-*/]{2,}', expression) or \
               re.search(r'^[*/]', expression) or \
               re.search(r'[+\-*/]$', expression) or \
               re.search(r'\(\)', expression):
                return {'success': False, 'error': 'Nieprawidłowe rozmieszczenie operatorów lub puste nawiasy.'}
            
            # Handle potential unary minus at the beginning or after an opening parenthesis
            expression = re.sub(r'^-', '0-', expression) # Replace leading minus with 0-
            expression = re.sub(r'\(-', '(0-', expression) # Replace minus after ( with (0-

            # Use eval carefully. The sanitization above aims to reduce risks.
            result = eval(expression)

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
        "5 ** 2", # Note: eval supports **, but the regex might need adjustment if ** is not desired. Keeping it for now.
        "10 / 0", # Test division by zero
        "abc + 5", # Test invalid characters
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "10.5 * 2",
        "2 +", # Test incomplete expression (invalid operator at end)
        "", # Test empty input
        "2 + (3 * 4) - 1",
        "-5 + 10", # Test unary minus at start
        "10 * (-2 + 5)", # Test unary minus in parenthesis
        "10 / (2 * 0)", # Test division by zero within expression
        "((2+3)*4)", # Nested parentheses
        "2 + 3)", # Unbalanced parentheses
        "(2 + 3", # Unbalanced parentheses
        "2 ++ 3", # Consecutive operators
        "2 * / 3", # Consecutive operators
        "()" # Empty parentheses
    ]

    for expr in test_expressions:
        params = {'text': expr}
        result = execute(params)
        print(f"Expression: '{expr}' -> Result: {result}")

    print("\nInfo:", get_info())
    print("Health Check:", health_check())
```