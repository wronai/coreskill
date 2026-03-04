#!/usr/bin/env python3
"""
evo-engine ProviderSelector — resource-aware skill provider selection
with ProviderChain auto-degradation.

Architecture:
    skills/{capability}/
        manifest.json           <- declares capability + providers
        providers/
            {provider_name}/
                stable/skill.py <- verified working version
                latest/skill.py <- newest version
                meta.json       <- tier, quality, requirements
"""
import json
import time
from pathlib import Path
from typing import Optional

from .config import SKILLS_DIR, get_config_value


# Tier priority (higher = more demanding but better quality)
TIER_ORDER = get_config_value("tier_order", {"lite": 0, "standard": 1, "premium": 2})

# Auto-degradation constants - loaded from system config
FAILURE_THRESHOLD = get_config_value("cooldowns.failure_threshold", 3)
DEMOTION_COOLDOWN = get_config_value("cooldowns.demotion", 300)
SUCCESS_RECOVERY = get_config_value("cooldowns.success_recovery", 2)


class ProviderInfo:
    """Parsed provider metadata."""
    def __init__(self, name: str, meta: dict):
        self.name = name
        self.tier = meta.get("tier", "standard")
        self.quality_score = meta.get("quality_score", 5)
        self.requirements = meta.get("requirements", {})
        self.fallback_to = meta.get("fallback_to")
        self.tags = meta.get("tags", [])
        self.auto_install = meta.get("auto_install", False)


