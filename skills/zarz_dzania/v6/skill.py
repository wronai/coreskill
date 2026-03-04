import subprocess
import os
import shutil
import re
import urllib.request
import time

def get_info() -> dict:
    return {
        "name": "zarzadzania",
        "version": "v1",
        "description": "Skill do zarządzania plikami i katalogami."
    }

def health_check() -> dict:
    return {"status": "ok"}

class ZarzadzaniaSkill:
    def execute(self, params: dict) -> dict:
        text = params.get('text', '').lower()
        
        try:
            if "utwórz katalog" in text:
                match = re.search(r"utwórz katalog (.+)", text)
                if match:
                    dir_name = match.group(1).strip()
                    if not os.path.exists(dir_name):
                        os.makedirs(dir_name)
                        return {'success': True, 'spoken': f"Katalog '{dir_name}' został utworzony."}
                    else:
                        return {'success': False, 'spoken': f"Katalog '{dir_name}' już istnieje."}
                else:
                    return {'success': False, 'spoken': "Nie podałeś nazwy katalogu do utworzenia."}

            elif "usuń katalog" in text:
                match = re.search(r"usuń katalog (.+)", text)
                if match:
                    dir_name = match.group(1).strip()
                    if os.path.exists(dir_name) and os.path.isdir(dir_name):
                        shutil.rmtree(dir_name)
                        return {'success': True, 'spoken': f"Katalog '{dir_name}' został usunięty."}
                    else:
                        return {'success': False, 'spoken': f"Katalog '{dir_name}' nie istnieje lub nie jest katalogiem."}
                else:
                    return {'success': False, 'spoken': "Nie podałeś nazwy katalogu do usunięcia."}

            elif "utwórz plik" in text:
                match = re.search(r"utwórz plik (.+)", text)
                if match:
                    file_name = match.group(1).strip()
                    if not os.path.exists(file_name):
                        with open(file_name, 'w') as f:
                            pass
                        return {'success': True, 'spoken': f"Plik '{file_name}' został utworzony."}
                    else:
                        return {'success': False, 'spoken': f"Plik '{file_name}' już istnieje."}
                else:
                    return {'success': False, 'spoken': "Nie podałeś nazwy pliku do utworzenia."}

            elif "usuń plik" in text:
                match = re.search(r"usuń plik (.+)", text)
                if match:
                    file_name = match.group(1).strip()
                    if os.path.exists(file_name) and os.path.isfile(file_name):
                        os.remove(file_name)
                        return {'success': True, 'spoken': f"Plik '{file_name}' został usunięty."}
                    else:
                        return {'success': False, 'spoken': f"Plik '{file_name}' nie istnieje lub nie jest plikiem."}
                else:
                    return {'success': False, 'spoken': "Nie podałeś nazwy pliku do usunięcia."}
            
            elif "listuj pliki" in text or "pokaż pliki" in text:
                current_dir = os.getcwd()
                files = [f for f in os.listdir(current_dir) if os.path.isfile(os.path.join(current_dir, f))]
                if files:
                    return {'success': True, 'spoken': f"Pliki w bieżącym katalogu: {', '.join(files)}"}
                else:
                    return {'success': True, 'spoken': "W bieżącym katalogu nie ma żadnych plików."}

            elif "listuj katalogi" in text or "pokaż katalogi" in text:
                current_dir = os.getcwd()
                dirs = [d for d in os.listdir(current_dir) if os.path.isdir(os.path.join(current_dir, d))]
                if dirs:
                    return {'success': True, 'spoken': f"Katalogi w bieżącym katalogu: {', '.join(dirs)}"}
                else:
                    return {'success': True, 'spoken': "W bieżącym katalogu nie ma żadnych podkatalogów."}
            
            elif "info o pliku" in text:
                match = re.search(r"info o pliku (.+)", text)
                if match:
                    file_name = match.group(1).strip()
                    if os.path.exists(file_name):
                        file_size = os.path.getsize(file_name)
                        creation_time = os.path.getctime(file_name)
                        modification_time = os.path.getmtime(file_name)
                        return {'success': True, 'spoken': f"Informacje o pliku '{file_name}': Rozmiar: {file_size} bajtów, Czas utworzenia: {creation_time}, Czas modyfikacji: {modification_time}"}
                    else:
                        return {'success': False, 'spoken': f"Plik '{file_name}' nie istnieje."}
                else:
                    return {'success': False, 'spoken': "Nie podałeś nazwy pliku do sprawdzenia."}

            elif "kopiuj plik" in text:
                match = re.search(r"kopiuj plik (.+) do (.+)", text)
                if match:
                    source_file = match.group(1).strip()
                    destination_file = match.group(2).strip()
                    if os.path.exists(source_file) and os.path.isfile(source_file):
                        shutil.copy2(source_file, destination_file)
                        return {'success': True, 'spoken': f"Plik '{source_file}' został skopiowany do '{destination_file}'."}
                    else:
                        return {'success': False, 'spoken': f"Plik źródłowy '{source_file}' nie istnieje lub nie jest plikiem."}
                else:
                    return {'success': False, 'spoken': "Nie podałeś nazw plików źródłowego i docelowego."}

            else:
                return {'success': False, 'spoken': "Nie rozumiem polecenia. Mogę tworzyć i usuwać katalogi oraz pliki, listować ich zawartość, kopiować pliki i podawać informacje o pliku."}

        except Exception as e:
            return {'success': False, 'spoken': f"Wystąpił błąd: {str(e)}"}

def execute(params: dict) -> dict:
    skill = ZarzadzaniaSkill()
    return skill.execute(params)

if __name__ == '__main__':
    # Example usage:
    print(get_info())
    print(health_check())

    # Test cases
    test_params_create_dir = {'text': 'utwórz katalog test_dir_123'}
    result_create_dir = execute(test_params_create_dir)
    print(f"Test create dir: {result_create_dir}")

    test_params_create_file = {'text': 'utwórz plik test_file_123.txt'}
    result_create_file = execute(test_params_create_file)
    print(f"Test create file: {result_create_file}")

    test_params_list_files = {'text': 'listuj pliki'}
    result_list_files = execute(test_params_list_files)
    print(f"Test list files: {result_list_files}")

    test_params_list_dirs = {'text': 'listuj katalogi'}
    result_list_dirs = execute(test_params_list_dirs)
    print(f"Test list dirs: {result_list_dirs}")
    
    test_params_file_info = {'text': 'info o pliku test_file_123.txt'}
    result_file_info = execute(test_params_file_info)
    print(f"Test file info: {result_file_info}")

    test_params_copy_file = {'text': 'kopiuj plik test_file_123.txt do test_file_123_copy.txt'}
    result_copy_file = execute(test_params_copy_file)
    print(f"Test copy file: {result_copy_file}")

    test_params_delete_file = {'text': 'usuń plik test_file_123.txt'}
    result_delete_file = execute(test_params_delete_file)
    print(f"Test delete file: {result_delete_file}")
    
    test_params_delete_file_copy = {'text': 'usuń plik test_file_123_copy.txt'}
    result_delete_file_copy = execute(test_params_delete_file_copy)
    print(f"Test delete file copy: {result_delete_file_copy}")

    test_params_delete_dir = {'text': 'usuń katalog test_dir_123'}
    result_delete_dir = execute(test_params_delete_dir)
    print(f"Test delete dir: {result_delete_dir}")

    test_params_unknown = {'text': 'nieznane polecenie'}
    result_unknown = execute(test_params_unknown)
    print(f"Test unknown command: {result_unknown}")