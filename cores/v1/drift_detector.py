#!/usr/bin/env python3
"""
drift_detector.py — Detects drift between manifest declarations and runtime state.

Compares manifest.json declarations with actual skill implementation:
- Interface drift: manifest declares X, skill implements Y
- Version drift: too many versions vs max_versions in manifest
- Quality drift: skill quality below min_quality_score
- Provider drift: providers in runtime don't match manifest
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .config import SKILLS_DIR
from .skill_schema import get_schema_validation_stats, SkillSchemaValidator
from .quality_gate import SkillQualityGate
from .preflight import SkillPreflight


@dataclass
class DriftReport:
    """Report of detected drift for a capability."""
    capability: str
    drift_detected: bool
    drifts: list = field(default_factory=list)
    manifest_path: Optional[Path] = None
    severity: str = "low"  # low, medium, high
    
    def summary(self) -> str:
        status = "⚠️" if self.drift_detected else "✓"
        parts = [f"{status} {self.capability}: {len(self.drifts)} drift(s)"]
        for d in self.drifts[:3]:
            parts.append(f"  - {d}")
        return "\n".join(parts)


class DriftDetector:
    """Detects drift between manifest declarations and runtime state."""
    
    def __init__(self):
        self.schema_validator = SkillSchemaValidator()
        self.quality_gate = SkillQualityGate(SkillPreflight())
    
    def detect(self, capability: str) -> DriftReport:
        """Detect drift for a specific capability."""
        skill_dir = SKILLS_DIR / capability
        if not skill_dir.exists():
            return DriftReport(
                capability=capability,
                drift_detected=False,
                drifts=["Capability not found"]
            )
        
        manifest_path = skill_dir / "manifest.json"
        if not manifest_path.exists():
            return DriftReport(
                capability=capability,
                drift_detected=False,
                drifts=["No manifest.json"]
            )
        
        # Load manifest
        try:
            manifest = json.loads(manifest_path.read_text())
        except json.JSONDecodeError as e:
            return DriftReport(
                capability=capability,
                drift_detected=True,
                drifts=[f"Invalid JSON: {e}"],
                manifest_path=manifest_path,
                severity="high"
            )
        
        drifts = []
        
        # Check 1: Interface drift (skill implements what manifest declares?)
        interface_drift = self._check_interface_drift(capability, manifest)
        if interface_drift:
            drifts.extend(interface_drift)
        
        # Check 2: Version count drift
        version_drift = self._check_version_drift(capability, manifest)
        if version_drift:
            drifts.append(version_drift)
        
        # Check 3: Provider drift (for multi-provider skills)
        provider_drift = self._check_provider_drift(capability, manifest)
        if provider_drift:
            drifts.extend(provider_drift)
        
        # Check 4: Quality drift (evaluate latest version)
        quality_drift = self._check_quality_drift(capability, manifest)
        if quality_drift:
            drifts.append(quality_drift)
        
        # Determine severity
        severity = "low"
        if any("quality" in d for d in drifts):
            severity = "high"
        elif any("interface" in d for d in drifts):
            severity = "medium"
        elif len(drifts) > 2:
            severity = "medium"
        
        return DriftReport(
            capability=capability,
            drift_detected=len(drifts) > 0,
            drifts=drifts,
            manifest_path=manifest_path,
            severity=severity
        )
    
    def detect_all(self) -> list[DriftReport]:
        """Detect drift for all capabilities."""
        reports = []
        
        if not SKILLS_DIR.exists():
            return reports
        
        for skill_dir in SKILLS_DIR.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith("."):
                continue
            report = self.detect(skill_dir.name)
            reports.append(report)
        
        return reports
    
    def _check_interface_drift(self, capability: str, manifest: dict) -> list[str]:
        """Check if skill implements declared interface."""
        drifts = []
        interface = manifest.get("interface", {})
        
        if not interface:
            return drifts
        
        # Get expected input/output keys
        expected_inputs = set(interface.get("input", {}).keys())
        expected_outputs = set(interface.get("output", {}).keys())
        
        # Check actual skills
        skill_dir = SKILLS_DIR / capability
        
        # Look at latest version
        latest = self._find_latest_version(skill_dir)
        if not latest:
            return ["No skill.py found to check interface"]
        
        try:
            code = latest.read_text()
            
            # Check if skill parses required inputs
            for inp in expected_inputs:
                if f"params.get('{inp}')" not in code and f'params.get("{inp}")' not in code:
                    drifts.append(f"interface: missing input '{inp}' in execute()")
            
            # Check if skill returns expected outputs
            for out in expected_outputs:
                if f"'{out}'" not in code and f'"{out}"' not in code:
                    drifts.append(f"interface: missing output '{out}' in return")
            
        except Exception as e:
            drifts.append(f"interface: could not analyze code: {e}")
        
        return drifts
    
    def _check_version_drift(self, capability: str, manifest: dict) -> Optional[str]:
        """Check if version count exceeds manifest limits."""
        constraints = manifest.get("constraints", {})
        evolution = manifest.get("evolution_rules", {})
        
        max_versions = evolution.get("max_auto_versions", 5)
        
        # Count actual versions
        skill_dir = SKILLS_DIR / capability
        version_count = self._count_versions(skill_dir)
        
        if version_count > max_versions:
            return f"version_drift: {version_count} versions > max {max_versions}"
        
        return None
    
    def _check_provider_drift(self, capability: str, manifest: dict) -> list[str]:
        """Check provider consistency."""
        drifts = []
        declared_providers = set(manifest.get("providers", []))
        
        if not declared_providers:
            return drifts
        
        # Check actual providers
        skill_dir = SKILLS_DIR / capability
        prov_dir = skill_dir / "providers"
        
        if prov_dir.exists():
            actual_providers = set(
                p.name for p in prov_dir.iterdir() 
                if p.is_dir() and not p.name.startswith(".")
            )
            
            missing = declared_providers - actual_providers
            extra = actual_providers - declared_providers
            
            if missing:
                drifts.append(f"provider_drift: missing {missing}")
            if extra:
                drifts.append(f"provider_drift: undeclared {extra}")
        
        return drifts
    
    def _check_quality_drift(self, capability: str, manifest: dict) -> Optional[str]:
        """Check if skill quality meets manifest requirements."""
        constraints = manifest.get("constraints", {})
        min_quality = constraints.get("min_quality_score", 0.5)
        
        # Find latest skill file
        skill_dir = SKILLS_DIR / capability
        latest = self._find_latest_version(skill_dir)
        
        if not latest:
            return None
        
        # Evaluate quality
        try:
            report = self.quality_gate.evaluate(latest, capability)
            if report.score < min_quality:
                return f"quality_drift: score {report.score:.2f} < min {min_quality}"
        except Exception:
            pass
        
        return None
    
    def _find_latest_version(self, skill_dir: Path) -> Optional[Path]:
        """Find the latest skill.py in a capability directory."""
        # Check providers structure
        prov_dir = skill_dir / "providers"
        if prov_dir.exists():
            for provider in prov_dir.iterdir():
                if not provider.is_dir():
                    continue
                # Try stable, then latest, then highest v{N}
                for pref in ["stable", "latest"]:
                    p = provider / pref / "skill.py"
                    if p.exists():
                        return p
                # Try version dirs
                versions = []
                for v in provider.iterdir():
                    if v.is_dir() and v.name.startswith("v"):
                        try:
                            versions.append((int(v.name[1:]), v))
                        except ValueError:
                            pass
                if versions:
                    versions.sort(reverse=True)
                    p = versions[0][1] / "skill.py"
                    if p.exists():
                        return p
        else:
            # Legacy structure
            versions = []
            for v in skill_dir.iterdir():
                if v.is_dir() and v.name.startswith("v"):
                    try:
                        versions.append((int(v.name[1:]), v))
                    except ValueError:
                        pass
            if versions:
                versions.sort(reverse=True)
                p = versions[0][1] / "skill.py"
                if p.exists():
                    return p
            # Try v1
            p = skill_dir / "v1" / "skill.py"
            if p.exists():
                return p
        
        return None
    
    def _count_versions(self, skill_dir: Path) -> int:
        """Count total versions in a skill directory."""
        count = 0
        
        prov_dir = skill_dir / "providers"
        if prov_dir.exists():
            for provider in prov_dir.iterdir():
                if not provider.is_dir():
                    continue
                count += len([v for v in provider.iterdir() if v.is_dir()])
        else:
            count = len([v for v in skill_dir.iterdir() 
                        if v.is_dir() and v.name.startswith("v")])
        
        return count
    
    def summary(self) -> dict:
        """Get summary of drift across all capabilities."""
        reports = self.detect_all()
        
        total = len(reports)
        drifting = sum(1 for r in reports if r.drift_detected)
        by_severity = {"low": 0, "medium": 0, "high": 0}
        
        for r in reports:
            if r.drift_detected:
                by_severity[r.severity] += 1
        
        return {
            "total_capabilities": total,
            "drifting": drifting,
            "healthy": total - drifting,
            "by_severity": by_severity,
            "top_issues": [
                {"capability": r.capability, "drifts": r.drifts[:2]}
                for r in sorted(reports, key=lambda x: len(x.drifts), reverse=True)[:5]
                if r.drift_detected
            ]
        }


# ─── Convenience Functions ─────────────────────────────────────────────

def detect_drift(capability: str) -> DriftReport:
    """Quick drift detection for a capability."""
    detector = DriftDetector()
    return detector.detect(capability)


def detect_all_drift() -> list[DriftReport]:
    """Detect drift across all capabilities."""
    detector = DriftDetector()
    return detector.detect_all()


def get_drift_summary() -> dict:
    """Get summary of system drift."""
    detector = DriftDetector()
    return detector.summary()


# ─── Exports ───────────────────────────────────────────────────────────

__all__ = [
    "DriftDetector",
    "DriftReport",
    "detect_drift",
    "detect_all_drift",
    "get_drift_summary",
]
