# Konfiguracja CoreSkill

## Pliki konfiguracyjne

### `.evo_state.json`

Główny plik stanu systemu. **Nie edytuj ręcznie** - używaj komend.

```json
{
  "api_key": "sk-or-v1-...",
  "model": "openrouter/meta-llama/llama-3.3-70b-instruct:free",
  "user_memory": {
    "directives": [
      {"id": 1, "text": "Zawsze rozmawiaj po polsku", "added": "...", "priority": "high"}
    ],
    "next_id": 2
  },
  "model_cooldowns": {
    "model-name": "2024-01-01T12:00:00"
  },
  "dead_models": ["broken-model"],
  "updated_at": "2024-01-01T12:00:00"
}
```

**Komendy zarządzania:**
- `/apikey <key>` - ustawia klucz API
- `/remember <text>` - dodaje dyrektywę
- `/forget <id>` - usuwa dyrektywę
- `/memories` - pokazuje wszystkie dyrektywy

### `config/models.json`

Konfiguracja modeli LLM.

```json
{
  "free_models": [
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/google/gemma-2-9b-it:free"
  ],
  "paid_models": [
    "openrouter/anthropic/claude-3.5-sonnet",
    "openrouter/openai/gpt-4o-mini"
  ],
  "local_preferred": [
    "qwen2.5-coder:3b",
    "gemma2:2b",
    "llama3.2:3b"
  ],
  "provider_scores": {
    "openrouter": 10,
    "ollama": 8
  },
  "speed_tiers": {
    "fast": ["gemma2:2b", "qwen2.5-coder:1.5b"],
    "balanced": ["qwen2.5-coder:3b"],
    "quality": ["llama3.3-70b:free"]
  }
}
```

## Zmienne środowiskowe

| Zmienna | Wartość | Opis |
|---------|---------|------|
| `OPENROUTER_API_KEY` | `sk-or-v1-...` | Klucz API dla tieru płatnego |
| `EVO_VERBOSE` | `1` / `0` | Włącza szczegółowe logowanie |
| `EVO_DISABLE_LOCAL` | `1` / `0` | Wyłącza modele lokalne |
| `EVO_DEFAULT_MODEL` | `model-name` | Domyślny model przy starcie |
| `OLLAMA_HOST` | `http://localhost:11434` | Host Ollama |

**Przykład użycia:**

```bash
# Tymczasowo na jedno uruchomienie
EVO_VERBOSE=1 python3 main.py

# Lub export na całą sesję
export EVO_VERBOSE=1
export OPENROUTER_API_KEY="sk-or-v1-..."
python3 main.py
```

## CLI Configuration

### `coreskill` komendy

```bash
# Status systemu
coreskill status

# Logi
coreskill logs reset          # Usuwa wszystkie logi

# Cache
coreskill cache reset         # Czyści cache Pythona
coreskill cache reset --full  # + cache w stanie

# Stan (ostrożnie!)
coreskill state reset --force # Resetuje cały stan
```

## Konfiguracja modeli

### Dodawanie modelu lokalnego

```python
# W powłoce:
/models add ollama/moj-model
```

### Zmiana domyślnego modelu

```bash
# W powłoce:
/model ollama/qwen2.5-coder:3b

# Lub w .evo_state.json:
{
  "model": "ollama/qwen2.5-coder:3b"
}
```

### Auto-tune

Automatyczny wybór najlepszego modelu:

```
/autotune
```

Testuje wszystkie dostępne modele i wybiera najszybszy/najlepszy.

## Konfiguracja skilli

### Instalacja providera

```
/providers install tts coqui
```

### Zmiana providera

```
/providers set tts espeak
```

### Status providerów

```
/providers
```

Pokazuje:
- Dostępne providery per capability
- Aktualnie używane
- Resource requirements

## Konfiguracja głosowa (TTS/STT)

### TTS (Text-to-Speech)

**Zmienne:**
```bash
export TTS_VOICE="pl"        # Język głosu
export TTS_SPEED=150         # Słowa na minutę
```

**W powłoce:**
```
/voice on    # Włącz voice mode
/voice off   # Wyłącz voice mode
```

### STT (Speech-to-Text)

