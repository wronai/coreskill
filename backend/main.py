"""
CoreSkill Demo — FastAPI Backend
=================================
WebSocket chat server with STT/TTS capabilities.
Supports: Ollama (local), OpenRouter, Anthropic as LLM backends.
TTS via edge-tts (Microsoft free), STT via faster-whisper (local).
"""

import asyncio
import base64
import io
import json
import logging
import os
import tempfile
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

try:
    from dotenv import load_dotenv  # type: ignore
except Exception:
    load_dotenv = None

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
_ROOT_DIR = Path(__file__).resolve().parents[1]
if load_dotenv is not None:
    load_dotenv(_ROOT_DIR / ".env", override=False)
    load_dotenv(override=False)


def _read_state() -> dict:
    for p in (_ROOT_DIR / ".evo_state.json", Path.cwd() / ".evo_state.json", Path("/app/.evo_state.json")):
        try:
            if p.exists():
                return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
    return {}


_STATE = _read_state()


def _get_key(*names: str, state_key: str) -> str:
    for n in names:
        v = os.getenv(n, "").strip()
        if v:
            return v
    v = (_STATE.get(state_key) or "").strip()
    if v:
        return v
    return ""


OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://ollama:11434")
OPENROUTER_KEY = _get_key("OPENROUTER_API_KEY", "OPENROUTERAPIKEY", state_key="openrouter_api_key")
ANTHROPIC_KEY = _get_key("ANTHROPIC_API_KEY", "ANTHROPICAPIKEY", state_key="anthropic_api_key")
DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(parents=True, exist_ok=True)
CHAT_LOG_FILE = DATA_DIR / "chat_history.jsonl"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("coreskill")

# ---------------------------------------------------------------------------
# CoreSkill Integration (after logging setup)
# ---------------------------------------------------------------------------
import sys
_CORESKILL_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_CORESKILL_ROOT))

# Initialize flag BEFORE try block to avoid UnboundLocalError
CORESKILL_AVAILABLE = False
skill_manager = None
evo_engine = None
intent_engine = None

# Import CoreSkill components
try:
    from cores.v1.skill_manager import SkillManager
    from cores.v1.evo_engine import EvoEngine
    from cores.v1.intent_engine import IntentEngine
    from cores.v1.logger import Logger
    from cores.v1.llm_client import LLMClient as CoreLLMClient
    from cores.v1.config import DEFAULT_MODEL
    CORESKILL_AVAILABLE = True
    log.info("CoreSkill modules loaded successfully")
except Exception as e:
    CORESKILL_AVAILABLE = False
    log.warning(f"CoreSkill modules not available: {e}")

# Debug: log env state (without exposing full keys)
log.info(f"OLLAMA_HOST={OLLAMA_HOST}")
log.info(f"OPENROUTER_KEY set: {bool(OPENROUTER_KEY)} (len={len(OPENROUTER_KEY)})")
log.info(f"ANTHROPIC_KEY set: {bool(ANTHROPIC_KEY)} (len={len(ANTHROPIC_KEY)})")

# ---------------------------------------------------------------------------
# Globals
# ---------------------------------------------------------------------------
whisper_model = None
active_connections: dict[str, WebSocket] = {}
chat_histories: dict[str, list] = {}

SYSTEM_PROMPT = """Jesteś CoreSkill Demo — asystentem AI z obsługą głosową STT/TTS.
Możliwości:
- 💬 Chat z odpowiedziami LLM (OpenRouter/Ollama)
- 🔊 Text-to-Speech (edge-tts)
- 🎤 Speech-to-Text (faster-whisper)

Zasady:
- Odpowiadaj ZWIĘŹLE (2-4 zdania max)
- Nie wymyślaj funkcji których nie masz
- Nie pisz tabel markdown ani formatowania ASCII
- Po polsku (chyba że user pisze po angielsku)

DOSTĘPNE KOMENDY:
/help - lista komend
/status - status systemu
/skills - lista skillów demo
/clear - wyczyść historię
"""


