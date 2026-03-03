import os
import subprocess
from typing import Optional, Dict, Any
import pyttsx3
from gtts import gTTS
import tempfile

class TTSSkill:
    def __init__(self):
        self.backends = {
            'pyttsx3': self._pyttsx3_backend,
            'espeak': self._espeak_backend,
            'gtts': self._gtts_backend
        }
        self.available_backends = self._detect_backends()

    def _detect_backends(self) -> Dict[str, bool]:
        """Detect available TTS backends"""
        available = {}
        try:
            engine = pyttsx3.init()
            available['pyttsx3'] = True
        except Exception:
            available['pyttsx3'] = False
        try:
            subprocess.run(['espeak', '--version'], capture_output=True, check=True)
            available['espeak'] = True
        except Exception:
            available['espeak'] = False
        try:
            import gtts
            subprocess.run(['mpv', '--version'], capture_output=True, check=True)
            available['gtts'] = True
        except Exception:
            available['gtts'] = False
        return available

    def _pyttsx3_backend(self, text: str) -> None:
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def _espeak_backend(self, text: str) -> None:
        subprocess.run(['espeak', text], check=True)

    def _gtts_backend(self, text: str) -> None:
        tts = gTTS(text)
        with tempfile.NamedTemporaryFile(suffix='.mp3') as f:
            tts.save(f.name)
            subprocess.run(['mpv', f.name], check=True)

    def speak(self, text: str, backend: Optional[str] = None) -> None:
        if backend is None:
            for preferred in ['pyttsx3', 'espeak', 'gtts']:
                if self.available_backends.get(preferred, False):
                    backend = preferred
                    break
            if backend is None:
                raise RuntimeError("No TTS backends available")
        self.backends[backend](text)

    def execute(self, input_data: dict) -> dict:
        text = input_data.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
        try:
            self.speak(text)
            return {"success": True, "spoken": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": False}

    def get_available_backends(self) -> Dict[str, bool]:
        return self.available_backends

    def get_preferred_backend(self) -> Optional[str]:
        for preferred in ['pyttsx3', 'espeak', 'gtts']:
            if self.available_backends.get(preferred, False):
                return preferred
        return None

def get_info():
    return {"name": "tts", "version": "v1", "description": "Text-to-Speech with pyttsx3/espeak/gtts"}

def health_check():
    try:
        tts = TTSSkill()
        return tts.get_preferred_backend() is not None
    except:
        return False

if __name__ == "__main__":
    tts = TTSSkill()
    print(f"Backends: {tts.get_available_backends()}")
    print(f"Preferred: {tts.get_preferred_backend()}")
    if tts.get_preferred_backend():
        tts.speak("Test TTS")
        print("OK")
    else:
        print("No backend")