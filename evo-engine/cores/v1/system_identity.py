#!/usr/bin/env python3
"""
evo-engine SystemIdentity — separates LLM knowledge from system knowledge.

The LLM is the BRAIN of evo-engine, not a standalone chatbot.
SystemIdentity tells the LLM what the system CAN do (even if broken)
and how to respond when skills fail.
"""
import json
from datetime import datetime, timezone

from .config import SKILLS_DIR


class SkillStatus:
    """Runtime status of a single capability."""
    def __init__(self, name, healthy=True, provider="default",
                 version="v1", error=None):
        self.name = name
        self.healthy = healthy
        self.provider = provider
        self.version = version
        self.error = error
        self.last_check = datetime.now(timezone.utc)

    def to_dict(self):
        return {
            "name": self.name,
            "status": "OK" if self.healthy else "BROKEN",
            "provider": self.provider,
            "version": self.version,
            "error": self.error,
        }


class SystemIdentity:
    """
    Builds dynamic system prompt that separates:
    - What the SYSTEM can do (capabilities)
    - What the LLM should do (analyze, route, respond)
    - How to handle failures (never say "I can't", say "skill is broken")
    """

    CAPABILITY_DESCRIPTIONS = {
        "tts": "Mówienie głosem — zamiana tekstu na mowę (Text-to-Speech)",
        "stt": "Słuchanie — zamiana mowy na tekst (Speech-to-Text)",
        "web_search": "Wyszukiwanie w internecie",
        "git_ops": "Operacje na repozytoriach Git",
        "devops": "Testowanie i walidacja kodu",
        "deps": "Zarządzanie zależnościami Python/system",
        "echo": "Test echo — weryfikacja działania systemu",
        "llm_router": "Routing zapytań LLM między modelami",
    }

    def __init__(self, skill_manager=None, resource_monitor=None):
        self.sm = skill_manager
        self.rm = resource_monitor
        self._skill_statuses = {}
        self._last_refresh = None

    def refresh_statuses(self):
        """Check health of all skills. Called on startup and periodically."""
        if not self.sm:
            return
        for name in self.sm.list_skills():
            try:
                healthy = self.sm.check_health(name)
                version = self.sm.latest_v(name) or "v1"
                provider = "default"
                if self.sm.provider_selector:
                    providers = self.sm.provider_selector.list_providers(name)
                    if providers and providers != ["default"]:
                        provider = self.sm.provider_selector.select(name)
                self._skill_statuses[name] = SkillStatus(
                    name=name, healthy=healthy,
                    provider=provider, version=version
                )
            except Exception as e:
                self._skill_statuses[name] = SkillStatus(
                    name=name, healthy=False, error=str(e)
                )
        self._last_refresh = datetime.now(timezone.utc)

    def get_status(self, skill_name):
        return self._skill_statuses.get(skill_name)

    def build_system_prompt(self):
        """Build dynamic system prompt with capability awareness."""
        identity = (
            "Jesteś RDZENIEM (brain) systemu evo-engine — ewolucyjnego systemu AI. "
            "NIE jesteś zwykłym chatbotem. Jesteś połączony z systemem który MA zdolności "
            "(skills) takie jak mówienie głosem (TTS), słuchanie (STT), przeszukiwanie internetu, "
            "zarządzanie Git, itp.\n\n"
            "FUNDAMENTALNA ZASADA: Nigdy nie mów 'nie umiem' ani 'nie mam możliwości'. "
            "Zamiast tego użyj odpowiedniego skilla. Jeśli skill jest uszkodzony, "
            "powiedz 'naprawiam skill' albo 'skill wymaga naprawy' — NIE 'nie potrafię'.\n"
        )

        cap_lines = []
        for name, desc in self.CAPABILITY_DESCRIPTIONS.items():
            status = self._skill_statuses.get(name)
            if status:
                s = "DZIAŁA" if status.healthy else f"USZKODZONY ({status.error or 'unknown'})"
                cap_lines.append(f"  - {name}: {desc} [{s}]")
            else:
                cap_lines.append(f"  - {name}: {desc} [NIEZNANY STATUS]")

        capabilities = "TWOJE ZDOLNOŚCI (skills systemu evo-engine):\n" + "\n".join(cap_lines) + "\n"

        rules = (
            "\nZASADY ODPOWIEDZI:\n"
            "1. Odpowiadaj po polsku jeśli user mówi po polsku.\n"
            "2. NIGDY nie wypisuj bloków kodu (```). Zamiast tego stwórz skill.\n"
            "3. NIGDY nie pytaj o wybór technologii. Sam wybierz najtańszą/najszybszą opcję i ZRÓB TO.\n"
            "4. NIGDY nie dawaj listy opcji do wyboru. Sam podejmij decyzję.\n"
            "5. NIGDY nie pisz instrukcji 'jak zainstalować'. Sam to zainstaluj.\n"
            "6. Jeśli user mówi 'tak' - natychmiast działaj w kontekście poprzedniej rozmowy.\n"
            "7. Bądź ULTRA zwięzły. Max 2-3 zdania. Używaj markdown.\n"
            "8. Jeśli skill jest USZKODZONY → powiedz: 'Skill [nazwa] wymaga naprawy' "
            "i NIE mów że nie umiesz.\n"
            "9. Nigdy nie mów 'jako model językowy nie mam możliwości' — BO MASZ, przez skille.\n"
            "10. Przy tworzeniu czegokolwiek - kalkuluj: co najtańsze, najszybsze.\n"
        )

        return identity + capabilities + rules

    def build_fallback_message(self, failed_skill, error=None, attempts=0):
        """Generate appropriate failure message (NOT 'I can't')."""
        desc = self.CAPABILITY_DESCRIPTIONS.get(failed_skill, failed_skill)

        if attempts >= 3:
            return (
                f"Skill '{failed_skill}' ({desc}) nie działa po {attempts} próbach naprawy. "
                f"Błąd: {error or 'nieznany'}. "
                f"Możesz spróbować: /rollback {failed_skill} lub /evolve {failed_skill}"
            )
        elif error:
            return (
                f"Skill '{failed_skill}' ma błąd: {error}. "
                f"Próbuję naprawić automatycznie..."
            )
        else:
            return (
                f"Skill '{failed_skill}' tymczasowo niedostępny. "
                f"System próbuje naprawić..."
            )

    def build_skill_context_for_llm(self, skill_name):
        """Context for LLM when generating/fixing skill code."""
        return (
            f"Generujesz kod Python dla skilla '{skill_name}' w systemie evo-engine.\n"
            f"WYMAGANIA:\n"
            f"1. Plik MUSI zaczynać się od WSZYSTKICH potrzebnych importów\n"
            f"2. OBOWIĄZKOWE: sprawdź czy importujesz os, sys, json, subprocess, shutil, pathlib\n"
            f"3. Klasa musi mieć metodę execute(self, input_data: dict) -> dict\n"
            f"4. Funkcja get_info() -> dict z kluczami: name, version, description\n"
            f"5. Funkcja health_check() -> bool\n"
            f"6. Blok if __name__ == '__main__' z testem\n"
            f"7. KAŻDY import użyty w kodzie MUSI być na górze pliku\n"
            f"8. Obsługa błędów try/except w execute()\n"
            f"9. Zwracaj ZAWSZE dict z kluczami 'success' i 'error' lub 'result'\n"
        )

    def get_readiness_report(self):
        """Full system readiness report."""
        total = len(self.CAPABILITY_DESCRIPTIONS)
        healthy = sum(1 for s in self._skill_statuses.values() if s.healthy)
        broken = [s.name for s in self._skill_statuses.values() if not s.healthy]
        missing = [n for n in self.CAPABILITY_DESCRIPTIONS
                   if n not in self._skill_statuses]

        return {
            "total_capabilities": total,
            "healthy": healthy,
            "broken": broken,
            "missing": missing,
            "readiness_pct": round(healthy / max(total, 1) * 100),
        }
