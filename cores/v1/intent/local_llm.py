"""LocalLLMClassifier — ollama-based intent classification.

Uses local ollama model (Qwen 3B, etc.) for intent classification.
Only called when embedding confidence is too low (<0.75).
~100-200ms via ollama API.
"""
import json
import os
import subprocess
from typing import Dict, Optional

try:
    from ..config import get_config_value
except ImportError:
    def get_config_value(k, d=None): return d


# Load intent configuration from system.json
_INTENT_CONFIG = {
    "local_llm_models": get_config_value("intent.local_llm_models", [
        "qwen3:4b", "qwen2.5:3b", "qwen2.5-coder:3b",
        "gemma3:4b", "phi4-mini", "llama3.2:3b"
    ]),
}

# Forward reference - imported at runtime to avoid circular imports
IntentResult = None


def _get_intent_result_class():
    """Lazy import to avoid circular dependency."""
    global IntentResult
    if IntentResult is None:
        from ..smart_intent import IntentResult as IR
        IntentResult = IR
    return IntentResult


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

    def _build_skill_schema(self, skills: dict) -> str:
        """Build rich schema from skills dict with descriptions and providers."""
        if not skills:
            return "- tts: synteza mowy (głos)\n- stt: rozpoznawanie mowy (słuchanie)"
        
        lines = []
        for name, meta in skills.items():
            if isinstance(meta, dict):
                desc = meta.get("description", meta.get("desc", ""))
                providers = meta.get("providers", meta.get("available_providers", []))
                active = meta.get("active_provider", "")
                if providers:
                    prov_str = ", ".join(str(p) for p in providers[:3])
                    if active:
                        lines.append(f"- {name}: {desc[:60] if desc else 'skill'} (providers: {prov_str}, aktywny: {active})")
                    else:
                        lines.append(f"- {name}: {desc[:60] if desc else 'skill'} (providers: {prov_str})")
                else:
                    lines.append(f"- {name}: {desc[:60] if desc else 'skill'}")
            else:
                lines.append(f"- {name}: skill")
        return "\n".join(lines)

    def classify(self, user_msg: str, skills: dict = None,
                 context: str = "") -> Optional["IntentResult"]:
        """Classify intent using local LLM with full skill schema."""
        if not self.available or not self._model:
            return None

        # Build rich skill schema from skills dict
        schema = self._build_skill_schema(skills or {})

        prompt = (
            f"Klasyfikuj intencję użytkownika.\n\n"
            f"=== DOSTĘPNE NARZĘDZIA ===\n{schema}\n\n"
            f"=== MOŻLIWE AKCJE ===\n"
            f"- use [skill] (użyj istniejącego narzędzia)\n"
            f"- create [skill] (stwórz nowy skill/program)\n"
            f"- evolve [skill] (napraw/ulepsz istniejący skill)\n"
            f"- configure [llm|tts|stt|voice] (zmień ustawienia)\n"
            f"- chat (zwykła rozmowa)\n\n"
            f"=== ZASADY PRIORYTETOW ===\n"
            f"1. \"lepszy/gorszy GŁOS\" w kontekście voice → configure tts\n"
            f"2. \"lepszy/gorszy MODEL\" → configure llm\n"
            f"3. \"napraw skill X\" gdy X istnieje → evolve X\n"
            f"4. \"napraw skill X\" gdy X nie istnieje → create X\n\n"
            f"=== KONTEKST ===\n{context[:300] or 'Brak'}\n\n"
            f"=== WIADOMOŚĆ ===\n\"{user_msg}\"\n\n"
            f"Odpowiedz TYLKO JSON:\n"
            f'{{"action":"use|create|evolve|configure|chat","skill":"nazwa","goal":"cel","reasoning":"krótkie uzasadnienie"}}'
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

            if action not in ("use", "create", "evolve", "configure", "chat"):
                action = "chat"

            IR = _get_intent_result_class()
            return IR(
                action=action, skill=skill, confidence=0.85,
                tier="local_llm_schema", goal=goal,
                input={"text": user_msg} if skill else {},
            )
        except Exception:
            return None
