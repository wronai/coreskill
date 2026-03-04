#!/usr/bin/env python3
"""
Advanced example: Pipeline execution with EvoEngine
"""
import sys
sys.path.insert(0, '/home/tom/github/wronai/coreskill')

from cores.v1.config import load_state
from cores.v1.llm_client import LLMClient
from cores.v1.skill_manager import SkillManager
from cores.v1.intent_engine import IntentEngine
from cores.v1.evo_engine import EvoEngine


def main():
    print("=== EvoEngine Pipeline Example ===\n")
    
    # Initialize components
    state = load_state()
    llm = LLMClient(api_key=state.get("api_key"))
    sm = SkillManager()
    
    # Get available skills for intent engine
    skills = {}
    for skill_name in sm.list_skills():
        try:
            info = sm.get_skill_info(skill_name)
            skills[skill_name] = info
        except:
            pass
    
    intent = IntentEngine(skills=skills)
    evo = EvoEngine(skill_manager=sm, llm_client=llm, intent_engine=intent)
    
    # Example 1: Process text through pipeline
    print("1. Processing: 'Przeczytaj mi artykuł o Pythonie'")
    
    analysis = intent.analyze(
        text="Przeczytaj mi artykuł o Pythonie",
        skills=skills,
        conversation=[]
    )
    
    print(f"   Intent: {analysis.get('action')} → {analysis.get('skill')}")
    print(f"   Confidence: {analysis.get('confidence', 0):.2f}")
    print(f"   Goal: {analysis.get('goal')}")
    
    # Example 2: Execute skill based on intent
    if analysis.get('action') == 'use' and analysis.get('skill'):
        print(f"\n2. Executing skill: {analysis['skill']}")
        
        # Note: This would actually execute the skill
        # result = sm.exec_skill(analysis['skill'], params={'text': analysis['goal']})
        print(f"   Would execute: {analysis['skill']} with params")
    
    # Example 3: Complex pipeline (chat + TTS)
    print("\n3. Complex pipeline simulation:")
    
    user_input = "Powiedz mi żart i przeczytaj na głos"
    
    # Step 1: Analyze
    analysis = intent.analyze(user_input, skills, conversation=[])
    print(f"   Step 1 - Intent: {analysis.get('action')} → {analysis.get('skill')}")
    
    # Step 2: Chat (if needed)
    if analysis.get('skill') in ['tts', 'voice']:
        print("   Step 2 - Chat: Generating response")
        # response = llm.chat([...])
        response = "Dlaczego programista zgubił się w lesie? Bo nie mógł znaleźć root!"
        print(f"   Response: {response[:50]}...")
        
        # Step 3: TTS
        print("   Step 3 - TTS: Would speak the response")
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
