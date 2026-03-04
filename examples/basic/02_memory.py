#!/usr/bin/env python3
"""
Basic example: Using user memory
"""
import sys
sys.path.insert(0, '/home/tom/github/wronai/coreskill')

from cores.v1.config import load_state, save_state
from cores.v1.user_memory import UserMemory


def main():
    print("=== User Memory Example ===\n")
    
    # Load state
    state = load_state()
    memory = UserMemory(state)
    
    # 1. Add a preference
    print("1. Adding preference...")
    memory.add("Zawsze rozmawiaj po polsku", priority="high")
    print("   ✓ Added: 'Zawsze rozmawiaj po polsku'")
    
    # 2. Show all memories
    print("\n2. Current memories:")
    memory.display()
    
    # 3. Build context for LLM
    print("\n3. Context for LLM:")
    context = memory.build_system_context()
    print(f"   {context[:100]}...")
    
    # 4. Check if something looks like preference
    print("\n4. Testing preference detection:")
    test_messages = [
        "zawsze używaj formatowania markdown",
        "wolę krótkie odpowiedzi",
        "jaka jest pogoda?"
    ]
    
    for msg in test_messages:
        looks_like = memory.looks_like_preference(msg)
        print(f"   '{msg}' -> {'YES' if looks_like else 'NO'}")
    
    # 5. Clean up (remove test preference)
    print("\n5. Cleaning up...")
    # Note: In real usage, you'd remove by ID
    # memory.remove(directive_id)
    
    print("\n=== Done ===")


if __name__ == "__main__":
    main()
