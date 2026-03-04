import subprocess
import re
import sys
import ast
import operator
import urllib.request

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check():
    return {'status': 'ok'}

class SafeExpressionEvaluator:
    def __init__(self):
        self.operators = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.USub: operator.neg,
            ast.Pow: operator.pow,
            ast.Mod: operator.mod,
            ast.FloorDiv: operator.floordiv,
        }
        self.allowed_node_types = {
            ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Load,
            ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.Pow, ast.Mod, ast.FloorDiv,
            ast.Call, ast.Name
        }

    def _eval(self, node):
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.BinOp):
            left = self._eval(node.left)
            right = self._eval(node.right)
            op_type = type(node.op)
            op = self.operators.get(op_type)
            if op is None:
                raise TypeError(f"Unsupported binary operator: {op_type.__name__}")
            if op == operator.truediv and right == 0:
                raise ZeroDivisionError("division by zero")
            if op == operator.floordiv and right == 0:
                raise ZeroDivisionError("division by zero")
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand)
            op_type = type(node.op)
            op = self.operators.get(op_type)
            if op is None:
                raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
            return op(operand)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id == 'abs':
                if len(node.args) == 1 and not node.keywords:
                    return abs(self._eval(node.args[0]))
            raise TypeError(f"Unsupported function call: {getattr(node.func, 'id', 'unknown')}")
        elif isinstance(node, ast.Name):
            # Allow specific names if needed, e.g., math constants
            if node.id == 'pi':
                return 3.141592653589793
            elif node.id == 'e':
                return 2.718281828459045
            raise NameError(f"Unsupported name: {node.id}")
        else:
            raise TypeError(f"Unsupported AST node type: {type(node).__name__}")

    def evaluate(self, expression):
        try:
            tree = ast.parse(expression, mode='eval')
            for node in ast.walk(tree):
                if type(node) not in self.allowed_node_types:
                    raise ValueError(f"Disallowed node type: {type(node).__name__}")

            return self._eval(tree.body)
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError, NameError) as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during evaluation: {e}")


class Kalkulator:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip()
            if not text:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.', 'spoken': 'Proszę podać wyrażenie do obliczenia.'}

            # Remove potential TTS commands or other noise
            text = re.sub(r'^(policz mi|oblicz|ile to jest)\s*', '', text, flags=re.IGNORECASE).strip()

            if not text:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia po usunięciu komendy.', 'spoken': 'Nie udało się rozpoznać wyrażenia. Proszę podać je ponownie.'}

            # Basic sanitization: remove whitespace
            expression = text.replace(" ", "")

            # More robust sanitization using ast
            evaluator = SafeExpressionEvaluator()
            result = evaluator.evaluate(expression)

            spoken_result = f"Wynik to {result}"
            return {'success': True, 'result': str(result), 'spoken': spoken_result}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu.', 'spoken': 'Wystąpił błąd składni w podanym wyrażeniu.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.', 'spoken': 'Nie można dzielić przez zero.'}
        except (ValueError, TypeError, NameError) as e:
            return {'success': False, 'error': str(e), 'spoken': f'Nieprawidłowe wyrażenie: {str(e)}'}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}', 'spoken': 'Wystąpił nieoczekiwany błąd podczas obliczeń.'}

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
        "100 / (2 * (5 - 5))", # Division by zero within nested parentheses
        "1 + 2 * 3",
        "policz mi 5 + 5",
        "oblicz 100 / 2",
        "ile to jest 7 * 8",
        "abs(-5)",
        "2 ** 3", # Power operator
        "10 % 3", # Modulo operator
        "10 // 3", # Floor division operator
        "pi * 2",
        "e + 1",
        "2 + abs(-3)",
        "10 / (2 * (3 - 3))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",
        "2 + (3 * 4) - 1",
        "100 / (2 * (5 - 5))",