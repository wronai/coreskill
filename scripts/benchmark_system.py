#!/usr/bin/env python3
"""
CoreSkill System Benchmark — measures key performance metrics.
Usage:
    python3 scripts/benchmark_system.py --output logs/benchmark/baseline.json
    python3 scripts/benchmark_system.py --output logs/benchmark/post_schema.json
"""
import argparse
import json
import os
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Avoid importing heavy modules until needed — measure import times too


@dataclass
class BenchmarkResult:
    """Single benchmark measurement."""
    name: str
    duration_ms: float
    success: bool
    error: str = ""
    details: dict = field(default_factory=dict)


@dataclass
class SystemMetrics:
    """Collected system metrics."""
    timestamp: str
    version: str
    # Core module sizes (complexity)
    core_lines: dict = field(default_factory=dict)
    # Import times
    import_times_ms: dict = field(default_factory=dict)
    # Operation benchmarks
    operations: list = field(default_factory=list)
    # Skill counts
    skill_count: int = 0
    skill_versions_total: int = 0
    # Config validation
    config_valid: bool = True
    # Summary
    total_duration_ms: float = 0.0


def run_benchmark(name: str, func, *args, **kwargs) -> BenchmarkResult:
    """Run a function and measure time."""
    start = time.perf_counter()
    try:
        result = func(*args, **kwargs)
        duration = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            name=name,
            duration_ms=round(duration, 2),
            success=True,
            details=result if isinstance(result, dict) else {}
        )
    except Exception as e:
        duration = (time.perf_counter() - start) * 1000
        return BenchmarkResult(
            name=name,
            duration_ms=round(duration, 2),
            success=False,
            error=str(e)
        )


def measure_import(module_name: str) -> float:
    """Measure import time for a module."""
    start = time.perf_counter()
    try:
        __import__(module_name)
        return (time.perf_counter() - start) * 1000
    except Exception:
        return -1  # Failed


def count_lines_in_file(path: Path) -> int:
    """Count lines in a Python file."""
    try:
        return len(path.read_text().splitlines())
    except Exception:
        return 0


def get_version() -> str:
    """Get version from VERSION file."""
    version_file = Path(__file__).parent.parent / "VERSION"
    if version_file.exists():
        return version_file.read_text().strip()
    return "unknown"


def count_skills_and_versions(skills_dir: Path) -> tuple[int, int]:
    """Count skills and total versions."""
    skill_count = 0
    version_count = 0
    
    if not skills_dir.exists():
        return 0, 0
    
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        skill_count += 1
        
        # Count versions in providers or legacy structure
        prov_dir = skill_dir / "providers"
        if prov_dir.exists():
            for provider in prov_dir.iterdir():
                if not provider.is_dir():
                    continue
                for vdir in provider.iterdir():
                    if vdir.is_dir() and (vdir / "skill.py").exists():
                        version_count += 1
        else:
            # Legacy structure
            for vdir in skill_dir.iterdir():
                if vdir.is_dir() and vdir.name.startswith("v") and (vdir / "skill.py").exists():
                    version_count += 1
    
    return skill_count, version_count


def validate_manifest_schemas(skills_dir: Path) -> dict:
    """Check which manifests are valid JSON."""
    results = {"valid": 0, "invalid": 0, "missing": 0, "total": 0}
    
    if not skills_dir.exists():
        return results
    
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        manifest = skill_dir / "manifest.json"
        results["total"] += 1
        if not manifest.exists():
            results["missing"] += 1
            continue
        try:
            json.loads(manifest.read_text())
            results["valid"] += 1
        except json.JSONDecodeError:
            results["invalid"] += 1
    
    return results


