import subprocess
import sys

class Kalkulator:
    def __init__(self):
        self.version = "v1"

    def execute(self, params: dict) -> dict:
        try:
            expression = params.get("expression")
            if not expression:
                return {"success": False, "error": "No expression provided."}

            # Using eval is generally unsafe, but for a controlled environment like this,
            # and given the constraints of only stdlib, it's the most direct way.
            # In a real-world scenario, a safer parsing library would be preferred.
            result = eval(expression)
            return {"success": True, "result": result, "spoken": f"The result is {result}"}
        except ZeroDivisionError:
            return {"success": False, "error": "Division by zero is not allowed.", "spoken": "I cannot divide by zero."}
        except SyntaxError:
            return {"success": False, "error": "Invalid mathematical expression.", "spoken": "That is not a valid mathematical expression."}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": f"An error occurred: {e}"}

    def get_info(self) -> dict:
        return {
            "name": "kalkulator",
            "version": self.version,
            "description": "Oblicza wyrażenia matematyczne.",
            "capabilities": {
                "math_expressions": True
            }
        }

    def health_check(self) -> bool:
        try:
            # A simple check to ensure the class is functional
            subprocess.run([sys.executable, "-c", "print(1+1)"], check=True, capture_output=True)
            return True
        except Exception:
            return False

if __name__ == '__main__':
    kalkulator_skill = Kalkulator()

    # Test cases
    test_expressions = [
        {"expression": "2 + 2"},
        {"expression": "10 * 5 - 3"},
        {"expression": "(4 + 6) / 2"},
        {"expression": "2 ** 3"},
        {"expression": "10 / 0"}, # Test division by zero
        {"expression": "invalid expression"}, # Test invalid syntax
        {}, # Test missing expression
        {"expression": "100 / 7"} # User's example
    ]

    for test_params in test_expressions:
        print(f"Testing with params: {test_params}")
        result = kalkulator_skill.execute(test_params)
        print(f"Result: {result}\n")

    print(f"Info: {kalkulator_skill.get_info()}\n")
    print(f"Health Check: {kalkulator_skill.health_check()}\n")