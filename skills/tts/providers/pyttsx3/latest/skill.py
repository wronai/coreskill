import subprocess
import shutil
import re


class TTSSkill:
    """Text-to-Speech using espeak (non-blocking via subprocess.Popen)."""

    MAX_TEXT_LEN = 500

    def __init__(self):
        self._backend = None
        for cmd in ("espeak-ng", "espeak"):
            if shutil.which(cmd):
                self._backend = cmd
                break

    @staticmethod
    def _clean_for_tts(text: str) -> str:
        """Strip markdown, emojis, and special chars."""
        if not text:
            return ""
        text = re.sub(r'```[\s\S]*?```', '', text)
        text = re.sub(r'`([^`]*)`', r'\1', text)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'\*{1,3}([^*]+)\*{1,3}', r'\1', text)
        text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
        text = re.sub(r'[\U0001F300-\U0001FAFF\u2600-\u27BF\u2300-\u23FF'
                      r'\u2B50\u2705\u274C\u26A0\u2728\u2757\u2753'
                      r'\u25B6\u25C0\u27A1\u2B05\u2B06\u2B07'
                      r'\u2139\u2049\u203C\u2934\u2935'
                      r'\uFE0E\uFE0F\u200D]+', '', text)
        text = re.sub(r'[\u2192\u2190\u2191\u2193\u21D2\u21D0\u2022\u25CF\u25CB\u25A0\u25A1\u25B8\u25B9]', ' ', text)
        text = re.sub(r'^\s*[-*+]\s+', '', text, flags=re.MULTILINE)
        text = re.sub(r'https?://\S+', '', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r'  +', ' ', text)
        return text.strip()

    def execute(self, params: dict) -> dict:
        text = params.get("text", "")
        if not text:
            return {"success": False, "error": "No text provided"}
        if not self._backend:
            return {"success": False, "error": "espeak not installed (apt install espeak)"}

        clean = self._clean_for_tts(text)
        if not clean:
            return {"success": False, "error": "No speakable text after cleanup"}
        if len(clean) > self.MAX_TEXT_LEN:
            clean = clean[:self.MAX_TEXT_LEN].rsplit(' ', 1)[0] + '...'

        try:
            subprocess.Popen(
                [self._backend, "-v", "pl", "-s", "150", "--", clean],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return {
                "success": True,
                "spoken": True,
                "text": clean,
                "backend": self._backend
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


def get_info():
    return {
        "name": "tts",
        "version": "v1",
        "description": "Text-to-Speech via espeak (non-blocking)"
    }


def health_check():
    if not shutil.which("espeak-ng") and not shutil.which("espeak"):
        return {"status": "error", "message": "espeak not installed"}
    return {"status": "ok"}


def execute(params: dict) -> dict:
    return TTSSkill().execute(params)


if __name__ == "__main__":
    # Simple test
    skill = TTSSkill()
    result = execute({"text": "Witaj świecie!"})
    print(result)