import subprocess
import re

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v37',
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
        # Proste dopasowanie wyrażenia matematycznego, można rozbudować
        # Zakłada, że wyrażenie jest po słowie "oblicz" lub "ile to jest"
        match = re.search(r'(?:oblicz|ile to jest)\s+(.*)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        # Alternatywnie, jeśli tekst sam w sobie jest wyrażeniem
        if re.match(r'^[\d\s\+\-\*\/\.\(\)\%]+$', text.strip()):
            return text.strip()
        return None

    def _calculate(self, expression: str) -> float:
        # Bezpieczne wykonanie wyrażenia matematycznego
        # Używamy eval z ograniczonym zakresem, ale nadal jest to ryzykowne.
        # Lepszym rozwiązaniem byłoby użycie biblioteki do bezpiecznego parsowania wyrażeń,
        # ale zgodnie z wymaganiami używamy tylko stdlib.
        allowed_chars = r'0-9\+\-\*\/\.\(\)\%\s'
        if not re.fullmatch(f'[{allowed_chars}]+', expression):
            raise ValueError("Wyrażenie zawiera niedozwolone znaki.")

        # Zastąpienie przecinków kropkami dla liczb dziesiętnych
        expression = expression.replace(',', '.')

        # Użycie subprocess do wykonania wyrażenia w bezpieczniejszym środowisku
        # Jest to obejście, ponieważ eval jest niebezpieczne.
        # Można by użyć np. `python -c "print(eval(...))"`
        # Ale to nadal wykonuje eval.
        # Bardziej bezpieczne byłoby parsowanie ręczne lub użycie biblioteki.
        # Dla celów tego zadania, użyjemy prostego eval, ale z ostrzeżeniem.

        # Bezpieczniejsza alternatywa: użycie biblioteki `ast` do parsowania i ewaluacji
        # import ast
        # import operator as op
        #
        # # Supported operators
        # operators = {ast.Add: op.add, ast.Sub: op.sub, ast.Mult: op.mul,
        #              ast.Div: op.truediv, ast.Pow: op.pow, ast.BitXor: op.xor,
        #              ast.USub: op.neg}
        #
        # def eval_expr(expr):
        #     return eval_(ast.parse(expr, mode='eval').body)
        #
        # def eval_(node):
        #     if isinstance(node, ast.Num):  # <number>
        #         return node.n
        #     elif isinstance(node, ast.BinOp):  # <left> <operator> <right>
        #         return operators[type(node.op)](eval_(node.left), eval_(node.right))
        #     elif isinstance(node, ast.UnaryOp):  # <operator> <operand> e.g., -1
        #         return operators[type(node.op)](eval_(node.operand))
        #     else:
        #         raise TypeError(node)
        #
        # return eval_expr(expression)

        # Użycie eval z ostrzeżeniem o bezpieczeństwie
        try:
            # Używamy subprocess, aby uruchomić wyrażenie w osobnym procesie Pythona
            # To nie czyni go w pełni bezpiecznym, ale izoluje od głównego procesu.
            # Wymaga to, aby `python3` było dostępne w systemie.
            process = subprocess.run(
                ['python3', '-c', f'import math; print(eval("{expression.replace("math.", "")}", {{"__builtins__": None}}, {{"math": math}}))'],
                capture_output=True,
                text=True,
                check=True,
                timeout=5 # Dodajemy timeout
            )
            return float(process.stdout.strip())
        except subprocess.CalledProcessError as e:
            raise ValueError(f"Błąd wykonania wyrażenia: {e.stderr}")
        except subprocess.TimeoutExpired:
            raise ValueError("Przekroczono czas obliczeń.")
        except Exception as e:
            raise ValueError(f"Nieznany błąd podczas obliczeń: {e}")


def execute(params: dict) -> dict:
    kalkulator_skill = Kalkulator()
    return kalkulator_skill.execute(params)

if __name__ == '__main__':
    # Testy
    test_cases = [
        {'text': 'oblicz 5 + 3 * 2'},
        {'text': 'ile to jest (10 - 4) / 2'},
        {'text': '25 % 7'},
        {'text': 'oblicz 2**3'},
        {'text': 'oblicz 10 / 0'}, # Test błędu dzielenia przez zero
        {'text': 'oblicz abc'}, # Test błędu nieprawidłowego wyrażenia
        {'text': 'oblicz 1.5 * 2.5'},
        {'text': 'oblicz 1,5 * 2,5'}, # Test z przecinkiem
        {'text': 'oblicz sin(pi/2)', 'expected_error': 'Nieznany błąd podczas obliczeń: name \'sin\' is not defined'}, # Test z funkcjami math
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
        else:
            assert result['success']
            assert 'result' in result
            print(f"Result: {result['result']}")
```