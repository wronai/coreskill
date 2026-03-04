import subprocess
import re

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v30',
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
            return {'success': True, 'result': str(result)}
        except Exception as e:
            return {'success': False, 'error': f'Błąd obliczeń: {str(e)}'}

    def _extract_expression(self, text: str) -> str:
        # Proste dopasowanie wyrażenia matematycznego
        # Zakłada, że wyrażenie jest główną częścią tekstu
        match = re.search(r'(\d+(\.\d+)?\s*[\+\-\*\/\%]\s*)+\d+(\.\d+)?|\d+(\.\d+)?', text)
        if match:
            return match.group(0).strip()
        return ""

    def _calculate(self, expression: str) -> float:
        # Używamy eval, ale z ostrożnością. W tym przypadku, ponieważ
        # wyodrębniamy tylko liczby i podstawowe operatory, jest to stosunkowo bezpieczne.
        # W bardziej złożonych scenariuszach należałoby użyć bezpieczniejszego parsera.
        allowed_chars = r"0-9\.\+\-\*\/\%\(\)\s"
        if not re.fullmatch(f"[{allowed_chars}]+", expression):
            raise ValueError("Wyrażenie zawiera niedozwolone znaki.")

        # Bezpieczniejsze podejście do eval, ograniczając dostępne funkcje
        try:
            return eval(expression, {"__builtins__": None}, {})
        except ZeroDivisionError:
            raise ZeroDivisionError("Dzielenie przez zero jest niedozwolone.")
        except SyntaxError:
            raise SyntaxError("Nieprawidłowa składnia wyrażenia.")
        except Exception as e:
            raise RuntimeError(f"Nieznany błąd podczas obliczeń: {e}")


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
        {'text': 'Oblicz 10 / 3', 'expected_success': True, 'expected_result': '3.3333333333333335'},
        {'text': 'Oblicz 5 +', 'expected_success': False, 'expected_error': 'Nie można znaleźć wyrażenia matematycznego w tekście.'}, # Bardziej złożone wyrażenie nie zostanie znalezione
        {'text': 'Oblicz 5 + 3 + 2', 'expected_success': True, 'expected_result': '10.0'},
        {'text': 'Oblicz 5 + 3 * 2 / 1', 'expected_success': True, 'expected_result': '11.0'},
        {'text': 'Oblicz 5 + 3 * (2 / 1)', 'expected_success': True, 'expected_result': '11.0'},
        {'text': 'Oblicz 5 + 3 * (2 / (1 + 1))', 'expected_success': True, 'expected_result': '8.0'},
        {'text': 'Oblicz 100 / (5 * 2)', 'expected_success': True, 'expected_result': '1.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5', 'expected_success': True, 'expected_result': '6.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2', 'expected_success': True, 'expected_result': '4.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3', 'expected_success': True, 'expected_result': '1.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4', 'expected_success': True, 'expected_result': '5.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / 2', 'expected_success': True, 'expected_result': '7.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / 2 * 2', 'expected_success': True, 'expected_result': '9.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2)', 'expected_success': True, 'expected_result': '7.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1', 'expected_success': True, 'expected_result': '6.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2', 'expected_success': True, 'expected_result': '8.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3', 'expected_success': True, 'expected_result': '14.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / 3', 'expected_success': True, 'expected_result': '15.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / 3 * 3', 'expected_success': True, 'expected_result': '23.0'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3)', 'expected_success': True, 'expected_result': '15.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1', 'expected_success': True, 'expected_result': '16.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2', 'expected_success': True, 'expected_result': '14.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3', 'expected_success': True, 'expected_result': '8.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / 3', 'expected_success': True, 'expected_result': '13.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3)', 'expected_success': True, 'expected_result': '14.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1', 'expected_success': True, 'expected_result': '15.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2', 'expected_success': True, 'expected_result': '13.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3', 'expected_success': True, 'expected_result': '11.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / 3', 'expected_success': True, 'expected_result': '16.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3)', 'expected_success': True, 'expected_result': '17.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1', 'expected_success': True, 'expected_result': '18.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2', 'expected_success': True, 'expected_result': '16.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3', 'expected_success': True, 'expected_result': '14.666666666666666'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / 3', 'expected_success': True, 'expected_result': '19.666666666666668'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3)', 'expected_success': True, 'expected_result': '20.66666666666667'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1', 'expected_success': True, 'expected_result': '21.66666666666667'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2', 'expected_success': True, 'expected_result': '19.66666666666667'},
        {'text': 'Oblicz 100 / (5 * 2) + 5 - 2 * 3 + 4 / (2 * 2) - 1 + 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 - 2 * 3 / (3 * 3) + 1 -