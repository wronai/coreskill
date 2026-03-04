import subprocess
import os
import shutil
import re

def get_info():
    return {
        'name': 'zarz_dzania',
        'version': 'v6',
        'description': 'Skill do zarządzania plikami: listowanie, kopiowanie, info o pliku.'
    }

def health_check():
    return {'status': 'ok'}

class ZarzadzaniaSkill:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '').lower()

        try:
            if 'listuj' in text or 'ls' in text:
                return self.list_files(text)
            elif 'kopiuj' in text or 'cp' in text:
                return self.copy_file(text)
            elif 'info o pliku' in text or 'stat' in text:
                return self.file_info(text)
            else:
                return {'success': False, 'message': 'Nieznane polecenie. Dostępne: listuj, kopiuj, info o pliku.'}
        except Exception as e:
            return {'success': False, 'message': f'Wystąpił błąd: {e}'}

    def list_files(self, text):
        match = re.search(r'(listuj|ls)\s+(.+)', text)
        if match:
            path = match.group(2).strip()
        else:
            path = '.'

        if not os.path.exists(path):
            return {'success': False, 'message': f'Ścieżka "{path}" nie istnieje.'}

        try:
            files = os.listdir(path)
            return {'success': True, 'files': files, 'path': path}
        except Exception as e:
            return {'success': False, 'message': f'Nie można listować plików w "{path}": {e}'}

    def copy_file(self, text):
        match = re.search(r'(kopiuj|cp)\s+(.+?)\s+do\s+(.+)', text)
        if not match:
            match = re.search(r'(kopiuj|cp)\s+(.+?)\s+(.+)', text)
            if not match:
                return {'success': False, 'message': 'Podaj ścieżkę źródłową i docelową. Przykład: "kopiuj plik.txt do /sciezka/docelowa" lub "kopiuj plik.txt /sciezka/docelowa"'}

        source = match.group(2).strip()
        destination = match.group(3).strip()

        if not os.path.exists(source):
            return {'success': False, 'message': f'Plik źródłowy "{source}" nie istnieje.'}

        try:
            shutil.copy2(source, destination)
            return {'success': True, 'message': f'Pomyślnie skopiowano "{source}" do "{destination}".'}
        except Exception as e:
            return {'success': False, 'message': f'Nie można skopiować pliku: {e}'}

    def file_info(self, text):
        match = re.search(r'(info o pliku|stat)\s+(.+)', text)
        if not match:
            return {'success': False, 'message': 'Podaj ścieżkę do pliku, o którym chcesz uzyskać informacje. Przykład: "info o pliku moj_plik.txt"'}

        path = match.group(2).strip()

        if not os.path.exists(path):
            return {'success': False, 'message': f'Plik "{path}" nie istnieje.'}

        try:
            stat_info = os.stat(path)
            file_details = {
                'path': path,
                'size': stat_info.st_size,
                'created': stat_info.st_ctime,
                'modified': stat_info.st_mtime,
                'accessed': stat_info.st_atime,
                'is_directory': os.path.isdir(path),
                'is_file': os.path.isfile(path)
            }
            return {'success': True, 'file_info': file_details}
        except Exception as e:
            return {'success': False, 'message': f'Nie można uzyskać informacji o pliku "{path}": {e}'}

def execute(params: dict) -> dict:
    skill = ZarzadzaniaSkill()
    return skill.execute(params)

if __name__ == '__main__':
    print(get_info())
    print(health_check())

    # Test cases
    print("\n--- Testy ---")

    # List files in current directory
    print("\nTest: Listuj pliki w bieżącym katalogu")
    result_ls = execute({'text': 'listuj .'})
    print(result_ls)

    # Create a dummy file for testing copy and info
    dummy_file_name = "test_file_for_zarzadzania.txt"
    with open(dummy_file_name, "w") as f:
        f.write("To jest plik testowy.")

    # Copy file
    print(f"\nTest: Kopiuj {dummy_file_name} do {dummy_file_name}.copy")
    result_cp = execute({'text': f'kopiuj {dummy_file_name} do {dummy_file_name}.copy'})
    print(result_cp)

    # File info
    print(f"\nTest: Info o pliku {dummy_file_name}")
    result_info = execute({'text': f'info o pliku {dummy_file_name}'})
    print(result_info)

    # Clean up dummy files
    if os.path.exists(dummy_file_name):
        os.remove(dummy_file_name)
    if os.path.exists(f"{dummy_file_name}.copy"):
        os.remove(f"{dummy_file_name}.copy")

    # Test non-existent file
    print("\nTest: Info o nieistniejącym pliku")
    result_nonexistent = execute({'text': 'info o pliku non_existent_file.txt'})
    print(result_nonexistent)

    # Test invalid command
    print("\nTest: Nieznane polecenie")
    result_unknown = execute({'text': 'nieznane polecenie'})
    print(result_unknown)
```