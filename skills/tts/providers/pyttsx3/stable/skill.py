import subprocess
import shutil
import tempfile
import threading
import time
import re
from pathlib import Path

try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False


class Pyttsx3TTSSkill:
    """High-quality Text-to-Speech using pyttsx3 (native voices)."""

    MAX_TEXT_LEN = 1000

    def __init__(self):
        self._engine = None
        self._init_engine()

    def _init_engine(self):
        """Initialize TTS engine with best available voice."""
        if not PYTTSX3_AVAILABLE:
            return False

        try:
            self._engine = pyttsx3.init()
            
            # Get available voices and prefer Polish
            voices = self._engine.getProperty('voices')
            polish_voice = None
            english_voice = None
            
            for voice in voices:
                if 'polish' in voice.name.lower() or 'pl' in voice.id.lower():
                    polish_voice = voice
                elif 'english' in voice.name.lower() or 'en' in voice.id.lower():
                    english_voice = voice
            
            # Set best available voice
            selected_voice = polish_voice or english_voice or voices[0] if voices else None
            if selected_voice:
                self._engine.setProperty('voice', selected_voice.id)
            
            # Optimize voice settings for quality
            self._engine.setProperty('rate', 150)  # Moderate speed
            self._engine.setProperty('volume', 0.9)  # Good volume
            
            return True
        except Exception as e:
            print(f"Failed to initialize pyttsx3: {e}")
            return False

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """Clean text for better TTS output."""
        if not text:
            return ""
        
        # Remove code blocks
        text = re.sub(r'```[\s\S]*?```', '', text)
        # Remove inline code
        text = re.sub(r'`([^`]*)`', r'\1', text)
        # Remove markdown headings
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        # Remove bold/italic
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        # Remove markdown links
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        # Remove emojis
        text = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF'
                      r'\u2B50\u2705\u274C\u26A0\u2728\u2757\u2753'
                      r'\u25B6\u25C0\u27A1\u2B05\u2B06\u2B07'
                      r'\u2139\u2049\u203C\u2934\u2935'
                      r'\uFE0E\uFE0F\u200D]+', '', text)
        # Clean whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'  +', ' ', text)
        return text.strip()

    def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}

        if not PYTTSX3_AVAILABLE:
            return {"success": False, "error": "pyttsx3 not available"}

        if not self._engine and not self._init_engine():
            return {"success": False, "error": "Failed to initialize TTS engine"}

        # Clean text
        clean = self._clean_for_tts(text)
        if not clean:
            return {"success": False, "error": "No speakable text after cleanup"}

        # Truncate if too long
        if len(clean) > self.MAX_TEXT_LEN:
            clean = clean[:self.MAX_TEXT_LEN].rsplit(' ', 1)[0] + '...'

        try:
            # Speak asynchronously
            def speak_async():
                self._engine.say(clean)
                self._engine.runAndWait()
            
            # Start speech in background thread
            thread = threading.Thread(target=speak_async, daemon=True)
            thread.start()
            
            # Wait a moment for speech to start
            time.sleep(0.1)
            
            return {
                "success": True, 
                "spoken": True, 
                "text": clean, 
                "backend": "pyttsx3",
                "voice": self._engine.getProperty('voice') if self._engine else None
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_info():
    return {
        "name": "tts", 
        "version": "v1", 
        "description": "High-quality Text-to-Speech via pyttsx3 (native voices)"
    }


def health_check():
    if not PYTTSX3_AVAILABLE:
        return {"status": "error", "error": "pyttsx3 not installed"}
    
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty('voices')
        if not voices:
            return {"status": "error", "error": "No TTS voices available"}
        return {"status": "ok", "voices": len(voices)}
    except Exception as e:
        return {"status": "error", "error": str(e)}


def execute(params: dict) -> dict:
    return Pyttsx3TTSSkill().execute(params)
