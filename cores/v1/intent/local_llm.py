"""Local LLM classifier for intent detection (ollama-based)."""
import json
import subprocess
from typing import Optional, List, Dict, Tuple
from .config import get_config_value


_INTENT_CONFIG = {
    "local_llm_models": get_config_value("intent.local_llm_models", [
        "qwen3:4b", "qwen2.5:3b", "qwen2.5-coder:3b",
        "gemma3:4b", "phi4-mini", "llama3.2:3b"
    ]),
}


class LocalLLMClassifier:
    """
    Uses local ollama model (Qwen 3B) for intent classification.
    
    Only called when embedding confidence is too low (<0.75).
    ~100-200ms via ollama API.
    """

    MODELS = _INTENT_CONFIG["local_llm_models"]

    def __init__(self):
        self._model = None
        self._available = None

    @property
    def available(self) -> bool:
        if self._available is not None:
            return self._available
        self._detect()
        return self._available

    def _detect(self):
        """Find available local model."""
        try:
            r = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=5
            )
            if r.returncode != 0:
                self._available = False
                return
            installed = r.stdout.lower()
            for m in self.MODELS:
                base = m.split(":")[0]
                if base in installed:
                    self._model = m
                    self._available = True
                    return
            self._available = False
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self._available = False

    def classify(self, user_msg: str, skills: list,
                 context: str = "") -> Optional["IntentResult"]:
        """Classify intent using local LLM."""
        if not self.available or not self._model:
            return None

        skills_str = ", ".join(skills) if skills else "tts, stt, web_search, git_ops, shell"

        prompt = (
            f"Klasyfikuj intencję użytkownika. Dostępne skills: [{skills_str}]\n"
            f"Kontekst: {context[:200]}\n\n"
            f"Wiadomość: \"{user_msg}\"\n\n"
            f"Odpowiedz TYLKO JSON:\n"
            f'{{"action":"use|create|evolve|chat","skill":"nazwa","goal":"cel"}}\n'
            f"Jeśli user chce rozmawiać głosowo → skill=stt.\n"
            f"Jeśli user chce żeby system mówił → skill=tts."
        )

        try:
            import requests
            base = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
            r = requests.post(
                f"{base}/api/generate",
                json={
                    "model": self._model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1, "num_predict": 100},
                },
                timeout=10,
            )
            if r.status_code != 200:
                return None

            text = r.json().get("response", "").strip()

            # Extract JSON from response
            import re
            m = re.search(r'\{[^}]+\}', text)
            if not m:
                return None
            d = json.loads(m.group())

            action = d.get("action", "chat")
            skill = d.get("skill", "")
            goal = d.get("goal", "")

            if action not in ("use", "create", "evolve", "chat"):
                action = "chat"

            # Lazy import to avoid circular dependency
            from . import IntentResult
            return IntentResult(
                action=action, skill=skill, confidence=0.80,
                tier="local_llm", goal=goal,
                input={"text": user_msg} if skill else {},
            )
        except Exception:
            return None
