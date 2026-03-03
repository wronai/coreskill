#!/usr/bin/env python3
"""
system_identity.py — Separates LLM knowledge from evo-engine system knowledge.

THE PROBLEM:
    When user says "pogadajmy glosowo" and STT skill fails, the LLM
    falls back to: "Nie mam mozliwosci komunikacji glosowej"
    
    This is WRONG. The LLM thinks it IS the system. But:
    - LLM = brain (generates text, analyzes intent)
    - evo-engine = body (has skills: TTS, STT, web_search, etc.)
    
    The LLM should say: "Skill STT jest uszkodzony, naprawiam..."
    NOT: "Nie umiem mowic" — because the SYSTEM umie, just the skill is broken.

THE FIX:
    Build the system prompt DYNAMICALLY from actual skill state.
    The LLM always knows:
    1. What capabilities the system HAS (even if broken)
    2. Which are HEALTHY right now
    3. What to say when a skill fails (not "I can't" but "skill is broken")

Usage:
    identity = SystemIdentity(skill_manager, resource_monitor)
    system_prompt = identity.build_system_prompt()
    fallback_msg = identity.build_fallback_message("stt", error="shutil not defined")
"""
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class SkillStatus:
    """Runtime status of a single capability."""
    def __init__(self, name: str, healthy: bool, provider: str = "default",
                 version: str = "v1", error: str = None, tier: str = "standard"):
        self.name = name
        self.healthy = healthy
        self.provider = provider
        self.version = version
        self.error = error
        self.tier = tier
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

    # These are SYSTEM capabilities — not LLM capabilities.
    # Even if the LLM "doesn't know how to speak", the SYSTEM has TTS/STT skills.
    CAPABILITY_DESCRIPTIONS = {
        "tts": "Mowienie glosem — zamiana tekstu na mowe (Text-to-Speech)",
        "stt": "Sluchanie — zamiana mowy na tekst (Speech-to-Text)",
        "web_search": "Wyszukiwanie w internecie",
        "git_ops": "Operacje na repozytoriach Git",
        "devops": "Testowanie i walidacja kodu",
        "deps": "Zarzadzanie zaleznosciami Python/system",
        "echo": "Test echo — weryfikacja dzialania systemu",
        "llm_router": "Routing zapytan LLM miedzy modelami",
    }

    # What user might say → what capability they need
    # This is SYSTEM routing, not LLM routing
    INTENT_TO_CAPABILITY = {
        # Voice / conversation
        "glosowo": ["stt", "tts"],
        "pogadajmy": ["stt", "tts"],
        "mow do mnie": ["tts"],
        "powiedz": ["tts"],
        "posluchaj": ["stt"],
        "nagraj": ["stt"],
        "rozmawiajmy": ["stt", "tts"],
        "voice": ["stt", "tts"],
        "speak": ["tts"],
        "listen": ["stt"],
        # Search
        "wyszukaj": ["web_search"],
        "znajdz w internecie": ["web_search"],
        "google": ["web_search"],
        "search": ["web_search"],
        # Git
        "commit": ["git_ops"],
        "push": ["git_ops"],
        "git": ["git_ops"],
        # Deps
        "zainstaluj": ["deps"],
        "install": ["deps"],
        "pip": ["deps"],
    }

    def __init__(self, skill_manager=None, resource_monitor=None):
        self.sm = skill_manager
        self.rm = resource_monitor
        self._skill_statuses = {}  # name -> SkillStatus
        self._last_refresh = None

    def refresh_statuses(self):
        """Check health of all skills. Called periodically."""
        if not self.sm:
            return
        for name in self.sm.list_skills():
            try:
                healthy = self.sm.health_check(name)
                provider = "default"
                version = self.sm.latest_v(name) or "v1"
                self._skill_statuses[name] = SkillStatus(
                    name=name, healthy=healthy,
                    provider=provider, version=version
                )
            except Exception as e:
                self._skill_statuses[name] = SkillStatus(
                    name=name, healthy=False, error=str(e)
                )
        self._last_refresh = datetime.now(timezone.utc)

    def get_status(self, skill_name: str) -> Optional[SkillStatus]:
        return self._skill_statuses.get(skill_name)

    def build_system_prompt(self, conversation_history: list = None) -> str:
        """
        Build the system prompt dynamically.
        
        KEY PRINCIPLE: The LLM is told it's the BRAIN of evo-engine,
        not a standalone chatbot. It MUST use skills for actions.
        """
        # Section 1: Identity
        identity = (
            "Jestes RDZENIEM (brain) systemu evo-engine — ewolucyjnego systemu AI. "
            "NIE jestes zwyklym chatbotem. Jestes polaczony z systemem ktory MA zdolnosci "
            "(skills) takie jak mowienie glosem (TTS), sluchanie (STT), przeszukiwanie internetu, "
            "zarzadzanie Git, itp.\n\n"
            "FUNDAMENTALNA ZASADA: Nigdy nie mow 'nie umiem' ani 'nie mam mozliwosci'. "
            "Zamiast tego uzyj odpowiedniego skilla. Jesli skill jest uszkodzony, "
            "powiedz 'naprawiam skill' albo 'skill wymaga naprawy' — NIE 'nie potrafie'.\n"
        )

        # Section 2: Current capabilities and their status
        cap_lines = []
        for name, desc in self.CAPABILITY_DESCRIPTIONS.items():
            status = self._skill_statuses.get(name)
            if status:
                s = "DZIALA" if status.healthy else f"USZKODZONY ({status.error or 'unknown'})"
                cap_lines.append(f"  - {name}: {desc} [{s}]")
            else:
                cap_lines.append(f"  - {name}: {desc} [NIEZNANY STATUS]")

        capabilities = (
            "TWOJE ZDOLNOSCI (skills systemu evo-engine):\n"
            + "\n".join(cap_lines) + "\n"
        )

        # Section 3: How to handle user requests
        routing = (
            "\nJAK OBSLUGIWAC ZAPYTANIA:\n"
            "1. User chce rozmawiac glosowo → uzyj skill 'stt' (sluchanie) + 'tts' (mowienie)\n"
            "2. User chce wyszukac cos w internecie → uzyj skill 'web_search'\n"
            "3. User chce zarzadzac kodem → uzyj skill 'git_ops'\n"
            "4. Jesli skill jest USZKODZONY → powiedz: 'Skill [nazwa] wymaga naprawy, "
            "probuje naprawic...' i NIE mow ze nie umiesz\n"
            "5. Jesli skill nie istnieje → zaproponuj stworzenie: '/create [nazwa]'\n"
            "6. Zwykla rozmowa (bez potrzeby skilla) → odpowiadaj normalnie po polsku\n"
        )

        # Section 4: Response rules
        rules = (
            "\nZASADY ODPOWIEDZI:\n"
            "- Odpowiadaj po polsku jesli user pisze po polsku\n"
            "- Krotkie odpowiedzi (2-3 zdania max)\n"
            "- Nigdy nie mow 'jako model jezykowy nie mam mozliwosci' — BO MASZ, przez skille\n"
            "- Nigdy nie mow 'nie moge generowac mowy' — BO MOZESZ, przez skill TTS\n"
            "- Jesli cos nie dziala, powiedz CO nie dziala i ze naprawiasz\n"
        )

        return identity + capabilities + routing + rules

    def build_fallback_message(self, failed_skill: str, error: str = None,
                                attempts: int = 0) -> str:
        """
        When a skill fails, generate appropriate message.
        
        WRONG: "Nie mam mozliwosci komunikacji glosowej"
        RIGHT: "Skill STT ma blad (shutil not defined). Naprawiam..."
        """
        desc = self.CAPABILITY_DESCRIPTIONS.get(failed_skill, failed_skill)
        status = self._skill_statuses.get(failed_skill)

        if attempts >= 3:
            # After 3 failed attempts
            msg = (
                f"Skill '{failed_skill}' ({desc}) nie dziala po {attempts} probach naprawy. "
                f"Blad: {error or 'nieznany'}. "
                f"Mozesz sprobowac: /rollback {failed_skill} lub /evolve {failed_skill}"
            )
        elif error:
            msg = (
                f"Skill '{failed_skill}' ma blad: {error}. "
                f"Probuje naprawic automatycznie..."
            )
        else:
            msg = (
                f"Skill '{failed_skill}' tymczasowo niedostepny. "
                f"System probuje naprawic..."
            )

        return msg

    def build_skill_context_for_llm(self, skill_name: str, action: str = "execute") -> str:
        """
        When LLM needs to generate/fix skill code, give it full context
        about what the system expects.
        """
        return (
            f"Generujesz kod Python dla skilla '{skill_name}' w systemie evo-engine.\n"
            f"WYMAGANIA:\n"
            f"1. Plik MUSI zaczynac sie od WSZYSTKICH potrzebnych importow\n"
            f"2. OBOWIAZKOWE importy sprawdz: os, sys, json, subprocess, shutil, pathlib\n"
            f"3. Klasa musi miec metode execute(self, input_data: dict) -> dict\n"
            f"4. Funkcja get_info() -> dict z kluczami: name, version, description, capabilities\n"
            f"5. Funkcja health_check() -> bool\n"
            f"6. Blok if __name__ == '__main__' z testem\n"
            f"7. KAZDY import uzyty w kodzie MUSI byc na gorze pliku\n"
            f"8. NIE uzywaj modulow ktorych nie importujesz\n"
            f"9. Obsluga bledow try/except w execute()\n"
            f"10. Zwracaj ZAWSZE dict z kluczami 'success' i 'error' lub 'result'\n"
        )

    def detect_needed_capabilities(self, user_message: str) -> list:
        """
        Detect which capabilities the user needs from their message.
        This is SYSTEM-level detection, not LLM-level.
        """
        msg_lower = user_message.lower()
        needed = set()

        for keyword, caps in self.INTENT_TO_CAPABILITY.items():
            if keyword in msg_lower:
                needed.update(caps)

        return list(needed)

    def get_readiness_report(self) -> dict:
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


