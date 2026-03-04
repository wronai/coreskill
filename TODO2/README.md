# 🧠 CoreSkill Demo — Docker Chat Interface

Interfejs demonstracyjny systemu **CoreSkill** z obsługą czatu głosowego (STT/TTS), działający jako aplikacja web i desktop, orkiestrowany przez Docker Compose.

## Szybki start

```bash
# 1. Sklonuj i uruchom
git clone <repo-url>
cd coreskill-demo
cp .env.example .env          # opcjonalnie: dodaj klucze API

# 2a. Tryb WEB — otwiera w przeglądarce
make web

# 2b. Tryb DESKTOP — otwiera jako natywne okno
make desktop
```

Otwórz **http://localhost:3000** — gotowe.

## Architektura

```
┌──────────────────────────────────────────────────┐
│                   Docker Compose                  │
│                                                   │
│  ┌─────────────┐  ┌───────────┐  ┌────────────┐ │
│  │  Frontend    │  │  Backend  │  │   Ollama   │ │
│  │  (nginx)     │→ │  (FastAPI)│→ │  (local    │ │
│  │  :3000       │  │  :8000    │  │   LLM)     │ │
│  │              │  │           │  │  :11434    │ │
│  └──────────────┘  └───────────┘  └────────────┘ │
│         ↑               ↑                         │
│    Static HTML     WebSocket +                    │
│    + JS (SPA)      REST API                       │
└───────────────────────┬──────────────────────────┘
                        │
          ┌─────────────┼─────────────┐
          │             │             │
     🌐 Browser    🖥️ Chrome     📱 Electron
     (web mode)    --app mode    (desktop)
```

## Funkcje

**Chat:**
- WebSocket real-time z automatycznym reconnect
- Markdown rendering (tabele, kod, listy)
- Historia sesji, komendy `/help`, `/skills`, `/status`

**Głos (STT/TTS) — dwukierunkowy:**
- **STT przeglądarki** → Web Speech API (Chrome/Edge, zero latency)
- **STT serwera** → faster-whisper (offline, każda przeglądarka)
- **TTS serwera** → edge-tts Microsoft Neural (wysoka jakość, PL/EN)
- **TTS przeglądarki** → Web Speech API (fallback)
- Tryb voice loop: mów → rozpoznaj → odpowiedz → czytaj na głos

**LLM — tiered fallback:**
1. **Ollama** (local, free) — qwen2.5:1.5b auto-pull
2. **OpenRouter** (remote, free tier) — gemma-2-9b
3. **Anthropic** (remote, paid) — Claude Sonnet

**Desktop:**
- Chrome `--app` mode (zero install, najszybsze)
- Electron wrapper (budowanie .AppImage/.exe/.dmg)
- Auto-start Docker jeśli nie działa

## Komendy

| Komenda | Opis |
|---------|------|
| `make up` | Start wszystkich serwisów |
| `make down` | Stop |
| `make web` | Start + otwórz przeglądarkę |
| `make desktop` | Start + otwórz jako desktop app |
| `make logs` | Podgląd logów na żywo |
| `make status` | Status serwisów + API |
| `make pull-model` | Pobierz model Ollama ręcznie |
| `make clean` | Usuń kontenery i dane |

## Konfiguracja

Skopiuj `.env.example` do `.env`:

```bash
# Opcjonalne — system działa bez kluczy (Ollama local)
OPENROUTER_API_KEY=sk-or-...
ANTHROPIC_API_KEY=sk-ant-...
```

### GPU (Ollama z NVIDIA)

```bash
# Odkomentuj sekcję ollama-gpu w docker-compose.yml lub:
docker compose --profile gpu up
```

## API Endpoints

| Endpoint | Metoda | Opis |
|----------|--------|------|
| `/health` | GET | Health check |
| `/api/status` | GET | Status systemu, providerów, capabilities |
| `/api/skills` | GET | Lista skillów |
| `/api/tts` | POST | Text-to-Speech (JSON → audio/mpeg) |
| `/api/stt` | POST | Speech-to-Text (audio file → JSON) |
| `/ws/chat` | WS | WebSocket chat (real-time) |

### Przykład TTS:

```bash
curl -X POST http://localhost:8000/api/tts \
  -H "Content-Type: application/json" \
  -d '{"text": "Witaj w CoreSkill!", "lang": "pl"}' \
  --output speech.mp3
```

### WebSocket protocol:

```json
// → Wysyłanie tekstu
{"type": "text", "content": "Cześć!", "voice_mode": true}

// → Wysyłanie audio (base64)
{"type": "audio", "audio": "<base64-wav>", "lang": "pl"}

// ← Odpowiedź tekstowa
{"type": "message", "role": "assistant", "content": "...", "provider": "ollama"}

// ← Audio TTS (gdy voice_mode=true)
{"type": "tts_audio", "audio": "<base64-mp3>", "format": "mp3"}
```

## Struktura projektu

```
coreskill-demo/
├── docker-compose.yml      # Orkiestracja serwisów
├── .env.example             # Szablon zmiennych środowiskowych
├── Makefile                 # Komendy skrótowe
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py              # FastAPI + WebSocket + STT/TTS
├── frontend/
│   ├── Dockerfile
│   ├── nginx.conf            # Proxy API + WebSocket
│   └── index.html            # Chat UI (single-page)
└── desktop/
    ├── run.sh                # Launcher (Chrome --app / Electron / fallback)
    └── electron-app/
        ├── package.json
        └── main.js           # Electron wrapper
```

## Wymagania

- **Docker** + Docker Compose v2
- ~2 GB RAM (Ollama + whisper)
- Mikrofon (dla STT)
- Chrome/Edge (dla Web Speech API; inne przeglądarki użyją server-side STT)
