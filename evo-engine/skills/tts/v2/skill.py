import subprocess
import tempfile
from typing import Dict, Optional, Any

class TTSSkill:
    def __init__(self):
        self.backends = {
            'espeak': self._espeak_backend,
            'festival': self._festival_backend
        }
        self.available_backends = self._detect_backends()

    def _detect_backends(self) -> Dict[str, bool]:
        """Detect available TTS backends"""
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
        """Use espeak for TTS with Polish voice if available"""
        try: