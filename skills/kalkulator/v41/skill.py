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
            return {'success': False, 'error': str(e)}

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

        # Basic sanitization to prevent common injection attempts
        # This is not a foolproof security measure for arbitrary code execution
        # but aims to block obvious keywords.
        for func_name in ['eval', 'exec', 'open', 'input', '__import__']:
            expression = re.sub(r'\b' + func_name + r'\b', '', expression)

        try:
            # Using a restricted environment for eval
            # We explicitly allow 'math' module and basic builtins like 'abs', 'pow', etc.
            # Note: eval is inherently risky. This is a simplified approach.
            # For robust calculation, a dedicated library or a more secure sandbox is recommended.
            result = eval(expression, {"__builtins__": {
                'abs': abs, 'pow': pow, 'round': round, 'max': max, 'min': min,
                'True': True, 'False': False, 'None': None
            }}, {"math": math})
            return float(result)
        except ZeroDivisionError:
            raise ValueError("Błąd: Dzielenie przez zero.")
        except SyntaxError:
            raise ValueError("Błąd składni w wyrażeniu.")
        except NameError as e:
            name_error_match = re.search(r"name '(\w+)' is not defined", str(e))
            if name_error_match:
                undefined_name = name_error_match.group(1)
                raise ValueError(f"Błąd: Nieznana nazwa lub funkcja: {undefined_name}")
            else:
                raise ValueError(f"Błąd: Nieznana nazwa lub funkcja w wyrażeniu.")
        except Exception as e:
            raise ValueError(f"Błąd wykonania wyrażenia: {str(e)}")


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
        {'text': 'oblicz abc', 'expected_error': "Błąd: Nieznana nazwa lub funkcja: abc"},
        {'text': 'oblicz 1.5 * 2.5', 'expected': '3.75'},
        {'text': 'oblicz 1,5 * 2,5', 'expected': '3.75'},
        {'text': 'oblicz math.sin(math.pi/2)', 'expected': '1.0'},
        {'text': 'oblicz 10 / (2 + 3)', 'expected': '2.0'},
        {'text': 'oblicz 5 +', 'expected_error': 'Błąd składni w wyrażeniu.'},
        {'text': 'oblicz sin(pi/2)', 'expected_error': "Błąd: Nieznana nazwa lub funkcja: sin"},
        {'text': 'oblicz abs(-5)', 'expected': '5.0'},
        {'text': 'oblicz pow(2, 3)', 'expected': '8.0'},
        {'text': 'oblicz round(3.14159, 2)', 'expected': '3.14'},
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
            assert result['success'], f"Expected success but got error: {result.get('error')}"