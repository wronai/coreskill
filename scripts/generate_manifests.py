#!/usr/bin/env python3
"""
generate_manifests.py — Auto-generate missing manifest.json for all skills.

Usage:
    python3 scripts/generate_manifests.py --dry-run    # Preview only
    python3 scripts/generate_manifests.py --apply      # Actually create files
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from cores.v1.config import SKILLS_DIR
from cores.v1.skill_schema import BlueprintRegistry, get_schema_validation_stats


def infer_interface_from_skill(skill_path: Path) -> dict:
    """Try to infer interface from skill code."""
    try:
        code = skill_path.read_text()
        interface = {"input": {"text": "str"}, "output": {"result": "any"}}
        
        # Look for param extraction patterns
        if "params.get('text'" in code or 'params.get("text"' in code:
            interface["input"]["text"] = "str"
        if "params.get('command'" in code or 'params.get("command"' in code:
            interface["input"]["command"] = "str?"
        if "params.get('url'" in code or 'params.get("url"' in code:
            interface["input"]["url"] = "str?"
        if "result" in code and "return" in code:
            interface["output"]["result"] = "any"
        
        return interface
    except Exception:
        return {"input": {"text": "str"}, "output": {"result": "any"}}


def infer_constraints_from_skill(skill_path: Path) -> dict:
    """Infer constraints from skill code."""
    try:
        code = skill_path.read_text()
        lines = len(code.splitlines())
        
        # Check for forbidden imports
        forbidden = []
        if "import requests" in code:
            forbidden.append("requests")
        if "os.system(" in code:
            forbidden.append("os.system")
        
        return {
            "max_lines": max(100, lines + 50),
            "min_quality_score": 0.5,
            "forbidden_imports": forbidden
        }
    except Exception:
        return {"max_lines": 200, "min_quality_score": 0.5}


def generate_manifest_for_skill(skill_dir: Path, registry: BlueprintRegistry) -> dict:
    """Generate a manifest.json for a skill directory."""
    skill_name = skill_dir.name
    
    # Check if provider structure exists
    prov_dir = skill_dir / "providers"
    if prov_dir.exists():
        # Multi-provider skill (like tts, stt)
        providers = []
        for p in prov_dir.iterdir():
            if p.is_dir() and not p.name.startswith("."):
                providers.append(p.name)
        
        # Find a skill.py to infer interface
        skill_py = None
        for p in prov_dir.iterdir():
            if p.is_dir():
                for v in p.iterdir():
                    if v.is_dir() and (v / "skill.py").exists():
                        skill_py = v / "skill.py"
                        break
                if skill_py:
                    break
        
        manifest = {
            "capability": skill_name,
            "description": f"Capability: {skill_name}",
            "version_structure": "stable/latest/archive",
            "interface": infer_interface_from_skill(skill_py) if skill_py else {"input": {"text": "str"}, "output": {"result": "any"}},
            "constraints": infer_constraints_from_skill(skill_py) if skill_py else {"max_lines": 200, "min_quality_score": 0.5},
            "evolution_rules": {
                "auto_create_from_query": True,
                "max_auto_versions": 5,
                "promote_after_n_successes": 3
            },
            "providers": providers,
            "default_provider": providers[0] if providers else "default",
            "selection_strategy": "best_available"
        }
    else:
        # Legacy flat structure
        v1_dir = skill_dir / "v1"
        skill_py = v1_dir / "skill.py" if v1_dir.exists() else None
        
        # Try to find any skill.py
        if not skill_py:
            for v in skill_dir.iterdir():
                if v.is_dir() and (v / "skill.py").exists():
                    skill_py = v / "skill.py"
                    break
        
        # Try to match with blueprint
        blueprint = registry.suggest_blueprint(skill_name) or "text_processor"
        base = registry.get_blueprint(blueprint).copy() if registry.get_blueprint(blueprint) else {}
        
        manifest = {
            "capability": skill_name,
            "description": base.get("description", f"Skill: {skill_name}"),
            "version_structure": "flat",
            "interface": infer_interface_from_skill(skill_py) if skill_py else base.get("interface", {"input": {"text": "str"}, "output": {"result": "any"}}),
            "constraints": infer_constraints_from_skill(skill_py) if skill_py else base.get("constraints", {"max_lines": 200, "min_quality_score": 0.5}),
            "evolution_rules": {
                "auto_create_from_query": True,
                "max_auto_versions": 5,
                "promote_after_n_successes": 3
            }
        }
    
    return manifest


def main():
    parser = argparse.ArgumentParser(description="Generate missing manifests")
    parser.add_argument("--dry-run", action="store_true", help="Preview only")
    parser.add_argument("--apply", action="store_true", help="Actually create files")
    args = parser.parse_args()
    
    if not args.dry_run and not args.apply:
        print("Use --dry-run to preview or --apply to create files")
        return 1
    
    print("📋 Manifest Generator")
    print("=" * 50)
    
    registry = BlueprintRegistry()
    stats_before = get_schema_validation_stats(SKILLS_DIR)
    
    print(f"\nBefore: {stats_before['valid']}/{stats_before['total']} skills with valid manifests")
    print(f"Missing: {stats_before['missing']}, Invalid: {stats_before['invalid']}")
    
    created = 0
    skipped = 0
    errors = []
    
    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        
        manifest_path = skill_dir / "manifest.json"
        
        if manifest_path.exists():
            skipped += 1
            continue
        
        manifest = generate_manifest_for_skill(skill_dir, registry)
        
        if args.dry_run:
            print(f"\n📝 Would create: {manifest_path}")
            print(json.dumps(manifest, indent=2, default=str)[:500] + "...")
        elif args.apply:
            try:
                manifest_path.write_text(json.dumps(manifest, indent=2, default=str))
                created += 1
                print(f"✓ Created: {skill_dir.name}/manifest.json")
            except Exception as e:
                errors.append((skill_dir.name, str(e)))
                print(f"✗ Error creating {skill_dir.name}: {e}")
    
    print(f"\n{'=' * 50}")
    print(f"Created: {created}, Skipped: {skipped}, Errors: {len(errors)}")
    
    if args.apply:
        stats_after = get_schema_validation_stats(SKILLS_DIR)
        print(f"\nAfter: {stats_after['valid']}/{stats_after['total']} skills with valid manifests")
        improvement = stats_after['valid'] - stats_before['valid']
        print(f"Improvement: +{improvement} valid manifests")
    
    if errors:
        print(f"\n⚠️ Errors:")
        for name, err in errors[:5]:
            print(f"  - {name}: {err}")
    
    return 0 if len(errors) == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
