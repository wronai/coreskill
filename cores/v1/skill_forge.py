#!/usr/bin/env python3
"""
skill_forge.py — Semantic dedup + gated skill creation.

Prevents garbage skill creation by:
1. Embedding similarity search against existing skills
2. Conversational query detection (→ chat, no skill)
3. Error budget enforcement (max N errors/hour)

Replaces the old "action==chat → auto-create" pattern in evo_engine.py
with "Decide Before Create" logic.
"""
import time
import re
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional, Tuple

from .config import SKILLS_DIR, cpr, C


# ─── Error Budget ────────────────────────────────────────────────────

class ErrorBudget:
    """Prevents runaway skill creation after repeated failures."""

    def __init__(self, max_errors_per_hour: int = 10, cooldown_minutes: int = 30):
        self.max = max_errors_per_hour
        self.cooldown = cooldown_minutes
        self.errors: List[float] = []

    def record_error(self):
        self.errors.append(time.time())
        cutoff = time.time() - 3600
        self.errors = [t for t in self.errors if t > cutoff]

    def exhausted(self) -> bool:
        return len(self.errors) >= self.max

    def time_until_reset(self) -> int:
        """Minutes until budget resets."""
        if not self.exhausted():
            return 0
        if not self.errors or self.max <= 0:
            return 0
        oldest_in_window = min(self.errors[-self.max:])
        return max(0, int((oldest_in_window + 3600 - time.time()) / 60))


# ─── Skill Match Result ──────────────────────────────────────────────

@dataclass
class SkillMatch:
    """Result of semantic skill search."""
    name: str
    similarity: float
    description: str = ""


# ─── Conversational Detection (multilingual) ────────────────────────

from .i18n import (
    ALL_GREETING_PATTERNS, ALL_FAREWELL_PATTERNS, ALL_THANKS_PATTERNS,
    ALL_QUESTION_WORDS, ALL_YES_NO_MAYBE, ALL_CREATE_KW_FLAT,
    ALL_ACTION_VERBS, match_any_keyword,
)


def is_conversational(query: str) -> bool:
    """Check if query is a conversational question that doesn't need a skill.
    Supports all European languages via i18n module."""
    q = query.strip()
    if not q:
        return True

    q_lower = q.lower()

    # Explicit creation request → NOT conversational
    if match_any_keyword(q_lower, ALL_CREATE_KW_FLAT):
        return False

    # Greetings in any European language
    if match_any_keyword(q_lower, ALL_GREETING_PATTERNS):
        return True

    # Farewells in any European language
    if match_any_keyword(q_lower, ALL_FAREWELL_PATTERNS):
        return True

    # Thanks / acknowledgment in any European language
    if match_any_keyword(q_lower, ALL_THANKS_PATTERNS):
        return True

    # Yes/No/Maybe single-word responses
    if q_lower.rstrip("?!.,") in ALL_YES_NO_MAYBE:
        return True

    # Questions starting with question words (any language)
    first_word = q_lower.split()[0].rstrip("?!.,") if q_lower.split() else ""
    if first_word in ALL_QUESTION_WORDS:
        return True

    # Short queries (≤3 words) without action verbs are usually conversational
    words = q.split()
    if len(words) <= 3:
        if not any(w.lower() in ALL_ACTION_VERBS for w in words):
            return True

    return False


# ─── SkillForge ──────────────────────────────────────────────────────

