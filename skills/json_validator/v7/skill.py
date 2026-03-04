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

        # Attempt to extract JSON if it's part of a larger string
        json_candidate = input_text
        if not (input_text.strip().startswith('{') and input_text.strip().endswith('}')) and \
           not (input_text.strip().startswith('[') and input_text.strip().endswith(']')):
            match = re.search(r'(\{.*\})|(\[.*\])', input_text, re.DOTALL)
            if match:
                json_candidate = match.group(0)
            else:
                # If no JSON-like structure is found, treat the whole input as potentially invalid JSON
                json_candidate = input_text

        try:
            json.loads(json_candidate)
            return {'success': True, 'message': 'The provided text is a valid JSON.', 'spoken': 'This is a valid JSON.'}
        except json.JSONDecodeError as e:
            return {'success': False, 'error': f'Invalid JSON: {e}', 'spoken': f'This is not a valid JSON. Error: {e}'}
        except Exception as e:
            return {'success': False, 'error': f'An unexpected error occurred: {e}', 'spoken': 'An unexpected error occurred during validation.'}

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
    assert result1['spoken'] == 'This is a valid JSON.'

    # Test case 2: Invalid JSON
    invalid_json_input = '{"name": "test", "value": 123' # Missing closing brace
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

    # Test case 5: JSON with different data types
    complex_json_input = '{"string": "hello", "number": 42, "boolean": true, "null_value": null, "array": [1, 2, 3], "object": {"nested": "value"}}'
    result5 = execute({'text': complex_json_input})
    print(f"Input: {complex_json_input}")
    print(f"Result: {result5}")
    assert result5['success'] is True
    assert result5['spoken'] == 'This is a valid JSON.'

    # Test case 6: User query with JSON
    user_query_input = 'zwaliduj ten json: {"name": "test", "value": 42}'
    result6 = execute({'text': user_query_input})
    print(f"Input: {user_query_input}")
    print(f"Result: {result6}")
    assert result6['success'] is True
    assert result6['spoken'] == 'This is a valid JSON.'

    # Test case 7: JSON array
    valid_json_array_input = '[1, 2, 3, {"a": 1}]'
    result7 = execute({'text': valid_json_array_input})
    print(f"Input: {valid_json_array_input}")
    print(f"Result: {result7}")
    assert result7['success'] is True
    assert result7['spoken'] == 'This is a valid JSON.'

    # Test case 8: Invalid JSON array
    invalid_json_array_input = '[1, 2, 3, {"a": 1}'
    result8 = execute({'text': invalid_json_array_input})
    print(f"Input: {invalid_json_array_input}")
    print(f"Result: {result8}")
    assert result8['success'] is False
    assert 'Invalid JSON' in result8['error']
    assert 'This is not a valid JSON.' in result8['spoken']

    # Test case 9: JSON embedded in text with surrounding characters
    embedded_json_input = 'Here is some text and then {"key": "value"} and more text.'
    result9 = execute({'text': embedded_json_input})
    print(f"Input: {embedded_json_input}")
    print(f"Result: {result9}")
    assert result9['success'] is True
    assert result9['spoken'] == 'This is a valid JSON.'

    # Test case 10: JSON embedded in text with newlines
    embedded_json_newline_input = '{\n  "key": "value"\n}'
    result10 = execute({'text': embedded_json_newline_input})
    print(f"Input: {embedded_json_newline_input}")
    print(f"Result: {result10}")
    assert result10['success'] is True
    assert result10['spoken'] == 'This is a valid JSON.'


    print("\njson_validator skill tests completed.")
    print(f"get_info(): {get_info()}")
    print(f"health_check(): {health_check()}")
```