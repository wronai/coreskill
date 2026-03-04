import json
import subprocess

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

        try:
            json.loads(input_text)
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
    # Extracting JSON from the text
    try:
        start_index = user_query_input.find('{')
        end_index = user_query_input.rfind('}') + 1
        if start_index != -1 and end_index != 0:
            json_to_validate = user_query_input[start_index:end_index]
            result6 = execute({'text': json_to_validate})
            print(f"Input: {user_query_input} (extracted: {json_to_validate})")
            print(f"Result: {result6}")
            assert result6['success'] is True
            assert result6['spoken'] == 'This is a valid JSON.'
        else:
            print(f"Could not extract JSON from: {user_query_input}")
            assert False, "Failed to extract JSON from user query"
    except Exception as e:
        print(f"Error processing user query: {e}")
        assert False, "Error during user query processing"


    print("\njson_validator skill tests completed.")
    print(f"get_info(): {get_info()}")
    print(f"health_check(): {health_check()}")
```