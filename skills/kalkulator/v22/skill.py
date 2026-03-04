import subprocess
import re
import sys
import ast
import operator

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
            ast.UAdd: operator.pos
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
            return op(left, right)
        elif isinstance(node, ast.UnaryOp):
            operand = self._eval(node.operand)
            op_type = type(node.op)
            op = self.operators.get(op_type)
            if op is None:
                raise TypeError(f"Unsupported unary operator: {op_type.__name__}")
            return op(operand)
        else:
            raise TypeError(f"Unsupported AST node type: {type(node).__name__}")

    def evaluate(self, expression):
        try:
            tree = ast.parse(expression, mode='eval')
            allowed_nodes = (
                ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant,
                ast.Load, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.USub, ast.UAdd
            )
            for node in ast.walk(tree):
                if not isinstance(node, allowed_nodes):
                    raise ValueError(f"Disallowed node type in expression: {type(node).__name__}")

            return self._eval(tree.body)
        except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
            raise e
        except Exception as e:
            raise RuntimeError(f"Unexpected error during evaluation: {e}")


class Kalkulator:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '').strip()
            if not text:
                return {'success': False, 'error': 'Brak wyrażenia do obliczenia.'}

            # Extract mathematical expression from text, allowing numbers, operators, parentheses, and spaces.
            # This regex is more permissive to capture potential expressions embedded in natural language.
            match = re.search(r'([\d\.\+\-\*\/\(\)\s]+)', text)
            if not match:
                return {'success': False, 'error': 'Nie można znaleźć wyrażenia matematycznego w tekście.'}

            expression_part = match.group(1)

            # Remove all whitespace for cleaner parsing by ast
            expression = expression_part.replace(" ", "")

            if not expression:
                return {'success': False, 'error': 'Wyrażenie matematyczne jest puste po usunięciu spacji.'}

            evaluator = SafeExpressionEvaluator()
            result = evaluator.evaluate(expression)

            return {'success': True, 'result': str(result)}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Dzielenie przez zero jest niedozwolone.'}
        except (ValueError, TypeError) as e:
            return {'success': False, 'error': str(e)}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}'}

def execute(params: dict) -> dict:
    kalkulator_skill = Kalkulator()
    return kalkulator_skill.execute(params)

if __name__ == '__main__':
    test_expressions = [
        "2 + 2",
        "10 * (5 - 3)",
        "100 / 4",
        "10 / 0",
        "abc + 5",
        "2 + 3 * 4",
        "(2 + 3) * 4",
        "10.5 * 2",
        "2 +",
        "",
        "2 + (3 * 4) - 1",
        "-5 + 10",
        "10 * (-2 + 5)",
        "10 / (2 * 0)",
        "((2+3)*4)",
        "2 + 3)",
        "(2 + 3",
        "2 ++ 3",
        "2 * / 3",
        "()",
        "5 * (3 + 2) / 5",
        "100 / (2 * (5 - 5))",
        "1 + 2 * 3",
        "a ile to 100 / 7?",
        "oblicz 2 * (3 + 4)"
    ]

    for expr in test_expressions:
        params = {'text': expr}
        result = execute(params)
        print(f"Input: '{expr}' -> Result: {result}")

    print("\nInfo:", get_info())
    print("Health Check:", health_check())