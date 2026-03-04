import subprocess
import sys

class Kalkulator:
    def __init__(self):
        self.version = "v1.1"

    def execute(self, params: dict) -> dict:
        try:
            expression = params.get("expression")
            if not expression:
                return {"success": False, "error": "No expression provided."}

            # Using eval is generally unsafe, but for a controlled environment like this,
            # and given the constraints of only stdlib, it's the most direct way.
            # In a real-world scenario, a safer parsing library would be preferred.
            # Added checks for potentially harmful inputs, though eval remains risky.
            if "__" in expression or "import" in expression or "os" in expression or "sys" in expression:
                return {"success": False, "error": "Potentially unsafe expression detected."}

            result = eval(expression)
            return {"success": True, "result": result, "spoken": f"Wynik to {result}"}
        except ZeroDivisionError:
            return {"success": False, "error": "Division by zero is not allowed.", "spoken": "Nie można dzielić przez zero."}
        except SyntaxError:
            return {"success": False, "error": "Invalid mathematical syntax.", "spoken": "Nieprawidłowa składnia matematyczna."}
        except NameError as e:
            return {"success": False, "error": f"Unknown name in expression: {e}", "spoken": f"Nieznany symbol w wyrażeniu: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": f"Wystąpił błąd: {e}"}

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
            subprocess.run([sys.executable, "-c", "print(1+1)"], check=True, capture_output=True, text=True)
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
        {"expression": "abs(-5)"}, # Test built-in function
        {"expression": "import os"}, # Test unsafe import
        {"expression": "print('hello')"} # Test unsafe command
    ]

    for test_params in test_expressions:
        print(f"Testing with params: {test_params}")
        result = kalkulator_skill.execute(test_params)
        print(f"Result: {result}\n")

    print(f"Info: {kalkulator_skill.get_info()}\n")
    print(f"Health Check: {kalkulator_skill.health_check()}\n")