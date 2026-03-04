#!/usr/bin/env python3
"""
FuzzyCommandRouter — fuzzy-matching slash command dispatch.

Uses rapidfuzz for typo-tolerant command matching.
Falls back to exact match if rapidfuzz unavailable.
"""
from typing import Callable, Optional

from .config import cpr, C

try:
    from rapidfuzz import fuzz, process
    _HAS_RAPIDFUZZ = True
except ImportError:
    _HAS_RAPIDFUZZ = False


class FuzzyCommandRouter:
    """Dispatch slash commands with fuzzy matching for typo tolerance.

    Usage:
        router = FuzzyCommandRouter(COMMANDS)
        handler = router.resolve("/skilss")  # → _cmd_skills
    """

    SCORE_THRESHOLD = 75  # minimum similarity score to accept a fuzzy match
    AMBIGUITY_GAP = 10    # min gap between top-2 scores to avoid ambiguity

    def __init__(self, commands: dict[str, Callable]):
        self.commands = commands
        self._keys = list(commands.keys())

    def resolve(self, cmd: str) -> tuple[Optional[Callable], str]:
        """Resolve a command string to its handler.

        Returns (handler, matched_command) or (None, "") if no match.
        Exact match is always preferred. Fuzzy match only when exact fails.
        """
        # Fast path: exact match
        handler = self.commands.get(cmd)
        if handler:
            return handler, cmd

        if not _HAS_RAPIDFUZZ or len(cmd) < 2:
            return None, ""

        # Fuzzy match against all command names
        results = process.extract(
            cmd, self._keys, scorer=fuzz.ratio, limit=3
        )
        if not results:
            return None, ""

        best_name, best_score, _ = results[0]

        # Score too low — not a match
        if best_score < self.SCORE_THRESHOLD:
            return None, ""

        # Check ambiguity: if top-2 are close, don't guess
        if len(results) >= 2:
            _, second_score, _ = results[1]
            if best_score - second_score < self.AMBIGUITY_GAP:
                cpr(C.DIM, f"  Niejednoznaczne: {cmd} → "
                    f"{results[0][0]} ({best_score}%) vs {results[1][0]} ({second_score}%)")
                return None, ""

        cpr(C.DIM, f"  (miałeś na myśli {best_name}?)")
        return self.commands[best_name], best_name

    def add(self, name: str, handler: Callable):
        """Register a new command."""
        self.commands[name] = handler
        self._keys = list(self.commands.keys())

    def remove(self, name: str):
        """Unregister a command."""
        self.commands.pop(name, None)
        self._keys = list(self.commands.keys())
