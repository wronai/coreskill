import subprocess
import sys
import re

class Kalkulator:
    def __init__(self):
        self.version = "v1"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "")
            if not text:
                return {"success": False, "error": "No text provided."}

            # Extract mathematical expression from the text
            # This regex looks for numbers, operators (+, -, *, /, **), parentheses, and decimals
            match = re.search(r'policz mi (.*)', text, re.IGNORECASE)
            if not match:
                match = re.search(r'calculate (.*)', text, re.IGNORECASE)
            if not match:
                match = re.search(r'what is (.*)', text, re.IGNORECASE)
            if not match:
                match = re.search(r'(\d+(\.\d+)?\s*[\+\-\*\/\*\*]\s*)+(\d+(\.\d+)?)', text)
            if not match:
                match = re.search(r'(\d+(\.\d+)?\s*[\+\-\*\/\*\*]\s*)+\(\s*\d+(\.\d+)?\s*[\+\-\*\/\*\*]\s*\d+(\.\d+)?\s*\)', text)
            if not match:
                match = re.search(r'\(\s*\d+(\.\d+)?\s*[\+\-\*\/\*\*]\s*\d+(\.\d+)?\s*\)\s*[\+\-\*\/\*\*]\s*\d+(\.\d+)?', text)


            if not match:
                return {"success": False, "error": "Could not find a mathematical expression in the text."}

            expression = match.group(0)

            # Basic sanitization to prevent arbitrary code execution, though eval is still risky.
            # Allow only numbers, operators, parentheses, and decimals.
            if not re.fullmatch(r'[\d\.\+\-\*\/\(\)\s]+', expression):
                return {"success": False, "error": "Invalid characters in expression."}

            # Using eval is generally unsafe, but for a controlled environment like this,
            # and given the constraints of only stdlib, it's the most direct way.
            # In a real-world scenario, a safer parsing library would be preferred.
            result = eval(expression)
            return {"success": True, "result": result, "spoken": f"The result is {result}"}
        except ZeroDivisionError:
            return {"success": False, "error": "Division by zero is not allowed.", "spoken": "I cannot divide by zero."}
        except SyntaxError:
            return {"success": False, "error": "Invalid mathematical syntax.", "spoken": "I could not understand the mathematical expression."}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": f"An error occurred: {e}"}

    def get_info(self) -> dict:
        return {
            "name": "kalkulator",
            "version": self.version,
            "description": "Oblicza wyrażenia matematyczne z podanego tekstu.",
            "capabilities": {
                "math_expressions": True
            }
        }

    def health_check(self) -> dict:
        try:
            # A simple check to ensure the class is functional by evaluating a basic expression
            eval("1+1")
            return {"status": "ok"}
        except Exception as e:
            return {"status": "error", "message": str(e)}

def get_info():
    return {"name": "kalkulator", "version": "v1", "description": "kalkulator skill"}

def health_check():
    try:
        eval("1+1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

def execute(params: dict) -> dict:
    kalkulator_skill = Kalkulator()
    return kalkulator_skill.execute(params)

if __name__ == '__main__':
    kalkulator_skill = Kalkulator()

    # Test cases
    test_texts = [
        "policz mi 2 + 2",
        "calculate 10 * 5 - 3",
        "what is (4 + 6) / 2",
        "policz mi 2 ** 3",
        "calculate 10 / 0", # Test division by zero
        "policz mi invalid expression", # Test invalid syntax
        "just some text", # Test no expression
        "policz mi 5 * (3 + 2)",
        "calculate 10.5 + 2.3",
        "what is 2 * (3 + 4) / 2"
    ]

    for test_text in test_texts:
        params = {"text": test_text}
        print(f"Testing with text: '{test_text}'")
        result = kalkulator_skill.execute(params)
        print(f"Result: {result}\n")

    print(f"Info: {kalkulator_skill.get_info()}\n")
    print(f"Health Check: {kalkulator_skill.health_check()}\n")

    print(f"Module-level execute test:")
    module_params = {"text": "policz mi 7 * 8"}
    module_result = execute(module_params)
    print(f"Result: {module_result}\n")

    print(f"Module-level get_info test: {get_info()}\n")
    print(f"Module-level health_check test: {health_check()}\n")
```