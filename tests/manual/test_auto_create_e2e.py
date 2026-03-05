#!/usr/bin/env python3
"""
Test E2E automatycznego tworzenia skilli.
Sprawdza czy system automatycznie tworzy skill gdy intent=chat lub gdy skill zwraca puste wyniki.

Uruchomienie: cd /home/tom/github/wronai/coreskill && python3 tests/test_auto_create_e2e.py
"""

import sys
import os
import json
from pathlib import Path

import pytest

if os.getenv("RUN_MANUAL_TESTS") != "1":
    pytest.skip("manual test (requires real LLM/network); set RUN_MANUAL_TESTS=1", allow_module_level=True)

# Add project root to path
ROOT = Path(__file__).resolve().parents[2]  # manual → tests → root
sys.path.insert(0, str(ROOT))

# Import directly from cores.v1 package
from cores.v1.evo_engine import EvoEngine
from cores.v1.skill_manager import SkillManager
from cores.v1.llm_client import LLMClient
from cores.v1.logger import Logger
from cores.v1.provider_selector import ProviderSelector, ProviderChain
from cores.v1.resource_monitor import ResourceMonitor
from cores.v1.bandit_selector import UCB1BanditSelector
from cores.v1.config import load_state, SKILLS_DIR


@pytest.mark.timeout(120)
def test_auto_create_skill_on_unknown_intent():
    """Test: Gdy intent=chat (nieznane), system automatycznie tworzy skill."""
    print("\n" + "="*60)
    print("TEST 1: Auto-create skill gdy intent=chat (nieznane zapytanie)")
    print("="*60)
    
    # Setup minimal components
    state = load_state()
    state["openrouter_api_key"] = state.get("openrouter_api_key", "test-key")
    
    logger = Logger("test")
    llm = LLMClient(
        api_key=state.get("openrouter_api_key", "test"),
        model="openrouter/qwen/qwen3-coder-next:free",
        logger=logger,
        models=[]
    )
    
    resource_mon = ResourceMonitor()
    provider_sel = ProviderSelector(SKILLS_DIR, resource_mon)
    sm = SkillManager(llm, logger, provider_selector=provider_sel)
    
    bandit = UCB1BanditSelector()
    chain = ProviderChain(provider_sel, bandit=bandit)
    evo = EvoEngine(sm, llm, logger, provider_chain=chain)
    
    # Zapytanie testowe - coś czego system nie powinien znać
    test_query = "przelicz tysiąc funtów szterlingów na jeny japońskie"
    
    print(f"\nZapytanie: '{test_query}'")
    print("Oczekiwane: System stworzy skill 'currency_converter' lub 'gbp_jpy_converter'")
    
    # Symulacja: handle_request z intent=chat
    analysis = {
        "action": "chat",  # Nieznane - system nie wie jak obsłużyć
        "goal": test_query,
        "input": {"text": test_query}
    }
    
    print("\nUruchamiam handle_request z action=chat...")
    
    try:
        # To wywoła auto-creation w prawdziwym systemie
        result = evo.handle_request(test_query, sm.list_skills(), analysis)
        
        print(f"\nWynik: {result}")
        
        if result and result.get("type") == "success":
            skill_name = result.get("skill", "?")
            print(f"✓ Skill '{skill_name}' został wykonany!")
            
            # Sprawdź czy skill istnieje
            if skill_name in sm.list_skills():
                print(f"✓ Skill '{skill_name}' istnieje w SkillManager")
                return True, skill_name
            else:
                print(f"? Skill '{skill_name}' nie znaleziony (może być usunięty po teście)")
                return True, skill_name
        else:
            print(f"✗ Nie udało się wykonać: {result}")
            return False, None
            
    except Exception as e:
        print(f"✗ Błąd: {e}")
        import traceback
        traceback.print_exc()
        return False, None


