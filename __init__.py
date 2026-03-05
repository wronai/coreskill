#!/usr/bin/env python3
"""
CoreSkill - Ewolucyjny system AI z ewoluującymi skillami
"""

__version__ = "1.0.7"

# Re-export core components for easy access
from .cores.v1.config import load_state, save_state
from .cores.v1.llm_client import LLMClient
from .cores.v1.skill_manager import SkillManager
from .cores.v1.evo_engine import EvoEngine
from .cores.v1.intent_engine import IntentEngine
from .cores.v1.logger import Logger

__all__ = [
    "load_state",
    "save_state", 
    "LLMClient",
    "SkillManager",
    "EvoEngine",
    "IntentEngine",
    "Logger",
]
