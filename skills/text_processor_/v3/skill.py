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
            
            # Improved sentence splitting to handle cases like "Mr. Smith" or "e.g."
            # This regex splits by '.', '!', '?' followed by whitespace or end of string,
            # but tries to avoid splitting after abbreviations.
            sentences = re.split(r'(?<!\w\.\w.)(?<![A-Z][a-z]\.)(?<=\.|\?|\!)\s', text)
            # Filter out any empty strings that might result from splitting
            sentences = [s for s in sentences if s.strip()]
            sentence_count = len(sentences)

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
    test_text = "To jest przykładowe zdanie. Jak się masz? Mam się dobrze! Pan Smith mieszka w Londynie. Np. to jest przykład."
    params = {'text': test_text}
    result = execute(params)
    print(f"Test Result: {result}")

    params_empty = {'text': ''}
    result_empty = execute(params_empty)
    print(f"Test Result (empty text): {result_empty}")

    params_no_text_key = {}
    result_no_text_key = execute(params_no_text_key)
    print(f"Test Result (no text key): {result_no_text_key}")

    test_text_complex = "This is the first sentence. Is this the second? Yes, it is! Mr. Jones went to the store. e.g. this is an example."
    params_complex = {'text': test_text_complex}
    result_complex = execute(params_complex)
    print(f"Test Result (complex text): {result_complex}")