import re
import subprocess
import ast
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
        text = params.get('text', '')
        if not text:
            return {'success': False, 'error': 'Brak tekstu do przetworzenia', 'spoken': 'Nie podałeś żadnego tekstu.'}

        expression = self._extract_expression(text)
        if not expression:
            return {'success': False, 'error': 'Nie można znaleźć wyrażenia matematycznego', 'spoken': 'Nie udało mi się znaleźć wyrażenia matematycznego.'}

        try:
            result = self._calculate(expression)
            return {'success': True, 'result': str(result), 'spoken': f'Wynik to {result}'}
        except ValueError as e:
            return {'success': False, 'error': str(e), 'spoken': str(e)}
        except Exception as e:
            return {'success': False, 'error': f'Błąd obliczeń: {e}', 'spoken': f'Wystąpił błąd podczas obliczeń: {e}'}

    def _extract_expression(self, text: str) -> str | None:
        match = re.search(r'(?:oblicz|ile to|policz mi)\s+(.+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        try:
            self._validate_expression(text)
            return text.strip()
        except ValueError:
            return None

    def _validate_expression(self, expression: str):
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError:
            raise ValueError("Nieprawidłowa składnia wyrażenia matematycznego")

        allowed_nodes = {
            ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
            ast.Num, 
            ast.Call, 
            ast.Name
        }
        
        allowed_names = {'pi', 'e'}
        allowed_functions = {'abs', 'round', 'pow'}

        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                if node.id not in allowed_names:
                    raise ValueError(f"Niedozwolona nazwa: {node.id}")
            elif isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name) or node.func.id not in allowed_functions:
                    raise ValueError(f"Niedozwolona funkcja: {getattr(node.func, 'id', 'unknown')}")
            elif not isinstance(node, tuple(allowed_nodes)):
                 raise ValueError("Niedozwolone operacje lub funkcje w wyrażeniu")

    def _calculate(self, expression: str) -> float:
        try:
            self._validate_expression(expression)
            expression = re.sub(r'\s+', ' ', expression).strip()
            
            # Using eval is still risky, but with ast validation, it's significantly safer.
            # For a truly secure solution, a dedicated math expression parser would be better.
            # Restrict builtins and globals for safety.
            result = eval(expression, {"__builtins__": None}, {}) 
            return float(result)
        except ZeroDivisionError:
            raise ValueError("Dzielenie przez zero jest niedozwolone")
        except ValueError as e: 
            raise e
        except Exception as e:
            raise ValueError(f"Błąd obliczeń: {e}")


def execute(params: dict) -> dict:
    skill = Kalkulator()
    return skill.execute(params)

if __name__ == '__main__':
    test_cases = [
        {'text': 'oblicz 2 + 2', 'expected_success': True, 'expected_result': '4.0'},
        {'text': 'ile to jest 5 * (3 + 2)', 'expected_success': True, 'expected_result': '25.0'},
        {'text': '10 / 2 - 1', 'expected_success': True, 'expected_result': '4.0'},
        {'text': 'oblicz 10 / 0', 'expected_success': False, 'expected_error': 'Dzielenie przez zero jest niedozwolone'},
        {'text': 'nie wiem co obliczyć', 'expected_success': False, 'expected_error': 'Nie można znaleźć wyrażenia matematycznego'},
        {'text': 'oblicz 2 + abc', 'expected_success': False, 'expected_error': 'Niedozwolona nazwa: abc'},
        {'text': '2**3', 'expected_success': False, 'expected_error': 'Niedozwolone operacje lub funkcje w wyrażeniu'}, 
        {'text': 'oblicz (5+3)*2/4', 'expected_success': True, 'expected_result': '4.0'},
        {'text': '1.5 * 2', 'expected_success': True, 'expected_result': '3.0'},
        {'text': 'oblicz 7', 'expected_success': True, 'expected_result': '7.0'},
        {'text': 'oblicz 5 +  3', 'expected_success': True, 'expected_result': '8.0'}, 
        {'text': 'oblicz (5+3) * 2 / 4', 'expected_success': True, 'expected_result': '4.0'}, 
        {'text': 'policz mi 2 + 2 * 3', 'expected_success': True, 'expected_result': '8.0'}, 
        {'text': 'oblicz abs(-5)', 'expected_success': True, 'expected_result': '5.0'}, 
        {'text': 'oblicz pow(2,3)', 'expected_success': True, 'expected_result': '8.0'}, 
        {'text': 'oblicz print("hello")', 'expected_success': False, 'expected_error': 'Niedozwolona funkcja: print'}, 
        {'text': 'import os', 'expected_success': False, 'expected_error': 'Nieprawidłowa składnia wyrażenia matematycznego'}, 
    ]

    for case in test_cases:
        result = execute(case)
        print(f"Input: '{case['text']}'")
        print(f"Output: {result}")
        if case['expected_success']:
            assert result['success'] is True, f"Expected success=True, got {result['success']}"
            assert result['result'] == case['expected_result'], f"Expected result '{case['expected_result']}', got '{result.get('result')}'"
        else:
            assert result['success'] is False, f"Expected success=False, got {result['success']}"
            assert case['expected_error'] in result.get('error', ''), f"Expected error containing '{case['expected_error']}', got '{result.get('error')}'"
        print("-" * 20)

    print("Wszystkie testy zakończone pomyślnie.")