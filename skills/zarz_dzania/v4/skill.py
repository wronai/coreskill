import subprocess
import os
import shutil
import re
import urllib.request
import json
import datetime
import time

def get_info() -> dict:
    return {
        'name': 'file_manager',
        'version': 'v1',
        'description': 'Skill do zarządzania plikami - listowanie, kopiowanie, info o pliku.'
    }

def health_check() -> dict:
    return {'status': 'ok'}

class FileManagerSkill:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '').lower()

        try:
            if 'listuj' in text or 'ls' in text:
                return self.list_directory(text)
            elif 'kopiuj' in text or 'cp' in text:
                return self.copy_file(text)
            elif 'info o pliku' in text or 'stat' in text:
                return self.file_info(text)
            else:
                return {'success': False, 'message': 'Nieznane polecenie. Dostępne: listuj, kopiuj, info o pliku.'}
        except Exception as e:
            return {'success': False, 'message': f'Wystąpił błąd: {str(e)}'}

    def list_directory(self, text: str) -> dict:
        match = re.search(r'(?:listuj|ls)\s+(.+)', text)
        if match:
            path = match.group(1).strip()
        else:
            path = '.'

        if not os.path.isdir(path):
            return {'success': False, 'message': f'Ścieżka "{path}" nie jest katalogiem.'}

        try:
            files = os.listdir(path)
            return {'success': True, 'files': files, 'path': path}
        except Exception as e:
            return {'success': False, 'message': f'Nie można odczytać katalogu "{path}": {str(e)}'}

    def copy_file(self, text: str) -> dict:
        # Try to match "kopiuj <source> do <destination>"
        match = re.search(r'(?:kopiuj|cp)\s+(.+?)\s+do\s+(.+)', text)
        if match:
            source = match.group(1).strip()
            destination = match.group(2).strip()
        else:
            # Try to match "kopiuj <source> <destination>"
            match = re.search(r'(?:kopiuj|cp)\s+(.+?)\s+(.+)', text)
            if match:
                source = match.group(1).strip()
                destination = match.group(2).strip()
            else:
                 return {'success': False, 'message': 'Nieprawidłowy format polecenia kopiowania. Użyj: "kopiuj <źródło> do <cel>" lub "kopiuj <źródło> <cel>".'}

        if not os.path.exists(source):
            return {'success': False, 'message': f'Plik źródłowy "{source}" nie istnieje.'}

        try:
            if os.path.isdir(destination):
                # If destination is a directory, copy the file into it
                shutil.copy2(source, destination)
                return {'success': True, 'message': f'Plik "{source}" został skopiowany do katalogu "{destination}".'}
            else:
                # If destination is a file path, copy and rename
                shutil.copy2(source, destination)
                return {'success': True, 'message': f'Plik "{source}" został skopiowany do "{destination}".'}
        except Exception as e:
            return {'success': False, 'message': f'Nie można skopiować pliku: {str(e)}'}

    def file_info(self, text: str) -> dict:
        match = re.search(r'(?:info o pliku|stat)\s+(.+)', text)
        if not match:
            return {'success': False, 'message': 'Nieprawidłowy format polecenia. Użyj: "info o pliku <ścieżka>" lub "stat <ścieżka>".'}

        file_path = match.group(1).strip()

        if not os.path.exists(file_path):
            return {'success': False, 'message': f'Plik "{file_path}" nie istnieje.'}

        try:
            stat_info = os.stat(file_path)
            info = {
                'path': file_path,
                'size_bytes': stat_info.st_size,
                'last_modified': datetime.datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                'created': datetime.datetime.fromtimestamp(stat_info.st_ctime).isoformat(),
                'is_directory': os.path.isdir(file_path),
                'is_file': os.path.isfile(file_path)
            }
            return {'success': True, 'info': info}
        except Exception as e:
            return {'success': False, 'message': f'Nie można pobrać informacji o pliku "{file_path}": {str(e)}'}

def execute(params: dict) -> dict:
    skill = FileManagerSkill()
    return skill.execute(params)

if __name__ == '__main__':
    # Test cases
    print("--- Test Listuj ---")
    print(execute({'text': 'listuj'}))
    print(execute({'text': 'listuj .'}))
    print(execute({'text': 'ls /tmp'}))
    print(execute({'text': 'ls /nonexistent_dir'}))

    print("\n--- Test Kopiuj ---")
    # Create a dummy file for testing copy
    try:
        with open("test_source.txt", "w") as f:
            f.write("This is a test file.")
        print(execute({'text': 'kopiuj test_source.txt test_destination.txt'}))
        print(execute({'text': 'cp test_destination.txt ./'})) # Copy to current dir
        print(execute({'text': 'kopiuj test_source.txt do /tmp/'}))
        print(execute({'text': 'kopiuj non_existent_file.txt test_dest.txt'}))
        print(execute({'text': 'kopiuj test_source.txt'})) # Invalid format
    finally:
        # Clean up dummy files
        if os.path.exists("test_source.txt"):
            os.remove("test_source.txt")
        if os.path.exists("test_destination.txt"):
            os.remove("test_destination.txt")
        if os.path.exists("/tmp/test_source.txt"):
            os.remove("/tmp/test_source.txt")


    print("\n--- Test Info o pliku ---")
    try:
        with open("test_info.txt", "w") as f:
            f.write("File for info test.")
        print(execute({'text': 'info o pliku test_info.txt'}))
        print(execute({'text': 'stat test_info.txt'}))
        print(execute({'text': 'info o pliku /'}))
        print(execute({'text': 'stat non_existent_file.txt'}))
        print(execute({'text': 'info o pliku'})) # Invalid format
    finally:
        if os.path.exists("test_info.txt"):
            os.remove("test_info.txt")


    print("\n--- Test Nieznane polecenie ---")
    print(execute({'text': 'powiedz cos'}))