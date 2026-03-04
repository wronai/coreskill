#!/usr/bin/env python3
"""
Resilience utilities — tenacity retry decorators + structlog structured logging.

Provides:
- Preconfigured retry decorators for LLM calls, skill execution, and I/O
- structlog integration layered on top of existing Logger class
- Retry event hooks that log attempts via structlog

Usage:
    from .resilience import retry_llm, retry_skill, get_struct_logger

    @retry_llm
    def call_model(prompt):
        return litellm.completion(...)

    log = get_struct_logger("evo_engine")
    log.info("pipeline_start", skill="tts", attempt=1)
"""
import time
import functools
from typing import Callable, Optional

try:
    import tenacity
    from tenacity import (
        retry, stop_after_attempt, wait_exponential,
        wait_fixed, retry_if_exception_type, before_sleep_log,
        RetryCallState,
    )
    _HAS_TENACITY = True
except ImportError:
    _HAS_TENACITY = False

try:
    import structlog
    _HAS_STRUCTLOG = True
except ImportError:
    _HAS_STRUCTLOG = False

import logging


# ── structlog Configuration ─────────────────────────────────────────

_STRUCTLOG_CONFIGURED = False


def configure_structlog():
    """Configure structlog with JSON + console processors (idempotent)."""
    global _STRUCTLOG_CONFIGURED
    if _STRUCTLOG_CONFIGURED or not _HAS_STRUCTLOG:
        return
    _STRUCTLOG_CONFIGURED = True

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.dev.ConsoleRenderer(colors=False),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_struct_logger(name: str = "coreskill"):
    """Get a structlog logger bound to a component name.

    Falls back to stdlib logging if structlog unavailable.
    """
    if _HAS_STRUCTLOG:
        configure_structlog()
        return structlog.get_logger(component=name)
    return logging.getLogger(name)


# ── Tenacity Retry Decorators ───────────────────────────────────────

def _log_retry(retry_state: 'RetryCallState'):
    """Log retry attempts via structlog."""
    if not _HAS_STRUCTLOG:
        return
    log = get_struct_logger("retry")
    fn_name = getattr(retry_state.fn, '__name__', '?')
    log.warning("retry_attempt",
                function=fn_name,
                attempt=retry_state.attempt_number,
                wait=round(retry_state.idle_for, 2) if retry_state.idle_for else 0,
                error=str(retry_state.outcome.exception())[:100]
                if retry_state.outcome and retry_state.outcome.exception() else "")


if _HAS_TENACITY:
    # LLM calls: 3 attempts, exponential backoff 1s→4s, retry on any Exception
    retry_llm = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        before_sleep=_log_retry,
        reraise=True,
    )

    # Skill execution: 2 attempts, fixed 0.5s wait
    retry_skill = retry(
        stop=stop_after_attempt(2),
        wait=wait_fixed(0.5),
        before_sleep=_log_retry,
        reraise=True,
    )

    # I/O operations: 3 attempts, exponential 0.5s→2s
    retry_io = retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=0.5, min=0.5, max=2),
        before_sleep=_log_retry,
        reraise=True,
    )
else:
    # Fallback: no-op decorators when tenacity not installed
    def retry_llm(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            return fn(*args, **kwargs)
        return wrapper

    retry_skill = retry_llm
    retry_io = retry_llm


# ── Convenience: retry with custom params ───────────────────────────

def with_retry(max_attempts: int = 3, backoff_base: float = 1.0,
               backoff_max: float = 8.0, on_retry: Optional[Callable] = None):
    """Create a custom retry decorator.

    Args:
        max_attempts: maximum number of attempts
        backoff_base: base wait time in seconds
        backoff_max: maximum wait time
        on_retry: optional callback(attempt, error) on each retry

    Returns decorator.
    """
    if not _HAS_TENACITY:
        def decorator(fn):
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                last_err = None
                for attempt in range(max_attempts):
                    try:
                        return fn(*args, **kwargs)
                    except Exception as e:
                        last_err = e
                        if on_retry:
                            on_retry(attempt + 1, e)
                        if attempt < max_attempts - 1:
                            wait = min(backoff_base * (2 ** attempt), backoff_max)
                            time.sleep(wait)
                raise last_err
            return wrapper
        return decorator

    def _custom_log(retry_state):
        _log_retry(retry_state)
        if on_retry and retry_state.outcome and retry_state.outcome.exception():
            on_retry(retry_state.attempt_number, retry_state.outcome.exception())

    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(multiplier=backoff_base, min=backoff_base, max=backoff_max),
        before_sleep=_custom_log,
        reraise=True,
    )


# ── Module info ─────────────────────────────────────────────────────

def status() -> dict:
    """Return availability status of resilience features."""
    return {
        "tenacity": _HAS_TENACITY,
        "structlog": _HAS_STRUCTLOG,
        "structlog_configured": _STRUCTLOG_CONFIGURED,
    }
