#!/usr/bin/env python3
"""
SessionConfig — user-facing configuration layer for evo-engine.

Allows users to modify system configuration DURING a conversation through
natural language (e.g., "używaj lepszego TTS", "przełącz na gemini-pro").

Key features:
- Configuration intents recognized by IntentEngine (action="configure")
- Hot-swappable providers (TTS, STT, LLM) without restart
- Session-persistent overrides (not saved to state, lost on restart)
- Clear feedback about what changed
"""
import re
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass, field

from .config import get_categories, get_provider_tiers


@dataclass
class ConfigChange:
    """Represents a single configuration change."""
    category: str  # 'llm', 'tts', 'stt', 'voice', 'system'
    setting: str   # 'model', 'provider', 'speed', 'quality', etc.
    old_value: Any
    new_value: Any
    success: bool = True
    message: str = ""


class SessionConfig:
    """
    User-facing configuration manager.
    
    This is a SESSION-ONLY layer - changes are NOT persisted to disk.
    They affect only the current conversation. This is intentional - 
    users can experiment freely without breaking their default setup.
    """
    
    def __init__(self, llm_client=None, provider_selector=None):
        self.llm = llm_client
        self.selector = provider_selector
        
        # Session overrides - these take precedence over defaults
        self._overrides: Dict[str, Dict[str, Any]] = {
            "llm": {},
            "tts": {},
            "stt": {},
            "voice": {},
        }
        
        # Change callbacks - notify components when config changes
        self._callbacks: Dict[str, list] = {}
        
        # Track last change for feedback
        self._last_change: Optional[ConfigChange] = None
    
    @property
    def CATEGORIES(self):
        """Configuration categories and their options - loaded from config file."""
        return get_categories()
    
    @property
    def PROVIDER_TIERS(self):
        """Provider quality tiers (for 'better/worse' resolution) - loaded from config file."""
        return get_provider_tiers()
    
    # ── Core API ──────────────────────────────────────────────────────
    
    def get(self, category: str, setting: str, default=None):
        """Get current value (override > default)."""
        if category in self._overrides and setting in self._overrides[category]:
            return self._overrides[category][setting]
        return default
    
    def set(self, category: str, setting: str, value: Any) -> ConfigChange:
        """Set a configuration value for this session."""
        old_value = self.get(category, setting)
        
        if category not in self._overrides:
            self._overrides[category] = {}
        
        self._overrides[category][setting] = value
        
        change = ConfigChange(
            category=category,
            setting=setting,
            old_value=old_value,
            new_value=value,
            success=True,
            message=f"{category}.{setting}: {old_value} → {value}"
        )
        self._last_change = change
        
        # Notify callbacks
        self._notify(f"{category}.{setting}", change)
        
        return change
    
    def reset(self, category: str = None, setting: str = None):
        """Reset overrides (all, category, or specific setting)."""
        if setting and category:
            if category in self._overrides and setting in self._overrides[category]:
                del self._overrides[category][setting]
        elif category:
            self._overrides[category] = {}
        else:
            self._overrides = {k: {} for k in self._overrides}
    
    def on_change(self, key: str, callback: Callable):
        """Register callback for configuration changes (key='tts.provider')."""
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)
    
    def _notify(self, key: str, change: ConfigChange):
        """Notify registered callbacks."""
        for cb in self._callbacks.get(key, []):
            try:
                cb(change)
            except Exception:
                pass
    
    # ── Intent Handlers ───────────────────────────────────────────────
    
    _QUERY_WORDS = ("jaki ", "jaki?", "który ", "która ", "what ", "which ", "current ", "aktualn")
    _QUALITY_WORDS = ("lepszy", "lepsza", "gorszy", "gorsza", "szybszy", "szybsza",
                      "better", "worse", "faster", "slower")
    _VOICE_INDICATORS = ("głos", "głosik", "mowa", "mówić", "voice", "tts",
                         "speech", "syntezator", "speak")
    _LLM_PATTERNS = ("gemini", "gpt", "claude", "llama", "qwen", "model")

    def _is_query_not_configure(self, ul, category):
        """Return ConfigChange if message is a query, not a configure request."""
        if not any(ul.startswith(w) or w in ul for w in self._QUERY_WORDS):
            return None
        if re.search(r'\b(ustaw|zmień|przełącz|set|change|switch)\b', ul):
            return None
        if self.llm and category in ("", "llm"):
            return ConfigChange(
                category="llm", setting="model",
                old_value=self.llm.model, new_value=self.llm.model,
                success=True, message=f"Aktualny model: {self.llm.model}"
            )
        return None

    def _resolve_category(self, category, target, ul, original):
        """Resolve ambiguous category to a concrete one."""
        if not category:
            if any(w in ul for w in self._QUALITY_WORDS):
                if not any(v in ul for v in self._VOICE_INDICATORS):
                    print(f"[SessionConfig] Ambiguous config '{original}' → defaulting to LLM (fallback)")
                    return "llm"
        if category in ("tts", "stt") and target:
            if any(p in ul for p in self._LLM_PATTERNS):
                print(f"[SessionConfig] Override: '{original}' contains LLM patterns → switching to LLM config")
                return "llm"
        return category

    def handle_configure_intent(self, intent_result: dict) -> ConfigChange:
        """
        Handle 'configure' intent from IntentEngine.
        
        intent_result contains:
        - category: 'llm', 'tts', 'stt', 'voice'
        - target: specific target (model name, provider name, 'better', 'best', 'worse')
        - original_msg: user's original message (for context)
        """
        category = intent_result.get("category", "")
        target = intent_result.get("target", "")
        original = intent_result.get("original_msg", "")
        ul = original.lower()
        
        query_result = self._is_query_not_configure(ul, category)
        if query_result:
            return query_result
        
        category = self._resolve_category(category, target, ul, original)
        
        _HANDLERS = {
            "llm": self._configure_llm,
            "tts": self._configure_tts,
            "stt": self._configure_stt,
            "voice": self._configure_voice,
        }
        handler = _HANDLERS.get(category)
        if handler:
            return handler(target, original)
        
        return ConfigChange(
            category="unknown",
            setting="",
            old_value=None,
            new_value=None,
            success=False,
            message=f"Nieznana kategoria konfiguracji: {category}"
        )
    
    def _configure_llm(self, target: str, original: str) -> ConfigChange:
        """Configure LLM model."""
        if not self.llm:
            return ConfigChange(
                category="llm", setting="model",
                old_value=None, new_value=None,
                success=False, message="LLM client not available"
            )
        
        current = self.llm.model
        
        # Resolve target
        if target in ("better", "best", "lepszy", "najlepszy"):
            new_model = self._resolve_better_model(current)
        elif target in ("worse", "simpler", "gorszy", "prostszy"):
            new_model = self._resolve_worse_model(current)
        elif target in ("faster", "szybszy"):
            new_model = self._resolve_faster_model(current)
        elif target in ("free", "darmowy"):
            new_model = self._resolve_free_model()
        else:
            # Specific model name
            new_model = target if target else self._extract_model_name(original)
            # If target looks partial (no '/'), try extracting full name from message
            if new_model and '/' not in new_model:
                extracted = self._extract_model_name(original)
                if extracted:
                    new_model = extracted
        
        if new_model and new_model != current:
            # Try to switch
            if hasattr(self.llm, 'set_model'):
                success = self.llm.set_model(new_model)
                return ConfigChange(
                    category="llm", setting="model",
                    old_value=current, new_value=new_model,
                    success=success,
                    message=f"Przełączono na model: {new_model}" if success else f"Nie udało się przełączyć na: {new_model}"
                )
            else:
                # Store as override - main loop needs to check this
                return self.set("llm", "model", new_model)
        
        return ConfigChange(
            category="llm", setting="model",
            old_value=current, new_value=current,
            success=True, message=f"Już używasz: {current}"
        )
    
    def _configure_tts(self, target: str, original: str) -> ConfigChange:
        """Configure TTS provider."""
        if not self.selector:
            return ConfigChange(
                category="tts", setting="provider",
                success=False, message="Provider selector not available"
            )
        
        current = self.get("tts", "provider")
        if not current:
            current = self.selector.select("tts", prefer="quality")
        
        providers = self.selector.list_providers("tts")
        
        # Resolve target
        if target in ("better", "best", "lepszy", "najlepszy", "wysoka jakość"):
            new_provider = self._resolve_better_provider("tts", current)
        elif target in ("worse", "simpler", "gorszy", "prostszy", "szybki"):
            new_provider = self._resolve_worse_provider("tts", current)
        elif target in ("faster", "szybszy", "szybko"):
            new_provider = self._resolve_fastest_provider("tts")
        elif target in providers:
            new_provider = target
        else:
            new_provider = self._extract_provider_name(original, "tts")
        
        if new_provider and new_provider != current:
            return self.set("tts", "provider", new_provider)
        
        return ConfigChange(
            category="tts", setting="provider",
            old_value=current, new_value=current,
            success=True, message=f"Już używasz: {current}"
        )
    
    def _configure_stt(self, target: str, original: str) -> ConfigChange:
        """Configure STT provider."""
        if not self.selector:
            return ConfigChange(
                category="stt", setting="provider",
                success=False, message="Provider selector not available"
            )
        
        current = self.get("stt", "provider")
        if not current:
            current = self.selector.select("stt", prefer="quality")
        
        providers = self.selector.list_providers("stt")
        
        if target in ("better", "best", "lepszy", "najlepszy"):
            new_provider = self._resolve_better_provider("stt", current)
        elif target in ("worse", "simpler", "gorszy"):
            new_provider = self._resolve_worse_provider("stt", current)
        elif target in providers:
            new_provider = target
        else:
            new_provider = self._extract_provider_name(original, "stt")
        
        if new_provider and new_provider != current:
            return self.set("stt", "provider", new_provider)
        
        return ConfigChange(
            category="stt", setting="provider",
            old_value=current, new_value=current,
            success=True, message=f"Już używasz: {current}"
        )
    
    def _configure_voice(self, target: str, original: str) -> ConfigChange:
        """Configure voice mode settings."""
        if target in ("on", "enable", "włącz", "true"):
            return self.set("voice", "auto_mode", True)
        elif target in ("off", "disable", "wyłącz", "wyłacz", "false"):
            return self.set("voice", "auto_mode", False)
        
        return ConfigChange(
            category="voice", setting="auto_mode",
            success=False, message=f"Nieznana opcja: {target}"
        )
    
    # ── Resolution Helpers ────────────────────────────────────────────
    
    def _resolve_better_model(self, current: str) -> Optional[str]:
        """Find a better model than current."""
        if not self.llm:
            return None
        
        # Get available models by tier
        tiers = ["TIER_PAID", "TIER_LOCAL", "TIER_FREE"]
        
        # Simple heuristic: prefer non-free models if available
        if hasattr(self.llm, '_models'):
            paid_models = [m for m in self.llm._models if ":free" not in m and not m.startswith("ollama/")]
            if paid_models:
                return paid_models[0]
        
        return None
    
    def _resolve_worse_model(self, current: str) -> Optional[str]:
        """Find a simpler/faster model than current."""
        if not self.llm:
            return None
        
        # Prefer free or local models
        if hasattr(self.llm, '_models'):
            free_models = [m for m in self.llm._models if ":free" in m]
            if free_models:
                return free_models[0]
            local_models = [m for m in self.llm._models if m.startswith("ollama/")]
            if local_models:
                return local_models[0]
        
        return None
    
    def _resolve_faster_model(self, current: str) -> Optional[str]:
        """Find a faster (likely local or free) model."""
        return self._resolve_worse_model(current)
    
    def _resolve_free_model(self) -> Optional[str]:
        """Find a free model."""
        return self._resolve_worse_model("")
    
    def _resolve_better_provider(self, capability: str, current: str) -> Optional[str]:
        """Find a better quality provider."""
        if not self.selector:
            return None
        
        tiers = self.PROVIDER_TIERS.get(capability, {})
        current_tier = tiers.get(current, {}).get("quality", 0)
        
        providers = self.selector.list_providers(capability)
        candidates = []
        
        for p in providers:
            p_tier = tiers.get(p, {}).get("quality", 5)
            if p_tier > current_tier:
                # Check if can run
                info = self.selector.get_provider_info(capability, p)
                can_run, _ = self.selector._check_runnable(info)
                if can_run:
                    candidates.append((p, p_tier))
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    def _resolve_worse_provider(self, capability: str, current: str) -> Optional[str]:
        """Find a simpler/faster provider."""
        if not self.selector:
            return None
        
        tiers = self.PROVIDER_TIERS.get(capability, {})
        current_tier = tiers.get(current, {}).get("quality", 10)
        
        providers = self.selector.list_providers(capability)
        candidates = []
        
        for p in providers:
            p_tier = tiers.get(p, {}).get("quality", 5)
            if p_tier < current_tier:
                info = self.selector.get_provider_info(capability, p)
                can_run, _ = self.selector._check_runnable(info)
                if can_run:
                    candidates.append((p, p_tier))
        
        if candidates:
            candidates.sort(key=lambda x: x[1])  # ascending
            return candidates[0][0]
        
        return None
    
    def _resolve_fastest_provider(self, capability: str) -> Optional[str]:
        """Find the fastest provider."""
        if not self.selector:
            return None
        
        tiers = self.PROVIDER_TIERS.get(capability, {})
        providers = self.selector.list_providers(capability)
        
        candidates = []
        for p in providers:
            speed = tiers.get(p, {}).get("speed", 5)
            info = self.selector.get_provider_info(capability, p)
            can_run, _ = self.selector._check_runnable(info)
            if can_run:
                candidates.append((p, speed))
        
        if candidates:
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[0][0]
        
        return None
    
    # ── Extraction Helpers ────────────────────────────────────────────
    
    def _extract_model_name(self, msg: str) -> Optional[str]:
        """Extract model name from message."""
        msg_lower = msg.lower()
        
        # Priority 1: namespace/model pattern (e.g. x-ai/grok-4.1-fast, google/gemma-3-27b)
        ns_match = re.search(r'([a-z][a-z0-9\-]*/[a-z][a-z0-9\-\.:]+)', msg_lower)
        if ns_match:
            model = ns_match.group(1)
            if not model.startswith("openrouter/"):
                return f"openrouter/{model}"
            return model
        
        # Priority 2: keyword + model name
        patterns = [
            r'(?:model|modelu|llm|na|używaj|przełącz na|zmień na)\s+([a-z0-9\-\.]+)',
            r'([a-z0-9\-]+(?:pro|flash|lite|mini|max))',
            r'(gpt-[a-z0-9\-]+)',
            r'(claude-[a-z0-9\-]+)',
            r'(gemini-[a-z0-9\-]+)',
            r'(llama-[a-z0-9\-]+)',
            r'(grok-[a-z0-9\-\.]+)',
            r'(qwen[a-z0-9\-\.]+)',
            r'(deepseek-[a-z0-9\-\.]+)',
            r'(gemma-[a-z0-9\-\.]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, msg_lower)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_provider_name(self, msg: str, capability: str) -> Optional[str]:
        """Extract provider name from message."""
        if not self.selector:
            return None
        
        providers = self.selector.list_providers(capability)
        msg_lower = msg.lower()
        
        for p in providers:
            if p.lower() in msg_lower:
                return p
        
        return None
    
    # ── Feedback & Display ────────────────────────────────────────────
    
    def get_last_change(self) -> Optional[ConfigChange]:
        """Get the last configuration change for feedback."""
        return self._last_change
    
    def format_change_feedback(self, change: ConfigChange) -> str:
        """Format configuration change for user feedback."""
        if not change.success:
            return f"⚠️ Nie udało się zmienić konfiguracji: {change.message}"
        
        category_names = {
            "llm": "Model LLM",
            "tts": "Synteza mowy (TTS)",
            "stt": "Rozpoznawanie mowy (STT)",
            "voice": "Tryb głosowy",
        }
        
        cat_name = category_names.get(change.category, change.category)
        
        return f"⚙️ {cat_name}: {change.old_value} → {change.new_value}"
    
    def get_session_summary(self) -> str:
        """Get summary of current session configuration."""
        lines = ["Konfiguracja sesji:"]
        
        for category, settings in self._overrides.items():
            if settings:
                lines.append(f"  {category}:")
                for k, v in settings.items():
                    lines.append(f"    {k}: {v}")
        
        if len(lines) == 1:
            return "Brak aktywnych zmian w sesji (używane domyślne ustawienia)."
        
        return "\n".join(lines)