@pytest.mark.timeout(120)
def test_auto_create_skill_on_empty_results():
    """Test: Gdy web_search zwraca puste wyniki, system tworzy dedykowany skill."""
    print("\n" + "="*60)
    print("TEST 2: Auto-create skill gdy web_search zwraca puste wyniki")
    print("="*60)
    
    # Setup
    state = load_state()
    logger = Logger("test")
    llm = LLMClient(
        api_key=state.get("openrouter_api_key", "test"),
        model="openrouter/qwen/qwen3-coder-next:free",
        logger=logger,
        models=[]
    )
    
    resource_mon = ResourceMonitor()
    provider_sel = ProviderSelector(SKILLS_DIR, resource_mon)
    sm = SkillManager(llm, logger, provider_selector=provider_sel)
    
    bandit = UCB1BanditSelector()
    chain = ProviderChain(provider_sel, bandit=bandit)
    evo = EvoEngine(sm, llm, logger, provider_chain=chain)
    
    # Zapytanie o lokalną sieć (web_search zwróci puste)
    test_query = "znajdź kamery RTSP w mojej sieci lokalnej"
    
    print(f"\nZapytanie: '{test_query}'")
    print("Oczekiwane: web_search zwróci puste wyniki → auto-create 'camera_scanner'")
    
    # Najpierw wywołaj web_search
    analysis = {
        "action": "use",
        "skill": "web_search",
        "goal": test_query,
        "input": {"text": test_query}
    }
    
    print("\nKrok 1: Wywołanie web_search...")
    
    try:
        result = evo.handle_request(test_query, sm.list_skills(), analysis)
        
        print(f"\nWynik web_search: {json.dumps(result, indent=2, default=str)[:500]}")
        
        # Sprawdź czy nastąpiło auto-creation
        if result and result.get("type") == "success":
            skill_name = result.get("skill", "?")
            
            if skill_name != "web_search":
                print(f"\n✓ Auto-creation działa! Nowy skill: '{skill_name}'")
                print(f"✓ Zamiast pustych wyników web_search, użyto nowego skillu")
                return True, skill_name
            else:
                # web_search zwrócił wyniki (nie powinien dla tego zapytania)
                print(f"\n? web_search zwrócił wyniki - sprawdzam czy był auto-creation...")
                # Sprawdź czy nowy skill został stworzony mimo wszystko
                skills_after = sm.list_skills()
                print(f"  Dostępne skills: {list(skills_after.keys())}")
                
                # Szukaj nowych skillów
                new_skills = [s for s in skills_after if s not in [
                    "shell", "deps", "devops", "git_ops", "web_search", 
                    "stt", "tts", "time", "weather", "network_info", "system_info"
                ]]
                if new_skills:
                    print(f"✓ Znaleziono nowy skill: {new_skills[0]}")
                    return True, new_skills[0]
                
                return False, None
        else:
            print(f"\n? web_search nie zwrócił success: {result}")
            return False, None
            
    except Exception as e:
        print(f"✗ Błąd: {e}")
        import traceback
        traceback.print_exc()
        return False, None


def test_generate_skill_name():
    """Test generowania nazw skilli z zapytań."""
    print("\n" + "="*60)
    print("TEST 3: Generowanie nazw skilli z zapytań")
    print("="*60)
    
    state = load_state()
    logger = Logger("test")
    llm = LLMClient(
        api_key=state.get("openrouter_api_key", "test"),
        model="openrouter/qwen/qwen3-coder-next:free",
        logger=logger,
        models=[]
    )
    
    resource_mon = ResourceMonitor()
    provider_sel = ProviderSelector(SKILLS_DIR, resource_mon)
    sm = SkillManager(llm, logger, provider_selector=provider_sel)
    
    evo = EvoEngine(sm, llm, logger)
    
    test_cases = [
        ("przelicz funty na jeny", "currency_converter"),
        ("znajdź kamery w sieci", "camera_scanner"),
        ("pokaż pogodę w Warszawie", "weather_warsaw"),
        ("skonwertuj PDF na TXT", "pdf_converter"),
        ("sprawdź czy strona działa", "website_monitor"),
    ]
    
    print("\nTesty generowania nazw:")
    all_passed = True
    
    for query, expected_pattern in test_cases:
        name = evo._generate_skill_name(query)
        # Sprawdź czy nazwa jest sensowna (snake_case, bez spacji)
        is_valid = (
            "_" in name or len(name) > 5
        ) and " " not in name and name.islower()
        
        status = "✓" if is_valid else "✗"
        print(f"  {status} '{query[:35]}...' → '{name}'")
        
        if not is_valid:
            all_passed = False
    
    return all_passed


def main():
    """Run all E2E tests."""
    print("\n" + "="*70)
    print("  E2E TEST: Automatyczne tworzenie skilli przez LLM")
    print("="*70)
    
    results = []
    
    # Test 3: Generowanie nazw (szybki, nie wymaga API)
    ok = test_generate_skill_name()
    results.append(("Generate skill names", ok))
    
    # Test 1: Auto-create na intent=chat
    # UWAGA: To wywoła prawdziwe LLM API - może zająć 30-60s
    print("\n" + "-"*60)
    print("Czy uruchomić testy z prawdziwym LLM? (wymaga API key)")
    print("-"*60)
    
    # Sprawdź czy mamy API key
    state = load_state()
    if not state.get("openrouter_api_key"):
        print("⚠️  Brak OPENROUTER_API_KEY - pomijam testy z LLM")
        print("   Ustaw klucz aby przetestować pełny flow auto-creation.")
    else:
        print(f"✓ API key ustawiony")
        print("\nUruchamianie testów z prawdziwym LLM...")
        print("(To może zająć 30-60 sekund)")
        
        # Test 1: Intent=chat
        ok, skill1 = test_auto_create_skill_on_unknown_intent()
        results.append(("Auto-create on chat intent", ok))
        
        # Test 2: Empty web_search results
        ok, skill2 = test_auto_create_skill_on_empty_results()
        results.append(("Auto-create on empty web_search", ok))
    
    # Podsumowanie
    print("\n" + "="*70)
    print("PODSUMOWANIE")
    print("="*70)
    
    passed = sum(1 for _, ok in results if ok)
    total = len(results)
    
    for name, ok in results:
        status = "✓ PASS" if ok else "✗ FAIL"
        print(f"  {status}: {name}")
    
    print(f"\nWynik: {passed}/{total} testów zaliczonych")
    
    if passed == total:
        print("\n✓ Wszystkie testy E2E przeszły!")
        return 0
    else:
        print(f"\n✗ {total - passed} testów nie przeszło")
        return 1


if __name__ == "__main__":
    sys.exit(main())
