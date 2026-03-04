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
            return {'success': False, 'error': 'Brak tekstu do przetworzenia.', 'spoken': 'Nie podałeś tekstu do obliczenia.'}

        expression = self._extract_expression(text)
        if not expression:
            return {'success': False, 'error': 'Nie można znaleźć wyrażenia matematycznego w tekście.', 'spoken': 'Nie udało mi się znaleźć wyrażenia matematycznego w Twojej wiadomości.'}

        try:
            result = self._calculate(expression)
            return {'success': True, 'result': str(result), 'spoken': f'Wynik to {str(result)}'}
        except Exception as e:
            return {'success': False, 'error': f'Błąd obliczeń: {str(e)}', 'spoken': f'Przepraszam, wystąpił błąd podczas obliczeń: {str(e)}'}

    def _extract_expression(self, text: str) -> str:
        match = re.search(r'oblicz\s*(.*)|ile\s*to\s*jest\s*(.*)|\s*(\d[\d\.\s\(\)\+\-\*\/\%]+)\s*', text, re.IGNORECASE)
        if match:
            for group in match.groups():
                if group:
                    expression = group.strip()
                    if re.search(r'\d', expression):
                        return expression
        return ""

    def _calculate(self, expression: str) -> float:
        allowed_chars = r"0-9\.\+\-\*\/\%\(\)\s"
        if not re.fullmatch(f"[{allowed_chars}]+", expression):
            raise ValueError("Wyrażenie zawiera niedozwolone znaki.")

        try:
            if not expression or not re.search(r'\d', expression):
                raise ValueError("Puste lub nieprawidłowe wyrażenie.")

            if expression.strip() and expression.strip()[-1] in '+-*/%' and not expression.strip().endswith(')'):
                raise SyntaxError("Wyrażenie kończy się operatorem.")
            
            return eval(expression, {"__builtins__": None}, {})
        except ZeroDivisionError:
            raise ZeroDivisionError("Dzielenie przez zero jest niedozwolone.")
        except SyntaxError:
            raise SyntaxError("Nieprawidłowa składnia wyrażenia.")
        except ValueError as ve:
            raise ve
        except Exception as e:
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
        {'text': 'Oblicz 10 / 4', 'expected_success': True, 'expected_result': '2.5'},
        {'text': 'Oblicz 100 / (2 * 5)', 'expected_success': True, 'expected_result': '10.0'},
        {'text': 'Oblicz 5 +', 'expected_success': False, 'expected_error': 'Wyrażenie kończy się operatorem.'},
        {'text': 'Oblicz abc', 'expected_success': False, 'expected_error': 'Wyrażenie zawiera niedozwolone znaki.'},
        {'text': '', 'expected_success': False, 'expected_error': 'Brak tekstu do przetworzenia.'},
    ]

    for case in test_cases:
        result = execute({'text': case['text']})
        print(f"Input: '{case['text']}'")
        print(f"Output: {result}")
        if case['expected_success']:
            assert result['success'] is True
            assert result['result'] == case['expected_result']
        else:
            assert result['success'] is False
            assert case['expected_error'] in result['error']
        print("-" * 20)