# ---------------------------------------------------------------------------
# LLM Client — multi-provider with fallback
# ---------------------------------------------------------------------------
class LLMClient:
    """Tiered LLM: Ollama (local free) → OpenRouter (remote free) → Anthropic (paid)."""

    def __init__(self):
        self.http = httpx.AsyncClient(timeout=60.0)
        self.active_provider = None

    async def close(self):
        await self.http.aclose()

    async def llm_chat(self, messages: list[dict], model: str = "auto") -> str:
        """Send chat request with automatic provider fallback."""
        log.info(f"[LLM] Starting chat with {len(messages)} messages")
        
        # Tier 1: OpenRouter (primary - matches .evo_state.json config)
        log.info(f"[LLM] Trying OpenRouter... (key present: {bool(OPENROUTER_KEY)})")
        if OPENROUTER_KEY:
            result = await self._try_openrouter(messages)
            log.info(f"[LLM] OpenRouter result: {'success' if result else 'failed/no response'}")
            if result:
                self.active_provider = "openrouter"
                return result
        else:
            log.warning("[LLM] OPENROUTER_KEY not set, skipping OpenRouter")

        # Tier 2: Ollama (local fallback)
        log.info("[LLM] Trying Ollama (fallback)...")
        result = await self._try_ollama(messages)
        log.info(f"[LLM] Ollama result: {'success' if result else 'failed/no response'}")
        if result:
            self.active_provider = "ollama"
            return result

        # Tier 3: Anthropic (paid)
        log.info(f"[LLM] Trying Anthropic... (key present: {bool(ANTHROPIC_KEY)})")
        if ANTHROPIC_KEY:
            result = await self._try_anthropic(messages)
            log.info(f"[LLM] Anthropic result: {'success' if result else 'failed/no response'}")
            if result:
                self.active_provider = "anthropic"
                return result
        else:
            log.warning("[LLM] ANTHROPIC_KEY not set, skipping Anthropic")

        self.active_provider = "echo"
        log.warning("[LLM] All providers failed, using echo mode")
        return self._echo_response(messages)

    async def _try_ollama(self, messages: list[dict]) -> Optional[str]:
        """Try Ollama with qwen2.5:1.5b (available model)."""
        try:
            resp = await self.http.post(
                f"{OLLAMA_HOST}/api/chat",
                json={"model": "qwen2.5:1.5b", "messages": messages, "stream": False},
                timeout=90.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data.get("message", {}).get("content", "")
            else:
                log.warning(f"Ollama HTTP {resp.status_code}: {resp.text[:100]}")
        except httpx.TimeoutException:
            log.warning("Ollama timeout after 90s")
        except Exception as e:
            log.warning(f"Ollama error: {e}")
        return None

    async def _try_openrouter(self, messages: list[dict]) -> Optional[str]:
        """Try OpenRouter with model from .evo_state.json or default."""
        # Get model from state file (format: "openrouter/namespace/model")
        raw_model = _STATE.get("model", "")
        if raw_model and raw_model.startswith("openrouter/"):
            model = raw_model.replace("openrouter/", "", 1)
        else:
            model = "meta-llama/llama-3.3-70b-instruct:free"
        
        # Try configured model first, then fallback to known free model
        for try_model in [model, "meta-llama/llama-3.3-70b-instruct:free"]:
            log.info(f"[OpenRouter] Trying model: {try_model}")
            try:
                resp = await self.http.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={"model": try_model, "messages": messages},
                    timeout=30.0,
                )
                if resp.status_code == 200:
                    return resp.json()["choices"][0]["message"]["content"]
                else:
                    log.warning(f"OpenRouter HTTP {resp.status_code} for {try_model}: {resp.text[:100]}")
            except Exception as e:
                log.warning(f"OpenRouter error for {try_model}: {e}")
        return None

    async def _try_anthropic(self, messages: list[dict]) -> Optional[str]:
        try:
            # Convert to Anthropic format
            system_msg = ""
            user_msgs = []
            for m in messages:
                if m["role"] == "system":
                    system_msg = m["content"]
                else:
                    user_msgs.append(m)

            resp = await self.http.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 1024,
                    "system": system_msg,
                    "messages": user_msgs,
                },
                timeout=30.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return data["content"][0]["text"]
        except Exception as e:
            log.warning(f"Anthropic error: {e}")
        return None

    def _echo_response(self, messages: list[dict]) -> str:
        last = messages[-1]["content"] if messages else ""
        return (
            f"🔄 **Tryb echo** — brak dostępnego LLM.\n\n"
            f"Twoja wiadomość: _{last}_\n\n"
            f"Aby aktywować pełne odpowiedzi:\n"
            f"1. Ustaw `OPENROUTER_API_KEY` w `.env` (lub w env kontenera)\n"
            f"2. Albo wpisz klucz do `.evo_state.json` jako `openrouter_api_key`\n"
            f"3. Lub ustaw `ANTHROPIC_API_KEY` w `.env`\n"
            f"4. Dla lokalnego fallback: uruchom/pobierz model Ollama (np. `phi3:mini`)"
        )

    async def get_status(self) -> dict:
        providers = {}
        # Check Ollama
        try:
            r = await self.http.get(f"{OLLAMA_HOST}/api/tags", timeout=5.0)
            models = [m["name"] for m in r.json().get("models", [])] if r.status_code == 200 else []
            providers["ollama"] = {"status": "ok" if models else "no_models", "models": models}
        except Exception:
            providers["ollama"] = {"status": "offline"}

        providers["openrouter"] = {"status": "configured" if OPENROUTER_KEY else "not_configured"}
        providers["anthropic"] = {"status": "configured" if ANTHROPIC_KEY else "not_configured"}
        return {"providers": providers, "active": self.active_provider}


