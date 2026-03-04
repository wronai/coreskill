import re
import subprocess

def get_info():
    return {
        'name': 'text_processor',
        'version': 'v1',
        'description': 'Processes text to count words, sentences, and characters.'
    }

def health_check():
    return {'status': 'ok'}

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
    test_text = "To jest przykładowe zdanie. Jak się masz? Mam się dobrze!"
    params = {'text': test_text}
    result = execute(params)
    print(f"Test Result: {result}")

    params_empty = {'text': ''}
    result_empty = execute(params_empty)
    print(f"Test Result (empty text): {result_empty}")

    params_no_text_key = {}
    result_no_text_key = execute(params_no_text_key)
    print(f"Test Result (no text key): {result_no_text_key}")
```