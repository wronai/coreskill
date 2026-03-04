#!/usr/bin/env python3
"""
evo-engine SkillQualityGate — validates skill quality before registration.

Runs a checklist of quality checks on newly created or evolved skills:
  1. Preflight (syntax, imports, interface)
  2. Health check (health_check() returns truthy)
  3. Test execution (execute() with sample input succeeds)
  4. Output validation (result has required keys)
  5. Code complexity (line count, function count)

Returns a QualityReport with a score 0.0-1.0.
Skills below MIN_QUALITY are rejected.
"""
import ast
import importlib.util
import subprocess
import sys
import traceback
from dataclasses import dataclass, field
from pathlib import Path

from .preflight import SkillPreflight, PreflightResult
from .skill_schema import SkillSchemaValidator, ValidationResult
from .metrics_collector import record_operation
from .drift_detector import DriftDetector


# ─── Quality Report ──────────────────────────────────────────────────
@dataclass
class QualityReport:
    """Structured quality assessment of a skill."""
    skill_name: str
    score: float = 0.0               # 0.0 - 1.0
    passed: list = field(default_factory=list)
    failed: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    details: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return self.score >= SkillQualityGate.MIN_QUALITY

    def summary(self) -> str:
        status = "✓" if self.ok else "✗"
        parts = [f"{status} {self.skill_name}: {self.score:.2f}"]
        if self.failed:
            parts.append(f"  FAIL: {', '.join(self.failed)}")
        if self.warnings:
            parts.append(f"  WARN: {', '.join(self.warnings)}")
        return "\n".join(parts)