class SkillForge:
    """Gated skill creation with semantic dedup.

    Prevents garbage skill creation by checking:
    1. Embedding similarity against existing skills
    2. Whether query is conversational (→ just chat)
    3. Error budget (max 10 failed creates per hour)

    Usage:
        forge = SkillForge(embedding_engine)
        should, reason = forge.should_create("policz 2+2", skills)
        if not should:
            if reason == "reuse:kalkulator":
                # use existing kalkulator skill
            elif reason == "chat":
                # let LLM handle directly
    """

    SIMILARITY_THRESHOLD = 0.85
    MIN_SIMILARITY_SUGGEST = 0.50

    def __init__(self, embedding_engine=None):
        """
        Args:
            embedding_engine: EmbeddingEngine from smart_intent.py (optional).
                If None, falls back to keyword matching.
        """
        self._embedder = embedding_engine
        self._skill_embeddings: dict = {}  # name → (description, embedding)
        self._error_budget = ErrorBudget(max_errors_per_hour=10)
        self._create_count = 0
        self._reuse_count = 0

    def index_skills(self, skills: dict):
        """Build embedding index from existing skills.

        Args:
            skills: dict from SkillManager.list_skills() → {name: [versions]}
        """
        self._skill_descriptions = {}
        for name in skills:
            desc = self._load_skill_description(name)
            if desc:
                self._skill_descriptions[name] = desc

        # Build embeddings if engine available
        if self._embedder and self._skill_descriptions:
            try:
                texts = list(self._skill_descriptions.values())
                names = list(self._skill_descriptions.keys())
                embeddings = self._embedder.encode_batch(texts)
                if embeddings is not None:
                    self._skill_embeddings = {
                        names[i]: (texts[i], embeddings[i])
                        for i in range(len(names))
                    }
            except Exception:
                pass

    @staticmethod
    def _read_json_field(path, field, default=None):
        """Read a field from a JSON file, returning default on any error."""
        if not path.exists():
            return default
        try:
            return json.loads(path.read_text()).get(field, default)
        except (json.JSONDecodeError, OSError):
            return default

    def _load_skill_description(self, name: str) -> str:
        """Load skill description from manifest.json or meta.json."""
        skill_dir = SKILLS_DIR / name
        if not skill_dir.exists():
            return ""

        # Check manifest.json
        manifest = skill_dir / "manifest.json"
        if manifest.exists():
            data = {}
            try:
                data = json.loads(manifest.read_text())
            except (json.JSONDecodeError, OSError):
                pass
            desc = data.get("description", "")
            cap = data.get("capability", name)
            if desc or cap != name:
                return f"{cap}: {desc}" if desc else cap

        # Check meta.json in provider structure then legacy v{N}
        meta_candidates = []
        prov_dir = skill_dir / "providers"
        if prov_dir.is_dir():
            for provider in sorted(prov_dir.iterdir()):
                for vdir in ("stable", "latest"):
                    meta_candidates.append(provider / vdir / "meta.json")
        for vdir in sorted(skill_dir.iterdir(), reverse=True):
            if vdir.is_dir() and vdir.name.startswith("v"):
                meta_candidates.append(vdir / "meta.json")

        for meta in meta_candidates:
            desc = self._read_json_field(meta, "description")
            if desc:
                return desc

        return name

    def search(self, query: str, top_k: int = 3) -> List[SkillMatch]:
        """Find most similar existing skills to query.

        Uses embedding similarity if available, falls back to keyword matching.
        """
        if self._embedder and self._skill_embeddings:
            return self._search_embedding(query, top_k)
        return self._search_keyword(query, top_k)

    def _search_embedding(self, query: str, top_k: int) -> List[SkillMatch]:
        """Semantic search using embeddings."""
        try:
            query_emb = self._embedder.encode(query)
            if query_emb is None:
                return self._search_keyword(query, top_k)

            scores = []
            for name, (desc, emb) in self._skill_embeddings.items():
                sim = self._embedder.cosine_similarity(query_emb, emb)
                scores.append(SkillMatch(name=name, similarity=sim, description=desc))

            scores.sort(key=lambda m: m.similarity, reverse=True)
            return [m for m in scores[:top_k] if m.similarity > self.MIN_SIMILARITY_SUGGEST]
        except Exception:
            return self._search_keyword(query, top_k)

    def _search_keyword(self, query: str, top_k: int) -> List[SkillMatch]:
        """Fallback keyword-based search."""
        q_lower = query.lower()
        q_words = set(re.findall(r'\b\w+\b', q_lower))
        matches = []

        descs = getattr(self, '_skill_descriptions', {})
        for name, desc in descs.items():
            desc_lower = desc.lower()
            desc_words = set(re.findall(r'\b\w+\b', desc_lower))

            # Jaccard-like similarity
            common = q_words & desc_words
            union = q_words | desc_words
            if not union:
                continue
            sim = len(common) / len(union)

            # Bonus for name substring match
            if name in q_lower or any(w in name for w in q_words if len(w) > 3):
                sim = min(sim + 0.3, 1.0)

            if sim > 0.1:
                matches.append(SkillMatch(name=name, similarity=sim, description=desc))

        matches.sort(key=lambda m: m.similarity, reverse=True)
        return matches[:top_k]

    def should_create(self, query: str, existing_skills: dict) -> Tuple[bool, str]:
        """Decide whether to create a new skill.

        Returns:
            (should_create, reason)
            reason is either:
                - "reuse:<skill_name>" → use existing skill
                - "chat" → let LLM handle directly
                - "budget_exceeded" → too many errors
                - "new_skill_needed" → proceed with creation
        """
        # 1. Check error budget
        if self._error_budget.exhausted():
            mins = self._error_budget.time_until_reset()
            cpr(C.YELLOW, f"[FORGE] Error budget exhausted. Reset in {mins}min.")
            return False, "budget_exceeded"

        # 2. Check if conversational
        if is_conversational(query):
            return False, "chat"

        # 3. Re-index if needed
        if not getattr(self, '_skill_descriptions', {}):
            self.index_skills(existing_skills)

        # 4. Semantic similarity search
        matches = self.search(query, top_k=3)
        if matches and matches[0].similarity > self.SIMILARITY_THRESHOLD:
            best = matches[0]
            cpr(C.DIM, f"[FORGE] Reuse '{best.name}' "
                       f"(sim={best.similarity:.2f})")
            self._reuse_count += 1
            return False, f"reuse:{best.name}"

        # 5. Log suggestion if close match exists
        if matches and matches[0].similarity > self.MIN_SIMILARITY_SUGGEST:
            cpr(C.DIM, f"[FORGE] Closest: '{matches[0].name}' "
                       f"(sim={matches[0].similarity:.2f}, below threshold)")

        self._create_count += 1
        return True, "new_skill_needed"

    def record_create_error(self):
        """Record a failed skill creation attempt."""
        self._error_budget.record_error()

    def stats(self) -> str:
        """Return human-readable stats."""
        budget_status = ("EXHAUSTED" if self._error_budget.exhausted()
                         else f"{len(self._error_budget.errors)}/10")
        return (f"created={self._create_count}, "
                f"reused={self._reuse_count}, "
                f"budget={budget_status}, "
                f"indexed={len(getattr(self, '_skill_descriptions', {}))}")
