import subprocess
import re

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne.'
    }

def health_check():
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '')
        if not text:
            return {'success': False, 'error': 'Brak tekstu do przetworzenia.'}

        expression = self._extract_expression(text)
        if not expression:
            return {'success': False, 'error': 'Nie można znaleźć wyrażenia matematycznego w tekście.'}

        try:
            result = self._calculate(expression)
            return {'success': True, 'result': str(result), 'spoken': f'Wynik to {str(result)}'}
        except Exception as e:
            return {'success': False, 'error': f'Błąd obliczeń: {str(e)}', 'spoken': f'Przepraszam, wystąpił błąd podczas obliczeń: {str(e)}'}

    def _extract_expression(self, text: str) -> str:
        # This regex is more robust to capture mathematical expressions
        match = re.search(r'oblicz\s*(.*)|ile\s*to\s*jest\s*(.*)|\s*(\d[\d\.\s\(\)\+\-\*\/\%]+)\s*', text, re.IGNORECASE)
        if match:
            # Try to find the first non-empty group
            for group in match.groups():
                if group:
                    expression = group.strip()
                    # Ensure it contains at least one digit to avoid empty or operator-only matches
                    if re.search(r'\d', expression):
                        return expression
        return ""

    def _calculate(self, expression: str) -> float:
        # Enhanced allowed characters to include common math symbols and numbers
        allowed_chars = r"0-9\.\+\-\*\/\%\(\)\s"
        if not re.fullmatch(f"[{allowed_chars}]+", expression):
            raise ValueError("Wyrażenie zawiera niedozwolone znaki.")

        try:
            # Basic validation to prevent some common errors before eval
            if not expression or not re.search(r'\d', expression):
                raise ValueError("Puste lub nieprawidłowe wyrażenie.")

            # Check for operators at the end, but allow parentheses
            if expression.strip() and expression.strip()[-1] in '+-*/%' and not expression.strip().endswith(')'):
                raise SyntaxError("Wyrażenie kończy się operatorem.")
            
            # Prevent eval from executing arbitrary code by restricting builtins and globals
            # Using a limited set of safe math functions could be an alternative for more complex scenarios
            # For now, we rely on the character check and restricted eval environment.
            return eval(expression, {"__builtins__": None}, {})
        except ZeroDivisionError:
            raise ZeroDivisionError("Dzielenie przez zero jest niedozwolone.")
        except SyntaxError:
            raise SyntaxError("Nieprawidłowa składnia wyrażenia.")
        except ValueError as ve:
            raise ve
        except Exception as e:
            # Catch any other unexpected errors during eval
            raise RuntimeError(f"Nieznany błąd podczas obliczeń: {str(e)}")


def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    test_cases = [
        {'text': 'Oblicz 5 + 3 * 2', 'expected_success': True, 'expected_result': '11.0'},
        {'text': 'Ile to jest 10 / 2', 'expected_success': True, 'expected_result': '5.0'},
        {'text': 'Podaj wynik 100 - 50', 'expected_success': True, 'expected_result': '50.0'},
        {'text': 'Policz 7 % 3', 'expected_success': True, 'expected_result': '1.0'},
        {'text': 'Oblicz (5 + 3) * 2', 'expected_success': True, 'expected_result': '16.0'},
        {'text': 'Dzielenie przez zero 10 / 0', 'expected_success': False, 'expected_error': 'Dzielenie przez zero jest niedozwolone.'},
        {'text': 'Nieprawidłowa składnia 5 +*', 'expected_success': False, 'expected_error': 'Nieprawidłowa składnia wyrażenia.'},
        {'text': 'Brak wyrażenia', 'expected_success': False, 'expected_error': 'Nie można znaleźć wyrażenia matematycznego w tekście.'},
        {'text': 'Oblicz 2.5 * 4', 'expected_success': True, 'expected_result': '10.0'},
        {'text': 'Oblicz 10 / 4',