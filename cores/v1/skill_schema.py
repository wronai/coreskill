#!/usr/bin/env python3
"""
skill_schema.py — JSON Schema validation for skills, manifests, and outputs.

Provides:
- SKILL_SCHEMA: JSON Schema for skill manifest.json
- SKILL_OUTPUT_SCHEMA: Schema for skill execute() return values
- SkillSchemaValidator: validation with detailed error reporting
- BlueprintRegistry: extended manifest blueprints for auto-generation
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


# ─── JSON Schemas ──────────────────────────────────────────────────────

SKILL_MANIFEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["capability"],
    "properties": {
        "capability": {
            "type": "string",
            "description": "Unique capability name"
        },
        "description": {
            "type": "string",
            "description": "Human-readable description"
        },
        "version_structure": {
            "type": "string",
            "enum": ["flat", "stable/latest/archive", "semantic"],
            "default": "flat"
        },
        "interface": {
            "type": "object",
            "properties": {
                "input": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-z_]+$": {
                            "type": "string",
                            "pattern": "^(str|int|float|bool|dict|list|any)(\\?)?$"
                        }
                    },
                    "additionalProperties": False
                },
                "output": {
                    "type": "object",
                    "patternProperties": {
                        "^[a-z_]+$": {"type": "string"}
                    }
                }
            }
        },
        "constraints": {
            "type": "object",
            "properties": {
                "max_lines": {"type": "integer", "minimum": 10},
                "min_lines": {"type": "integer", "minimum": 1},
                "required_imports": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "forbidden_imports": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "min_quality_score": {
                    "type": "number",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            }
        },
        "evolution_rules": {
            "type": "object",
            "properties": {
                "auto_create_from_query": {"type": "boolean", "default": True},
                "max_auto_versions": {"type": "integer", "minimum": 1, "maximum": 20},
                "promote_after_n_successes": {"type": "integer", "minimum": 1},
                "allow_external_deps": {"type": "boolean", "default": False}
            }
        },
        "providers": {
            "type": "array",
            "items": {"type": "string"}
        },
        "default_provider": {"type": "string"},
        "selection_strategy": {
            "type": "string",
            "enum": ["best_available", "quality_first", "speed_first", "manual"]
        }
    },
    "additionalProperties": True
}

SKILL_OUTPUT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["success"],
    "properties": {
        "success": {"type": "boolean"},
        "result": {"type": "object"},
        "error": {"type": "string"},
        "spoken": {"type": "string"},  # For TTS/STT
        "text": {"type": "string"},   # For text output
        "exit_code": {"type": "integer"}  # For shell
    },
    "additionalProperties": True
}

SKILL_INTERFACE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["execute"],
    "properties": {
        "get_info": {
            "type": "object",
            "required": ["name", "version"],
            "properties": {
                "name": {"type": "string"},
                "version": {"type": "string"},
                "description": {"type": "string"}
            }
        },
        "health_check": {
            "type": "object",
            "required": ["status"],
            "properties": {
                "status": {"type": "string", "enum": ["ok", "error", "degraded"]},
                "message": {"type": "string"}
            }
        },
        "execute": {
            "type": "object",
            "required": ["params", "returns"],
            "properties": {
                "params": {"type": "object"},
                "returns": {"type": "object"}
            }
        }
    }
}


# ─── Validation Result ─────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """Result of schema validation."""
    valid: bool
    errors: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    
    def is_ok(self) -> bool:
        return self.valid and len(self.errors) == 0
    
    def summary(self) -> str:
        status = "✓" if self.is_ok() else "✗"
        parts = [f"{status} Valid={self.valid}, Errors={len(self.errors)}, Warnings={len(self.warnings)}"]
        if self.errors:
            parts.append(f"  Errors: {', '.join(str(e) for e in self.errors[:3])}")
        return "\n".join(parts)


# ─── Schema Validator ──────────────────────────────────────────────────

class SkillSchemaValidator:
    """Validate skill manifests and outputs against JSON Schema."""
    
    def __init__(self):
        self._schemas = {
            "manifest": SKILL_MANIFEST_SCHEMA,
            "output": SKILL_OUTPUT_SCHEMA,
            "interface": SKILL_INTERFACE_SCHEMA,
        }
    
    def validate_manifest(self, data: dict) -> ValidationResult:
        """Validate a skill manifest against schema."""
        return self._validate_against_schema(data, "manifest")
    
    def validate_output(self, data: dict) -> ValidationResult:
        """Validate skill execute() output."""
        return self._validate_against_schema(data, "output")
    
    def validate_file(self, path: Path) -> ValidationResult:
        """Validate a manifest.json file."""
        if not path.exists():
            return ValidationResult(
                valid=False,
                errors=[f"File not found: {path}"]
            )
        
        try:
            data = json.loads(path.read_text())
            return self.validate_manifest(data)
        except json.JSONDecodeError as e:
            return ValidationResult(
                valid=False,
                errors=[f"Invalid JSON: {e}"]
            )
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Read error: {e}"]
            )
    
    def _validate_against_schema(self, data: dict, schema_name: str) -> ValidationResult:
        """Internal validation using simple schema checking."""
        schema = self._schemas.get(schema_name, {})
        errors = []
        warnings = []
        
        # Check required fields
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                errors.append(f"Missing required field: {field}")
        
        # Check type constraints
        if "properties" in schema:
            for field, field_schema in schema["properties"].items():
                if field in data:
                    value = data[field]
                    expected_type = field_schema.get("type")
                    
                    if expected_type == "object" and not isinstance(value, dict):
                        errors.append(f"{field}: expected object, got {type(value).__name__}")
                    elif expected_type == "array" and not isinstance(value, list):
                        errors.append(f"{field}: expected array, got {type(value).__name__}")
                    elif expected_type == "string" and not isinstance(value, str):
                        errors.append(f"{field}: expected string, got {type(value).__name__}")
                    elif expected_type == "integer" and not isinstance(value, int):
                        errors.append(f"{field}: expected integer, got {type(value).__name__}")
                    elif expected_type == "boolean" and not isinstance(value, bool):
                        errors.append(f"{field}: expected boolean, got {type(value).__name__}")
                    elif expected_type == "number" and not isinstance(value, (int, float)):
                        errors.append(f"{field}: expected number, got {type(value).__name__}")
        
        # Check enum values
        if "properties" in schema:
            for field, field_schema in schema["properties"].items():
                if field in data and "enum" in field_schema:
                    value = data[field]
                    allowed = field_schema["enum"]
                    if value not in allowed:
                        errors.append(f"{field}: '{value}' not in allowed values: {allowed}")
        
        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )


# ─── Blueprint Registry ────────────────────────────────────────────────

class BlueprintRegistry:
    """Registry of skill blueprints for auto-generation."""
    
    # Default blueprints for common skill types
    DEFAULT_BLUEPRINTS = {
        "calculator": {
            "capability": "calculator",
            "description": "Mathematical expression evaluator",
            "interface": {
                "input": {"text": "str"},
                "output": {"result": "float", "expression": "str"}
            },
            "constraints": {
                "max_lines": 100,
                "required_imports": ["re"],
                "forbidden_imports": ["eval", "exec"],
                "min_quality_score": 0.7
            },
            "evolution_rules": {
                "auto_create_from_query": True,
                "max_auto_versions": 5,
                "promote_after_n_successes": 3
            }
        },
        "api_client": {
            "capability": "api_client",
            "description": "HTTP API client using urllib",
            "interface": {
                "input": {"text": "str", "url": "str?", "method": "str?"},
                "output": {"status": "int", "body": "str", "headers": "dict"}
            },
            "constraints": {
                "max_lines": 150,
                "required_imports": ["urllib.request", "json"],
                "forbidden_imports": ["requests"],
                "min_quality_score": 0.6
            },
            "evolution_rules": {
                "auto_create_from_query": True,
                "allow_external_deps": False
            }
        },
        "text_processor": {
            "capability": "text_processor",
            "description": "Text transformation and analysis",
            "interface": {
                "input": {"text": "str", "operation": "str?"},
                "output": {"result": "str", "word_count": "int?", "char_count": "int?"}
            },
            "constraints": {
                "max_lines": 120,
                "required_imports": ["re", "string"],
                "min_quality_score": 0.6
            }
        },
        "converter": {
            "capability": "converter",
            "description": "Unit and currency conversion",
            "interface": {
                "input": {"text": "str", "from": "str?", "to": "str?", "amount": "float?"},
                "output": {"result": "float", "rate": "float?", "from": "str", "to": "str"}
            },
            "constraints": {
                "max_lines": 150,
                "required_imports": ["re", "urllib.request", "json"],
                "min_quality_score": 0.6
            }
        }
    }
    
    def __init__(self):
        self._blueprints = dict(self.DEFAULT_BLUEPRINTS)
    
    def get_blueprint(self, name: str) -> Optional[dict]:
        """Get a blueprint by name."""
        return self._blueprints.get(name)
    
    def list_blueprints(self) -> list[str]:
        """List available blueprints."""
        return list(self._blueprints.keys())
    
    def register_blueprint(self, name: str, blueprint: dict) -> None:
        """Register a custom blueprint."""
        # Validate the blueprint first
        validator = SkillSchemaValidator()
        result = validator.validate_manifest(blueprint)
        if not result.is_ok():
            raise ValueError(f"Invalid blueprint: {result.errors}")
        self._blueprints[name] = blueprint
    
    def suggest_blueprint(self, query: str) -> Optional[str]:
        """Suggest best blueprint for a user query."""
        query_lower = query.lower()
        
        # Keyword matching (could be ML-based later)
        keywords = {
            "calculator": ["policz", "oblicz", "calculate", "math", "kalkulator", "dodaj", "sum"],
            "api_client": ["api", "http", "url", "fetch", "get", "post", "request"],
            "text_processor": ["text", "tekst", "word", "count", "transform", "reverse", "upper"],
            "converter": ["convert", "konwertuj", "currency", "waluta", "usd", "eur", "gbp", "jpy"],
        }
        
        for bp_name, words in keywords.items():
            if any(word in query_lower for word in words):
                return bp_name
        
        return None
    
    def generate_manifest(self, query: str, skill_name: str) -> dict:
        """Generate a manifest from a query using best matching blueprint."""
        blueprint_name = self.suggest_blueprint(query)
        
        if blueprint_name:
            blueprint = self.get_blueprint(blueprint_name).copy()
            blueprint["capability"] = skill_name
            blueprint["description"] = f"Auto-generated {skill_name} based on: {query}"
            return blueprint
        
        # Fallback: generic manifest
        return {
            "capability": skill_name,
            "description": f"Auto-generated skill for: {query}",
            "interface": {
                "input": {"text": "str"},
                "output": {"result": "any"}
            },
            "constraints": {
                "max_lines": 200,
                "min_quality_score": 0.5
            },
            "evolution_rules": {
                "auto_create_from_query": True,
                "max_auto_versions": 5
            }
        }


# ─── Convenience Functions ─────────────────────────────────────────────

def validate_manifest_file(path: Path) -> ValidationResult:
    """Quick validation of a manifest.json file."""
    validator = SkillSchemaValidator()
    return validator.validate_file(path)


def generate_skill_manifest(skill_name: str, query: str) -> dict:
    """Generate a manifest for a new skill from user query."""
    registry = BlueprintRegistry()
    return registry.generate_manifest(query, skill_name)


def get_schema_validation_stats(skills_dir: Path) -> dict:
    """Get statistics on manifest validation across all skills."""
    stats = {"total": 0, "valid": 0, "invalid": 0, "missing": 0, "errors": []}
    validator = SkillSchemaValidator()
    
    if not skills_dir.exists():
        return stats
    
    for skill_dir in skills_dir.iterdir():
        if not skill_dir.is_dir() or skill_dir.name.startswith("."):
            continue
        
        manifest_path = skill_dir / "manifest.json"
        stats["total"] += 1
        
        if not manifest_path.exists():
            stats["missing"] += 1
            continue
        
        result = validator.validate_file(manifest_path)
        if result.is_ok():
            stats["valid"] += 1
        else:
            stats["invalid"] += 1
            stats["errors"].append({
                "skill": skill_dir.name,
                "errors": result.errors
            })
    
    return stats


# ─── Exports ───────────────────────────────────────────────────────────

__all__ = [
    "SKILL_MANIFEST_SCHEMA",
    "SKILL_OUTPUT_SCHEMA",
    "SKILL_INTERFACE_SCHEMA",
    "ValidationResult",
    "SkillSchemaValidator",
    "BlueprintRegistry",
    "validate_manifest_file",
    "generate_skill_manifest",
    "get_schema_validation_stats",
]
