#!/usr/bin/env python3
"""
Komenda coreskill do pobierania API key z OpenRouter i zapisu do .env
Użycie: ./coreskill openrouter get-api-key
"""
import sys
import json
from pathlib import Path

# Add skills to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "skills" / "openrouter_automation" / "v1"))

from skill import OpenRouterAutomationSkill

def main():
    skill = OpenRouterAutomationSkill()
    
    print("=" * 60)
    print("OpenRouter API Key - Automatyczne pobieranie")
    print("=" * 60)
    print()
    
    # Krok 1: Pobierz API key z sesji przeglądarki
    print("[1/3] Otwieram przeglądarkę i pobieram API key...")
    print("      (Jeśli Playwright nie jest zainstalowany, zostanie zainstalowany automatycznie)")
    print()
    
    result = skill.get_api_key_from_session(headless=False)
    
    if not result.get("success"):
        print(f"❌ Błąd: {result.get('error')}")
        if result.get('step') == 'not_logged_in':
            print()
            print("💡 Musisz być zalogowany do OpenRouter w Firefox!")
            print("   1. Otwórz Firefox")
            print("   2. Idź do https://openrouter.ai/keys")
            print("   3. Zaloguj się")
            print("   4. Uruchom tę komendę ponownie")
        sys.exit(1)
    
    api_key = result.get("api_key")
    print(f"✅ API key pobrany: {result.get('key_preview')}")
    print()
    
    # Krok 2: Zapisz do pliku
    print("[2/3] Zapisuję klucz do ~/.evo_openrouter/api_key.txt...")
    save_result = skill.save_key(api_key)
    if save_result.get("success"):
        print("✅ Zapisano")
    else:
        print(f"⚠️  Ostrzeżenie: {save_result.get('error')}")
    print()
    
    # Krok 3: Zapisz do .env
    print("[3/3] Zapisuję klucz do .env...")
    env_result = skill.save_key_to_env(api_key, ".env")
    if env_result.get("success"):
        print(f"✅ {env_result.get('message')}")
    else:
        print(f"⚠️  Ostrzeżenie: {env_result.get('error')}")
    print()
    
    print("=" * 60)
    print("✅ Gotowe! API key zapisany.")
    print("=" * 60)
    print()
    print("Możesz teraz używać klucza:")
    print("  - W kodzie: os.environ.get('OPENROUTER_API_KEY')")
    print("  - W .env:  OPENROUTER_API_KEY=sk-or-v1-...")
    print()
    print("Sprawdź klucz:")
    print("  ./coreskill openrouter check-key")

if __name__ == "__main__":
    main()
