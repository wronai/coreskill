import json
import subprocess
import re

def get_info() -> dict:
    return {
        "name": "json_validator",
        "version": "v1",
        "description": "Validates if a given string is a valid JSON object."
    }

def health_check() -> dict:
    return {"status": "ok"}

class JsonValidator:
    def execute(self, params: dict) -> dict:
        input_text = params.get('text', '')
        if not input_text:
            return {'success': False, 'error': 'No input text provided.', 'spoken': 'Please provide some text to validate.'}

        json_candidate = input_text
        # Attempt to extract JSON if it's part of a larger string
        # This regex tries to find a JSON object or array, even if it's not the whole string.
        # It's a bit more robust than just checking start/end characters.
        match = re.search(r'(\{.*\})|(\[.*\])', input_text, re.DOTALL)
        if match:
            json_candidate = match.group(0)
        else:
            # If no JSON-like structure is found, treat the whole input as potentially invalid JSON
            # This covers cases where the user might have typed invalid JSON directly without surrounding text.
            json_candidate = input_text

        try:
            json.loads(json_candidate)
            return {'success': True, 'message': 'The provided text is a valid JSON.', 'spoken': 'This is a valid JSON.'}
        except json.JSONDecodeError as e:
            # Provide a more user-friendly message for invalid JSON
            return {'success': False, 'error': f'Invalid JSON: {e}', 'spoken': f'This is not a valid JSON. The error is: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'An unexpected error occurred: {e}', 'spoken': 'An unexpected error occurred during validation.'}

def execute(params: dict) -> dict:
    validator = JsonValidator()
    return validator.execute(params)

if __name__ == '__main__':
    print("Testing json_validator skill...")

    # Test case 1: Valid JSON object
    valid_json_input = '{"name": "test", "value": 123}'
    result1 = execute({'text': valid_json_input})
    print(f"Input: {valid_json_input}")
    print(f"Result: {result1}")
    assert result1['success'] is True
    assert result1['spoken'] == 'This is a valid JSON.'

    # Test case 2: Invalid JSON object (missing closing brace)
    invalid_json_input = '{"name": "test", "value": 123'
    result2 = execute({'text': invalid_json_input})
    print(f"Input: {invalid_json_input}")
    print(f"Result: {result2}")
    assert result2['success'] is False
    assert 'Invalid JSON' in result2['error']
    assert 'This is not a valid JSON.' in result2['spoken']

    # Test case 3: Empty input
    empty_input = ''
    result3 = execute({'text': empty_input})
    print(f"Input: '{empty_input}'")
    print(f"Result: {result3}")
    assert result3['success'] is False
    assert 'No input text provided' in result3['error']
    assert result3['spoken'] == 'Please provide some text to validate.'

    # Test case 4: Non-JSON string
    non_json_input = 'This is just a plain string.'
    result4 = execute({'text': non_json_input})
    print(f"Input: {non_json_input}")
    print(f"Result: {result4}")
    assert result4['success'] is False
    assert 'Invalid JSON' in result4['error']
    assert 'This is not a valid JSON.' in result4['spoken']

    # Test case 5: Complex valid JSON object
    complex_json_input = '{"string": "hello", "number": 42, "boolean": true, "null_value": null, "array": [1, 2, 3], "object": {"nested": "value"}}'
    result5 = execute({'text': complex_json_input})
    print(f"Input: {complex_json_input}")
    print(f"Result: {result5}")
    assert result5['success'] is True
    assert result5['spoken'] == 'This is a valid JSON.'

    # Test case 6: User query with JSON embedded
    user_query_input = 'zwaliduj ten json: {"name": "test", "value": 42}'
    result6 = execute({'text': user_query_input})
    print(f"Input: {user_query_input}")
    print(f"Result: {result6}")
    assert result6['success'] is True
    assert result6['spoken'] == 'This is a valid JSON.'

    # Test case 7: Valid JSON array
    valid_json_array_input = '[1, 2, 3, {"a": 1}]'
    result7 = execute({'text': valid_json_array_input})
    print(f"Input: {valid_json_array_input}")
    print(f"Result: {result7}")
    assert result7['success'] is True
    assert result7['spoken'] == 'This is a valid JSON.'

    # Test case 8: Invalid JSON array (missing closing brace)
    invalid_json_array_input = '[1, 2, 3, {"a": 1}'
    result8 = execute({'text': invalid_json_array_input})
    print(f"Input: {invalid_json_array_input}")
    print(f"Result: {result8}")
    assert result8['success'] is False
    assert 'Invalid JSON' in result8['error']
    assert 'This is not a valid JSON.' in result8['spoken']

    # Test case 9: JSON object embedded in text
    embedded_json_input = 'Here is some text and then {"key": "value"} and more text.'
    result9 = execute({'text': embedded_json_input})
    print(f"Input: {embedded_json_input}")
    print(f"Result: {result9}")
    assert result9['success'] is True
    assert result9['spoken'] == 'This is a valid JSON.'

    # Test case 10: JSON object with newlines
    embedded_json_newline_input = '{\n  "key": "value"\n}'
    result10 = execute({'text': embedded_json_newline_input})
    print(f"Input: {embedded_json_newline_input}")
    print(f"Result: {result10}")
    assert result10['success'] is True
    assert result10['spoken'] == 'This is a valid JSON.'

    # Test case 11: JSON array embedded in text
    embedded_json_array_input = 'Some text before [1, 2, {"k": "v"}] and after.'
    result11 = execute({'text': embedded_json_array_input})
    print(f"Input: {embedded_json_array_input}")
    print(f"Result: {result11}")
    assert result11['success'] is True
    assert result11['spoken'] == 'This is a valid JSON.'

    # Test case 12: Invalid JSON with extra comma
    invalid_json_extra_comma = '{"a": 1, "b": 2,}'
    result12 = execute({'text': invalid_json_extra_comma})
    print(f"Input: {invalid_json_extra_comma}")
    print(f"Result: {result12}")
    assert result12['success'] is False
    assert 'Invalid JSON' in result12['error']
    assert 'This is not a valid JSON.' in result12['spoken']

    print("\njson_validator skill tests completed.")
    print(f"get_info(): {get_info()}")
    print(f"health_check(): {health_check()}")