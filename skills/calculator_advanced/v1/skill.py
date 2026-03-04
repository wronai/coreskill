#!/usr/bin/env python3
"""
calculator_advanced skill - Advanced calculator with variables, formulas, and history.
Uses math module for scientific calculations.
"""
import math
import json
import re
from pathlib import Path


def get_info():
    return {
        "name": "calculator_advanced",
        "version": "v1",
        "description": "Advanced calculator with variables, formulas, scientific functions, and history.",
        "capabilities": ["calculator", "math", "scientific", "variables"],
        "actions": ["calculate", "solve", "convert_base", "stats", "history"]
    }


def health_check():
    try:
        import math
        return True
    except:
        return False


class AdvancedCalculatorSkill:
    """Advanced calculator with variables and scientific functions."""

    # Safe math functions whitelist
    SAFE_FUNCTIONS = {
        # Basic math
        'abs': abs, 'round': round, 'max': max, 'min': min,
        'sum': sum, 'pow': pow, 'divmod': divmod,

        # Math module functions
        'sqrt': math.sqrt, 'sin': math.sin, 'cos': math.cos,
        'tan': math.tan, 'asin': math.asin, 'acos': math.acos,
        'atan': math.atan, 'atan2': math.atan2, 'sinh': math.sinh,
        'cosh': math.cosh, 'tanh': math.tanh, 'exp': math.exp,
        'log': math.log, 'log10': math.log10, 'log2': math.log2,
        'ceil': math.ceil, 'floor': math.floor, 'factorial': math.factorial,
        'gcd': math.gcd, 'degrees': math.degrees, 'radians': math.radians,
        'pi': math.pi, 'e': math.e, 'tau': math.tau, 'inf': math.inf,
        'nan': math.nan, 'isfinite': math.isfinite, 'isinf': math.isinf,
        'isnan': math.isnan
    }

    def __init__(self):
        self.history_file = Path.home() / ".evo_calculator_history.json"
        self.variables = {}
        self._load_history()

    def _load_history(self):
        """Load calculation history."""
        try:
            if self.history_file.exists():
                with open(self.history_file, 'r') as f:
                    data = json.load(f)
                    self.variables = data.get('variables', {})
        except:
            self.variables = {}

    def _save_history(self):
        """Save calculation history."""
        try:
            with open(self.history_file, 'w') as f:
                json.dump({'variables': self.variables}, f)
        except:
            pass

    def calculate(self, expression, variables=None):
        """Safely evaluate mathematical expression."""
        try:
            if not expression or not isinstance(expression, str):
                return {"success": False, "error": "No expression provided"}

            # Merge provided variables with stored ones
            local_vars = dict(self.variables)
            if variables:
                local_vars.update(variables)

            # Create safe evaluation environment
            safe_dict = dict(self.SAFE_FUNCTIONS)
            safe_dict.update(local_vars)

            # Evaluate expression
            result = eval(expression, {"__builtins__": {}}, safe_dict)

            # Store result in history variable 'ans'
            self.variables['ans'] = result
            self._save_history()

            # Format result
            if isinstance(result, float):
                # Round if close to integer
                if abs(result - round(result)) < 1e-10:
                    result = round(result)
                else:
                    result = round(result, 10)

            return {
                "success": True,
                "expression": expression,
                "result": result,
                "type": type(result).__name__
            }

        except SyntaxError as e:
            return {"success": False, "error": f"Syntax error: {e}"}
        except NameError as e:
            return {"success": False, "error": f"Unknown variable or function: {e}"}
        except ZeroDivisionError:
            return {"success": False, "error": "Division by zero"}
        except OverflowError:
            return {"success": False, "error": "Number too large"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def set_variable(self, name, value):
        """Set a variable for later use."""
        try:
            if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', name):
                return {"success": False, "error": f"Invalid variable name: {name}"}

            # If value is expression, evaluate it
            if isinstance(value, str):
                result = self.calculate(value)
                if not result.get("success"):
                    return result
                value = result["result"]

            self.variables[name] = value
            self._save_history()

            return {
                "success": True,
                "variable": name,
                "value": value
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_variables(self):
        """Get all stored variables."""
        return {
            "success": True,
            "variables": self.variables,
            "count": len(self.variables)
        }

    def clear_variables(self):
        """Clear all variables."""
        self.variables = {}
        self._save_history()
        return {"success": True, "message": "All variables cleared"}

    def solve_linear(self, equation, variable='x'):
        """Solve simple linear equation of form ax + b = c."""
        try:
            # Parse equation like "2*x + 5 = 15" or "2x + 5 = 15"
            eq = equation.replace(' ', '')

            # Handle implicit multiplication (2x -> 2*x)
            eq = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', eq)

            # Split by equals
            if '=' not in eq:
                return {"success": False, "error": "Equation must contain ="}

            left, right = eq.split('=', 1)

            # Move everything to left side: left - right = 0
            full = f"({left}) - ({right})"

            # Try to solve numerically by trying different values
            # This is a simple approach for linear equations
            def evaluate_at(x_val):
                try:
                    safe_dict = dict(self.SAFE_FUNCTIONS)
                    safe_dict[variable] = x_val
                    return eval(full, {"__builtins__": {}}, safe_dict)
                except:
                    return None

            # Use binary search for solution
            # Try range -1000 to 1000
            low, high = -1000, 1000
            best_x, best_error = 0, float('inf')

            for _ in range(100):  # Max iterations
                mid = (low + high) / 2
                val = evaluate_at(mid)

                if val is None:
                    break

                error = abs(val)
                if error < best_error:
                    best_error = error
                    best_x = mid

                if error < 1e-10:  # Found exact solution
                    break

                # Determine which side
                val_low = evaluate_at(low)
                if val_low is None:
                    break

                if (val_low > 0 and val > 0) or (val_low < 0 and val < 0):
                    low = mid
                else:
                    high = mid

            if best_error < 0.001:
                # Round if close to integer
                if abs(best_x - round(best_x)) < 0.0001:
                    best_x = round(best_x)

                return {
                    "success": True,
                    "equation": equation,
                    "solution": {variable: best_x},
                    "error": best_error
                }
            else:
                return {
                    "success": False,
                    "error": f"Could not find solution (best guess: {best_x}, error: {best_error})"
                }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def convert_base(self, number, from_base=10, to_base=10):
        """Convert number between bases (2-36)."""
        try:
            if from_base < 2 or from_base > 36 or to_base < 2 or to_base > 36:
                return {"success": False, "error": "Base must be between 2 and 36"}

            # Convert to decimal first
            if isinstance(number, str):
                decimal = int(number, from_base)
            else:
                decimal = int(number)

            # Convert from decimal to target base
            digits = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

            if decimal == 0:
                result = "0"
            else:
                result = ""
                n = decimal
                while n > 0:
                    result = digits[n % to_base] + result
                    n //= to_base

            return {
                "success": True,
                "original": number,
                "from_base": from_base,
                "to_base": to_base,
                "result": result,
                "decimal": decimal
            }

        except ValueError:
            return {"success": False, "error": f"Invalid number for base {from_base}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def stats(self, numbers):
        """Calculate statistics for a list of numbers."""
        try:
            if not numbers or not isinstance(numbers, list):
                return {"success": False, "error": "Provide a list of numbers"}

            data = [float(x) for x in numbers if x is not None]
            if not data:
                return {"success": False, "error": "No valid numbers"}

            n = len(data)
            mean = sum(data) / n
            sorted_data = sorted(data)
            median = sorted_data[n // 2] if n % 2 else (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2

            # Variance and std dev
            variance = sum((x - mean) ** 2 for x in data) / n
            std_dev = math.sqrt(variance)

            return {
                "success": True,
                "count": n,
                "sum": sum(data),
                "mean": round(mean, 6),
                "median": round(median, 6),
                "min": min(data),
                "max": max(data),
                "range": max(data) - min(data),
                "variance": round(variance, 6),
                "std_dev": round(std_dev, 6)
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def execute(self, input_data: dict) -> dict:
        """evo-engine interface."""
        action = input_data.get("action", "calculate")

        if action == "calculate":
            return self.calculate(
                input_data.get("expression", ""),
                input_data.get("variables")
            )
        elif action == "set_variable":
            return self.set_variable(
                input_data.get("name", ""),
                input_data.get("value")
            )
        elif action == "get_variables":
            return self.get_variables()
        elif action == "clear_variables":
            return self.clear_variables()
        elif action == "solve":
            return self.solve_linear(
                input_data.get("equation", ""),
                input_data.get("variable", "x")
            )
        elif action == "convert_base":
            return self.convert_base(
                input_data.get("number"),
                input_data.get("from_base", 10),
                input_data.get("to_base", 10)
            )
        elif action == "stats":
            return self.stats(input_data.get("numbers", []))
        else:
            return {"success": False, "error": f"Unknown action: {action}"}


def execute(input_data: dict) -> dict:
    return AdvancedCalculatorSkill().execute(input_data)


if __name__ == "__main__":
    skill = AdvancedCalculatorSkill()
    print(f"Info: {json.dumps(get_info(), indent=2)}")
    print(f"Health: {health_check()}")

    tests = [
        {"action": "calculate", "expression": "sqrt(16) + sin(pi/2)"},
        {"action": "set_variable", "name": "radius", "value": "5"},
        {"action": "calculate", "expression": "pi * radius**2"},
        {"action": "solve", "equation": "2*x + 5 = 15"},
        {"action": "convert_base", "number": "1010", "from_base": 2, "to_base": 10},
        {"action": "stats", "numbers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]},
    ]

    for test in tests:
        print(f"\n{test}:")
        print(json.dumps(skill.execute(test), indent=2))
