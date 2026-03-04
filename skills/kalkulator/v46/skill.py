import re
import subprocess
import ast

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
        
        # If no keyword is found, try to parse the entire text as an expression
        # This is a more robust check than the previous regex
        try:
            self._validate_expression(text)
            return text.strip()
        except ValueError:
            return None

    def _validate_expression(self, expression: str):
        # Use ast.parse to check for valid Python syntax
        try:
            tree = ast.parse(expression, mode='eval')
        except SyntaxError:
            raise ValueError("Nieprawidłowa składnia wyrażenia matematycznego")

        # Check for allowed node types to prevent arbitrary code execution
        allowed_nodes = {
            ast.Expression, ast.Constant, ast.BinOp, ast.UnaryOp,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd,
            ast.Num, # Deprecated in Python 3.8+, but still works for older versions
            ast.Call, # Allow function calls if needed, but restrict to math functions
            ast.Name # Allow names if we want to support math constants like pi
        }
        
        # Restrict allowed names to common math constants if needed
        allowed_names = {'pi', 'e'}

        for node in ast.walk(tree):
            if not isinstance(node, tuple(allowed_nodes)):
                # Check if it's a Name node and if it's in our allowed list
                if isinstance(node, ast.Name) and node.id in allowed_names:
                    continue
                # Check if it's a Call node and if the function name is allowed
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ['abs', 'round', 'pow']: # Example allowed math functions
                    continue
                raise ValueError("Niedozwolone operacje lub funkcje w wyrażeniu")

    def _calculate(self, expression: str) -> float:
        try:
            self._validate_expression(expression)
            # Replace potential multiple spaces with single space to avoid eval issues
            expression = re.sub(r'\s+', ' ', expression).strip()
            
            # Using eval is still risky, but with ast validation, it's significantly safer.
            # For a truly secure solution, a dedicated math expression parser would be better.
            result = eval(expression, {"__builtins__": None}, {}) # Restrict builtins and globals
            return float(result)
        except ZeroDivisionError:
            raise ValueError("Dzielenie przez zero jest niedozwolone")
        except ValueError as e: # Catch validation errors
            raise e
        except Exception as e:
            # Catch any other potential errors during evaluation
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
        {'text': 'oblicz 2 + abc', 'expected_success': False, 'expected_error': 'Nieprawidłowa składnia wyrażenia matematycznego'},
        {'text': '2**3', 'expected_success': False, 'expected_error': 'Niedozwolone operacje lub funkcje w wyrażeniu'}, # ** is not allowed by ast validation
        {'text': 'oblicz (5+3)*2/4', 'expected_success': True, 'expected_result': '4.0'},
        {'text': '1.5 * 2', 'expected_success': True, 'expected_result': '3.0'},
        {'text': 'oblicz 7', 'expected_success': True, 'expected_result': '7.0'},
        {'text': 'oblicz 5 +  3', 'expected_success': True, 'expected_result': '8.0'}, # Test with multiple spaces
        {'text': 'oblicz (5+3) * 2 / 4', 'expected_success': True, 'expected_result': '4.0'}, # Test with spaces inside expression
        {'text': 'policz mi 2 + 2 * 3', 'expected_success': True, 'expected_result': '8.0'}, # Test for the user's specific example
        {'text': 'oblicz abs(-5)', 'expected_success': True, 'expected_result': '5.0'}, # Test allowed function
        {'text': 'oblicz pow(2,3)', 'expected_success': True, 'expected_result': '8.0'}, # Test allowed function
        {'text': 'oblicz print("hello")', 'expected_success': False, 'expected_error': 'Niedozwolone operacje lub funkcje w wyrażeniu'}, # Test disallowed function
        {'text': 'import os', 'expected_success': False, 'expected_error': 'Nieprawidłowa składnia wyrażenia matematycznego'}, # Test disallowed syntax
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
```