**Zmienne:**
```bash
export STT_LANG="pl"         # Język rozpoznawania
export STT_DURATION=5        # Domyślny czas nagrywania (s)
```

**W powłoce:**
```
/stt         # Nagrywaj 5s
/stt 10      # Nagrywaj 10s
```

## Konfiguracja logowania

### Log levels

W `cores/v1/config.py`:

```python
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
```

### Log destinations

| Destynacja | Plik | Opis |
|------------|------|------|
| SQLite | `logs/nfo/skills.db` | Structured queryable logs |
| JSONL | `logs/nfo/skills.jsonl` | Line-delimited JSON |
| Text | `logs/*.log` | Human-readable logs |
| **Evolution** | `logs/evo/evo_journal.jsonl` | Evolution tracking |
| **Repair** | `logs/repair/repair_journal.jsonl` | Repair attempts |
| **Repair** | `logs/repair/known_fixes.json` | Proven fix patterns |

## Konfiguracja sieci

### Proxy

```bash
export HTTP_PROXY="http://proxy:8080"
export HTTPS_PROXY="http://proxy:8080"
```

### Timeouts

W `cores/v1/config.py`:

```python
REQUEST_TIMEOUT = 30  # seconds
LLM_TIMEOUT = 60      # seconds
```

## Konfiguracja bezpieczeństwa

### Shell skill

**Blocked commands** (nieodwracalne):
- `rm -rf /`
- `mkfs.*`
- `dd if=/dev/zero`

### API Keys

**Bezpieczne przechowywanie:**
```python
# W kodzie - NIE RÓB TEGO:
# api_key = "sk-or-v1-..."  # ❌

# Zamiast tego:
from cores.v1.config import load_state
state = load_state()
api_key = state.get("api_key")  # ✅
```

## Konfiguracja development

### Debug mode

```bash
# Maksymalne logowanie
EVO_VERBOSE=1 EVO_DEBUG=1 python3 main.py
```

### Hot reload

```bash
# Auto-restart przy zmianach
watchmedo auto-restart --directory=./ --pattern=*.py -- python3 main.py
```

### Testy

```bash
# Wszystkie testy
python3 -m pytest tests/

# Szybki check
python3 main.py --check

# Konkretny test
python3 -m pytest tests/test_e2e.py::TestUserMemory -v
```

## Konfiguracja Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

ENV EVO_VERBOSE=0
ENV PYTHONUNBUFFERED=1

CMD ["python3", "main.py"]
```

### docker-compose

```yaml
version: '3.8'
services:
  coreskill:
    build: .
    volumes:
      - ./.evo_state.json:/app/.evo_state.json
      - ./logs:/app/logs
    environment:
      - OPENROUTER_API_KEY=${OPENROUTER_API_KEY}
      - EVO_VERBOSE=1
```

## Troubleshooting config

### Problem: "No API key"

```bash
# Rozwiązanie 1: Ustaw env
export OPENROUTER_API_KEY="sk-or-v1-..."

# Rozwiązanie 2: W powłoce
/apikey sk-or-v1-...

# Sprawdź:
coreskill status
```

### Problem: "Model not found"

```bash
# Odśwież listę
/models refresh

# Sprawdź dostępne
/models

# Użyj innego
/model ollama/llama3.2:3b
```

### Problem: "Skill failed"

```bash
# Health check
/health

# Diagnose
/diagnose nazwa_skillu

# Fix
/fix nazwa_skillu
```

## Zaawansowana konfiguracja

### Custom intent patterns

W `intent_training.json`:

```json
{
  "examples": [
    {
      "text": "Przeczytaj mi to",
      "intent": "use:tts",
      "confidence": 0.95
    }
  ]
}
```

### Custom pipeline

```python
# W kodzie:
from cores.v1.evo_engine import EvoEngine

evo = EvoEngine(
    skill_manager=sm,
    llm_client=llm,
    custom_pipeline=[
        "validate",
        "intent",
        "execute",
        "tts"  # Auto TTS output
    ]
)
```

### Plugin system

```python
# W __init__.py skillu:
def register():
    return {
        "hooks": {
            "pre_execute": my_pre_hook,
            "post_execute": my_post_hook
        }
    }
```
