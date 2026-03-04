# Tworzenie Skillów

## Szybki start

### Metoda 1: Automatyczna (zalecana)

```
/create nazwa_skillu
```

System automatycznie wygeneruje skill na podstawie opisu.

### Metoda 2: Manualna

```bash
mkdir -p skills/nazwa/v1
touch skills/nazwa/v1/skill.py
touch skills/nazwa/v1/meta.json
```

## Struktura skillu

### Minimalny skill

```python
#!/usr/bin/env python3
"""
Opis funkcjonalności skillu
"""

def get_info():
    """Zwraca metadane skilla."""
    return {
        "name": "nazwa",
        "version": "v1",
        "description": "Krótki opis co skill robi"
    }

def execute(params: dict) -> dict:
    """
    Wykonuje akcję skilla.
    
    Args:
        params: Słownik parametrów (zależny od skillu)
    
    Returns:
        dict: {
            "success": bool,
            "result": any,  # dane wynikowe
            "error": str    # jeśli success=False
        }
    """
    try:
        # Implementacja
        result = _process(params)
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "suggestion": "Sprawdź parametry wejściowe"
        }

def _process(params):
    """Wewnętrzna logika."""
    return {"processed": params}
```

### Meta.json

```json
{
  "name": "nazwa",
  "version": "v1",
  "description": "Opis skillu",
  "author": "Twoje Imię",
  "actions": ["execute"],
  "parameters": {
    "param1": {
      "type": "string",
      "description": "Opis parametru",
      "required": true
    },
    "param2": {
      "type": "integer",
      "default": 42,
      "description": "Parametr opcjonalny"
    }
  }
}
```

## Przykłady skillów

### Skill API

```python
def execute(params):
    """Pobiera dane z API."""
    import urllib.request
    import json
    
    url = params.get("url")
    if not url:
        return {"success": False, "error": "Missing url parameter"}
    
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            data = json.loads(response.read().decode())
            return {"success": True, "result": data}
    except Exception as e:
        return {"success": False, "error": str(e)}
```

### Skill z zależnościami

```python
def execute(params):
    """Skill korzystający z zewnętrznej biblioteki."""
    try:
        import requests  # pip install requests
    except ImportError:
        return {
            "success": False,
            "error": "Missing dependency: requests",
            "suggestion": "Run: pip install requests"
        }
    
    # Implementacja z requests
    response = requests.get(params.get("url"))
    return {"success": True, "result": response.json()}
```

### Skill z plikiem

```python
def execute(params):
    """Czyta/zapisuje do pliku."""
    from pathlib import Path
    
    filepath = params.get("path")
    content = params.get("content")
    
    if content is not None:
        # Zapisz
        Path(filepath).write_text(content)
        return {"success": True, "result": f"Saved to {filepath}"}
    else:
        # Odczytaj
        content = Path(filepath).read_text()
        return {"success": True, "result": content}
```

## Zaawansowane techniki

### Klasa Skill

```python
class CalculatorSkill:
    """Skill jako klasa - pozwala na state."""
    
    def __init__(self):
        self.name = "calculator"
        self._history = []
    
    def get_info(self):
        return {
            "name": self.name,
            "version": "v1",
            "description": "Calculator with history"
        }
    
    def execute(self, params):
        operation = params.get("op")
        a = params.get("a", 0)
        b = params.get("b", 0)
        
        if operation == "add":
            result = a + b
        elif operation == "mul":
            result = a * b
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}
        
        self._history.append(f"{a} {operation} {b} = {result}")
        
        return {
            "success": True,
            "result": result,
            "history": self._history[-5:]  # last 5
        }

# Module-level functions
def get_info():
    return CalculatorSkill().get_info()

def execute(params):
    return CalculatorSkill().execute(params)
```

### Async Skill

```python
import asyncio

def execute(params):
    """Skill z async operacjami."""
    
    async def _fetch():
        # Async logic here
        await asyncio.sleep(1)
        return {"data": "fetched"}
    
    # Run async in sync context
    result = asyncio.get_event_loop().run_until_complete(_fetch())
    return {"success": True, "result": result}
```

### Skill z walidacją

```python
def execute(params):
    """Skill z pełną walidacją."""
    errors = []
    
    # Walidacja email
    email = params.get("email")
    if email and "@" not in email:
        errors.append("Invalid email format")
    
    # Walidacja zakresu
    age = params.get("age")
    if age and (age < 0 or age > 150):
        errors.append("Age must be 0-150")
    
    if errors:
        return {
            "success": False,
            "error": "Validation failed",
            "errors": errors
        }
    
    # Process
    return {"success": True, "result": "Validated data"}
```

## Debugowanie skillów

### Logging

```python
import logging

logger = logging.getLogger(__name__)

def execute(params):
    logger.info(f"Executing with params: {params}")
    
    try:
        result = _process(params)
        logger.info(f"Success: {result}")
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"Failed: {e}")
        return {"success": False, "error": str(e)}
```

