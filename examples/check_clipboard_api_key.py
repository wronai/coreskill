#!/usr/bin/env python3
"""
Sprawdź schowek pod kątem API key OpenRouter i zweryfikuj format.
"""
import re
import subprocess
import sys

def get_clipboard_content():
    """Pobierz zawartość schowka systemowego."""
    try:
        # Próba xclip (Linux)
        result = subprocess.run(
            ['xclip', '-o', '-selection', 'clipboard'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    try:
        # Próba xsel (Linux)
        result = subprocess.run(
            ['xsel', '-o', '-b'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    try:
        # Próba wl-copy/wl-paste (Wayland)
        result = subprocess.run(
            ['wl-paste'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    try:
        # Próba pbpaste (macOS)
        result = subprocess.run(
            ['pbpaste'],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except:
        pass
    
    return None

def validate_openrouter_api_key(text):
    """
    Sprawdź czy tekst jest poprawnym API key OpenRouter.
    Format: sk-or-v1-[64 znaki hex]
    """
    if not text:
        return {
            "valid": False,
            "error": "Schowek jest pusty",
            "clipboard_content": None
        }
    
    # Regex dla API key OpenRouter
    pattern = r'^sk-or-v1-[a-f0-9]{64}$'
    
    # Sprawdź dokładne dopasowanie
    if re.match(pattern, text):
        return {
            "valid": True,
            "api_key": text,
            "prefix": text[:10],
            "suffix": text[-10:],
            "length": len(text),
            "source": "clipboard",
            "clipboard_content": text[:20] + "..." + text[-10:] if len(text) > 30 else text
        }
    
    # Spróbuj znaleźć API key w tekście
    matches = re.findall(r'sk-or-v1-[a-f0-9]{64}', text)
    if matches:
        return {
            "valid": True,
            "api_key": matches[0],
            "prefix": matches[0][:10],
            "suffix": matches[0][-10:],
            "length": len(matches[0]),
            "source": "extracted_from_clipboard",
            "clipboard_preview": text[:100] + "..." if len(text) > 100 else text,
            "all_matches": matches
        }
    
    # Sprawdź czy to w ogóle wygląda jak API key
    if text.startswith("sk-"):
        return {
            "valid": False,
            "error": "Tekst zaczyna się od 'sk-' ale nie pasuje do formatu OpenRouter",
            "clipboard_content": text[:50] + "..." if len(text) > 50 else text,
            "hint": "Oczekiwany format: sk-or-v1-[64 znaki hex]"
        }
    
    return {
        "valid": False,
        "error": "W schowku nie ma API key OpenRouter",
        "clipboard_content": text[:50] + "..." if len(text) > 50 else text,
        "hint": "Skopiuj API key z OpenRouter (format: sk-or-v1-...)"
    }

def main():
    print("=" * 60)
    print("WERYFIKACJA API KEY OPENROUTER Z SCHOWKA")
    print("=" * 60)
    print()
    
    # Pobierz zawartość schowka
    clipboard = get_clipboard_content()
    
    if clipboard is None:
        print("❌ Nie udało się odczytać schowka")
        print("   Upewnij się, że masz zainstalowane xclip, xsel lub wl-clipboard")
        sys.exit(1)
    
    print(f"📋 Zawartość schowka: {clipboard[:50]}{'...' if len(clipboard) > 50 else ''}")
    print()
    
    # Walidacja
    result = validate_openrouter_api_key(clipboard)
    
    if result["valid"]:
        print("✅ API KEY POPRAWNY!")
        print(f"   Format: OpenRouter API Key")
        print(f"   Długość: {result['length']} znaków")
        print(f"   Prefix: {result['prefix']}")
        print(f"   Suffix: {result['suffix']}")
        print()
        print("🔑 Pełny klucz (ukryty):")
        print(f"   {result['api_key'][:15]}...{result['api_key'][-15:]}")
        print()
        print("💡 Możesz teraz zapisać klucz:")
        print(f"   export OPENROUTER_API_KEY='{result['api_key']}'")
        return 0
    else:
        print(f"❌ {result['error']}")
        if "hint" in result:
            print(f"   💡 {result['hint']}")
        print()
        print("Aby skopiować API key z OpenRouter:")
        print("   1. Otwórz https://openrouter.ai/keys w przeglądarce")
        print("   2. Zaloguj się (jeśli nie jesteś)")
        print("   3. Kliknij 'Create Key' lub skopiuj istniejący")
        print("   4. Wróć tutaj i uruchom ten skrypt ponownie")
        return 1

if __name__ == "__main__":
    sys.exit(main())
