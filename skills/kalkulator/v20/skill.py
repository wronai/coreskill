import subprocess
import re
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
            expression = params.get('text', '').strip()
            if not expression:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.', 'spoken': 'Proszę podać wyrażenie do obliczenia.'}

            # Remove whitespace
            expression = expression.replace(" ", "")

            # Check for invalid characters: allow digits, +, -, *, /, ., (, )
            if not re.fullmatch(r'^[0-9+\-*/().]+$', expression):
                 return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.', 'spoken': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Check for unbalanced parentheses
            if expression.count('(') != expression.count(')'):
                return {'success': False, 'error': 'Niezrównoważone nawiasy.', 'spoken': 'Niezrównoważone nawiasy w wyrażeniu.'}
            
            # Check for invalid operator placement (basic)
            # Disallow consecutive operators (except for unary minus handled below)
            if re.search(r'[+\-*/]{2,}', expression):
                return {'success': False, 'error': 'Nieprawidłowe rozmieszczenie operatorów.', 'spoken': 'Nieprawidłowe rozmieszczenie operatorów.'}
            # Disallow operators at the start or end
            if re.search(r'^[*/]', expression) or re.search(r'[+\-*/]$', expression):
                return {'success': False, 'error': 'Operator na początku lub końcu wyrażenia.', 'spoken': 'Operator na początku lub końcu wyrażenia.'}
            # Disallow empty parentheses
            if re.search(r'\(\)', expression):
                return {'success': False, 'error': 'Puste nawiasy są niedozwolone.', 'spoken': 'Puste nawiasy są niedozwolone.'}
            
            # Handle potential unary minus at the beginning or after an opening parenthesis
            # Replace leading minus with '0-'
            if expression.startswith('-'):
                expression = '0' + expression
            # Replace minus after an opening parenthesis with '(0-'
            expression = expression.replace('(-', '(0-')

            # Use eval carefully. The sanitization above aims to reduce risks.
            # For Python 3, eval is generally safer than in older versions,
            # but still carries risks if input is not strictly controlled.
            # The regex and checks above provide a layer of security.
            result = eval(expression)

            return {'success': True, 'result': str(result), 'spoken': f'Wynik to {str(result)}'}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu.', 'spoken': 'Błąd składni w wyrażeniu.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.', 'spoken': 'Dzielenie przez zero jest niedozwolone.'}
        except Exception as e:
            # Catch any other unexpected errors
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}', 'spoken': f'Wystąpił nieoczekiwany błąd: {str(e)}'}

def execute(params: dict) -> dict:
    kalkulator_skill = Kalkulator()
    return kalkulator_skill.execute(params)

if __name__ == '__main__':
    # Test cases
    test_expressions = [
        "2 + 2",
        "10 * (5 - 3)",
        "100 / 4",
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
        "()", # Empty parentheses
        "5 * (3 + 2) / 5",
        "100 / (2 * (5 - 5))" # Division by zero within nested parentheses
    ]

    for expr in test_expressions:
        params = {'text': expr}
        result = execute(params)
        print(f"Expression: '{expr}' -> Result: {result}")

    print("\nInfo:", get_info())
    print("Health Check:", health_check())