### Testowanie lokalne

```python
if __name__ == "__main__":
    # Test skill locally
    print("Testing skill...")
    
    # Test 1: Valid input
    result = execute({"text": "Hello"})
    print(f"Test 1: {result}")
    
    # Test 2: Invalid input
    result = execute({})
    print(f"Test 2: {result}")
    
    # Test 3: Edge case
    result = execute({"text": "", "lang": "pl"})
    print(f"Test 3: {result}")
```

## Ewolucja skillu

### Manualna ewolucja

```python
# W powłoce:
/evolve nazwa_skillu

# Cel: "Dodaj obsługę formatowania markdown"
```

### Auto-fix przy błędzie

System automatycznie próbuje naprawić skill gdy zwróci `success: False`.

### Best practices dla ewolucji

1. **Jasne error messages** - pomagają LLM zrozumieć problem
2. **Suggestion field** - podpowiedź jak naprawić
3. **Granular errors** - rozdzielaj błędy walidacji od runtime

```python
def execute(params):
    if not params.get("required_param"):
        return {
            "success": False,
            "error": "Missing required_param",
            "suggestion": "Add required_param to params",
            "error_type": "validation"
        }
    
    try:
        risky_operation()
    except FileNotFoundError as e:
        return {
            "success": False,
            "error": f"File not found: {e}",
            "suggestion": "Create the file first or check path",
            "error_type": "file_not_found"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "runtime"
        }
```

## Manifest dla providerów

Dla skillów z wieloma providerami:

```json
{
  "capability": "tts",
  "description": "Text-to-Speech",
  "version_structure": "stable/latest/archive",
  "providers": ["espeak", "pyttsx3", "coqui"],
  "default_provider": "espeak"
}
```

## Weryfikacja skillu

### Health check

```python
def health_check():
    """Opcjonalna funkcja sprawdzająca health."""
    return {
        "status": "ok",  # lub "degraded", "error"
        "message": "Working normally",
        "metrics": {
            "latency_ms": 50,
            "success_rate": 0.98
        }
    }
```

### Preflight check

System automatycznie sprawdza:
- ✓ Składnia Python
- ✓ Dostępne importy
- ✓ Istnienie funkcji `get_info`, `execute`

## Wskazówki

### DO's

✅ Zawsze zwracaj `dict` z `success` (bool)
✅ Używaj `try/except` dla operacji ryzykownych
✅ Podawaj `suggestion` przy błędach
✅ Dokumentuj parametry w `meta.json`
✅ Testuj skill lokalnie przed commitem

### DON'Ts

❌ Nie używaj `print()` - użyj logging
❌ Nie modyfikuj `sys.path` wewnątrz skillu
❌ Nie importuj z `cores.*` - skills są independent
❌ Nie twórz plików poza swoim folderem
❌ Nie używaj `input()` - skills są non-interactive

## Przykład kompletnego skillu

```python
#!/usr/bin/env python3
"""
qr_generator - Generuje kody QR z tekstu
"""
import subprocess
import tempfile
from pathlib import Path


def get_info():
    return {
        "name": "qr_generator",
        "version": "v1", 
        "description": "Generuje kody QR z podanego tekstu",
        "author": "CoreSkill AI",
        "actions": ["generate"],
        "parameters": {
            "text": {
                "type": "string",
                "required": True,
                "description": "Tekst do zakodowania"
            },
            "size": {
                "type": "integer",
                "default": 200,
                "description": "Rozmiar w pikselach"
            }
        }
    }


def execute(params: dict) -> dict:
    """Generuje kod QR."""
    text = params.get("text")
    size = params.get("size", 200)
    
    if not text:
        return {
            "success": False,
            "error": "Missing required parameter: text",
            "suggestion": "Provide text to encode: execute({'text': 'hello'})"
        }
    
    try:
        # Use qrencode (usually preinstalled on Linux)
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as f:
            output_path = f.name
        
        result = subprocess.run(
            ['qrencode', '-s', '10', '-o', output_path, text],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"qrencode failed: {result.stderr}",
                "suggestion": "Install qrencode: sudo apt install qrencode"
            }
        
        return {
            "success": True,
            "result": {
                "path": output_path,
                "text": text,
                "size": size
            },
            "message": f"QR code saved to: {output_path}"
        }
        
    except FileNotFoundError:
        return {
            "success": False,
            "error": "qrencode not found",
            "suggestion": "Install: sudo apt install qrencode"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "runtime"
        }


if __name__ == "__main__":
    # Test
    result = execute({"text": "Hello World"})
    print(f"Result: {result}")
```

## Więcej przykładów

Zobacz istniejące skille w folderze `skills/` jako referencje:
- `echo/v1/` - najprostszy skill
- `shell/v1/` - skill z subprocess
- `tts/providers/espeak/v1/` - skill providera
