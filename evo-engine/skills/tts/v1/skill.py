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
        # Check pyttsx3
        try:
            engine = pyttsx3.init()
            available['pyttsx3'] = True
        except Exception:
            available['pyttsx3'] = False

        # Check espeak
        try:
            subprocess.run(['espeak', '--version'], capture_output=True, check=True)
            available['espeak'] = True
        except Exception:
            available['espeak'] = False

        # Check gtts (requires mpv for playback)
        try:
            import gtts
            subprocess.run(['mpv', '--version'], capture_output=True, check=True)
            available['gtts'] = True
        except Exception:
            available['gtts'] = False

        return available

    def _pyttsx3_backend(self, text: str) -> None:
        """Text-to-speech using pyttsx3"""
        if not self.available_backends.get('pyttsx3', False):
            raise RuntimeError("pyttsx3 backend not available")
        engine = pyttsx3.init()
        engine.say(text)
        engine.runAndWait()

    def _espeak_backend(self, text: str) -> None:
        """Text-to-speech using espeak"""
        if not self.available_backends.get('espeak', False):
            raise RuntimeError("espeak backend not available")
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt') as temp_file:
            temp_file.write(text)
            temp_file.flush()
            subprocess.run(['espeak', '-f', temp_file.name], check=True)

    def _gtts_backend(self, text: str) -> None:
        """Text-to-speech using gTTS + mpv"""
        if not self.available_backends.get('gtts', False):
            raise RuntimeError("gtts backend not available")
        tts = gTTS(text)
        with tempfile.NamedTemporaryFile(suffix='.mp3') as temp_file:
            tts.save(temp_file.name)
            temp_file.flush()
            subprocess.run(['mpv', temp_file.name], check=True)

    def speak(self, text: str, backend: Optional[str] = None) -> None:
        """
        Speak the given text using the specified backend or auto-detect
        """
        if backend is None:
            # Auto-select backend in order of preference
            for preferred in ['pyttsx3', 'espeak', 'gtts']:
                if self.available_backends.get(preferred, False):
                    backend = preferred
                    break
            if backend is None:
                raise RuntimeError("No TTS backends available")

        if backend not in self.backends:
            raise ValueError(f"Unknown backend: {backend}")

        self.backends[backend](text)

    def get_available_backends(self) -> Dict[str, bool]:
        """Return dictionary of available backends"""
        return self.available_backends

    def get_preferred_backend(self) -> Optional[str]:
        """Return the preferred available backend"""
        for preferred in ['pyttsx3', 'espeak', 'gtts']:
            if self.available_backends.get(preferred, False):
                return preferred
        return None