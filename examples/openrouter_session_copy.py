#!/usr/bin/env python3
"""
Przykład użycia openrouter_automation z kopiowaniem sesji przeglądarki.

Pozwala pobrać API key z OpenRouter bez ponownego logowania,
wykorzystując istniejącą sesję zalogowaną w przeglądarce.
"""
import sys
import json

sys.path.insert(0, '/home/tom/github/wronai/coreskill/skills/openrouter_automation/v1')
from skill import OpenRouterAutomationSkill, execute

def main():
    skill = OpenRouterAutomationSkill()
    
    print("=" * 60)
    print("OpenRouter API Key - Browser Session Copy")
    print("=" * 60)
    
    # Krok 1: Sprawdź dostępne przeglądarki
    print("\n1. Sprawdzam dostępne przeglądarki...")
    browsers = skill.list_available_browsers()
    print(json.dumps(browsers, indent=2))
    
    if browsers.get("has_saved_session"):
        print("\n   ✅ Znaleziono zapisana sesję!")
        print(f"   Ścieżka: {browsers.get('saved_session_path')}")
        
        # Użyj zapisanej sesji
        print("\n2. Próbuję pobrać API key z zapisanej sesji...")
        result = skill.get_api_key_from_storage_state(headless=True)
        print(json.dumps(result, indent=2))
        
        if result.get("success"):
            print(f"\n   ✅ API key pobrany!")
            print(f"   Key: {result.get('key_preview')}")
            return
    
    # Krok 2: Spróbuj skopiować z istniejącej sesji przeglądarki
    print("\n2. Próbuję skopiować sesję z przeglądarki...")
    
    # Próbuj Chromium/Chrome
    result = skill.get_api_key_from_session(
        browser_type="chromium",
        headless=False  # Widoczna przeglądarka dla debugowania
    )
    
    if result.get("success"):
        print(f"\n   ✅ API key pobrany z sesji Chromium!")
        print(f"   Key: {result.get('key_preview')}")
    elif result.get("step") == "not_logged_in":
        print(f"\n   ⚠️ {result.get('error')}")
        print(f"   {result.get('suggestion')}")
        
        # Próbuj Firefox
        print("\n3. Próbuję z Firefox...")
        result = skill.get_api_key_from_session(
            browser_type="firefox",
            headless=False
        )
        
        if result.get("success"):
            print(f"\n   ✅ API key pobrany z sesji Firefox!")
            print(f"   Key: {result.get('key_preview')}")
        else:
            print(f"\n   ❌ Nie udało się: {result.get('error')}")
    else:
        print(f"\n   ❌ Błąd: {result.get('error')}")

if __name__ == "__main__":
    main()
