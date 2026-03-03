#!/usr/bin/env python3
"""
evo-engine utils — code/json cleaning, rich markdown printing.
"""
import os
import sys
import subprocess
import warnings
import builtins
import logging

# ─── Suppress ALL noisy output BEFORE any imports ───────────────────
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*[Pp]ydantic.*")
os.environ["LITELLM_LOG"] = "ERROR"
os.environ["LITELLM_SUPPRESS_DEBUG_INFO"] = "1"

# Monkey-patch print() BEFORE litellm import (litellm captures ref at import)
_real_print = builtins.print
_SPAM = ("Provider List", "Give Feedback", "LiteLLM.Info", "litellm._turn_on_debug",
         "LiteLLM completion()", "litellm.completion")
def _quiet_print(*a, **kw):
    msg = " ".join(str(x) for x in a)
    if any(s in msg for s in _SPAM):
        return
    _real_print(*a, **kw)
builtins.print = _quiet_print

# Suppress pydantic warnings (they go through warnings.warn → stderr)
_orig_showwarning = warnings.showwarning
def _quiet_warning(msg, cat, *a, **kw):
    s = str(msg)
    if "pydantic" in s.lower() or "Pydantic" in s or "serializer" in s.lower():
        return
    _orig_showwarning(msg, cat, *a, **kw)
warnings.showwarning = _quiet_warning

for _ln in ("LiteLLM", "LiteLLM Proxy", "LiteLLM Router", "litellm",
            "httpx", "httpcore", "openai", "urllib3"):
    logging.getLogger(_ln).setLevel(logging.CRITICAL)


def setup_litellm():
    import litellm
    litellm.drop_params = True
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
    try: litellm._logging._disable_debugging()
    except: pass
    return litellm

try:
    litellm = setup_litellm()
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "litellm", "-q",
                           "--break-system-packages"])
    litellm = setup_litellm()


# ─── Rich Markdown terminal rendering ────────────────────────────────
try:
    from rich.console import Console
    from rich.markdown import Markdown as RichMarkdown
    from rich.theme import Theme
    _rich_theme = Theme({"info": "dim cyan", "warning": "yellow", "error": "bold red"})
    _console = Console(theme=_rich_theme, highlight=False)
    def mprint(text, style=None):
        """Print rich-rendered markdown to terminal."""
        if not text: return
        try:
            _console.print(RichMarkdown(text), style=style)
        except:
            print(text)
    HAS_RICH = True
except ImportError:
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "rich", "-q",
                               "--break-system-packages"])
        from rich.console import Console
        from rich.markdown import Markdown as RichMarkdown
        _console = Console(highlight=False)
        def mprint(text, style=None):
            if not text: return
            try: _console.print(RichMarkdown(text), style=style)
            except: print(text)
        HAS_RICH = True
    except:
        def mprint(text, style=None): print(text)
        HAS_RICH = False


# ─── Code/JSON cleaning ──────────────────────────────────────────────
def clean_code(code):
    """Remove markdown fences from code."""
    if not code: return ""
    code = code.strip()
    if code.startswith("```"):
        lines = code.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        code = "\n".join(lines[1:end])
    return code

def clean_json(text):
    """Extract JSON from potential markdown wrapping."""
    if not text: return "{}"
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        end = -1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[1:end])
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        return text[start:end]
    return text

# Backward compat aliases
_clean = clean_code
_clean_json = clean_json
