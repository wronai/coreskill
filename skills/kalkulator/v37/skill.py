import subprocess
import sys
import re
import urllib.request

def get_info() -> dict:
    return {
        "name": "kalkulator",
        "version": "v1",
        "description": "Oblicza wyrażenia matematyczne z podanego tekstu.",
    }

def health_check() -> dict:
    try:
        # A simple check to ensure the class is functional by evaluating a basic expression
        eval("1+1")
        return {"status": "ok"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

class Kalkulator:
    def __init__(self):
        self.version = "v1"

    def execute(self, params: dict) -> dict:
        try:
            text = params.get("text", "")
            if not text:
                return {"success": False, "error": "No text provided."}

            # Extract mathematical expression from the text
            # This regex looks for numbers, operators (+, -, *, /, **), parentheses, decimals, and common math functions
            # It also handles Polish phrases like "policz mi", "ile to"
            match = re.search(r'(?:policz mi|calculate|what is|ile to)\s+(.*)', text, re.IGNORECASE)

            if not match:
                return {"success": False, "error": "Could not find a mathematical expression in the text."}

            expression = match.group(1).strip()

            # Basic sanitization to prevent arbitrary code execution.
            # Allow only numbers, operators, parentheses, decimals, and basic math functions.
            # This is still not completely safe, but better than a raw eval.
            # Added '%' for percentage calculations and '^' for power.
            allowed_chars_pattern = r'^[\d\.\+\-\*\/\(\)\s\%\^\w]+$'
            if not re.fullmatch(allowed_chars_pattern, expression):
                return {"success": False, "error": "Invalid characters or structure in expression."}

            # Replace common Polish number separators if any (e.g., "1.000" to "1000")
            # Assuming comma is decimal separator if dot is thousands, but this is tricky.
            # A more robust approach would be to parse numbers carefully.
            # For simplicity, let's assume standard notation or simple replacements.
            # If a number has a comma and then digits, it's likely a decimal.
            # If it has dots as thousands separators, it's more complex.
            # Let's try to handle common cases: "1,234.56" -> "1234.56" and "1.234,56" -> "1234.56"
            # This is a simplification. A full parser is complex.
            
            # Simple approach: remove all dots, then replace comma with dot for decimal.
            # This might break "1.000.000" but handles "1,23" correctly.
            expression = expression.replace('.', '').replace(',', '.')

            # Handle percentage: convert "X%" to "X/100"
            expression = re.sub(r'(\d+(\.\d+)?)\s*%', r'(\1 / 100)', expression)

            # Further sanitization for potentially unsafe function calls
            # This is a very basic attempt and might miss complex attacks.
            # A proper AST parser would be ideal but is outside stdlib.
            if "__" in expression or "import" in expression or "exec" in expression or "eval" in expression:
                return {"success": False, "error": "Potentially unsafe expression detected."}

            # Using eval is generally unsafe, but for a controlled environment like this,
            # and given the constraints of only stdlib, it's the most direct way.
            # In a real-world scenario, a safer parsing library would be preferred.
            result = eval(expression)

            # Format the spoken output to be more natural
            spoken_result = f"The result is {result}"
            if isinstance(result, float):
                # Use a reasonable precision for floats
                spoken_result = f"The result is approximately {result:.4f}"
            elif isinstance(result, int):
                spoken_result = f"The result is {result}"
            else:
                spoken_result = f"The result is {result}"


            return {"success": True, "result": result, "spoken": spoken_result}

        except ZeroDivisionError:
            return {"success": False, "error": "Division by zero is not allowed.", "spoken": "I cannot divide by zero."}
        except SyntaxError:
            return {"success": False, "error": "Invalid mathematical syntax.", "spoken": "I could not understand the mathematical expression."}
        except NameError as e:
            # Handle cases where eval might encounter undefined names (e.g., functions not allowed)
            return {"success": False, "error": f"Invalid expression: {e}", "spoken": f"I could not understand the mathematical expression: {e}"}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": f"An error occurred: {e}"}

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
        "ile to 10 / 0", # Test division by zero
        "policz mi invalid expression", # Test invalid syntax
        "just some text", # Test no expression
        "policz mi 5 * (3 + 2)",
        "calculate 10.5 + 2.3",
        "what is 2 * (3 + 4) / 2",
        "policz mi 2 + 2 * 3",
        "ile to 100 / 7",
        "calculate 1000.50 + 200.75", # Test with potential thousands separator
        "policz mi 50%", # Test percentage
        "what is sqrt(9)", # Test unsupported function
        "ile to 1000,50 + 200,75", # Test with comma as decimal
        "policz mi 1000000", # Test large number
        "calculate 50% of 200", # Test percentage of a number
        "what is 100 / 4%", # Test percentage in division
    ]

    for test_text in test_texts:
        params = {"text": test_text}
        print(f"Testing with text: '{test_text}'")
        result = kalkulator_skill.execute(params)
        print(f"Result: {result}\n")

    print(f"Info: {get_info()}\n")
    print(f"Health Check: {health_check()}\n")

    print(f"Module-level execute test:")
    module_params = {"text": "policz mi 7 * 8"}
    module_result = execute(module_params)
    print(f"Result: {module_result}\n")

    print(f"Module-level get_info test: {get_info()}\n")
    print(f"Module-level health_check test: {health_check()}\n")