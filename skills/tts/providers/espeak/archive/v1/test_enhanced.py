#!/usr/bin/env python3
"""
Enhanced test script for TTS skill v1 with auto-installation
"""
import sys
import os
import subprocess
from pathlib import Path

# Add parent directories to path for imports
ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(ROOT))

from skills.tts.v1.skill import TTSSkill

def test_tts():
    try:
        tts = TTSSkill()
        print("Available backends:", tts.get_available_backends())
        preferred = tts.get_preferred_backend()
        print(f"Preferred backend: {preferred}")

        if preferred:
            print("Testing TTS with: 'Test message from TTS skill'")
            tts.speak("Test message from TTS skill", backend=preferred)
            print("TTS test completed successfully!")
        else:
            print("No TTS backends available. Trying to install gtts...")
            try:
                subprocess.run([sys.executable, '-m', 'pip', 'install', 'gtts'], check=True)
                print("gtts installed successfully!")
                tts = TTSSkill()  # Reinitialize with new backend
                preferred = tts.get_preferred_backend()
                if preferred:
                    print(f"Testing TTS with gtts backend: 'Test message from TTS skill'")
                    tts.speak("Test message from TTS skill", backend=preferred)
                    print("TTS test completed successfully!")
                else:
                    print("Still no TTS backends available after installing gtts")
            except Exception as e:
                print(f"Failed to install gtts: {e}")
                print("Please install one of the following:")
                print("  pip install pyttsx3")
                print("  apt install espeak")
                print("  pip install gtts")
                print("  and install mpv for audio playback")
    except Exception as e:
        print(f"Error initializing TTS: {e}")
        print("Please install one of the following TTS backends:")
        print("  pip install pyttsx3")
        print("  apt install espeak")
        print("  pip install gtts")
        print("  and install mpv for audio playback")

def get_info():
    return {
        "name": "tts_test_enhanced",
        "version": "v1",
        "description": "Enhanced test script for TTS skill with auto-installation",
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
    return {"success": True, "message": "Enhanced TTS test completed"}

if __name__ == "__main__":
    test_tts()