# ---------------------------------------------------------------------------
# TTS — edge-tts (Microsoft free, high quality)
# ---------------------------------------------------------------------------
class TTSEngine:
    VOICES = {
        "pl": "pl-PL-MarekNeural",
        "pl-f": "pl-PL-ZofiaNeural",
        "en": "en-US-GuyNeural",
        "en-f": "en-US-JennyNeural",
    }

    async def synthesize(self, text: str, lang: str = "pl", voice_key: str = None) -> bytes:
        import edge_tts
        voice = self.VOICES.get(voice_key or lang, self.VOICES["pl"])
        communicate = edge_tts.Communicate(text, voice)
        buf = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                buf.write(chunk["data"])
        buf.seek(0)
        return buf.read()


# ---------------------------------------------------------------------------
# STT — faster-whisper (local, runs on CPU)
# ---------------------------------------------------------------------------
class STTEngine:
    def __init__(self):
        self.model = None

    def _ensure_model(self):
        if self.model is None:
            try:
                from faster_whisper import WhisperModel
                self.model = WhisperModel("tiny", device="cpu", compute_type="int8")
                log.info("Whisper model loaded (tiny/int8)")
            except Exception as e:
                log.error(f"Cannot load whisper: {e}")

    async def transcribe(self, audio_bytes: bytes, lang: str = "pl") -> str:
        self._ensure_model()
        if not self.model:
            return "[STT niedostępne — brak modelu whisper]"

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            f.flush()
            tmp_path = f.name

        try:
            segments, _ = self.model.transcribe(tmp_path, language=lang)
            return " ".join(s.text for s in segments).strip()
        finally:
            Path(tmp_path).unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Skill demos — showcase CoreSkill capabilities
