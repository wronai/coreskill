import json
import subprocess

def get_info() -> dict:
    return {
        "name": "json_validator",
        "version": "v5",
        "description": "Validates if a given string is a valid JSON object."
    }

def health_check() -> dict:
    return {"status": "ok"}

class JsonValidator:
    def execute(self, params: dict) -> dict:
        input_text = params.get('text', '')
        if not input_text:
            return {'success': False, 'error': 'No input text provided.'}

        try:
            json.loads(input_text)
            return {'success': True, 'message': 'The provided text is a valid JSON.'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'An unexpected error occurred: {e}'}

def execute(params: dict) -> dict:
    validator = JsonValidator()
    return validator.execute(params)

if __name__ == '__main__':
    print("Testing json_validator skill...")

    # Test case 1: Valid JSON
    valid_json_input = '{"name": "test", "value": 123}'
    result1 = execute({'text': valid_json_input})
    print(f"Input: {valid_json_input}")
    print(f"Result: {result1}")
    assert result1['success'] is True

    # Test case 2: Invalid JSON
    invalid_json_input = '{"name": "test", "value": 123' # Missing closing brace
    result2 = execute({'text': invalid_json_input})
    print(f"Input: {invalid_json_input}")
    print(f"Result: {result2}")
    assert result2['success'] is False
    assert 'Invalid JSON' in result2['error']

    # Test case 3: Empty input
    empty_input = ''
    result3 = execute({'text': empty_input})
    print(f"Input: '{empty_input}'")
    print(f"Result: {result3}")
    assert result3['success'] is False
    assert 'No input text provided' in result3['error']

    # Test case 4: Non-JSON string
    non_json_input = 'This is just a plain string.'
    result4 = execute({'text': non_json_input})
    print(f"Input: {non_json_input}")
    print(f"Result: {result4}")
    assert result4['success'] is False
    assert 'Invalid JSON' in result4['error']

    # Test case 5: JSON with different data types
    complex_json_input = '{"string": "hello", "number": 42, "boolean": true, "null_value": null, "array": [1, 2, 3], "object": {"nested": "value"}}'
    result5 = execute({'text': complex_json_input})
    print(f"Input: {complex_json_input}")
    print(f"Result: {result5}")
    assert result5['success'] is True

    print("\njson_validator skill tests completed.")
    print(f"get_info(): {get_info()}")
    print(f"health_check(): {health_check()}")