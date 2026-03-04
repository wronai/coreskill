#!/usr/bin/env python3
"""
evo-engine EvolutionGarbageCollector — cleans up failed evolution stubs,
manages stable/latest/archive version structure.

Version structure (per provider):
    skills/{capability}/providers/{provider}/
        stable/skill.py     ← last verified working version
        latest/skill.py     ← newest version (may be unstable)
        archive/            ← old versions (limited)
            v1/skill.py
            v63/skill.py

Legacy structure (still supported):
    skills/{capability}/providers/{provider}/v{N}/skill.py
    skills/{capability}/v{N}/skill.py
"""
import json
import shutil
from pathlib import Path
from datetime import datetime, timezone

from .config import SKILLS_DIR, cpr, C


class EvolutionGarbageCollector:
    """Cleans up failed evolution stubs, promotes stable versions."""

    MAX_ARCHIVE_VERSIONS = 5
    STUB_MAX_LINES = 10

    def __init__(self, skills_dir: Path = None):
        self.skills_dir = skills_dir or SKILLS_DIR

    # ── Stub Detection ──────────────────────────────────────────────

    def is_stub(self, skill_path: Path) -> bool:
        """Check if a skill file is a stub (placeholder/failed evolution).
        Stub = <STUB_MAX_LINES lines AND no real functional code."""
        if not skill_path or not skill_path.exists():
            return False
        try:
            code = skill_path.read_text()
        except Exception:
            return True
        lines = [l.strip() for l in code.split("\n") if l.strip()]
        if len(lines) < self.STUB_MAX_LINES:
            # Short file — check for functional code
            _functional = ("subprocess", "os.system", "urllib", "socket",
                           "shutil.which", "Popen", "tempfile", "arecord",
                           "espeak", "vosk")
            if any(f in code for f in _functional):
                return False
            return True
        return False

    def is_broken(self, skill_path: Path) -> bool:
        """Check if skill has syntax errors or markdown artifacts."""
        if not skill_path or not skill_path.exists():
            return True
        try:
            code = skill_path.read_text()
            # Markdown artifacts from LLM
            if "```" in code:
                return True
            import ast
            ast.parse(code)
            return False
        except SyntaxError:
            return True
        except Exception:
            return False

    # ── Version Analysis ────────────────────────────────────────────

    def scan_versions(self, provider_dir: Path) -> dict:
        """Scan a provider directory and classify versions.
        Returns {all: [...], stubs: [...], working: [...], broken: [...],
                 best: Path|None}."""
        result = {"all": [], "stubs": [], "working": [], "broken": [],
                  "best": None, "best_version": None}
        if not provider_dir.is_dir():
            return result

        for vdir in sorted(provider_dir.iterdir()):
            if not vdir.is_dir():
                continue
            if not vdir.name.startswith("v") or vdir.name in ("stable", "latest", "archive"):
                continue
            if not vdir.name[1:].isdigit():
                continue

            sp = vdir / "skill.py"
            if not sp.exists():
                continue

            result["all"].append(vdir)
            if self.is_stub(sp):
                result["stubs"].append(vdir)
            elif self.is_broken(sp):
                result["broken"].append(vdir)
            else:
                result["working"].append(vdir)

        # Best = highest-numbered working version
        if result["working"]:
            result["best"] = result["working"][-1]
            result["best_version"] = result["working"][-1].name

        return result

    # ── Cleanup ─────────────────────────────────────────────────────

    def cleanup_provider(self, provider_dir: Path, dry_run: bool = False) -> dict:
        """Clean stubs and broken versions from a provider directory.
        Returns report dict with actions taken."""
        scan = self.scan_versions(provider_dir)
        report = {"provider": provider_dir.name,
                  "total": len(scan["all"]),
                  "stubs": len(scan["stubs"]),
                  "broken": len(scan["broken"]),
                  "working": len(scan["working"]),
                  "deleted": [], "kept": []}

        # Keep: all working versions (up to MAX_ARCHIVE)
        keep = set()
        for v in scan["working"][-self.MAX_ARCHIVE_VERSIONS:]:
            keep.add(v)

        # Also keep stable/ and latest/ if they exist
        for special in ("stable", "latest"):
            sd = provider_dir / special
            if sd.is_dir():
                keep.add(sd)

        # Delete stubs and broken versions
        for vdir in scan["stubs"] + scan["broken"]:
            if vdir in keep:
                continue
            if dry_run:
                report["deleted"].append(f"[DRY] {vdir.name}")
            else:
                shutil.rmtree(vdir, ignore_errors=True)
                report["deleted"].append(vdir.name)

        # Delete excess working versions (keep only last MAX_ARCHIVE)
        excess = scan["working"][:-self.MAX_ARCHIVE_VERSIONS]
        for vdir in excess:
            if vdir in keep:
                continue
            if dry_run:
                report["deleted"].append(f"[DRY] {vdir.name}")
            else:
                shutil.rmtree(vdir, ignore_errors=True)
                report["deleted"].append(vdir.name)

        report["kept"] = [v.name for v in keep if v.exists()]
        return report

    def cleanup_legacy(self, skill_dir: Path, dry_run: bool = False) -> dict:
        """Clean stubs from a legacy skill directory (v{N} directly under skill)."""
        report = {"skill": skill_dir.name, "total": 0, "deleted": [], "kept": []}
        if not skill_dir.is_dir():
            return report

        all_versions = []
        stubs = []
        working = []

        for vdir in sorted(skill_dir.iterdir()):
            if not vdir.is_dir() or not vdir.name.startswith("v"):
                continue
            if not vdir.name[1:].isdigit():
                continue
            sp = vdir / "skill.py"
            if not sp.exists():
                continue
            all_versions.append(vdir)
            if self.is_stub(sp):
                stubs.append(vdir)
            else:
                working.append(vdir)

        report["total"] = len(all_versions)

        # Keep last MAX_ARCHIVE working versions
        keep = set(working[-self.MAX_ARCHIVE_VERSIONS:])

        for vdir in stubs:
            if vdir in keep:
                continue
            if dry_run:
                report["deleted"].append(f"[DRY] {vdir.name}")
            else:
                shutil.rmtree(vdir, ignore_errors=True)
                report["deleted"].append(vdir.name)

        report["kept"] = [v.name for v in keep if v.exists()]
        return report

    # ── Migration to stable/latest/archive ──────────────────────────

    def migrate_to_stable_latest(self, provider_dir: Path,
                                  dry_run: bool = False) -> dict:
        """Migrate v{N}/ structure to stable/latest/archive.
        1. Find best working version → copy to stable/
        2. Find highest version (working) → copy to latest/
        3. Move remaining working to archive/
        4. Delete stubs and broken versions."""
        scan = self.scan_versions(provider_dir)
        report = {"provider": provider_dir.name,
                  "migrated": False, "stable": None, "latest": None,
                  "archived": [], "deleted": []}

        # Already migrated?
        if (provider_dir / "stable" / "skill.py").exists():
            report["migrated"] = True
            report["stable"] = "stable"
            if (provider_dir / "latest" / "skill.py").exists():
                report["latest"] = "latest"
            # Still clean up any remaining v{N} dirs
            cleanup = self.cleanup_provider(provider_dir, dry_run)
            report["deleted"] = cleanup["deleted"]
            return report

        if not scan["working"]:
            # No working versions — nothing to migrate
            # Still clean stubs
            for vdir in scan["stubs"] + scan["broken"]:
                if not dry_run:
                    shutil.rmtree(vdir, ignore_errors=True)
                report["deleted"].append(vdir.name)
            return report

        # Find best version for stable (prefer original v1 if it works)
        best_for_stable = scan["working"][0]  # oldest working (usually original)
        best_for_latest = scan["working"][-1]  # newest working

        if not dry_run:
            # Create stable/
            stable_dir = provider_dir / "stable"
            stable_dir.mkdir(exist_ok=True)
            self._copy_version(best_for_stable, stable_dir)
            report["stable"] = best_for_stable.name

            # Create latest/ (same as stable if only one working version)
            latest_dir = provider_dir / "latest"
            latest_dir.mkdir(exist_ok=True)
            self._copy_version(best_for_latest, latest_dir)
            report["latest"] = best_for_latest.name

            # Archive up to MAX_ARCHIVE working versions
            archive_dir = provider_dir / "archive"
            archive_dir.mkdir(exist_ok=True)
            for vdir in scan["working"][-self.MAX_ARCHIVE_VERSIONS:]:
                dst = archive_dir / vdir.name
                if not dst.exists():
                    shutil.copytree(vdir, dst)
                report["archived"].append(vdir.name)

            # Delete all v{N} dirs (they're now in stable/latest/archive)
            for vdir in scan["all"]:
                shutil.rmtree(vdir, ignore_errors=True)
                report["deleted"].append(vdir.name)

        report["migrated"] = True
        return report

    def _copy_version(self, src_dir: Path, dst_dir: Path):
        """Copy skill files from a version dir to a target dir."""
        for f in ("skill.py", "meta.json", "Dockerfile"):
            src = src_dir / f
            if src.exists():
                shutil.copy2(src, dst_dir / f)

    # ── Full Cleanup ────────────────────────────────────────────────

    def cleanup_all(self, migrate: bool = True, dry_run: bool = False) -> list:
        """Clean all skills. Returns list of reports."""
        reports = []
        for skill_dir in sorted(self.skills_dir.iterdir()):
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue

            prov_dir = skill_dir / "providers"
            if prov_dir.is_dir():
                # Provider-based skill (tts, stt)
                for provider in sorted(prov_dir.iterdir()):
                    if not provider.is_dir() or provider.name.startswith("."):
                        continue
                    if migrate:
                        r = self.migrate_to_stable_latest(provider, dry_run)
                    else:
                        r = self.cleanup_provider(provider, dry_run)
                    r["skill"] = skill_dir.name
                    reports.append(r)
            else:
                # Legacy skill (kalkulator, shell, etc.)
                r = self.cleanup_legacy(skill_dir, dry_run)
                reports.append(r)

        return reports

    def summary(self, reports: list) -> str:
        """Human-readable summary of cleanup results."""
        lines = ["[GC] Cleanup summary:"]
        total_deleted = 0
        for r in reports:
            deleted = len(r.get("deleted", []))
            total_deleted += deleted
            if deleted > 0:
                skill = r.get("skill", r.get("provider", "?"))
                prov = r.get("provider", "")
                name = f"{skill}/{prov}" if prov and prov != skill else skill
                lines.append(f"  {name}: deleted {deleted}, "
                           f"kept {len(r.get('kept', r.get('archived', [])))}")
                if r.get("stable"):
                    lines.append(f"    stable={r['stable']}, latest={r.get('latest', '?')}")
        lines.append(f"  Total deleted: {total_deleted} version dirs")
        return "\n".join(lines)