# ---------------------------------------------------------------------------
DEMO_SKILLS = {
    "system_info": {
        "name": "System Info",
        "description": "Informacje o systemie",
        "icon": "💻",
    },
    "benchmark": {
        "name": "LLM Benchmark",
        "description": "Test wydajności modeli",
        "icon": "📊",
    },
    "web_search": {
        "name": "Web Search",
        "description": "Wyszukiwanie DuckDuckGo",
        "icon": "🔍",
    },
    "task_manager": {
        "name": "Task Manager",
        "description": "Zarządzanie zadaniami",
        "icon": "📋",
    },
    "file_manager": {
        "name": "File Manager",
        "description": "Operacje na plikach",
        "icon": "📁",
    },
    "shell": {
        "name": "Shell",
        "description": "Wykonywanie komend",
        "icon": "🖥️",
    },
    "stt": {
        "name": "Speech-to-Text",
        "description": "Rozpoznawanie mowy (Vosk/Whisper)",
        "icon": "🎤",
    },
    "tts": {
        "name": "Text-to-Speech",
        "description": "Synteza mowy (Piper/edge-tts)",
        "icon": "🔊",
    },
    "auto_repair": {
        "name": "Auto Repair",
        "description": "Samonaprawa skillów",
        "icon": "🔧",
    },
    "evo_engine": {
        "name": "Evo Engine",
        "description": "Ewolucja i tworzenie skillów",
        "icon": "🧬",
    },
}


# ---------------------------------------------------------------------------
# App lifecycle
# ---------------------------------------------------------------------------
llm = LLMClient()
tts = TTSEngine()
stt = STTEngine()


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("CoreSkill Demo starting...")
    # Initialize CoreSkill
    await _init_coreskill()
    # Try to pull a small model on startup
    # asyncio.create_task(_pull_ollama_model())  # TODO: implement this function
    yield
    await llm.close()
    log.info("CoreSkill Demo shutdown.")


async def _init_coreskill():
    """Initialize CoreSkill components for skill execution."""
    global CORESKILL_AVAILABLE, skill_manager, evo_engine, intent_engine
    if not CORESKILL_AVAILABLE:
        log.warning("CoreSkill not available, skipping initialization")
        return
    
    try:
        logger = Logger("chat_backend")

        model = _STATE.get("model") or DEFAULT_MODEL
        core_llm = CoreLLMClient(api_key=OPENROUTER_KEY, model=model, logger=logger)

        # SkillManager signature: (llm, logger, provider_selector=None)
        skill_manager = SkillManager(core_llm, logger)

        # IntentEngine signature: (llm, logger, state)
        intent_state = dict(_STATE) if isinstance(_STATE, dict) else {}
        intent_engine = IntentEngine(core_llm, logger, intent_state)

        # EvoEngine signature: (sm, llm, logger, provider_chain=None, state=None)
        evo_engine = EvoEngine(skill_manager, core_llm, logger, state=intent_state)

        log.info(f"CoreSkill initialized: {len(skill_manager.list_skills())} skills available")
    except Exception as e:
        log.error(f"Failed to initialize CoreSkill: {e}")
        CORESKILL_AVAILABLE = False


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(
    title="CoreSkill Demo",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# REST endpoints
# ---------------------------------------------------------------------------
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/status")
async def status():
    llm_status = await llm.get_status()
    return {
        "system": "CoreSkill Demo v2.0",
        "uptime": time.monotonic(),
        "skills_count": len(DEMO_SKILLS),
        "llm": llm_status,
        "capabilities": {
            "stt": True,
            "tts": True,
            "voice_loop": True,
            "intent_classification": True,
            "self_healing": True,
            "skill_evolution": True,
        },
    }


@app.get("/api/diagnose")
async def diagnose():
    """Run diagnostics on LLM connectivity."""
    results = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "env": {
            "OLLAMA_HOST": OLLAMA_HOST,
            "OPENROUTER_KEY_SET": bool(OPENROUTER_KEY),
            "ANTHROPIC_KEY_SET": bool(ANTHROPIC_KEY),
        },
        "tests": {}
    }
    
    # Test Ollama
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get(f"{OLLAMA_HOST}/api/tags")
            models = [m["name"] for m in r.json().get("models", [])] if r.status_code == 200 else []
            results["tests"]["ollama"] = {"status": "ok" if models else "no_models", "models": models}
    except Exception as e:
        results["tests"]["ollama"] = {"status": "error", "error": str(e)}
    
    # Test OpenRouter (simple request)
    if OPENROUTER_KEY:
        try:
            async with httpx.AsyncClient(timeout=10.0) as c:
                r = await c.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
                    json={"model": "meta-llama/llama-3.3-70b-instruct:free", "messages": [{"role": "user", "content": "Hi"}]},
                )
                results["tests"]["openrouter"] = {"status": "ok" if r.status_code == 200 else f"http_{r.status_code}"}
        except Exception as e:
            results["tests"]["openrouter"] = {"status": "error", "error": str(e)}
    else:
        results["tests"]["openrouter"] = {"status": "skipped", "reason": "no_key"}
    
    return results


