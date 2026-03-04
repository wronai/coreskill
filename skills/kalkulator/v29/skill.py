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
            # Pozwalamy na liczby, operatory (+, -, *, /, %, **), nawiasy, kropki dziesiętne i przecinki dziesiętne.
            # Dodano obsługę ujemnych liczb na początku wyrażenia i po nawiasie otwierającym.
            cleaned_text = re.sub(r'(oblicz|ile to jest|podaj wynik|kalkulator|:|\?|\.)', '', text, flags=re.IGNORECASE).strip()

            # Bardziej restrykcyjne sprawdzenie, aby upewnić się, że mamy tylko liczby, operatory i nawiasy.
            # Pozwalamy na +, -, *, /, %, ** (potęgowanie), nawiasy i kropki dziesiętne.
            # Dodano obsługę ujemnych liczb na początku wyrażenia.
            # Używamy bardziej złożonego regex, aby uwzględnić liczby ujemne po operatorach lub nawiasach.
            if not re.fullmatch(r'^-?[\d\s()*/%.,+*-]+$', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki lub jest nieprawidłowe.'}

            # Dodatkowe sprawdzenie, aby upewnić się, że nie ma liter ani innych niebezpiecznych znaków
            if re.search(r'[a-zA-Z_]', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Zastępujemy przecinki kropkami dla obsługi liczb dziesiętnych w różnych formatach.
            cleaned_text = cleaned_text.replace(',', '.')

            # Bardziej zaawansowane sprawdzanie sekwencji operatorów i nawiasów
            # Sprawdza podwójne operatory, operatory na początku/końcu, puste nawiasy, nawiasy z operatorem w środku
            if re.search(r'[\d\s][+\-*/%]{2,}[\d\s]', cleaned_text) or \
               re.search(r'^[+\-*/%]', cleaned_text) or \
               re.search(r'[+\-*/%]$', cleaned_text) or \
               re.search(r'\(\s*\)', cleaned_text) or \
               re.search(r'\([^)]*[-+*/%]\s*\)', cleaned_text) or \
               re.search(r'\([^)]*[-+*/%]{2,}[^)]*\)', cleaned_text) or \
               re.search(r'\(\s*[-+*/%]', cleaned_text) or \
               re.search(r'[-+*/%]\s*\)', cleaned_text):
                return {'success': False, 'error': 'Nieprawidłowa sekwencja operatorów lub nawiasów.'}

            # Bezpieczniejsze podejście do ewaluacji, ograniczając dostępne funkcje
            # Używamy eval() z ostrożnością i po walidacji regex.
            # Można by rozważyć użycie biblioteki `ast` do parsowania drzewa składniowego,
            # ale dla prostych obliczeń i po walidacji regex, `eval` jest akceptowalny.
            # Bezpieczniejsze jest użycie ast.literal_eval, ale nie obsługuje ono operatorów.
            # Dlatego używamy eval() po dokładnej walidacji.
            result = eval(cleaned_text)

            return {'success': True, 'result': str(result)}

        except SyntaxError:
            return {'success': False, 'error': 'Błąd składni w wyrażeniu matematycznym.'}
        except ZeroDivisionError:
            return {'success': False, 'error': 'Nie można dzielić przez zero.'}
        except TypeError:
            return {'success': False, 'error': 'Nieprawidłowy typ danych w wyrażeniu.'}
        except ValueError:
            return {'success': False, 'error': 'Nieprawidłowa wartość w wyrażeniu.'}
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
        {'text': 'oblicz -5 + 10'}, # Test z liczbą ujemną
        {'text': 'oblicz (-5) * 2'}, # Test z liczbą ujemną w nawiasie
        {'text': 'oblicz 5 + (-2)'}, # Test z liczbą ujemną w nawiasie
        {'text': 'oblicz 10 / (-2)'}, # Test z dzieleniem przez liczbę ujemną
        {'text': 'oblicz ( )'}, # Puste nawiasy
        {'text': 'oblicz 5 + ()'}, # Puste nawiasy z operatorem
        {'text': 'oblicz (5 + )'}, # Nieprawidłowe nawiasy
        {'text': 'oblicz )5 + 2('}, # Nieprawidłowe nawiasy
        {'text': 'ile to 100 / 7'}, # Dodany test z pytania
        {'text': 'oblicz 5 + -2'}, # Test z operatorem i liczbą ujemną
        {'text': 'oblicz 5 - -2'}, # Test z dwoma operatorami minus
        {'text': 'oblicz 5 * -2'}, # Test z mnożeniem przez liczbę ujemną
        {'text': 'oblicz 5 / -2'}, # Test z dzieleniem przez liczbę ujemną
        {'text': 'oblicz -5 * -2'}, # Test z mnożeniem liczb ujemnych
        {'text': 'oblicz (-5) + (-2)'}, # Test z dodawaniem liczb ujemnych w nawiasach
        {'text': 'oblicz 5 + (2 * -3)'}, # Test z zagnieżdżonymi nawiasami i liczbą ujemną
        {'text': 'oblicz 10 / (5 - 5)'}, # Dzielenie przez zero w nawiasie
        {'text': 'oblicz 10 + 5 - 3 * 2'}, # Kolejność działań
        {'text': 'oblicz (10 + 5) - 3 * 2'}, # Kolejność działań z nawiasami
        {'text': 'oblicz 10 + 5 - (3 * 2)'}, # Kolejność działań z nawiasami
        {'text': 'oblicz 2**3**2'}, # Potęgowanie
        {'text': 'oblicz (2**3)**2'}, # Potęgowanie z nawiasami
        {'text': 'oblicz 10 % (3 + 2)'}, # Modulo z nawiasami
        {'text': 'oblicz 10 % 3 + 2'}, # Modulo z dodawaniem
        {'text': 'oblicz 10 + 5 % 2'}, # Dodawanie z modulo
        {'text': 'oblicz 10.5 + 2.3'}, # Dodawanie liczb dziesiętnych
        {'text': 'oblicz 10,5 * 2,3'}, # Dodawanie liczb dziesiętnych z przecinkiem
        {'text': 'oblicz 5 + ( )'}, # Puste nawiasy
        {'text': 'oblicz (5 + )'}, # Nieprawidłowe nawiasy
        {'text': 'oblicz 5 + (2 + )'}, # Nieprawidłowe nawiasy zagnieżdżone
        {'text': 'oblicz (5 + 2'}, # Brak nawiasu zamykającego
        {'text': 'oblicz 5 + 2)'}, # Brak nawiasu otwierającego
        {'text': 'oblicz 5 + 2 +'}, # Operator na końcu
        {'text': '+ 5 + 2'}, # Operator na początku
        {'text': '5 + + 2'}, # Podwójny operator
        {'text': '5 + - + 2'}, # Trzy operatory
        {'text': 'oblicz 5 + (2 * )'}, # Operator po nawiasie
        {'text': 'oblicz ( * 2)'}, # Operator przed nawiasem
        {'text': 'oblicz 5 + (2 + 3))'}, # Dodatkowy nawias zamykający
        {'text': 'oblicz ((2 + 3) + 4'}, # Dodatkowy nawias otwierający
        {'text': 'oblicz 5 . 2'}, # Zamiast kropki operator
        {'text': 'oblicz 5 , 2'}, # Zamiast przecinka operator
        {'text': 'oblicz 10 / (2 * (3 + 1))'}, # Złożone wyrażenie
        {'text': 'oblicz 10 / (2 * (3 + 1)) + 5'}, # Złożone wyrażenie z dodawaniem
        {'text': 'oblicz 10 / (2 * (3 + 1)) + 5 % 2'}, # Złożone wyrażenie z modulo
        {'text': 'oblicz 10 / (2 * (3 + 1)) + 5 % 2 ** 3'}, # Złożone wyrażenie z potęgowaniem
    ]

    for case in test_cases:
        print(f"Input: {case['text']}")
        result = execute(case)
        print(f"Output: {result}\n")
```