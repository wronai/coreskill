import subprocess
import re

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v25',
        'description': 'Oblicza wyrażenia matematyczne.'
    }

def health_check():
    return {'status': 'ok'}

class Kalkulator:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '')
        if not text:
            return {'success': False, 'error': 'Brak tekstu do przetworzenia.'}

        try:
            # Usuń słowa kluczowe i znaki interpunkcyjne, zostawiając tylko wyrażenie matematyczne
            expression = re.sub(r'(oblicz|ile to jest|podaj wynik|kalkulator|:|\?|\.)', '', text, flags=re.IGNORECASE).strip()

            # Proste zabezpieczenie przed niebezpiecznymi poleceniami
            if re.search(r'[a-zA-Z_]', expression):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Użyj eval() ostrożnie, po wcześniejszym oczyszczeniu
            result = eval(expression)

            return {'success': True, 'result': str(result)}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu matematycznym.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Nie można dzielić przez zero.'}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}'}

def execute(params: dict) -> dict:
    kalkulator_instance = Kalkulator()
    return kalkulator_instance.execute(params)

if __name__ == '__main__':
    # Test cases
    test_cases = [
        {'text': 'oblicz 2 + 2'},
        {'text': 'ile to jest 5 * (10 - 3)'},
        {'text': 'podaj wynik 100 / 4'},
        {'text': 'kalkulator 2**10'},
        {'text': 'oblicz 10 / 0'},
        {'text': 'ile to jest abc + 5'},
        {'text': ''},
        {'text': 'oblicz 10 + (5 * 2)'},
    ]

    for case in test_cases:
        print(f"Input: {case['text']}")
        result = execute(case)
        print(f"Output: {result}\n")
```