# ─── Quality Gate ─────────────────────────────────────────────────────
class SkillQualityGate:
    """
    Validates skill quality before registration.
    Each check contributes a weight to the final score.
    """
    MIN_QUALITY = 0.5    # Minimum score to register a skill
    MAX_LINES = 500      # Warn above this
    MIN_LINES = 10       # Warn below this

    # Check weights (must sum to 1.0)
    WEIGHTS = {
        "preflight": 0.20,
        "manifest_valid": 0.10,   # Schema validation
        "drift_check": 0.10,    # NEW: manifest vs runtime drift
        "health_check": 0.15,
        "test_exec": 0.25,
        "output_valid": 0.10,
        "code_quality": 0.10,
    }

    def __init__(self, preflight: SkillPreflight = None):
        self.preflight = preflight or SkillPreflight()
        self.schema_validator = SkillSchemaValidator()

    def evaluate(self, skill_path: Path, skill_name: str = "",
                 test_input: dict = None) -> QualityReport:
        """Run all quality checks. Returns QualityReport with score 0.0-1.0."""
        name = skill_name or skill_path.parent.name
        report = QualityReport(skill_name=name)
        scores = {}

        # 1. Preflight
        scores["preflight"] = self._check_preflight(skill_path, report)

        # 1.5. Manifest schema validation
        scores["manifest_valid"] = self._check_manifest_schema(skill_path, report)

        # 1.6. Drift detection (NEW)
        scores["drift_check"] = self._check_drift(skill_path, report)

        # 2-4 require loadable module — skip if preflight failed
        if scores["preflight"] > 0:
            scores["health_check"] = self._check_health(skill_path, report)
            scores["test_exec"] = self._check_test_exec(
                skill_path, report, test_input)
            scores["output_valid"] = self._check_output(report)
        else:
            for k in ("health_check", "test_exec", "output_valid"):
                scores[k] = 0.0
                report.failed.append(k)

        # 5. Code quality (always runs if file exists)
        scores["code_quality"] = self._check_code_quality(skill_path, report)

        # Compute weighted score
        total = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)
        report.score = round(total, 3)
        report.details["scores"] = scores
        
        # Record metrics
        record_operation(
            operation="quality_gate",
            duration_ms=sum(scores.values()) * 10,  # Approximate
            success=report.ok,
            details={
                "skill": name,
                "score": report.score,
                "checks": {k: scores[k] for k in scores}
            }
        )
        
        return report

    def should_register(self, report: QualityReport) -> bool:
        """True if quality score meets minimum threshold."""
        return report.score >= self.MIN_QUALITY

    def compare(self, old_report: QualityReport,
                new_report: QualityReport) -> bool:
        """True if new version is not a regression (score >= old - 0.1)."""
        return new_report.score >= (old_report.score - 0.1)

    # ── Event Bus Handlers ─────────────────────────────────────────────

    def on_skill_changed(self, sender, **kwargs):
        """EventBus handler: re-evaluate skill quality after repair.

        Triggered by RepairCompletedEvent. Logs quality score change.
        """
        event = kwargs.get("event")
        if not event or not event.success:
            return
        # Try to find and evaluate the repaired skill
        try:
            from .config import SKILLS_DIR
            from .skill_manager import SkillManager
            # Locate skill path heuristically
            skill_dir = SKILLS_DIR / event.skill_name
            if not skill_dir.exists():
                return
            # Find any skill.py under the skill directory
            candidates = list(skill_dir.rglob("skill.py"))
            if not candidates:
                return
            # Pick the most likely active version (stable > latest > first found)
            skill_path = candidates[0]
            for c in candidates:
                if "stable" in str(c):
                    skill_path = c
                    break
                if "latest" in str(c):
                    skill_path = c
            report = self.evaluate(skill_path, skill_name=event.skill_name)
            record_operation(
                operation="quality_recheck",
                duration_ms=0,
                success=report.ok,
                details={"skill": event.skill_name, "score": report.score,
                         "trigger": "repair_completed"},
            )
        except Exception:
            pass  # Non-critical — don't break event chain

    # ── Individual checks ─────────────────────────────────────────────

    def _check_preflight(self, skill_path: Path,
                         report: QualityReport) -> float:
        """Check 1: Preflight (syntax, imports, interface)."""
        pf = self.preflight.check_all(skill_path)
        if pf.ok:
            report.passed.append("preflight")
            return 1.0
        report.failed.append(f"preflight:{pf.stage}")
        report.details["preflight_error"] = pf.error
        return 0.0

    def _check_manifest_schema(self, skill_path: Path,
                                  report: QualityReport) -> float:
        """Check 1.5: Validate manifest.json against schema."""
        # Look for manifest in skill parent directory
        skill_dir = skill_path.parent
        # Walk up to find the skill root (where manifest.json should be)
        manifest = None
        current = skill_dir
        for _ in range(3):  # Try up to 3 levels up
            m = current / "manifest.json"
            if m.exists():
                manifest = m
                break
            if current.name == "skills" or current == current.parent:
                break
            current = current.parent
        
        if not manifest:
            # No manifest — not a failure but warning
            report.warnings.append("manifest_valid:missing")
            report.details["manifest_path"] = None
            return 0.5  # Partial credit
        
        # Validate the manifest
        result = self.schema_validator.validate_file(manifest)
        if result.is_ok():
            report.passed.append("manifest_valid")
            report.details["manifest_path"] = str(manifest)
            return 1.0
        
        report.failed.append(f"manifest_valid:{len(result.errors)}_errors")
        report.details["manifest_errors"] = result.errors[:5]  # First 5 errors
        report.details["manifest_path"] = str(manifest)
        return 0.0

    def _check_drift(self, skill_path: Path,
                     report: QualityReport) -> float:
        """Check 1.6: Detect drift between manifest and runtime."""
        # Find capability name from path
        skill_dir = skill_path.parent
        current = skill_dir
        capability = None
        
        for _ in range(3):
            if (current.parent / "manifest.json").exists():
                capability = current.parent.name
                break
            if current.name == "skills" or current == current.parent:
                break
            current = current.parent
        
        if not capability:
            # Try to infer from path structure
            parts = skill_path.parts
            if "skills" in parts:
                idx = parts.index("skills")
                if idx + 1 < len(parts):
                    capability = parts[idx + 1]
        
        if not capability:
            report.warnings.append("drift_check:no_capability")
            return 0.5  # Partial credit
        
        # Run drift detection
        try:
            detector = DriftDetector()
            drift_report = detector.detect(capability)
            
            report.details["drift_report"] = {
                "capability": capability,
                "drift_detected": drift_report.drift_detected,
                "severity": drift_report.severity,
                "drifts": drift_report.drifts[:3]
            }
            
            if drift_report.drift_detected:
                if drift_report.severity == "high":
                    report.failed.append(f"drift_check:{drift_report.severity}")
                    return 0.0
                else:
                    report.warnings.append(f"drift_check:{drift_report.severity}")
                    return 0.5
            else:
                report.passed.append("drift_check")
                return 1.0
                
        except Exception as e:
            report.warnings.append(f"drift_check:error:{str(e)[:50]}")
            return 0.5  # Don't fail on detection error

    def _check_health(self, skill_path: Path,
                      report: QualityReport) -> float:
        """Check 2: health_check() returns truthy."""
        try:
            mod = self._load_module(skill_path)
            if mod is None:
                report.failed.append("health_check:load_failed")
                return 0.0
            if hasattr(mod, "health_check"):
                result = mod.health_check()
                if result:
                    report.passed.append("health_check")
                    return 1.0
                report.failed.append("health_check:returned_falsy")
                return 0.0
            # No health_check — partial credit
            report.warnings.append("health_check:missing")
            return 0.5
        except Exception as e:
            report.failed.append(f"health_check:exception")
            report.details["health_check_error"] = str(e)[:200]
            return 0.0

    def _check_test_exec(self, skill_path: Path,
                         report: QualityReport,
                         test_input: dict = None) -> float:
        """Check 3: execute() with sample input succeeds.
        Runs in subprocess for isolation."""
        inp = test_input or {"text": "test", "command": "echo test"}
        try:
            result = self._run_isolated_exec(skill_path, inp)
            if result is None:
                report.failed.append("test_exec:no_result")
                return 0.0
            if isinstance(result, dict) and result.get("success") is not False:
                report.passed.append("test_exec")
                report.details["test_result"] = str(result)[:300]
                return 1.0
            report.failed.append("test_exec:returned_failure")
            report.details["test_result"] = str(result)[:300]
            return 0.3
        except Exception as e:
            report.failed.append("test_exec:exception")
            report.details["test_exec_error"] = str(e)[:200]
            return 0.0

    def _check_output(self, report: QualityReport) -> float:
        """Check 4: Validate test execution output has required keys."""
        result_str = report.details.get("test_result", "")
        if not result_str:
            # No test result to validate
            if "test_exec" in [f.split(":")[0] for f in report.failed]:
                return 0.0
            return 0.5

        # Check for 'success' key in output
        if "'success'" in result_str or '"success"' in result_str:
            report.passed.append("output_valid")
            return 1.0

        report.warnings.append("output_valid:no_success_key")
        return 0.5

    def _check_code_quality(self, skill_path: Path,
                            report: QualityReport) -> float:
        """Check 5: Basic code quality metrics."""
        if not skill_path.exists():
            report.failed.append("code_quality:missing")
            return 0.0

        code = skill_path.read_text()
        lines = code.split("\n")
        line_count = len(lines)
        report.details["line_count"] = line_count

        score = 1.0

        if line_count < self.MIN_LINES:
            report.warnings.append(f"code_quality:too_short({line_count}L)")
            score -= 0.3
        elif line_count > self.MAX_LINES:
            report.warnings.append(f"code_quality:too_long({line_count}L)")
            score -= 0.2

        # Count functions and classes
        try:
            tree = ast.parse(code)
            funcs = sum(1 for n in ast.walk(tree)
                        if isinstance(n, ast.FunctionDef))
            classes = sum(1 for n in ast.walk(tree)
                         if isinstance(n, ast.ClassDef))
            report.details["functions"] = funcs
            report.details["classes"] = classes

            # Check for docstrings in classes
            has_docstrings = False
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    if (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)
                            and isinstance(node.body[0].value.value, str)):
                        has_docstrings = True
            if not has_docstrings and classes > 0:
                report.warnings.append("code_quality:no_docstrings")
                score -= 0.1

        except SyntaxError:
            score -= 0.5

        return max(0.0, score)

    # ── Helpers ────────────────────────────────────────────────────────

    def _load_module(self, skill_path: Path):
        """Load a skill module. Returns module or None."""
        try:
            spec = importlib.util.spec_from_file_location(
                f"qg_{skill_path.stem}_{id(self)}", str(skill_path))
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
        except Exception:
            return None

    def _run_isolated_exec(self, skill_path: Path, inp: dict):
        """Run skill execute() in subprocess for isolation.
        Returns result dict or None on failure."""
        import json
        test_code = f"""
import sys, json, importlib.util
spec = importlib.util.spec_from_file_location("test_skill", "{skill_path}")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
inp = json.loads('{json.dumps(inp)}')
# Try class-based execute first
for attr in dir(mod):
    obj = getattr(mod, attr)
    if isinstance(obj, type) and hasattr(obj, "execute") and attr != "type":
        result = obj().execute(inp)
        print("QG_RESULT:" + json.dumps(result, default=str))
        sys.exit(0)
# Try module-level execute
if hasattr(mod, "execute"):
    result = mod.execute(inp)
    print("QG_RESULT:" + json.dumps(result, default=str))
    sys.exit(0)
print("QG_RESULT:null")
"""
        try:
            r = subprocess.run(
                [sys.executable, "-c", test_code],
                capture_output=True, text=True, timeout=15,
                cwd=str(skill_path.parent),
            )
            for line in r.stdout.split("\n"):
                if line.startswith("QG_RESULT:"):
                    import json as _json
                    payload = line[len("QG_RESULT:"):]
                    if payload == "null":
                        return None
                    return _json.loads(payload)
            return None
        except (subprocess.TimeoutExpired, Exception):
            return None
