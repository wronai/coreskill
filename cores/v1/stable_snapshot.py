"""stable_snapshot.py — Stable version management for skills.

When a skill works correctly, save it as "stable".
When fixing bugs, create a "bugfix" branch.
When improving, create a "feature" branch.
Stable always remains as the reference point for validation and testing.

Directory structure per skill:
  skills/<name>/providers/<provider>/
    stable/          ← known-good version (reference point)
    latest/          ← current working version
    branches/
      bugfix_<ts>/   ← bug fix attempts
      feature_<ts>/  ← feature improvements
    archive/         ← old versions
"""

import json
import shutil
import time
import difflib
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from .config import SKILLS_DIR, cpr, C


@dataclass
class SnapshotInfo:
    """Metadata for a saved snapshot."""
    skill_name: str
    provider: str
    branch_type: str         # "stable", "latest", "bugfix", "feature"
    branch_name: str         # e.g. "bugfix_20240304_1120"
    created_at: str
    source_version: str      # What it was branched from
    health_status: str       # "ok", "broken", "untested"
    description: str = ""
    test_results: dict = field(default_factory=dict)


class StableSnapshot:
    """Manages stable/bugfix/feature versions of skills.
    
    Key principles:
    - Stable is SACRED — only promote to stable after verification
    - Bug fixes go to branches/bugfix_<ts>/ — never overwrite stable
    - Features go to branches/feature_<ts>/ — experimental
    - After verification, promote branch → stable (old stable → archive)
    """
    
    SNAPSHOT_META = ".snapshot_meta.json"
    
    def __init__(self, skill_manager=None, logger=None):
        self.sm = skill_manager
        self.log = logger
    
    # ─── Save / Promote ─────────────────────────────────────────────
    
    def save_as_stable(self, skill_name: str, provider: str = None) -> Optional[str]:
        """Save current working version as stable.
        Only call this when the skill is VERIFIED working.
        
        Returns path to stable version or None on error.
        """
        src = self._find_current_version(skill_name, provider)
        if not src:
            cpr(C.YELLOW, f"[SNAPSHOT] Nie znaleziono aktualnej wersji {skill_name}")
            return None
        
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            return None
            
        stable_dir = SKILLS_DIR / skill_name / "providers" / provider / "stable"
        
        # If stable already exists, archive it first
        if stable_dir.exists() and any(stable_dir.iterdir()):
            self._archive_version(skill_name, provider, "stable", "pre_promote")
        
        # Copy current to stable
        stable_dir.mkdir(parents=True, exist_ok=True)
        self._copy_skill_files(src, stable_dir)
        
        # Write metadata
        meta = SnapshotInfo(
            skill_name=skill_name,
            provider=provider,
            branch_type="stable",
            branch_name="stable",
            created_at=datetime.now(timezone.utc).isoformat(),
            source_version=str(src),
            health_status="ok",
            description="Promoted to stable (verified working)",
        )
        self._save_meta(stable_dir, meta)
        
        cpr(C.GREEN, f"[SNAPSHOT] ✓ {skill_name}/{provider}: zapisano jako stable")
        return str(stable_dir)
    
    def create_branch(self, skill_name: str, branch_type: str = "bugfix",
                      description: str = "", provider: str = None) -> Optional[str]:
        """Create a branch from stable for bug fixing or feature development.
        
        branch_type: "bugfix" or "feature"
        Returns path to new branch or None.
        """
        if branch_type not in ("bugfix", "feature"):
            cpr(C.RED, f"[SNAPSHOT] Nieznany typ brancha: {branch_type}")
            return None
        
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            return None
        
        stable_dir = SKILLS_DIR / skill_name / "providers" / provider / "stable"
        if not stable_dir.exists():
            cpr(C.YELLOW, f"[SNAPSHOT] Brak wersji stable dla {skill_name}/{provider}")
            # Use latest or any existing version
            stable_dir = self._find_current_version(skill_name, provider)
            if not stable_dir:
                return None
        
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        branch_name = f"{branch_type}_{ts}"
        branch_dir = (SKILLS_DIR / skill_name / "providers" / provider 
                      / "branches" / branch_name)
        branch_dir.mkdir(parents=True, exist_ok=True)
        
        self._copy_skill_files(stable_dir, branch_dir)
        
        meta = SnapshotInfo(
            skill_name=skill_name,
            provider=provider,
            branch_type=branch_type,
            branch_name=branch_name,
            created_at=datetime.now(timezone.utc).isoformat(),
            source_version="stable",
            health_status="untested",
            description=description or f"{branch_type} branch from stable",
        )
        self._save_meta(branch_dir, meta)
        
        cpr(C.CYAN, f"[SNAPSHOT] Utworzono branch: {branch_name} (z stable)")
        return str(branch_dir)
    
    def promote_branch(self, skill_name: str, branch_name: str,
                       provider: str = None) -> bool:
        """Promote a branch to stable after verification.
        Current stable is archived first.
        """
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            return False
        
        branch_dir = (SKILLS_DIR / skill_name / "providers" / provider
                      / "branches" / branch_name)
        if not branch_dir.exists():
            cpr(C.RED, f"[SNAPSHOT] Branch nie istnieje: {branch_name}")
            return False
        
        # Verify health before promoting
        health = self._check_health(branch_dir)
        if health != "ok":
            cpr(C.YELLOW, f"[SNAPSHOT] Branch {branch_name} nie przeszedł health check: {health}")
            cpr(C.YELLOW, f"[SNAPSHOT] Nie promując do stable bez weryfikacji.")
            return False
        
        # Archive current stable
        stable_dir = SKILLS_DIR / skill_name / "providers" / provider / "stable"
        if stable_dir.exists():
            self._archive_version(skill_name, provider, "stable", f"before_{branch_name}")
        
        # Copy branch to stable
        stable_dir.mkdir(parents=True, exist_ok=True)
        self._copy_skill_files(branch_dir, stable_dir)
        
        meta = SnapshotInfo(
            skill_name=skill_name,
            provider=provider,
            branch_type="stable",
            branch_name="stable",
            created_at=datetime.now(timezone.utc).isoformat(),
            source_version=branch_name,
            health_status="ok",
            description=f"Promoted from {branch_name}",
        )
        self._save_meta(stable_dir, meta)
        
        cpr(C.GREEN, f"[SNAPSHOT] ✓ {branch_name} → stable (zweryfikowane)")
        return True
    
    def restore_stable(self, skill_name: str, provider: str = None) -> bool:
        """Restore stable version to latest/ (rollback)."""
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            return False
        
        stable_dir = SKILLS_DIR / skill_name / "providers" / provider / "stable"
        latest_dir = SKILLS_DIR / skill_name / "providers" / provider / "latest"
        
        if not stable_dir.exists():
            cpr(C.RED, f"[SNAPSHOT] Brak stable do przywrócenia dla {skill_name}")
            return False
        
        # Archive current latest
        if latest_dir.exists():
            self._archive_version(skill_name, provider, "latest", "pre_rollback")
        
        latest_dir.mkdir(parents=True, exist_ok=True)
        self._copy_skill_files(stable_dir, latest_dir)
        
        cpr(C.GREEN, f"[SNAPSHOT] ✓ {skill_name}: przywrócono stable → latest (rollback)")
        return True
    
    # ─── Validation ──────────────────────────────────────────────────
    
    def validate_against_stable(self, skill_name: str,
                                provider: str = None) -> dict:
        """Compare current version against stable reference.
        
        Returns: {"matches": bool, "diff_lines": int, "health_stable": str,
                  "health_current": str, "changes_summary": str}
        """
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            return {"matches": False, "error": "no provider found"}
        
        stable_dir = SKILLS_DIR / skill_name / "providers" / provider / "stable"
        current_dir = self._find_current_version(skill_name, provider)
        
        if not stable_dir.exists():
            return {"matches": False, "error": "no stable version",
                    "health_current": self._check_health(current_dir) if current_dir else "missing"}
        
        if not current_dir:
            return {"matches": False, "error": "no current version"}
        
        # Compare files
        stable_skill = stable_dir / "skill.py"
        current_skill = current_dir / "skill.py"
        
        if not stable_skill.exists() or not current_skill.exists():
            return {"matches": False, "error": "skill.py missing in one version"}
        
        stable_code = stable_skill.read_text()
        current_code = current_skill.read_text()
        
        diff = list(difflib.unified_diff(
            stable_code.splitlines(), current_code.splitlines(),
            fromfile="stable", tofile="current", lineterm=""))
        
        h_stable = self._check_health(stable_dir)
        h_current = self._check_health(current_dir)
        
        changes = ""
        if diff:
            added = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
            removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))
            changes = f"+{added}/-{removed} lines changed"
        
        return {
            "matches": len(diff) == 0,
            "diff_lines": len(diff),
            "health_stable": h_stable,
            "health_current": h_current,
            "changes_summary": changes or "identical",
        }
    
    def list_branches(self, skill_name: str, provider: str = None) -> List[dict]:
        """List all branches for a skill."""
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            return []
        
        branches_dir = SKILLS_DIR / skill_name / "providers" / provider / "branches"
        if not branches_dir.exists():
            return []
        
        result = []
        for bdir in sorted(branches_dir.iterdir()):
            if bdir.is_dir():
                meta = self._load_meta(bdir)
                result.append({
                    "name": bdir.name,
                    "type": meta.branch_type if meta else "unknown",
                    "created": meta.created_at if meta else "",
                    "health": meta.health_status if meta else "untested",
                    "description": meta.description if meta else "",
                })
        return result
    
    # ─── Internal ────────────────────────────────────────────────────
    
    def _detect_provider(self, skill_name: str) -> Optional[str]:
        """Detect the provider for a skill."""
        prov_dir = SKILLS_DIR / skill_name / "providers"
        if not prov_dir.is_dir():
            return None
        for p in sorted(prov_dir.iterdir()):
            if p.is_dir() and not p.name.startswith("."):
                return p.name
        return None
    
    def _find_current_version(self, skill_name: str,
                              provider: str = None) -> Optional[Path]:
        """Find the current active version directory."""
        provider = provider or self._detect_provider(skill_name)
        if not provider:
            # Try legacy structure
            legacy = SKILLS_DIR / skill_name / "v1"
            if legacy.exists():
                return legacy
            return None
        
        base = SKILLS_DIR / skill_name / "providers" / provider
        for pref in ("stable", "latest"):
            d = base / pref
            if d.exists() and (d / "skill.py").exists():
                return d
        # Try v{N} dirs
        for vdir in sorted(base.iterdir(), reverse=True):
            if vdir.is_dir() and (vdir / "skill.py").exists():
                return vdir
        return None
    
    def _copy_skill_files(self, src: Path, dst: Path):
        """Copy skill files from src to dst."""
        dst.mkdir(parents=True, exist_ok=True)
        for item in src.iterdir():
            if item.name.startswith(".") or item.name == "__pycache__":
                continue
            if item.name == "branches" or item.name == "archive":
                continue
            target = dst / item.name
            if item.is_file():
                shutil.copy2(str(item), str(target))
            elif item.is_dir():
                if target.exists():
                    shutil.rmtree(str(target))
                shutil.copytree(str(item), str(target))
    
    def _archive_version(self, skill_name: str, provider: str,
                         version_name: str, reason: str):
        """Move a version to archive."""
        src = SKILLS_DIR / skill_name / "providers" / provider / version_name
        if not src.exists():
            return
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        archive_dir = (SKILLS_DIR / skill_name / "providers" / provider
                       / "archive" / f"{version_name}_{reason}_{ts}")
        archive_dir.mkdir(parents=True, exist_ok=True)
        self._copy_skill_files(src, archive_dir)
        cpr(C.DIM, f"  [ARCHIVE] {version_name} → archive/{archive_dir.name}")
    
    def _check_health(self, skill_dir: Path) -> str:
        """Quick health check of a skill version."""
        if not skill_dir or not skill_dir.exists():
            return "missing"
        skill_py = skill_dir / "skill.py"
        if not skill_py.exists():
            return "no_skill_py"
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location("_hcheck", str(skill_py))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            # Check for health_check function
            if hasattr(mod, "health_check"):
                result = mod.health_check()
                if isinstance(result, dict):
                    return "ok" if result.get("status") == "ok" else "degraded"
                return "ok" if result else "degraded"
            return "ok"  # Loads without error
        except Exception as e:
            return f"error: {str(e)[:60]}"
    
    def _save_meta(self, skill_dir: Path, info: SnapshotInfo):
        """Save snapshot metadata."""
        try:
            meta_path = skill_dir / self.SNAPSHOT_META
            with open(meta_path, "w") as f:
                json.dump(asdict(info), f, indent=2, ensure_ascii=False)
        except Exception:
            pass
    
    def _load_meta(self, skill_dir: Path) -> Optional[SnapshotInfo]:
        """Load snapshot metadata."""
        try:
            meta_path = skill_dir / self.SNAPSHOT_META
            if meta_path.exists():
                with open(meta_path) as f:
                    data = json.load(f)
                return SnapshotInfo(**data)
        except Exception:
            pass
        return None
