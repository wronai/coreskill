#!/usr/bin/env python3
"""
evo-engine ProviderSelector — resource-aware skill provider selection.

Architecture:
    skills/{capability}/
        manifest.json           <- declares capability + providers
        providers/
            {provider_name}/
                v{N}/skill.py   <- implementation
                meta.json       <- tier, quality, requirements
"""
import json
from pathlib import Path
from typing import Optional

from .config import SKILLS_DIR


# Tier priority (higher = more demanding but better quality)
TIER_ORDER = {"lite": 0, "standard": 1, "premium": 2}


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
        # New structure
        meta_path = self.skills_dir / capability / "providers" / provider / "meta.json"
        if meta_path.exists():
            return json.loads(meta_path.read_text())

        # Legacy: meta.json in version dir
        cap_dir = self.skills_dir / capability
        if provider == "default":
            # Find latest version
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
            # Latest version
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
