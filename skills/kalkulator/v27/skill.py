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
            return {'success': False, 'error': 'Brak tekstu do przetworzenia.', 'spoken': 'Proszę podać wyrażenie matematyczne.'}

        try:
            # Usuń słowa kluczowe i znaki interpunkcyjne, zostawiając tylko wyrażenie matematyczne
            # Zabezpieczenie przed potencjalnie niebezpiecznymi wyrażeniami
            cleaned_text = re.sub(r'(oblicz|ile to jest|podaj wynik|kalkulator|:|\?|\.)', '', text, flags=re.IGNORECASE).strip()

            # Bardziej restrykcyjne sprawdzenie, aby upewnić się, że mamy tylko liczby, operatory i nawiasy
            # Pozwalamy na +, -, *, /, %, ** (potęgowanie) i nawiasy.
            if not re.fullmatch(r'[-+]?[\d\s()*/%+\-.]+', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki lub jest nieprawidłowe.', 'spoken': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Upewnij się, że nie ma liter ani innych niebezpiecznych znaków
            if re.search(r'[a-zA-Z_]', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.', 'spoken': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Bezpieczniejsze podejście do ewaluacji, ograniczając dostępne funkcje
            # Używamy ast.literal_eval, ale to nie obsługuje operacji.
            # Dlatego stosujemy eval() z ostrożnością i po walidacji regex.
            # Ograniczamy dozwolone znaki i operatory.
            
            # Sprawdzenie czy wyrażenie jest puste po czyszczeniu
            if not cleaned_text:
                return {'success': False, 'error': 'Wyrażenie matematyczne jest puste.', 'spoken': 'Proszę podać wyrażenie matematyczne.'}

            # Dodatkowe zabezpieczenie przed potencjalnie niebezpiecznymi konstrukcjami
            # np. wywołaniami funkcji, które nie są matematyczne.
            # Pozwalamy tylko na podstawowe operatory i liczby.
            allowed_chars = set("0123456789+-*/%(). ")
            if not all(char in allowed_chars for char in cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.', 'spoken': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Ograniczamy funkcje dostępne w eval, ale w tym przypadku, ponieważ użyliśmy regex,
            # nie ma potrzeby dodatkowego ograniczania, o ile regex jest wystarczająco restrykcyjny.
            # Bezpieczniej jest użyć ast.parse i przejść przez drzewo, ale dla prostych obliczeń
            # i po walidacji regex, eval jest akceptowalny.
            
            result = eval(cleaned_text)

            return {'success': True, 'result': str(result), 'spoken': f'Wynik to {str(result)}'}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu matematycznym.', 'spoken': 'Błąd składni w wyrażeniu.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Nie można dzielić przez zero.', 'spoken': 'Nie można dzielić przez zero.'}
        except TypeError:
            return {'success': False, 'error': 'Nieprawidłowy typ danych w wyrażeniu.', 'spoken': 'Nieprawidłowy typ danych w wyrażeniu.'}
        except ValueError:
            return {'success': False, 'error': 'Nieprawidłowa wartość w wyrażeniu.', 'spoken': 'Nieprawidłowa wartość w wyrażeniu.'}
        except Exception as e:
            return {'success': False, 'error': f'Wystąpił nieoczekiwany błąd: {str(e)}', 'spoken': f'Wystąpił nieoczekiwany błąd: {str(e)}'}

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
        {'text': 'kalkulator 5.'}, # Test z kropką na końcu
        {'text': 'oblicz 5 + '}, # Test z niekompletnym wyrażeniem
        {'text': 'oblicz 2^3'}, # Test z potęgowaniem za pomocą ^
        {'text': 'oblicz 10 / 3.14'},
        {'text': 'oblicz (10 + 5) * 2 / (6 - 4)'},
        {'text': 'oblicz sin(90)'}, # Test z niedozwoloną funkcją
        {'text': 'oblicz 10 + '}, # Test z niekompletnym wyrażeniem po czyszczeniu
        {'text': 'oblicz '}, # Test z pustym wyrażeniem po czyszczeniu
    ]

    for case in test_cases:
        print(f"Input: {case['text']}")
        result = execute(case)
        print(f"Output: {result}\n")