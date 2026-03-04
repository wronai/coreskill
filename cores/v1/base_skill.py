#!/usr/bin/env python3
"""
base_skill.py — BaseSkill class eliminating boilerplate errors in auto-generated skills.

Provides:
- BaseSkill: abstract base with safe_execute(), get_info(), health_check()
- SkillManifest: YAML manifest loader/validator for skill metadata
- generate_scaffold(): creates minimal skill code from manifest

55% of LLM-generated skill errors are in boilerplate (get_info, health_check,
class definition, __main__ block). BaseSkill eliminates all of them.
"""
import json
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


# ─── YAML Manifest ───────────────────────────────────────────────────

@dataclass
class InputField:
    """Single input field from manifest."""
    name: str
    type: str = "string"
    default: Any = None
    required: bool = False
    description: str = ""


@dataclass
class SkillManifest:
    """Parsed skill manifest (from YAML or JSON)."""
    name: str
    version: str = "v1"
    language: str = "python"
    description: str = ""
    inputs: List[InputField] = field(default_factory=list)
    output_schema: Dict[str, str] = field(default_factory=dict)
    requires_commands: List[str] = field(default_factory=list)
    requires_packages: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    author: str = ""
    evolution_rules: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "SkillManifest":
        """Build manifest from dict (loaded from YAML/JSON)."""
        inputs = []
        for fname, fspec in data.get("input", {}).items():
            if isinstance(fspec, dict):
                inputs.append(InputField(
                    name=fname,
                    type=fspec.get("type", "string"),
                    default=fspec.get("default"),
                    required=fspec.get("required", False),
                    description=fspec.get("description", ""),
                ))
            elif isinstance(fspec, str):
                inputs.append(InputField(name=fname, type=fspec))

        return cls(
            name=data.get("name", "unnamed"),
            version=str(data.get("version", "v1")),
            language=data.get("language", "python"),
            description=data.get("description", ""),
            inputs=inputs,
            output_schema=data.get("output", {}),
            requires_commands=data.get("requires", {}).get("commands", [])
                if isinstance(data.get("requires"), dict) else [],
            requires_packages=data.get("requires", {}).get("packages", [])
                if isinstance(data.get("requires"), dict) else [],
            tags=data.get("tags", []),
            author=data.get("author", ""),
            evolution_rules=data.get("evolution_rules", {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> Optional["SkillManifest"]:
        """Load manifest from YAML or JSON file."""
        if not path.exists():
            return None
        text = path.read_text(encoding="utf-8")
        try:
            # Try YAML first
            try:
                import yaml
                data = yaml.safe_load(text)
            except ImportError:
                data = None

            # Fallback to JSON
            if data is None:
                data = json.loads(text)

            if isinstance(data, dict):
                return cls.from_dict(data)
        except Exception:
            pass
        return None

    def to_dict(self) -> dict:
        """Serialize to dict for JSON/YAML export."""
        d = {
            "name": self.name,
            "version": self.version,
            "language": self.language,
            "description": self.description,
        }
        if self.inputs:
            d["input"] = {}
            for inp in self.inputs:
                spec = {"type": inp.type}
                if inp.default is not None:
                    spec["default"] = inp.default
                if inp.required:
                    spec["required"] = True
                if inp.description:
                    spec["description"] = inp.description
                d["input"][inp.name] = spec
        if self.output_schema:
            d["output"] = self.output_schema
        if self.requires_commands or self.requires_packages:
            d["requires"] = {}
            if self.requires_commands:
                d["requires"]["commands"] = self.requires_commands
            if self.requires_packages:
                d["requires"]["packages"] = self.requires_packages
        if self.tags:
            d["tags"] = self.tags
        if self.author:
            d["author"] = self.author
        if self.evolution_rules:
            d["evolution_rules"] = self.evolution_rules
        return d

    def validate_input(self, params: dict) -> List[str]:
        """Validate params against manifest input schema. Returns list of errors."""
        errors = []
        for inp in self.inputs:
            if inp.required and inp.name not in params:
                errors.append(f"Missing required field: {inp.name}")
            if inp.name in params:
                val = params[inp.name]
                expected = inp.type.rstrip("?")
                TYPE_MAP = {
                    "string": str, "str": str,
                    "integer": int, "int": int,
                    "float": (int, float), "number": (int, float),
                    "boolean": bool, "bool": bool,
                    "dict": dict, "object": dict,
                    "list": list, "array": list,
                }
                expected_type = TYPE_MAP.get(expected)
                if expected_type and not isinstance(val, expected_type):
                    errors.append(
                        f"{inp.name}: expected {expected}, "
                        f"got {type(val).__name__}")
        return errors

    def get_defaults(self) -> dict:
        """Return dict of default values for all input fields."""
        defaults = {}
        for inp in self.inputs:
            if inp.default is not None:
                defaults[inp.name] = inp.default
        return defaults


# ─── BaseSkill ────────────────────────────────────────────────────────

class BaseSkill:
    """Base class eliminating 55% of boilerplate errors in auto-generated skills.

    Subclasses only need to override execute(params).
    get_info(), health_check(), safe_execute() are all provided.

    Usage:
        class CameraScanner(BaseSkill):
            name = "camera_scanner"
            description = "Scans network for IP cameras"

            def execute(self, params):
                network = params.get("network", params.get("text", "192.168.1.0/24"))
                # ... actual logic ...
                return {"success": True, "devices": devices}
    """
    name: str = "unnamed"
    version: str = "v1"
    description: str = ""

    def execute(self, params: dict) -> dict:
        """Override this. Must return dict with 'success' key."""
        raise NotImplementedError(
            f"{self.__class__.__name__}.execute() not implemented")

    def get_info(self) -> dict:
        """Return skill metadata. Override only if custom fields needed."""
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
        }

    def health_check(self) -> dict:
        """Return health status. Override for custom checks (e.g. binary exists)."""
        return {"status": "ok"}

    def safe_execute(self, params: dict) -> dict:
        """Wrapper with error handling and type normalization.
        Called by skill_manager instead of execute() directly."""
        try:
            # Normalize input
            if not isinstance(params, dict):
                params = {"text": str(params) if params else ""}

            # Load manifest and apply defaults if available
            manifest = self._get_manifest()
            if manifest:
                defaults = manifest.get_defaults()
                for k, v in defaults.items():
                    if k not in params:
                        params[k] = v

            # Execute
            result = self.execute(params)

            # Normalize output
            if not isinstance(result, dict):
                result = {"success": True, "result": result}
            if "success" not in result:
                result["success"] = True
            return result

        except NotImplementedError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc(),
            }

    def _get_manifest(self) -> Optional[SkillManifest]:
        """Try to load manifest from skill directory. Returns None if not found."""
        try:
            skill_file = Path(__file__)
            # Walk up to find manifest.yaml or manifest.json
            for parent in [skill_file.parent, skill_file.parent.parent]:
                for name in ("manifest.yaml", "manifest.yml", "manifest.json"):
                    mp = parent / name
                    if mp.exists():
                        return SkillManifest.from_file(mp)
        except Exception:
            pass
        return None


# ─── Module-level wrappers ────────────────────────────────────────────
# These are needed for backward compatibility with skill_manager._load_and_run()

def _make_module_functions(skill_class):
    """Generate module-level execute/get_info/health_check from a BaseSkill subclass.

    Usage at end of skill file:
        class MySkill(BaseSkill):
            ...
        execute, get_info, health_check = _make_module_functions(MySkill)
    """
    instance = skill_class()

    def execute(params):
        return instance.safe_execute(params)

    def get_info():
        return instance.get_info()

    def health_check():
        return instance.health_check()

    return execute, get_info, health_check


# ─── Scaffold Generator ──────────────────────────────────────────────

def generate_scaffold(manifest: SkillManifest) -> str:
    """Generate minimal Python skill code from manifest.

    Used by create_skill() to give LLM a starting scaffold instead of
    asking it to generate everything from scratch.
    """
    name_class = "".join(w.capitalize() for w in manifest.name.split("_"))
    if not name_class:
        name_class = "GeneratedSkill"

    # Build input parsing lines
    input_lines = []
    for inp in manifest.inputs:
        default_repr = repr(inp.default) if inp.default is not None else '""'
        input_lines.append(
            f'        {inp.name} = params.get("{inp.name}", '
            f'params.get("text", {default_repr}))')

    input_block = "\n".join(input_lines) if input_lines else \
        '        text = params.get("text", "")'

    # Build requires comment
    requires_comment = ""
    if manifest.requires_commands:
        requires_comment = (
            f"\n    # Requires system commands: "
            f"{', '.join(manifest.requires_commands)}")

    code = f'''#!/usr/bin/env python3
"""{manifest.description or manifest.name}"""
from cores.v1.base_skill import BaseSkill, _make_module_functions


class {name_class}(BaseSkill):
    name = "{manifest.name}"
    version = "{manifest.version}"
    description = "{manifest.description}"{requires_comment}

    def execute(self, params: dict) -> dict:
{input_block}

        # TODO: implement actual logic here
        return {{"success": True, "result": "not implemented yet"}}


execute, get_info, health_check = _make_module_functions({name_class})

if __name__ == "__main__":
    import json
    print(json.dumps(execute({{"text": "test"}}), indent=2, ensure_ascii=False))
'''
    return code


def generate_manifest_yaml(name: str, description: str = "",
                           inputs: dict = None, tags: list = None) -> str:
    """Generate YAML manifest content for a skill."""
    lines = [
        f"name: {name}",
        f'version: "1"',
        f"language: python",
    ]
    if description:
        lines.append(f'description: "{description}"')
    if inputs:
        lines.append("")
        lines.append("input:")
        for fname, fspec in inputs.items():
            if isinstance(fspec, dict):
                ftype = fspec.get("type", "string")
                lines.append(f"  {fname}:")
                lines.append(f"    type: {ftype}")
                if "default" in fspec:
                    lines.append(f"    default: {json.dumps(fspec['default'])}")
            else:
                lines.append(f"  {fname}:")
                lines.append(f"    type: {fspec}")
    if tags:
        lines.append("")
        lines.append(f"tags: [{', '.join(tags)}]")
    return "\n".join(lines) + "\n"
