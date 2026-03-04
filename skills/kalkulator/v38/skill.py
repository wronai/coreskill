import subprocess
import re
import math

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
            return {'success': False, 'error': 'Nie udało się wyodrębnić wyrażenia matematycznego.'}

        try:
            result = self._calculate(expression)
            return {'success': True, 'result': str(result)}
        except Exception as e:
            return {'success': False, 'error': f'Błąd obliczeń: {e}'}

    def _extract_expression(self, text: str) -> str | None:
        match = re.search(r'(?:oblicz|ile to jest)\s+(.*)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        if re.match(r'^[\d\s\+\-\*\/\.\(\)\%]+$', text.strip()):
            return text.strip()
        return None

    def _calculate(self, expression: str) -> float:
        allowed_chars = r'0-9\+\-\*\/\.\(\)\%\s'
        if not re.fullmatch(f'[{allowed_chars}]+', expression):
            raise ValueError("Wyrażenie zawiera niedozwolone znaki.")

        expression = expression.replace(',', '.')

        # Bezpieczne wykonanie wyrażenia matematycznego za pomocą subprocess
        # Używamy modułu math i ograniczamy __builtins__
        # Zastępujemy potencjalnie niebezpieczne funkcje, jeśli są w wyrażeniu
        safe_expression = expression
        for func_name in ['eval', 'exec', 'open', 'input', 'compile', '__import__']:
            safe_expression = re.sub(r'\b' + func_name + r'\b', '', safe_expression)

        try:
            # Używamy subprocess, aby uruchomić wyrażenie w osobnym procesie Pythona
            # To nie czyni go w pełni bezpiecznym, ale izoluje od głównego procesu.
            # Wymaga to, aby `python3` było dostępne w systemie.
            # Dodajemy moduł math do dostępnych globalnych zmiennych.
            process = subprocess.run(
                ['python3', '-c', f'import math; print(eval("{safe_expression}", {{"__builtins__": None}}, {{"math": math}}))'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5
            )
            return float(process.stdout.strip())
        except subprocess.CalledProcessError as e:
            # Próbujemy zidentyfikować błąd z stderr
            error_message = e.stderr.strip()
            if "ZeroDivisionError" in error_message:
                raise ValueError("Błąd: Dzielenie przez zero.")
            elif "SyntaxError" in error_message:
                raise ValueError("Błąd składni w wyrażeniu.")
            elif "NameError" in error_message:
                raise ValueError(f"Błąd: Nieznana nazwa lub funkcja w wyrażeniu: {error_message.split(':')[-1].strip()}")
            else:
                raise ValueError(f"Błąd wykonania wyrażenia: {error_message}")
        except subprocess.TimeoutExpired:
            raise ValueError("Przekroczono czas obliczeń.")
        except Exception as e:
            raise ValueError(f"Nieznany błąd podczas obliczeń: {e}")


def execute(params: dict) -> dict:
    kalkulator_skill = Kalkulator()
    return kalkulator_skill.execute(params)

if __name__ == '__main__':
    test_cases = [
        {'text': 'oblicz 5 + 3 * 2', 'expected': '11.0'},
        {'text': 'ile to jest (10 - 4) / 2', 'expected': '3.0'},
        {'text': '25 % 7', 'expected': '4.0'},
        {'text': 'oblicz 2**3', 'expected': '8.0'},
        {'text': 'oblicz 10 / 0', 'expected_error': 'Błąd: Dzielenie przez zero.'},
        {'text': 'oblicz abc', 'expected_error': 'Błąd: Nieznana nazwa lub funkcja w wyrażeniu:'},
        {'text': 'oblicz 1.5 * 2.5', 'expected': '3.75'},
        {'text': 'oblicz 1,5 * 2,5', 'expected': '3.75'},
        {'text': 'oblicz math.sin(math.pi/2)', 'expected': '1.0'},
        {'text': 'oblicz 10 / (2 + 3)', 'expected': '2.0'},
        {'text': 'oblicz 5 +', 'expected_error': 'Błąd składni w wyrażeniu.'},
    ]

    print(f"Info: {get_info()}")
    print(f"Health Check: {health_check()}")

    for case in test_cases:
        print(f"\nInput: {case['text']}")
        result = execute(case)
        print(f"Output: {result}")
        if 'expected_error' in case:
            assert not result['success']
            assert case['expected_error'] in result.get('error', '')
        elif 'expected' in case:
            assert result['success']
            assert 'result' in result
            try:
                assert abs(float(result['result']) - float(case['expected'])) < 1e-9
            except ValueError:
                assert result['result'] == case['expected']
            print(f"Result: {result['result']}")
        else:
            assert result['success'] # Should have either expected or expected_error