#!/usr/bin/env python3
"""
Test script for TTS skill v1
"""
import sys
import os
from pathlib import Path

# Add parent directories to path for imports
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.tts.v1.skill import TTSSkill

def test_tts():
    tts = TTSSkill()
    print("Available backends:", tts.get_available_backends())
    preferred = tts.get_preferred_backend()
    print(f"Preferred backend: {preferred}")

    if preferred:
        print("Testing TTS with: 'Test message from TTS skill'")
        tts.speak("Test message from TTS skill", backend=preferred)
        print("TTS test completed successfully!")
    else:
        print("No TTS backends available. Please install:")
        print("  pip install pyttsx3")
        print("  or apt install espeak")
        print("  or install gtts and mpv")

def get_info():
    return {
        "name": "tts_test",
        "version": "v1", 
        "description": "Test script for TTS skill",
        "author": "evo-engine"
    }

def health_check():
    try:
        tts = TTSSkill()
        return tts.get_preferred_backend() is not None
    except:
        return False

def execute(input_data=None):
    test_tts()
    return {"success": True, "message": "TTS test completed"}

if __name__ == "__main__":
    test_tts()
