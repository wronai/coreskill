import re
import subprocess

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v1',
        'description': 'Oblicza wyrażenia matematyczne'
    }

def health_check():
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '')
        if not text:
            return {'success': False, 'error': 'Brak tekstu do przetworzenia'}

        expression = self._extract_expression(text)
        if not expression:
            return {'success': False, 'error': 'Nie można znaleźć wyrażenia matematycznego'}

        try:
            result = self._calculate(expression)
            return {'success': True, 'result': str(result), 'spoken': f'Wynik to {result}'}
        except ValueError as e:
            return {'success': False, 'error': str(e), 'spoken': str(e)}
        except Exception as e:
            return {'success': False, 'error': f'Błąd obliczeń: {e}', 'spoken': f'Wystąpił błąd podczas obliczeń: {e}'}

    def _extract_expression(self, text: str) -> str | None:
        match = re.search(r'(?:oblicz|ile to)\s+(.+)', text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        # Check if the entire text is a valid mathematical expression
        if re.fullmatch(r'[\d\s\+\-\*\/\.\(\)]+', text):
            return text.strip()
            
        return None

    def _calculate(self, expression: str) -> float:
        allowed_chars = "0123456789+-*/.() "
        if not all(c in allowed_chars for c in expression):
            raise ValueError("Niedozwolone znaki w wyrażeniu")
            
        # Using eval is generally unsafe, but for this specific, restricted case with allowed_chars check,
        # it might be acceptable for a simple calculator skill.
        # A more robust solution would involve parsing the expression with ast module or a dedicated library.
        try:
            result = eval(expression)
            return float(result)
        except ZeroDivisionError:
            raise ValueError("Dzielenie przez zero jest niedozwolone")
        except Exception as e:
            raise ValueError(f"Nieprawidłowe wyrażenie matematyczne: {e}")


def execute(params: dict) -> dict:
    skill = Kalkulator()
    return skill.execute(params)

if __name__ == '__main__':
    test_cases = [
        {'text': 'oblicz 2 + 2', 'expected_success': True, 'expected_result': '4.0'},
        {'text': 'ile to jest 5 * (3 + 2)', 'expected_success': True, 'expected_result': '25.0'},
        {'text': '10 / 2 - 1', 'expected_success': True, 'expected_result': '4.0'},
        {'text': 'oblicz 10 / 0', 'expected_success': False, 'expected_error': 'Dzielenie przez zero jest niedozwolone'},
        {'text': 'nie wiem co obliczyć', 'expected_success': False, 'expected_error': 'Nie można znaleźć wyrażenia matematycznego'},
        {'text': 'oblicz 2 + abc', 'expected_success': False, 'expected_error': 'Niedozwolone znaki w wyrażeniu'},
        {'text': '2**3', 'expected_success': False, 'expected_error': 'Niedozwolone znaki w wyrażeniu'},
        {'text': 'oblicz (5+3)*2/4', 'expected_success': True, 'expected_result': '4.0'},
        {'text': '1.5 * 2', 'expected_success': True, 'expected_result': '3.0'},
        {'text': 'oblicz 7', 'expected_success': True, 'expected_result': '7.0'},
    ]

    for case in test_cases:
        result = execute(case)
        print(f"Input: '{case['text']}'")
        print(f"Output: {result}")
        if case['expected_success']:
            assert result['success'] is True
            assert result['result'] == case['expected_result']
        else:
            assert result['success'] is False
            assert case['expected_error'] in result.get('error', '')
        print("-" * 20)

    print("Wszystkie testy zakończone pomyślnie.")