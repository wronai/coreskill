import subprocess
from typing import Optional, Dict, Any

class TTS:
    def __init__(self):
        self.backends = {
            'espeak': self._espeak_backend,
            'festival': self._festival_backend
        }
        self.available_backends = self._detect_backends()

    def _detect_backends(self) -> Dict[str, bool]:
        available = {}
        try:
            subprocess.run(['espeak', '--version'], capture_output=True, check=True)
            available['espeak'] = True
        except Exception:
            available['espeak'] = False
        try:
            subprocess.run(['festival', '--version'], capture_output=True, check=True)
            available['festival'] = True
        except Exception:
            available['festival'] = False
        return available

    def _espeak_backend(self, text: str) -> None:
        subprocess.run(['espeak', text], check=True)

    def _festival_backend(self, text: str) -> None:
        subprocess.run(['festival', '--tts'], input=text, text=True, check=True)

    def speak(self, text: str, backend: Optional[str] = None) -> None:
        if backend is None:
            for preferred in ['espeak', 'festival']:
                if self.available_backends.get(preferred, False):
                    backend = preferred
                    break
            if backend is None:
                raise RuntimeError("No TTS backends available")
        self.backends[backend](text)

    def execute(self, input_data: dict) -> dict:
        text = input_data.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided", "spoken": False}
        try:
            self.speak(text)
            return {"success": True, "spoken": True, "text": text}
        except Exception as e:
            return {"success": False, "error": str(e), "spoken": False}

    def get_info(self) -> dict:
        return {"name": "tts", "version": "v1", "description": "Text-to-Speech using espeak/festival"}

    def get_preferred_backend(self) -> Optional[str]:
        for preferred in ['espeak', 'festival']:
            if self.available_backends.get(preferred, False):
                return preferred
        return None

def health_check() -> bool:
    try:
        tts = TTS()
        return tts.get_preferred_backend() is not None
    except Exception:
        return False

def get_info():
    return {"name": "tts", "version": "v1", "description": "Text-to-Speech using espeak/festival"}

if __name__ == "__main__":
    tts = TTS()
    print(f"Backends: {tts.available_backends}")
    pref = tts.get_preferred_backend()
    print(f"Preferred: {pref}")
    if pref:
        tts.speak("Test TTS")
        print("OK")
    else:
        print("No backend")