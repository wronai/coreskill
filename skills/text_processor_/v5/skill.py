import re
import subprocess

def get_info():
    return {
        "name": "text_processor",
        "version": "v5",
        "description": "Processes text to count words, sentences, and characters."
    }

def health_check():
    return {"status": "ok"}

class TextProcessor:
    def execute(self, params: dict) -> dict:
        try:
            text = params.get('text', '')
            if not text:
                return {'success': False, 'message': 'No text provided.'}

            word_count = len(text.split())
            sentence_count = len(re.split(r'[.!?]+', text)) - 1
            char_count = len(text)

            return {
                'success': True,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'char_count': char_count
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

def execute(params: dict) -> dict:
    processor = TextProcessor()
    return processor.execute(params)

if __name__ == '__main__':
    test_params = {'text': 'This is a sample sentence. This is another one! And a third?'}
    result = execute(test_params)
    print(f"Test Result: {result}")

    test_params_empty = {'text': ''}
    result_empty = execute(test_params_empty)
    print(f"Test Result (empty text): {result_empty}")

    test_params_no_punctuation = {'text': 'Just a few words'}
    result_no_punctuation = execute(test_params_no_punctuation)
    print(f"Test Result (no punctuation): {result_no_punctuation}")
```