class TTSRequest(BaseModel):
    text: str
    lang: str = "pl"
    voice: Optional[str] = None


@app.post("/api/tts")
async def tts_endpoint(req: TTSRequest):
    """Synthesize speech from text. Returns audio/mpeg."""
    try:
        audio = await tts.synthesize(req.text, req.lang, req.voice)
        return StreamingResponse(io.BytesIO(audio), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(500, f"TTS error: {e}")


@app.post("/api/stt")
async def stt_endpoint(audio: UploadFile = File(...), lang: str = "pl"):
    """Transcribe audio file. Returns text."""
    try:
        data = await audio.read()
        text = await stt.transcribe(data, lang)
        return {"text": text, "lang": lang}
    except Exception as e:
        raise HTTPException(500, f"STT error: {e}")


# ---------------------------------------------------------------------------
# WebSocket chat
# ---------------------------------------------------------------------------
@app.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    session_id = str(uuid.uuid4())[:8]
    active_connections[session_id] = ws
    chat_histories[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]

    log.info(f"[{session_id}] Client connected")

    # Send welcome
    await ws.send_json({
        "type": "system",
        "content": f"Połączono z CoreSkill Demo • Sesja: {session_id}",
        "session_id": session_id,
        "provider": llm.active_provider,
    })

    try:
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)

            msg_type = msg.get("type", "text")
            content = msg.get("content", "")

            # Handle audio messages (STT → LLM → TTS pipeline)
            if msg_type == "audio":
                audio_b64 = msg.get("audio", "")
                if audio_b64:
                    audio_bytes = base64.b64decode(audio_b64)
                    content = await stt.transcribe(audio_bytes, msg.get("lang", "pl"))
                    await ws.send_json({
                        "type": "stt_result",
                        "content": content,
                    })

            if not content.strip():
                continue

            # Add to history
            chat_histories[session_id].append({"role": "user", "content": content})

            # Handle special commands
            if content.startswith("/"):
                response = _handle_command(content, session_id)
            else:
                # Try CoreSkill first, then fall back to LLM
                await ws.send_json({"type": "typing", "content": True})
                
                skill_used, skill_result = await _execute_skill_for_chat(content)
                
                if skill_used:
                    # Skill executed successfully - use its result
                    log.info(f"[{session_id}] Skill result: {skill_result[:50]}...")
                    # Add skill result to context and let LLM summarize it
                    chat_histories[session_id].append({
                        "role": "system", 
                        "content": f"Wykonano skill. Wynik: {skill_result}\nPodsumuj krótko po polsku."
                    })
                    response = await llm.llm_chat(chat_histories[session_id])
                    # Remove the system message after getting response
                    chat_histories[session_id].pop()
                else:
                    # No skill matched - use LLM directly
                    log.info(f"[{session_id}] Sending to LLM: {content[:50]}...")
                    response = await llm.llm_chat(chat_histories[session_id])
                
                log.info(f"[{session_id}] Response ({llm.active_provider}): {response[:50]}...")
                
            # Log chat to file
            chat_log_entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": session_id,
                "provider": llm.active_provider,
                "user": content,
                "assistant": response,
            }
            with open(CHAT_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(chat_log_entry, ensure_ascii=False) + "\n")

            chat_histories[session_id].append({"role": "assistant", "content": response})

            await ws.send_json({
                "type": "message",
                "role": "assistant",
                "content": response,
                "provider": llm.active_provider,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # If voice mode — also send TTS
            if msg.get("voice_mode"):
                try:
                    # Strip markdown for cleaner TTS
                    clean_text = response.replace("**", "").replace("*", "").replace("`", "")
                    audio = await tts.synthesize(clean_text[:500], msg.get("lang", "pl"))
                    audio_b64 = base64.b64encode(audio).decode()
                    await ws.send_json({
                        "type": "tts_audio",
                        "audio": audio_b64,
                        "format": "mp3",
                    })
                except Exception as e:
                    log.warning(f"TTS failed: {e}")

    except WebSocketDisconnect:
        log.info(f"[{session_id}] Client disconnected")
    except Exception as e:
        log.error(f"[{session_id}] Error: {e}")
    finally:
        active_connections.pop(session_id, None)
        chat_histories.pop(session_id, None)


async def _execute_skill_for_chat(user_msg: str) -> tuple[bool, str]:
    """Check intent and execute skill if needed. Returns (skill_used, result)."""
    if not CORESKILL_AVAILABLE or skill_manager is None or intent_engine is None:
        return False, ""
    
    try:
        # Get available skills
        skills = skill_manager.list_skills()

        # Check intent (returns analysis dict)
        analysis = intent_engine.analyze(user_msg, skills, conv=None)
        action = (analysis or {}).get("action", "chat")
        skill_name = (analysis or {}).get("skill", "")
        conf = (analysis or {}).get("_conf", 0.0)

        log.info(f"[Intent] action={action}, skill={skill_name}, confidence={conf}")
        
        # If chat intent, let LLM handle it
        if action == "chat" or not skill_name:
            return False, ""
        
        # Execute skill via EvoEngine
        if evo_engine:
            outcome = evo_engine.handle_request(user_msg, skills, analysis=analysis)
            if outcome and outcome.get("type") == "success":
                result = outcome.get("result", {})
                result_data = result.get("result", "") if isinstance(result, dict) else str(result)
                log.info(f"[Skill] {skill_name} executed successfully")
                return True, f"[{skill_name}] {result_data}"
            else:
                error = outcome.get("message", "unknown error") if outcome else "no outcome"
                log.warning(f"[Skill] {skill_name} failed: {error}")
                return False, ""
        
        # Fallback: direct skill execution
        if skill_name in skills:
            result = skill_manager.exec_skill(skill_name, inp={"text": user_msg})
            if result.get("success"):
                result_data = result.get("result", "")
                log.info(f"[Skill] {skill_name} executed (direct)")
                return True, f"[{skill_name}] {result_data}"
    except Exception as e:
        log.warning(f"[Skill] Execution error: {e}")
    
    return False, ""


def _handle_command(cmd: str, session_id: str) -> str:
    parts = cmd.strip().split()
    command = parts[0].lower()

    if command == "/help":
        return (
            "## 🛠️ Dostępne komendy\n\n"
            "| Komenda | Opis |\n"
            "|---------|------|\n"
            "| `/help` | Ta lista |\n"
            "| `/skills` | Lista skillów |\n"
            "| `/status` | Status systemu |\n"
            "| `/voice on/off` | Tryb głosowy |\n"
            "| `/models` | Dostępne modele LLM |\n"
            "| `/clear` | Wyczyść historię |\n"
            "| `/demo <skill>` | Demo skilla |\n"
        )
    elif command == "/skills":
        lines = ["## 🧩 Zainstalowane skille\n"]
        for sid, info in DEMO_SKILLS.items():
            lines.append(f"- {info['icon']} **{info['name']}** — {info['description']}")
        return "\n".join(lines)
    elif command == "/status":
        return (
            "## 📊 Status systemu\n\n"
            f"- **Wersja**: CoreSkill Demo v2.0\n"
            f"- **Skille**: {len(DEMO_SKILLS)} zainstalowanych\n"
            f"- **LLM Provider**: {llm.active_provider or 'auto-detecting'}\n"
            f"- **STT**: faster-whisper (tiny/int8)\n"
            f"- **TTS**: edge-tts (Microsoft Neural)\n"
            f"- **Sesja**: {session_id}\n"
        )
    elif command == "/clear":
        chat_histories[session_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
        return "🗑️ Historia wyczyszczona."
    else:
        return f"Nieznana komenda: `{command}`. Wpisz `/help` po listę."