# === Integration points for existing core.py ===

def patch_analyze_need(original_analyze_need, identity: SystemIdentity):
    """
    Wraps LLMClient.analyze_need to inject system identity.
    
    Instead of modifying core.py directly, this wraps the method.
    """
    def patched(user_msg, conversation=None, skills=None):
        # First: check if system-level routing can handle it
        needed_caps = identity.detect_needed_capabilities(user_msg)
        if needed_caps:
            # System knows what to do — don't ask LLM
            primary = needed_caps[0]
            return {
                "action": "use_skill",
                "skill": primary,
                "all_skills_needed": needed_caps,
                "input": {"text": user_msg},
                "source": "system_identity",  # Flag: this came from system, not LLM
            }
        # Ambiguous — let LLM decide, but with system context
        return original_analyze_need(user_msg, conversation, skills)
    return patched


def patch_handle_request_fallback(identity: SystemIdentity):
    """
    Generate the fallback message when a skill fails.
    
    BEFORE (wrong):
        LLM generates: "Nie mam mozliwosci komunikacji glosowej"
    
    AFTER (correct):
        System generates: "Skill STT ma blad. Naprawiam..."
        Then optionally LLM adds context.
    """
    def build_fallback(skill_name: str, error: str, attempts: int,
                       user_msg: str) -> str:
        system_msg = identity.build_fallback_message(skill_name, error, attempts)
        return system_msg
    return build_fallback


