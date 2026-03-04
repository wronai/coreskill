#!/usr/bin/env python3
"""
evo-engine SkillValidator — plugin registry for skill-specific result validation.

Replaces hardcoded `if skill_name == "stt"` branches in EvoEngine._validate_result()
with a registerable validator pattern.

Built-in validators: stt, shell, tts, web_search.
Custom validators can be registered at runtime.
"""
from typing import Callable, Dict, Optional


# ─── Validation Result ────────────────────────────────────────────────
class ValidationResult:
    """Structured validation outcome."""
    __slots__ = ("verdict", "reason")

    def __init__(self, verdict: str, reason: str):
        self.verdict = verdict   # "success" | "partial" | "fail"
        self.reason = reason

    def to_dict(self) -> dict:
        return {"verdict": self.verdict, "reason": self.reason}

    def __repr__(self):
        return f"ValidationResult({self.verdict}: {self.reason[:60]})"


# Type alias for validator functions
# Signature: (result: dict, goal: str, user_msg: str) -> ValidationResult | None
ValidatorFunc = Callable[[dict, str, str], Optional[ValidationResult]]


# ─── Built-in validators ──────────────────────────────────────────────

def _validate_stt(result: dict, goal: str, user_msg: str) -> Optional[ValidationResult]:
    """STT-specific validation: check for hardware errors, silence, empty transcription."""
    inner = result.get("result", {})
    if not isinstance(inner, dict):
        return None

    # STT v2: hardware check failed
    if inner.get("hardware_ok") is False:
        error_msg = inner.get("error", "Unknown hardware error")
        return ValidationResult("fail", f"STT hardware error: {error_msg}")

    # STT v2: no sound detected
    if inner.get("has_sound") is False:
        db_level = inner.get("audio_level_db", -999)
        return ValidationResult(
            "partial",
            f"STT silence detected ({db_level:.1f}dB). "
            f"Check microphone and speak louder.")

    # Legacy: empty transcription
    spoken = inner.get("spoken") or inner.get("text") or ""
    if not spoken.strip():
        return ValidationResult(
            "partial",
            "STT returned empty transcription (silence or mic issue)")

    return None  # Pass to generic validation


def _validate_shell(result: dict, goal: str, user_msg: str) -> Optional[ValidationResult]:
    """Shell-specific validation: check exit code."""
    inner = result.get("result", {})
    if not isinstance(inner, dict):
        return None

    exit_code = inner.get("exit_code", 0)
    if exit_code != 0:
        stderr = inner.get("stderr", "")[:200]
        return ValidationResult("partial", f"exit_code={exit_code}: {stderr}")

    return None


def _validate_tts(result: dict, goal: str, user_msg: str) -> Optional[ValidationResult]:
    """TTS-specific validation: check for error field."""
    inner = result.get("result", {})
    if not isinstance(inner, dict):
        return None

    if inner.get("error"):
        return ValidationResult("fail", inner["error"])

    return None


# Local network keywords for web_search validation
_LOCAL_NET_KEYWORDS = (
    "kamer", "camera", "rtsp", "onvif", "sieć lokal", "local network",
    "lan ", "lan:", "skanuj", "scan", "urządzenia w sieci", "devices in network",
    "ip w sieci", "ip in network", "drukark", "printer", "router",
)


def _validate_web_search(result: dict, goal: str, user_msg: str) -> Optional[ValidationResult]:
    """Web search validation: check for empty results, especially local network queries."""
    inner = result.get("result", {})
    if not isinstance(inner, dict):
        return None

    results = inner.get("results", [])
    query = inner.get("query", "").lower()

    is_local_net = any(kw in query for kw in _LOCAL_NET_KEYWORDS)
    if is_local_net and not results:
        return ValidationResult(
            "partial",
            f"web_search: no results for local network query '{query[:50]}'. "
            f"Requires dedicated network scanner skill.")

    if not results:
        return ValidationResult(
            "partial",
            f"web_search: empty results for '{query[:50]}'")

    return None


# ─── Validator Registry ───────────────────────────────────────────────

class SkillValidator:
    """
    Plugin registry for skill-specific result validation.

    Usage:
        validator = SkillValidator()
        # Built-in validators are registered automatically.
        # Register custom:
        validator.register("my_skill", my_validator_func)
        # Validate:
        result = validator.validate("stt", exec_result, goal, user_msg)
    """

    def __init__(self):
        self._validators: Dict[str, ValidatorFunc] = {}
        # Register built-in validators
        self._validators["stt"] = _validate_stt
        self._validators["shell"] = _validate_shell
        self._validators["tts"] = _validate_tts
        self._validators["web_search"] = _validate_web_search

    def register(self, skill_name: str, func: ValidatorFunc):
        """Register a custom validator for a skill."""
        self._validators[skill_name] = func

    def unregister(self, skill_name: str):
        """Remove a custom validator."""
        self._validators.pop(skill_name, None)

    def has_validator(self, skill_name: str) -> bool:
        """Check if a skill has a registered validator."""
        return skill_name in self._validators

    def validate(self, skill_name: str, result: dict,
                 goal: str = "", user_msg: str = "") -> ValidationResult:
        """
        Validate a skill execution result.

        1. Check outer success flag
        2. Check inner success flag
        3. Run skill-specific validator (if registered)
        4. Return generic success

        Returns ValidationResult with verdict: success | partial | fail
        """
        # Outer failure
        if not result.get("success"):
            return ValidationResult(
                "fail",
                result.get("error", "skill returned success=False"))

        inner = result.get("result", {})

        # Inner failure (dict with explicit success=False)
        if isinstance(inner, dict) and inner.get("success") is False:
            return ValidationResult(
                "fail",
                inner.get("error", "inner result success=False"))

        # Non-dict inner — trust the skill
        if not isinstance(inner, dict):
            return ValidationResult("success", "non-dict result, trusting skill")

        # Skill-specific validation
        if skill_name in self._validators:
            specific = self._validators[skill_name](result, goal, user_msg)
            if specific is not None:
                return specific

        # Generic success
        return ValidationResult("success", "skill reports success")

    def list_validators(self) -> list:
        """List registered validator skill names."""
        return sorted(self._validators.keys())
