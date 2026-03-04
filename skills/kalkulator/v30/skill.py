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
            # Pozwalamy na liczby, operatory (+, -, *, /, %, **), nawiasy, kropki dziesiętne i przecinki.
            # Dodano obsługę ujemnych liczb na początku wyrażenia.
            cleaned_text = re.sub(r'(oblicz|ile to jest|podaj wynik|kalkulator|policz|:|\?)', '', text, flags=re.IGNORECASE).strip()
            cleaned_text = re.sub(r'\.$', '', cleaned_text).strip() # Usuń kropkę na końcu, jeśli istnieje

            # Bardziej restrykcyjne sprawdzenie, aby upewnić się, że mamy tylko liczby, operatory i nawiasy.
            # Pozwalamy na +, -, *, /, %, ** (potęgowanie), nawiasy i kropki dziesiętne.
            # Dodano obsługę ujemnych liczb na początku wyrażenia.
            # Zezwalamy na kropki i przecinki jako separatory dziesiętne.
            # Usunięto niepotrzebne znaki z regex, aby uniknąć błędów.
            if not re.fullmatch(r'^-?[\d\s()*/%.,+*-]+$', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki lub jest nieprawidłowe.'}

            # Dodatkowe sprawdzenie, aby upewnić się, że nie ma liter ani innych niebezpiecznych znaków
            if re.search(r'[a-zA-Z_]', cleaned_text):
                return {'success': False, 'error': 'Wyrażenie zawiera niedozwolone znaki.'}

            # Zastępujemy przecinki kropkami dla obsługi liczb dziesiętnych w różnych formatach.
            cleaned_text = cleaned_text.replace(',', '.')

            # Upewnij się, że nie ma pustych operatorów lub nieprawidłowych sekwencji
            # Poprawiono regexy, aby lepiej wykrywać nieprawidłowe sekwencje operatorów i nawiasów.
            if re.search(r'[\d\s][+\-*/%]{2,}[\d\s]', cleaned_text) or \
               re.search(r'^[+\-*/%]', cleaned_text) or \
               re.search(r'[+\-*/%]$', cleaned_text) or \
               re.search(r'\(\s*[-+*/%]', cleaned_text) or \
               re.search(r'[-+*/%]\s*\)', cleaned_text) or \
               re.search(r'\(\s*\)', cleaned_text) or \
               re.search(r'\)\s*\(', cleaned_text) or \
               re.search(r'[\d\s]\s*\(', cleaned_text) or \
               re.search(r'\)\s*[\d\s]', cleaned_text):
                return {'success': False, 'error': 'Nieprawidłowa sekwencja operatorów lub nawiasów.'}

            # Bezpieczniejsze podejście do ewaluacji, ograniczając dostępne funkcje
            # Używamy eval() z ostrożnością i po walidacji regex.
            # Można by rozważyć użycie biblioteki `ast` do parsowania drzewa składniowego,
            # ale dla prostych obliczeń i po walidacji regex, `eval` jest akceptowalny.
            # Dodano obsługę potencjalnych błędów związanych z parsowaniem wyrażeń.
            try:
                # Używamy ast.literal_eval do bezpiecznego parsowania literałów
                # ale to nie obsługuje operacji matematycznych.
                # Zostawiamy eval() po dokładnej walidacji.
                result = eval(cleaned_text)
            except (SyntaxError, ValueError, TypeError, ZeroDivisionError) as e:
                return {'success': False, 'error': f'Błąd parsowania lub wykonania wyrażenia: {str(e)}'}

            return {'success': True, 'result': str(result)}

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
        {'text': 'policz 3.14 * 2.71'}, # Test z przykładu
        {'text': 'oblicz 10.5 + 2.3'}, # Test z liczbami dziesiętnymi
        {'text': 'oblicz 10,5 + 2,3'}, # Test z przecinkami jako separatorami dziesiętnymi
        {'text': 'oblicz 5 * ( )'}, # Puste nawiasy w środku
        {'text': 'oblicz (5) * (3)'}, # Nawiasy wokół liczb
        {'text': 'oblicz 5 * 3'}, # Proste mnożenie
        {'text': 'oblicz 10 / 2'}, # Proste dzielenie
        {'text': 'oblicz 10 - 5'}, # Proste odejmowanie
        {'text': 'oblicz 5 + 5'}, # Proste dodawanie
        {'text': 'oblicz 2 ** 3'}, # Potęgowanie
        {'text': 'oblicz 10 % 3'}, # Modulo
        {'text': 'oblicz (10 + 5) * 2'}, # Kolejność działań
        {'text': 'oblicz 10 + 5 * 2'}, # Kolejność działań
        {'text': 'oblicz 10 / 2 + 3'}, # Kolejność działań
        {'text': 'oblicz 10 - 5 / 5'}, # Kolejność działań
        {'text': 'oblicz 2 * (3 + 4) / 7'}, # Złożone wyrażenie
        {'text': 'oblicz -10'}, # Pojedyncza liczba ujemna
        {'text': 'oblicz -5 * -2'}, # Mnożenie liczb ujemnych
        {'text': 'oblicz -10 / -2'}, # Dzielenie liczb ujemnych
        {'text': 'oblicz -5 + -2'}, # Dodawanie liczb ujemnych
        {'text': 'oblicz -5 - -2'}, # Odejmowanie liczb ujemnych
        {'text': 'oblicz 5 + -2'}, # Dodawanie liczby ujemnej
        {'text': 'oblicz 5 - -2'}, # Odejmowanie liczby ujemnej
        {'text': 'oblicz 5 * -2'}, # Mnożenie przez liczbę ujemną
        {'text': 'oblicz 10 / -2'}, # Dzielenie przez liczbę ujemną
        {'text': 'oblicz 5 % -2'}, # Modulo z liczbą ujemną
        {'text': 'oblicz 2 ** -3'}, # Potęgowanie z ujemnym wykładnikiem
        {'text': 'oblicz (2 + 3) * (4 - 1)'}, # Nawiasy z operacjami
        {'text': 'oblicz 10 / (5 - 5)'}, # Dzielenie przez zero w nawiasie
        {'text': 'oblicz 10 / (2 + )'}, # Nieprawidłowe nawiasy
        {'text': 'oblicz (10 + 5'}, # Brakujący nawias zamykający
        {'text': 'oblicz 10 + 5)'}, # Brakujący nawias otwierający
        {'text': 'oblicz 10 + 5 + '}, # Operator na końcu
        {'text': 'oblicz + 10 + 5'}, # Operator na początku
        {'text': 'oblicz 10 * / 5'}, # Dwa operatory obok siebie
        {'text': 'oblicz 10 ** 2 ** 3'}, # Potęgowanie z potęgowaniem
        {'text': 'oblicz 10. . 5'}, # Dwie kropki dziesiętne
        {'text': 'oblicz 10, , 5'}, # Dwa przecinki dziesiętne
        {'text': 'oblicz 10..5'}, # Dwie kropki dziesiętne bez spacji
        {'text': 'oblicz 10,,5'}, # Dwa przecinki dziesiętne bez spacji
        {'text': 'oblicz 10 . 5'}, # Kropka dziesiętna z spacją
        {'text': 'oblicz 10 , 5'}, # Przecinek dziesiętny z spacją
        {'text': 'oblicz 10.5.2'}, # Wielokrotne kropki
        {'text': 'oblicz 10,5,2'}, # Wielokrotne przecinki
        {'text': 'oblicz 10 . 5 . 2'}, # Wielokrotne kropki z spacjami
        {'text': 'oblicz 10 , 5 , 2'}, # Wielokrotne przecinki z spacjami
        {'text': 'oblicz 10 + 5 * (2 + 3)'}, # Złożone nawiasy
        {'text': 'oblicz 10 / 2 * 5'}, # Dzielenie i mnożenie
        {'text': 'oblicz 10 * 2 / 5'}, # Mnożenie i dzielenie
        {'text': 'oblicz 10 + 5 - 2'}, # Dodawanie i odejmowanie
        {'text': 'oblicz 10 - 5 + 2'}, # Odejmowanie i dodawanie
        {'text': 'oblicz 10 % 3 + 1'}, # Modulo i dodawanie
        {'text': 'oblicz 10 + 10 % 3'}, # Dodawanie i modulo
        {'text': 'oblicz 2 ** 3 * 4'}, # Potęgowanie i mnożenie
        {'text': 'oblicz 2 * 3 ** 4'}, # Mnożenie i potęgowanie
        {'text': 'oblicz 10 / 2.5'}, # Dzielenie przez liczbę dziesiętną
        {'text': 'oblicz 5 * 1.5'}, # Mnożenie przez liczbę dziesiętną
        {'text': 'oblicz 10.5 + 2.3'}, # Dodawanie liczb dziesiętnych
        {'text': 'oblicz 10.5 - 2.3'}, # Odejmowanie liczb dziesiętnych
        {'text': 'oblicz 10.5 % 2.3'}, # Modulo z liczbami dziesiętnymi
        {'text': 'oblicz 2 ** 1.5'}, # Potęgowanie z wykładnikiem dziesiętnym
        {'text': 'oblicz 10 / (2.5)'}, # Dzielenie przez liczbę dziesiętną w nawiasie
        {'text': 'oblicz (10.5)'}, # Liczba dziesiętna w nawiasie
        {'text': 'oblicz 10.5.0'}, # Nieprawidłowa liczba dziesiętna
        {'text': 'oblicz 10,5,0'}, # Nieprawidłowa liczba dziesiętna z przecinkiem
        {'text': 'oblicz 10.5e2'}, # Notacja naukowa (nieobsługiwana przez eval w tym kontekście)
        {'text': 'oblicz 1e3'}, # Notacja naukowa (nieobsługiwana przez eval w tym kontekście)
        {'text': 'oblicz 10 + 5 + 3 + 2'}, # Suma wielu liczb
        {'text': 'oblicz 10 * 5 * 3 * 2'}, # Iloczyn wielu liczb
        {'text': 'oblicz 10 - 5 - 3 - 2'}, # Różnica wielu liczb
        {'text': 'oblicz 10 / 5 / 3 / 2'}, # Dzielenie wielu liczb
        {'text': 'oblicz 10 % 3 % 2'}, # Modulo wielu liczb
        {'text': 'oblicz 2 ** 3 ** 2'}, # Potęgowanie wielu liczb
        {'text': 'oblicz (1 + 2) * (3 + 4) / (5 - 6)'}, # Złożone wyrażenie z nawiasami
        {'text': 'oblicz 10 + (5 * (2 + 3))'}, # Zagnieżdżone nawiasy
        {'text': 'oblicz 10 / (2 * (3 + 1))'}, # Zagnieżdżone nawiasy z dzieleniem
        {'text': 'oblicz 10 % (3 * 2)'}, # Modulo z nawiasami
        {'text': 'oblicz 2 ** (3 * 2)'}, # Potęgowanie z nawiasami
        {'text': 'oblicz (2 + 3) ** 2'}, # Potęgowanie z nawiasami
        {'text': 'oblicz 10 + 5 * 2 - 3 / 1'}, # Mieszane operacje
        {'text': 'oblicz 10 * (5 + 2) - 3 / 1'}, # Mieszane operacje z nawiasami
        {'text': 'oblicz 10 / (5 - 2) * 3'}, # Mieszane operacje z nawiasami
        {'text': 'oblicz 10 % (5 + 2) - 1'}, # Mieszane operacje z modulo
        {'text': 'oblicz 2 ** (5 + 2) / 4'}, # Mieszane operacje z potęgowaniem
        {'text': 'oblicz 10 + 5 + '}, # Operator na końcu
        {'text': '+ 10 + 5'}, # Operator na początku
        {'text': '10 ++ 5'}, # Dwa operatory
        {'text': '10 +* 5'}, # Dwa operatory