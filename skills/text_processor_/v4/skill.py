import re
import subprocess

def get_info():
    return {
        "name": "text_processor",
        "version": "v4",
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

            # Count characters (including spaces and punctuation)
            char_count = len(text)

            # Count words (split by whitespace)
            words = text.split()
            word_count = len(words)

            # Count sentences (simple heuristic: count '.', '!', '?')
            sentence_enders = re.compile(r'[.!?]+')
            sentence_count = len(sentence_enders.findall(text))
            if sentence_count == 0 and char_count > 0: # Handle case with text but no punctuation
                sentence_count = 1

            return {
                'success': True,
                'word_count': word_count,
                'sentence_count': sentence_count,
                'character_count': char_count
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}

def execute(params: dict) -> dict:
    processor = TextProcessor()
    return processor.execute(params)

if __name__ == '__main__':
    # Example usage
    test_text_1 = "To jest pierwsze zdanie. A to jest drugie! Czy to trzecie?"
    params_1 = {'text': test_text_1}
    result_1 = execute(params_1)
    print(f"Test 1 Result: {result_1}")

    test_text_2 = "Jedno słowo."
    params_2 = {'text': test_text_2}
    result_2 = execute(params_2)
    print(f"Test 2 Result: {result_2}")

    test_text_3 = ""
    params_3 = {'text': test_text_3}
    result_3 = execute(params_3)
    print(f"Test 3 Result: {result_3}")

    test_text_4 = "No punctuation here"
    params_4 = {'text': test_text_4}
    result_4 = execute(params_4)
    print(f"Test 4 Result: {result_4}")

    print(f"Info: {get_info()}")
    print(f"Health Check: {health_check()}")