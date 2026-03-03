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

if __name__ == "__main__":
    test_tts()