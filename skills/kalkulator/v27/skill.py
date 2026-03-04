import subprocess
import re
import ast

def get_info():
    return {
        'name': 'kalkulator',
        'version': 'v1',
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
            # Zabezpieczenie przed potencjalnie niebezpiecznymi wyrażeniami
            cleaned_text = re.sub(r'(oblicz|ile to jest|podaj wynik|kalkulator|:|\?|\.)', '', text, flags=re.IGNORECASE).strip()

            # Bardziej restrykcyjne sprawdzenie, aby upewnić się, że mamy tylko liczby, operatory i nawiasy
            # Pozwalamy na +, -, *, /, %, ** (potęgowanie), nawiasy i kropki dziesiętne.
            if not re.fullmatch(r'[-+]?[\d\s()*/%.,+*-]+', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki lub jest nieprawidłowe.'}

            # Dodatkowe sprawdzenie, aby upewnić się, że nie ma liter ani innych niebezpiecznych znaków
            if re.search(r'[a-zA-Z_]', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Bezpieczniejsze podejście do ewaluacji, ograniczając dostępne funkcje
            # Używamy ast.literal_eval, ale to nie obsługuje operacji.
            # Dlatego stosujemy eval() z ostrożnością i po walidacji regex.
            # Zastępujemy przecinki kropkami dla obsługi liczb dziesiętnych w różnych formatach.
            cleaned_text = cleaned_text.replace(',', '.')

            # Upewnij się, że nie ma pustych operatorów lub nieprawidłowych sekwencji
            if re.search(r'[\d\s][+\-*/%]{2,}[\d\s]', cleaned_text) or \
               re.search(r'[\d\s][+\-*/%][+\-*/%][\d\s]', cleaned_text) or \
               re.search(r'^[+\-*/%]', cleaned_text) or \
               re.search(r'[+\-*/%]$', cleaned_text):
                return {'success': False, 'error': 'Nieprawidłowa sekwencja operatorów.'}

            # Ograniczenie do bezpiecznych operacji matematycznych
            # Używamy eval z ostrożnością, po dokładnej walidacji.
            # Można by rozważyć użycie biblioteki `ast` do parsowania drzewa składniowego,
            # ale dla prostych obliczeń i po walidacji regex, `eval` jest akceptowalny.
            result = eval(cleaned_text)

            return {'success': True, 'result': str(result)}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu matematycznym.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Nie można dzielić przez zero.'}
        except TypeError:
            return {'success': False, 'error': 'Nieprawidłowy typ danych w wyrażeniu.'}
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
        {'text': 'oblicz 10 % 3'},
        {'text': 'ile to jest (2+3)*(4-1)'},
        {'text': 'kalkulator 5.'},
        {'text': 'oblicz 5 + '},
        {'text': 'oblicz 2,5 * 2'}, # Test z przecinkiem
        {'text': 'oblicz 10 / 3'},
        {'text': 'oblicz 2 + 2 * 3'},
        {'text': 'oblicz 10 / (2 + 2)'},
        {'text': 'oblicz 10 ++ 5'}, # Nieprawidłowa sekwencja operatorów
        {'text': 'oblicz * 5'}, # Nieprawidłowy operator na początku
        {'text': 'oblicz 5 *'}, # Nieprawidłowy operator na końcu
        {'text': 'oblicz 10 / 2.5'},
    ]

    for case in test_cases:
        print(f"Input: {case['text']}")
        result = execute(case)
        print(f"Output: {result}\n")
```