def run_all_benchmarks() -> SystemMetrics:
    """Run complete benchmark suite."""
    print("🚀 CoreSkill System Benchmark")
    print("=" * 50)
    
    metrics = SystemMetrics(
        timestamp=datetime.now(timezone.utc).isoformat(),
        version=get_version()
    )
    
    root = Path(__file__).parent.parent
    cores_dir = root / "cores" / "v1"
    skills_dir = root / "skills"
    
    # 1. Measure core module import times
    print("\n📦 Measuring import times...")
    core_modules = [
        "cores.v1.config",
        "cores.v1.utils",
        "cores.v1.logger",
        "cores.v1.llm_client",
        "cores.v1.intent_engine",
        "cores.v1.skill_manager",
        "cores.v1.evo_engine",
        "cores.v1.quality_gate",
    ]
    
    for mod in core_modules:
        t = measure_import(mod)
        metrics.import_times_ms[mod] = round(t, 2)
        status = "✓" if t > 0 else "✗"
        print(f"  {status} {mod}: {t:.2f}ms" if t > 0 else f"  ✗ {mod}: FAILED")
    
    # 2. Count lines in core modules (complexity)
    print("\n📏 Measuring code complexity (lines)...")
    core_files = [
        "core.py",
        "evo_engine.py",
        "intent_engine.py",
        "skill_manager.py",
        "smart_intent.py",
        "provider_selector.py",
        "quality_gate.py",
        "auto_repair.py",
        "self_reflection.py",
    ]
    
    for fname in core_files:
        fpath = cores_dir / fname
        lines = count_lines_in_file(fpath)
        metrics.core_lines[fname] = lines
        print(f"  {fname}: {lines} lines")
    
    # 3. Count skills and versions
    print("\n🎯 Counting skills...")
    skill_count, version_count = count_skills_and_versions(skills_dir)
    metrics.skill_count = skill_count
    metrics.skill_versions_total = version_count
    print(f"  Skills: {skill_count}")
    print(f"  Total versions: {version_count}")
    
    # 4. Validate manifest schemas
    print("\n📋 Validating manifest schemas...")
    manifest_stats = validate_manifest_schemas(skills_dir)
    print(f"  Valid: {manifest_stats['valid']}/{manifest_stats['total']}")
    print(f"  Invalid: {manifest_stats['invalid']}")
    print(f"  Missing: {manifest_stats['missing']}")
    
    # 5. Operation benchmarks (require imports)
    print("\n⚡ Running operation benchmarks...")
    
    # Benchmark: Load system config
    def bench_config_load():
        from cores.v1.config import get_system_config
        return get_system_config()
    
    result = run_benchmark("config_load", bench_config_load)
    metrics.operations.append(asdict(result))
    print(f"  {'✓' if result.success else '✗'} config_load: {result.duration_ms:.2f}ms")
    
    # Benchmark: List skills
    def bench_list_skills():
        from cores.v1.config import SKILLS_DIR
        from cores.v1.skill_manager import SkillManager
        from cores.v1.llm_client import LLMClient
        from cores.v1.logger import Logger
        
        logger = Logger("benchmark")
        llm = LLMClient(None, "test", logger)
        sm = SkillManager(llm, logger)
        return sm.list_skills()
    
    result = run_benchmark("list_skills", bench_list_skills)
    metrics.operations.append(asdict(result))
    print(f"  {'✓' if result.success else '✗'} list_skills: {result.duration_ms:.2f}ms")
    
    # Benchmark: Quality gate evaluation (if test skill exists)
    def bench_quality_gate():
        from cores.v1.quality_gate import SkillQualityGate
        from cores.v1.preflight import SkillPreflight
        from pathlib import Path
        
        # Find a test skill
        test_skill = skills_dir / "echo" / "v1" / "skill.py"
        if test_skill.exists():
            qg = SkillQualityGate(SkillPreflight())
            report = qg.evaluate(test_skill, "echo")
            return {"score": report.score, "passed": report.passed}
        return {"skipped": True}
    
    result = run_benchmark("quality_gate_eval", bench_quality_gate)
    metrics.operations.append(asdict(result))
    print(f"  {'✓' if result.success else '✗'} quality_gate_eval: {result.duration_ms:.2f}ms")
    if result.success and result.details.get("score"):
        print(f"    Quality score: {result.details['score']:.2f}")
    
    # 6. Check tests pass
    print("\n🧪 Checking test suite...")
    def run_tests():
        result = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/", "--co", "-q"],
            capture_output=True,
            text=True,
            cwd=root
        )
        # Parse test count from output
        lines = result.stdout.split("\n")
        for line in lines:
            if "test" in line.lower() and "/" in line:
                return {"test_line": line.strip()}
        return {"returncode": result.returncode}
    
    result = run_benchmark("test_discovery", run_tests)
    metrics.operations.append(asdict(result))
    print(f"  {'✓' if result.success else '✗'} test_discovery: {result.duration_ms:.2f}ms")
    
    # Total duration
    metrics.total_duration_ms = round(
        sum(m for m in metrics.import_times_ms.values() if m > 0) +
        sum(op["duration_ms"] for op in metrics.operations),
        2
    )
    
    print("\n" + "=" * 50)
    print(f"✅ Benchmark complete in {metrics.total_duration_ms:.2f}ms")
    print(f"   Version: {metrics.version}")
    
    return metrics


def main():
    parser = argparse.ArgumentParser(description="CoreSkill System Benchmark")
    parser.add_argument("--output", "-o", type=str, help="Output JSON file path")
    parser.add_argument("--compare", "-c", type=str, help="Compare with previous benchmark")
    args = parser.parse_args()
    
    metrics = run_all_benchmarks()
    
    # Convert to JSON
    data = asdict(metrics)
    json_output = json.dumps(data, indent=2, default=str)
    
    # Save to file if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json_output)
        print(f"\n💾 Saved to: {args.output}")
    
    # Compare with previous if requested
    if args.compare:
        compare_path = Path(args.compare)
        if compare_path.exists():
            print(f"\n📊 Comparison with {args.compare}:")
            old_data = json.loads(compare_path.read_text())
            # Show key differences
            old_import = sum(m for m in old_data["import_times_ms"].values() if m > 0)
            new_import = sum(m for m in data["import_times_ms"].values() if m > 0)
            delta = new_import - old_import
            print(f"  Import time delta: {delta:+.2f}ms ({delta/old_import*100:+.1f}%)")
        else:
            print(f"\n⚠️  Comparison file not found: {args.compare}")
    
    return 0 if all(op["success"] for op in data["operations"]) else 1


if __name__ == "__main__":
    sys.exit(main())