class ProviderSelector:
    """Selects the best available provider for a capability."""

    def __init__(self, skills_dir: Path = None, resource_monitor=None):
        self.skills_dir = skills_dir or SKILLS_DIR
        self.rm = resource_monitor  # ResourceMonitor instance

    def list_capabilities(self) -> list:
        """List all capabilities (skill names)."""
        caps = []
        for d in sorted(self.skills_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("."):
                if (d / "manifest.json").exists() or (d / "providers").is_dir():
                    caps.append(d.name)
                elif any((d / v / "skill.py").exists()
                         for v in d.iterdir() if v.is_dir()):
                    # Legacy structure: skills/name/v1/skill.py
                    caps.append(d.name)
        return caps

    def list_providers(self, capability: str) -> list:
        """List available providers for a capability."""
        cap_dir = self.skills_dir / capability

        # New structure: providers/ subdir
        prov_dir = cap_dir / "providers"
        if prov_dir.is_dir():
            return sorted([
                p.name for p in prov_dir.iterdir()
                if p.is_dir() and not p.name.startswith(".")
            ])

        # Legacy structure: v1/, v2/ directly under capability
        # Treat as single "default" provider
        return ["default"]

    def load_manifest(self, capability: str) -> dict:
        """Load manifest.json for a capability."""
        mp = self.skills_dir / capability / "manifest.json"
        if mp.exists():
            return json.loads(mp.read_text())
        # Generate minimal manifest for legacy skills
        return {
            "capability": capability,
            "providers": self.list_providers(capability),
            "default_provider": "default",
            "selection_strategy": "best_available",
        }

    def load_meta(self, capability: str, provider: str) -> dict:
        """Load meta.json for a specific provider."""
        # New structure: provider-level meta.json
        meta_path = self.skills_dir / capability / "providers" / provider / "meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())

        # Check stable/latest dirs for meta.json
        prov_dir = self.skills_dir / capability / "providers" / provider
        if prov_dir.is_dir():
            for pref in ("stable", "latest"):
                pm = prov_dir / pref / "meta.json"
                if pm.exists():
                    return json.loads(pm.read_text())

        # Legacy: meta.json in version dir
        cap_dir = self.skills_dir / capability
        if provider == "default":
            versions = sorted([
                v.name for v in cap_dir.iterdir()
                if v.is_dir() and v.name.startswith("v")
            ])
            if versions:
                legacy_meta = cap_dir / versions[-1] / "meta.json"
                if legacy_meta.exists():
                    return json.loads(legacy_meta.read_text())

        return {"provider": provider, "tier": "standard", "quality_score": 5}

    def get_provider_info(self, capability: str, provider: str) -> ProviderInfo:
        meta = self.load_meta(capability, provider)
        return ProviderInfo(provider, meta)

    def select(self, capability: str,
               prefer: str = "quality",
               force: Optional[str] = None,
               context: Optional[dict] = None) -> str:
        """
        Select the best provider for a capability.

        Args:
            capability: e.g. "tts", "stt", "web_search"
            prefer: "quality" (default), "speed", "reliability"
            force: force a specific provider
            context: additional context dict
        Returns:
            provider name (e.g. "espeak", "coqui")
        """
        if force:
            providers = self.list_providers(capability)
            if force in providers:
                return force
            # Force requested but not available
            return self._fallback(capability)

        providers = self.list_providers(capability)
        if not providers:
            return "default"

        if len(providers) == 1:
            return providers[0]

        # Score each provider
        scored = []
        for pname in providers:
            info = self.get_provider_info(capability, pname)
            can_run, reason = self._check_runnable(info)
            if can_run:
                score = self._score(info, prefer, context)
                scored.append((pname, score, info))

        if not scored:
            # Nothing can run — try default or first available
            manifest = self.load_manifest(capability)
            return manifest.get("default_provider", providers[0])

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[0][0]

    def _check_runnable(self, info: ProviderInfo) -> tuple:
        """Check if provider can run on this system."""
        if not self.rm:
            # No resource monitor — assume everything works
            return True, "no monitor"
        return self.rm.can_run(info.requirements)

    def _score(self, info: ProviderInfo, prefer: str, context: dict = None) -> float:
        """Score a provider based on preference."""
        score = 0.0

        if prefer == "quality":
            score = info.quality_score * 10
            score += TIER_ORDER.get(info.tier, 1) * 5

        elif prefer == "speed":
            # Lite tier = fast, premium = slow
            speed_bonus = {0: 30, 1: 15, 2: 0}  # lite=30, standard=15, premium=0
            tier_idx = TIER_ORDER.get(info.tier, 1)
            score = speed_bonus.get(tier_idx, 10)
            score += (10 - info.quality_score)  # lower quality = likely faster

        elif prefer == "reliability":
            # Prefer lite (fewer deps = more reliable)
            if info.tier == "lite":
                score += 30
            elif info.tier == "standard":
                score += 20
            score += 5 if not info.requirements.get("gpu") else 0
            score += 5 if not info.requirements.get("python_packages") else 0

        # Context bonuses
        if context:
            if context.get("prefer_fast") and info.tier == "lite":
                score += 20
            if context.get("prefer_quality") and info.tier == "premium":
                score += 20
            if context.get("offline") and "offline" in info.tags:
                score += 25

        return score

    def _fallback(self, capability: str) -> str:
        """Get fallback provider."""
        manifest = self.load_manifest(capability)
        return manifest.get("default_provider", "default")

    def get_skill_path(self, capability: str, provider: str,
                       version: Optional[str] = None) -> Optional[Path]:
        """Get the actual skill.py path for a capability/provider/version."""
        # New structure
        prov_dir = self.skills_dir / capability / "providers" / provider
        if prov_dir.is_dir():
            if version:
                sp = prov_dir / version / "skill.py"
                return sp if sp.exists() else None
            # Prefer stable > latest > highest v{N}
            for pref in ("stable", "latest"):
                sp = prov_dir / pref / "skill.py"
                if sp.exists():
                    return sp
            versions = sorted([
                v.name for v in prov_dir.iterdir()
                if v.is_dir() and v.name.startswith("v")
            ])
            if versions:
                return prov_dir / versions[-1] / "skill.py"

        # Legacy structure: skills/capability/v{N}/skill.py
        if provider == "default":
            cap_dir = self.skills_dir / capability
            versions = sorted([
                v.name for v in cap_dir.iterdir()
                if v.is_dir() and v.name.startswith("v")
            ])
            if versions:
                target = version if version and version in versions else versions[-1]
                sp = cap_dir / target / "skill.py"
                return sp if sp.exists() else None

        return None

    def summary(self) -> str:
        """Human-readable summary of all capabilities and providers."""
        lines = []
        for cap in self.list_capabilities():
            providers = self.list_providers(cap)
            selected = self.select(cap)
            parts = []
            for p in providers:
                info = self.get_provider_info(cap, p)
                can, _ = self._check_runnable(info)
                marker = " <-" if p == selected else ""
                status = "OK" if can else "X"
                parts.append(f"{p}(q={info.quality_score},{info.tier},{status}){marker}")
            lines.append(f"  {cap}: {' | '.join(parts)}")
        return "\n".join(lines)


class ProviderChain:
    """Ordered provider fallback chain with auto-degradation.

    Tracks failures per provider and automatically demotes/restores
    providers based on their runtime reliability.
    """

    def __init__(self, selector: ProviderSelector):
        self.selector = selector
        # {(capability, provider): {failures: int, last_fail: float,
        #                           successes: int, demoted: bool}}
        self._stats: dict = {}

    def _key(self, cap: str, prov: str) -> tuple:
        return (cap, prov)

    def _get_stats(self, cap: str, prov: str) -> dict:
        k = self._key(cap, prov)
        if k not in self._stats:
            self._stats[k] = {
                "failures": 0, "successes": 0,
                "last_fail": 0.0, "demoted": False,
            }
        return self._stats[k]

    # ── Chain Building ──────────────────────────────────────────────

    def build_chain(self, capability: str,
                    prefer: str = "quality",
                    context: Optional[dict] = None) -> list:
        """Build ordered provider chain for a capability.

        Order: selected (best scored) → fallback_to chain → remaining by score.
        Demoted providers are pushed to the end.
        """
        providers = self.selector.list_providers(capability)
        if not providers:
            return ["default"]

        # Score all providers
        scored = []
        for pname in providers:
            info = self.selector.get_provider_info(capability, pname)
            can_run, _ = self.selector._check_runnable(info)
            score = self.selector._score(info, prefer, context) if can_run else -1
            scored.append((pname, score, info))

        # Sort by score descending
        scored.sort(key=lambda x: x[1], reverse=True)

        # Build chain: non-demoted first, demoted last
        chain = []
        demoted_list = []
        for pname, score, info in scored:
            if score < 0:
                continue  # can't run
            stats = self._get_stats(capability, pname)
            if stats["demoted"] and not self._cooldown_expired(stats):
                demoted_list.append(pname)
            else:
                chain.append(pname)

        # Follow fallback_to chains to ensure proper ordering
        chain = self._reorder_by_fallback(capability, chain)

        # Append demoted providers at the end (still available as last resort)
        chain.extend(demoted_list)

        return chain if chain else [providers[0]]

    def _reorder_by_fallback(self, capability: str, chain: list) -> list:
        """Reorder chain following fallback_to links from meta.json."""
        if len(chain) <= 1:
            return chain

        # Build fallback graph
        fallbacks = {}
        for pname in chain:
            info = self.selector.get_provider_info(capability, pname)
            if info.fallback_to and info.fallback_to in chain:
                fallbacks[pname] = info.fallback_to

        # If no fallback links, keep score-based order
        if not fallbacks:
            return chain

        # Reorder: primary first, then follow fallback links
        ordered = []
        remaining = set(chain)
        for p in chain:
            if p in remaining:
                ordered.append(p)
                remaining.discard(p)
                # Follow fallback chain
                fb = fallbacks.get(p)
                while fb and fb in remaining:
                    ordered.append(fb)
                    remaining.discard(fb)
                    fb = fallbacks.get(fb)

        return ordered

    # ── Selection with Fallback ─────────────────────────────────────

    def select_with_fallback(self, capability: str,
                              prefer: str = "quality",
                              context: Optional[dict] = None) -> list:
        """Return ordered list of providers to try (best first).

        Caller should try each in order, calling record_success/failure.
        """
        return self.build_chain(capability, prefer, context)

    def select_best(self, capability: str,
                    prefer: str = "quality",
                    context: Optional[dict] = None) -> str:
        """Select single best provider (health-aware)."""
        chain = self.build_chain(capability, prefer, context)
        return chain[0] if chain else "default"

    # ── Failure/Success Tracking ────────────────────────────────────

    def record_failure(self, capability: str, provider: str,
                       error: str = ""):
        """Record a provider failure. Auto-demotes after threshold."""
        stats = self._get_stats(capability, provider)
        stats["failures"] += 1
        stats["successes"] = 0  # reset consecutive successes
        stats["last_fail"] = time.time()

        if stats["failures"] >= FAILURE_THRESHOLD:
            stats["demoted"] = True

    def record_success(self, capability: str, provider: str):
        """Record a provider success. Restores after threshold."""
        stats = self._get_stats(capability, provider)
        stats["successes"] += 1

        if stats["successes"] >= SUCCESS_RECOVERY:
            stats["demoted"] = False
            stats["failures"] = 0

    def _cooldown_expired(self, stats: dict) -> bool:
        """Check if demotion cooldown has expired."""
        if not stats["demoted"]:
            return True
        elapsed = time.time() - stats["last_fail"]
        return elapsed >= DEMOTION_COOLDOWN

    # ── Status ──────────────────────────────────────────────────────

    def is_demoted(self, capability: str, provider: str) -> bool:
        stats = self._get_stats(capability, provider)
        return stats["demoted"] and not self._cooldown_expired(stats)

    def get_stats(self, capability: str, provider: str) -> dict:
        """Get failure/success stats for a provider."""
        stats = self._get_stats(capability, provider)
        return {
            "provider": provider,
            "failures": stats["failures"],
            "successes": stats["successes"],
            "demoted": stats["demoted"],
            "cooldown_remaining": max(0, DEMOTION_COOLDOWN - (time.time() - stats["last_fail"]))
            if stats["demoted"] else 0,
        }

    def chain_summary(self, capability: str) -> str:
        """Human-readable chain summary."""
        chain = self.build_chain(capability)
        parts = []
        for i, pname in enumerate(chain):
            stats = self._get_stats(capability, pname)
            demoted = " [DEMOTED]" if self.is_demoted(capability, pname) else ""
            fail_info = f" (f={stats['failures']})" if stats["failures"] > 0 else ""
            parts.append(f"{i+1}. {pname}{fail_info}{demoted}")
        return f"{capability}: {' → '.join(parts)}"
