#!/usr/bin/env python3
"""
migrate_skills.py — Migrates legacy skill structure to capability/provider layout.

Before: skills/tts/v1/skill.py
After:  skills/tts/providers/espeak/v1/skill.py + manifest.json + meta.json

Run: python3 migrate_skills.py [--dry-run]
"""
import json
import os
import shutil
import sys
from pathlib import Path

SKILLS_DIR = Path(__file__).parent.parent / "skills"


# Definitions: which skills to split into providers
MIGRATIONS = {
    "tts": {
        "description": "Text-to-Speech: converts text to spoken audio",
        "interface": {
            "input": {"text": "str", "lang": "str (default: pl)"},
            "output": {"spoken": "bool", "method": "str"}
        },
        "current_provider": "espeak",
        "current_tier": "lite",
        "current_quality": 3,
        "current_requirements": {"system_packages": ["espeak"]},
        "current_tags": ["offline", "fast", "low-quality"],
        "planned_providers": {
            "pyttsx3": {
                "tier": "standard", "quality_score": 5,
                "requirements": {"python_packages": ["pyttsx3"]},
                "fallback_to": "espeak",
                "tags": ["offline", "medium-quality"],
            },
            "coqui": {
                "tier": "premium", "quality_score": 9,
                "requirements": {
                    "python_packages": ["TTS>=0.20"],
                    "system_packages": ["ffmpeg"],
                    "gpu": True, "min_ram_mb": 2048,
                },
                "fallback_to": "pyttsx3",
                "tags": ["neural", "high-quality", "slow-first-run"],
            },
        },
    },
    "stt": {
        "description": "Speech-to-Text: transcribes audio to text",
        "interface": {
            "input": {"audio_path": "str", "lang": "str"},
            "output": {"text": "str", "confidence": "float"}
        },
        "current_provider": "vosk",
        "current_tier": "standard",
        "current_quality": 6,
        "current_requirements": {"python_packages": ["vosk"]},
        "current_tags": ["offline"],
        "planned_providers": {
            "whisper": {
                "tier": "premium", "quality_score": 9,
                "requirements": {
                    "python_packages": ["openai-whisper"],
                    "gpu": True, "min_ram_mb": 4096,
                },
                "fallback_to": "vosk",
                "tags": ["neural", "high-quality", "multilingual"],
            },
        },
    },
    "web_search": {
        "description": "Web search: searches the internet",
        "interface": {
            "input": {"query": "str", "max_results": "int"},
            "output": {"results": "list[dict]"}
        },
        "current_provider": "duckduckgo",
        "current_tier": "lite",
        "current_quality": 5,
        "current_requirements": {},
        "current_tags": ["no-api-key", "privacy"],
        "planned_providers": {},
    },
}

# Skills that stay single-provider (no split needed)
SIMPLE_SKILLS = ["echo", "devops", "deps", "git_ops"]


def migrate_skill(name: str, config: dict, dry_run: bool = False):
    """Migrate a skill from flat to provider structure."""
    skill_dir = SKILLS_DIR / name

    if not skill_dir.exists():
        print(f"  SKIP {name}: directory not found")
        return

    # Check if already migrated
    if (skill_dir / "providers").is_dir():
        print(f"  SKIP {name}: already migrated")
        return

    current_provider = config["current_provider"]

    # 1. Create manifest.json
    all_providers = [current_provider] + list(config.get("planned_providers", {}).keys())
    manifest = {
        "capability": name,
        "description": config["description"],
        "interface": config["interface"],
        "providers": all_providers,
        "default_provider": current_provider,
        "selection_strategy": "best_available",
    }

    print(f"  {name}/manifest.json")
    if not dry_run:
        (skill_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))

    # 2. Create providers/ directory
    prov_dir = skill_dir / "providers" / current_provider
    print(f"  {name}/providers/{current_provider}/")

    if not dry_run:
        prov_dir.mkdir(parents=True, exist_ok=True)

    # 3. Move existing versions into provider
    for item in sorted(skill_dir.iterdir()):
        if item.is_dir() and item.name.startswith("v"):
            dest = prov_dir / item.name
            print(f"    mv {item.name}/ -> providers/{current_provider}/{item.name}/")
            if not dry_run:
                shutil.move(str(item), str(dest))

    # 4. Create meta.json for current provider
    meta = {
        "provider": current_provider,
        "tier": config["current_tier"],
        "quality_score": config["current_quality"],
        "requirements": config["current_requirements"],
        "fallback_to": None,
        "tags": config["current_tags"],
    }
    print(f"    providers/{current_provider}/meta.json")
    if not dry_run:
        (prov_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # 5. Create empty dirs for planned providers
    for pp_name, pp_config in config.get("planned_providers", {}).items():
        pp_dir = skill_dir / "providers" / pp_name
        print(f"    providers/{pp_name}/ (placeholder)")
        if not dry_run:
            pp_dir.mkdir(parents=True, exist_ok=True)
            (pp_dir / "meta.json").write_text(json.dumps({
                "provider": pp_name, **pp_config
            }, indent=2))
            # Create placeholder skill.py
            v1 = pp_dir / "v1"
            v1.mkdir(exist_ok=True)
            (v1 / "skill.py").write_text(
                f"# Placeholder for {name}/{pp_name} provider\n"
                f"# TODO: implement by running /evolve {name} --provider {pp_name}\n\n"
                f"def get_info():\n"
                f"    return {{'name': '{name}', 'provider': '{pp_name}', "
                f"'version': 'v1', 'status': 'placeholder'}}\n\n"
                f"def health_check():\n    return False  # not implemented yet\n\n"
                f"class {pp_name.title().replace('_','')}Skill:\n"
                f"    def execute(self, input_data):\n"
                f"        return {{'error': 'Provider {pp_name} not yet implemented'}}\n"
            )


def add_manifest_to_simple(name: str, dry_run: bool = False):
    """Add manifest.json to simple single-provider skills."""
    skill_dir = SKILLS_DIR / name
    if not skill_dir.exists():
        return

    if (skill_dir / "manifest.json").exists():
        print(f"  SKIP {name}: manifest exists")
        return

    # Read existing meta for description
    desc = f"Skill: {name}"
    for vdir in sorted(skill_dir.iterdir()):
        if vdir.is_dir() and vdir.name.startswith("v"):
            mp = vdir / "meta.json"
            if mp.exists():
                m = json.loads(mp.read_text())
                desc = m.get("description", desc)
                break

    manifest = {
        "capability": name,
        "description": desc,
        "providers": ["default"],
        "default_provider": "default",
        "selection_strategy": "single",
    }
    print(f"  {name}/manifest.json (simple)")
    if not dry_run:
        (skill_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))


def main():
    dry_run = "--dry-run" in sys.argv
    if dry_run:
        print("=== DRY RUN (no changes) ===\n")
    else:
        print("=== MIGRATING ===\n")

    print("Multi-provider skills:")
    for name, config in MIGRATIONS.items():
        migrate_skill(name, config, dry_run)
        print()

    print("Simple skills (adding manifest):")
    for name in SIMPLE_SKILLS:
        add_manifest_to_simple(name, dry_run)
    print()

    if dry_run:
        print("Run without --dry-run to apply changes.")
    else:
        print("Migration complete.")


if __name__ == "__main__":
    main()
