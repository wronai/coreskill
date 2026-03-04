#!/usr/bin/env python3
"""
Basic example: Using CoreSkill programmatically
"""
import sys
sys.path.insert(0, '/home/tom/github/wronai/coreskill')

from cores.v1.config import load_state, save_state
from cores.v1.llm_client import LLMClient
from cores.v1.skill_manager import SkillManager


def main():
    print("=== CoreSkill Basic Example ===\n")
    
    # 1. Load state
    state = load_state()
    print(f"✓ Loaded state: {len(state)} keys")
    
    # 2. Create LLM client
    llm = LLMClient(
        api_key=state.get("api_key"),
        model=state.get("model", "openrouter/meta-llama/llama-3.3-70b-instruct:free")
    )
    print(f"✓ LLM client ready: {llm.model}")
    
    # 3. Simple chat
    print("\n--- Simple Chat ---")
    response = llm.chat([
        {"role": "user", "content": "Powiedz 'Cześć' po polsku"}
    ])
    print(f"User: Powiedz 'Cześć' po polsku")
    print(f"AI: {response}")
    
    # 4. Execute a skill
    print("\n--- Execute Skill ---")
    sm = SkillManager()
    
    result = sm.exec_skill("echo", params={"text": "Hello from CoreSkill!"})
    print(f"Echo skill result: {result}")
    
    # 5. Check health
    print("\n--- Health Check ---")
    health = sm.check_health("tts")
    print(f"TTS health: {health.get('status', 'unknown')}")
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
