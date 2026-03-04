#!/usr/bin/env python3
"""
UserMemory — persistent long-term memory for user preferences, directives, and configuration.

Stores directives that the core should always prioritize:
- Communication style (e.g., voice mode, language)
- Behavioral rules (e.g., always respond in Polish)
- Skill preferences (e.g., prefer STT for input)
- Any user-defined configuration notes

Persisted in .evo_state.json under key "user_memory".
"""
from __future__ import annotations
import json
import re
from datetime import datetime, timezone
from typing import Optional

from .config import save_state, cpr, C


# Keywords that suggest the user is stating a preference to remember
_PREF_PATTERNS = [
    r"\bzawsze\b",           # always
    r"\bdomyślnie\b",        # by default
    r"\bwolę\b",             # I prefer
    r"\bpreferuję\b",        # I prefer
    r"\bpamiętaj\b",         # remember
    r"\bzapamiętaj\b",       # memorize
    r"\bchcę żeby\b",        # I want you to
    r"\bchciałbym żeby\b",   # I would like
    r"\bużywaj\b",           # use (imperative)
    r"\brespond in\b",
    r"\balways\b",
    r"\bremember that\b",
    r"\bprefer\b",
    r"\bby default\b",
]

_COMPILED = [re.compile(p, re.IGNORECASE) for p in _PREF_PATTERNS]


class UserMemory:
    """
    Persistent long-term memory for user preferences and directives.

    Directives are short text notes that get injected into every system prompt
    so the LLM always follows user preferences.

    Storage format in state["user_memory"]:
    {
      "directives": [
        {"id": 1, "text": "Zawsze odpowiadaj po polsku", "added": "2026-03-04T...", "priority": "high"},
        {"id": 2, "text": "Preferuj rozmowę głosową zamiast pisania", ...},
        ...
      ],
      "next_id": 3
    }
    """

    def __init__(self, state: dict):
        self.state = state
        mem = state.setdefault("user_memory", {"directives": [], "next_id": 1})
        if "directives" not in mem:
            mem["directives"] = []
        if "next_id" not in mem:
            mem["next_id"] = len(mem["directives"]) + 1
        self._mem = mem

    @property
    def directives(self) -> list[dict]:
        return self._mem.get("directives", [])

    def add(self, text: str, priority: str = "high") -> dict:
        """Add a new directive. Returns the new entry."""
        text = text.strip()
        if not text:
            return {}
        # Deduplicate: don't add if very similar text already exists
        tl = text.lower()
        for d in self.directives:
            if d["text"].lower() == tl:
                return d
        entry = {
            "id": self._mem["next_id"],
            "text": text,
            "added": datetime.now(timezone.utc).isoformat(),
            "priority": priority,
        }
        self._mem["directives"].append(entry)
        self._mem["next_id"] += 1
        save_state(self.state)
        return entry

    def remove(self, directive_id: int) -> bool:
        """Remove a directive by id. Returns True if found and removed."""
        before = len(self.directives)
        self._mem["directives"] = [d for d in self.directives if d["id"] != directive_id]
        if len(self.directives) < before:
            save_state(self.state)
            return True
        return False

    def clear_all(self) -> int:
        """Remove all directives. Returns count removed."""
        n = len(self.directives)
        self._mem["directives"] = []
        save_state(self.state)
        return n

    # ── Voice Mode ────────────────────────────────────────────────

    _VOICE_DIRECTIVE = "Zawsze rozmawiaj głosowo (tryb głosowy włączony)"

    @property
    def voice_mode(self) -> bool:
        """Check if persistent voice mode is active."""
        return any("tryb głosowy" in d["text"].lower() or
                   "rozmawiaj głosowo" in d["text"].lower()
                   for d in self.directives)

    def set_voice_mode(self, enabled: bool) -> dict | None:
        """Enable or disable persistent voice mode."""
        if enabled:
            if self.voice_mode:
                return None  # already active
            return self.add(self._VOICE_DIRECTIVE, priority="high")
        else:
            removed = False
            for d in list(self.directives):
                if ("tryb głosowy" in d["text"].lower() or
                        "rozmawiaj głosowo" in d["text"].lower()):
                    self.remove(d["id"])
                    removed = True
            return {"removed": removed}

    def has_directive(self, keyword: str) -> bool:
        """Check if any directive contains the keyword."""
        kw = keyword.lower()
        return any(kw in d["text"].lower() for d in self.directives)

    def build_system_context(self) -> str:
        """Return directives formatted for injection into system prompt."""
        if not self.directives:
            return ""
        lines = ["WAŻNE — trwałe preferencje użytkownika (zawsze przestrzegaj):"]
        for d in self.directives:
            lines.append(f"  • {d['text']}")
        return "\n".join(lines)

    def looks_like_preference(self, msg: str) -> bool:
        """Return True if the message looks like a preference the user wants remembered."""
        return any(p.search(msg) for p in _COMPILED)

    def suggest_save(self, msg: str) -> Optional[str]:
        """
        If the message looks like a preference, return a clean version
        suitable for saving. Otherwise return None.
        """
        if not self.looks_like_preference(msg):
            return None
        # Trim to reasonable length
        clean = msg.strip().rstrip(".!?")
        if len(clean) > 200:
            clean = clean[:200] + "..."
        return clean

    def display(self) -> None:
        """Print all directives to terminal."""
        if not self.directives:
            cpr(C.DIM, "  (brak zapisanych preferencji)")
            return
        for d in self.directives:
            ts = d.get("added", "")[:10]
            pri = "❗" if d.get("priority") == "high" else "ℹ"
            cpr(C.CYAN, f"  [{d['id']}] {pri} {d['text']}")
            cpr(C.DIM, f"       dodano: {ts}")