# === Example: how main() chat loop changes ===

EXAMPLE_INTEGRATION = """
# In cores/v1/core.py main() function, BEFORE:

    sys_prompt = (
        "Jestes asystentem AI..."  # <-- LLM thinks it's a chatbot
    )
    resp = llm.chat([{"role":"system","content":sys_prompt}, ...])

# AFTER:

    identity = SystemIdentity(skill_manager=sm)
    identity.refresh_statuses()
    sys_prompt = identity.build_system_prompt()  # <-- dynamic, capability-aware
    resp = llm.chat([{"role":"system","content":sys_prompt}, ...])

# In handle_request(), BEFORE (when skill fails):

    cpr(C.RE, f"Nie udalo sie: {goal}")
    # Then LLM generates: "Nie mam mozliwosci..."  <-- WRONG

# AFTER:

    fallback_msg = identity.build_fallback_message("stt", error=str(e), attempts=3)
    cpr(C.YE, fallback_msg)  # "Skill STT ma blad. Naprawiam..."
    # LLM is NOT asked to explain failure — system handles it
"""


if __name__ == "__main__":
    # Demo
    identity = SystemIdentity()
    
    # Simulate skill statuses
    identity._skill_statuses = {
        "tts": SkillStatus("tts", healthy=True, provider="espeak"),
        "stt": SkillStatus("stt", healthy=False, error="shutil not defined"),
        "echo": SkillStatus("echo", healthy=True),
        "web_search": SkillStatus("web_search", healthy=True),
    }
    
    print("=== SYSTEM PROMPT ===")
    print(identity.build_system_prompt())
    
    print("\n=== FALLBACK MESSAGE (stt failed) ===")
    print(identity.build_fallback_message("stt", "name 'shutil' is not defined", 3))
    
    print("\n=== CAPABILITY DETECTION ===")
    tests = [
        "pogadajmy glosowo",
        "wyszukaj python tutorial",
        "commituj zmiany",
        "jaka jest dzisiaj pogoda",  # no direct skill match
    ]
    for t in tests:
        caps = identity.detect_needed_capabilities(t)
        print(f"  '{t}' -> {caps or 'LLM decides'}")
    
    print("\n=== READINESS REPORT ===")
    import json
    print(json.dumps(identity.get_readiness_report(), indent=2))
