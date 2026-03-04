#!/usr/bin/env python3
"""
PromptManager — centralized prompt management for evo-engine.

All LLM prompts are externalized to JSON files in cores/v1/prompts/.
This enables:
- Easy A/B testing of prompts
- Hot-swapping prompts without code changes
- Version control and rollback
- Standardization across the codebase

Usage:
    from .prompts import prompt_manager
    
    # Get system prompt
    system_prompt = prompt_manager.get("skill_generation", "system")
    
    # Get user prompt with variable substitution
    user_prompt = prompt_manager.render("skill_creation", variables={
        "name": "my_skill",
        "description": "does X",
        "version": "v1"
    })
"""
import json
import re
from pathlib import Path
from typing import Optional, Dict, Any

# Directory containing prompt JSON files
PROMPTS_DIR = Path(__file__).resolve().parent

# Cache for loaded prompts
_PROMPT_CACHE: Dict[str, Dict[str, Any]] = {}


def _load_prompt(name: str) -> Optional[Dict[str, Any]]:
    """Load a prompt from JSON file."""
    if name in _PROMPT_CACHE:
        return _PROMPT_CACHE[name]
    
    path = PROMPTS_DIR / f"{name}.json"
    if not path.exists():
        return None
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            prompt_data = json.load(f)
            _PROMPT_CACHE[name] = prompt_data
            return prompt_data
    except Exception as e:
        print(f"[PromptManager] Error loading prompt '{name}': {e}")
        return None


def get(name: str, prompt_type: str = "content", default: Optional[str] = None) -> str:
    """
    Get a prompt by name and type.
    
    Args:
        name: Prompt file name (without .json)
        prompt_type: Type of prompt to retrieve:
            - "content" or "system": The system prompt content
            - "template" or "user": The user prompt template
            - "system_context": Additional system context
            - Full metadata access via "metadata", "fallback"
    Returns:
        The prompt string or default value
    """
    data = _load_prompt(name)
    if not data:
        return default or ""
    
    # Map common aliases
    if prompt_type in ("content", "system", "system_prompt"):
        prompt_type = "content"
    elif prompt_type in ("template", "user", "user_template"):
        prompt_type = "template"
    
    # Try to get the requested field
    if prompt_type in data:
        return data[prompt_type]
    
    # For system type, try content
    if prompt_type == "content" and "content" in data:
        return data["content"]
    
    # For user type, try template
    if prompt_type == "template" and "template" in data:
        return data["template"]
    
    return default or ""


def render(name: str, variables: Optional[Dict[str, str]] = None, prompt_type: str = "template") -> str:
    """
    Render a prompt template with variable substitution.
    
    Args:
        name: Prompt file name
        variables: Dictionary of variables to substitute
        prompt_type: "template" for user prompt or "content" for system
    Returns:
        Rendered prompt string
    """
    data = _load_prompt(name)
    if not data:
        return ""
    
    # Get the template
    template = ""
    if prompt_type == "template" and "template" in data:
        template = data["template"]
    elif prompt_type == "content" and "content" in data:
        template = data["content"]
    elif "user_template" in data and prompt_type == "template":
        template = data["user_template"]
    
    if not template:
        return ""
    
    # Variable substitution: {var_name} -> value
    if variables:
        for key, value in variables.items():
            template = template.replace(f"{{{key}}}", str(value))
    
    return template


def get_metadata(name: str) -> Dict[str, Any]:
    """Get metadata for a prompt (temperature, max_tokens, model, etc.)"""
    data = _load_prompt(name)
    if not data:
        return {}
    return data.get("metadata", {})


def list_available() -> list:
    """List all available prompt names."""
    prompts = []
    for f in PROMPTS_DIR.glob("*.json"):
        if f.stem != "__init__":
            prompts.append(f.stem)
    return sorted(prompts)


def clear_cache():
    """Clear the prompt cache. Useful for hot-reloading."""
    global _PROMPT_CACHE
    _PROMPT_CACHE = {}


class PromptManager:
    """Class-based interface for prompt management."""
    
    def get(self, name: str, prompt_type: str = "content", default: Optional[str] = None) -> str:
        return get(name, prompt_type, default)
    
    def render(self, name: str, variables: Optional[Dict[str, str]] = None, prompt_type: str = "template") -> str:
        return render(name, variables, prompt_type)
    
    def get_metadata(self, name: str) -> Dict[str, Any]:
        return get_metadata(name)
    
    def list(self) -> list:
        return list_available()
    
    def clear_cache(self):
        clear_cache()


# Singleton instance
prompt_manager = PromptManager()

# Convenience exports
__all__ = [
    "prompt_manager",
    "PromptManager",
    "get",
    "render",
    "get_metadata",
    "list_available",
    "clear_cache",
]
