# Architektura CoreSkill

## Przegląd systemu

CoreSkill to ewolucyjny system AI oparty na architekturze "text2pipeline" z samonaprawialnymi skillemi.

## Diagram architektury

```
┌─────────────────────────────────────────────────────────────┐
│                        Użytkownik                          │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Interfejs (CLI/API)                     │
│         main.py → cli.py → COMMANDS dispatch               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   IntentEngine (ML-based)                  │
│  SmartIntentClassifier: embedding → local LLM → remote LLM │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                    EvoEngine (Pipeline)                    │
│  _execute_with_validation → skill exec → validation → fix │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                   SkillManager + ProviderSelector            │
│  ProviderChain: stable → latest → fallback providers       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                     Skille (skills/)                         │
│  tts/  stt/  shell/  git_ops/  web_search/  [evolvable]    │
└─────────────────────────────────────────────────────────────┘
```

## Główne komponenty

### 1. LLMClient (`cores/v1/llm_client.py`)

**Tiered LLM Routing:**
- **TIER_FREE** (OpenRouter :free) - darmowe modele
- **TIER_LOCAL** (Ollama) - lokalne modele
- **TIER_PAID** (OpenRouter paid) - płatne modele

**Funkcje:**
- Automatyczny fallback między tierami
- Cooldown dla rate-limited modeli (60s)
- Blacklist dla modeli z błędami 404/auth
- Auto-discovery lokalnych modeli Ollama

### 2. IntentEngine (`cores/v1/intent_engine.py`)

**Multi-stage ML classification:**
```
Stage 0: Trivial filter (puste, exit, help)
   ↓
Stage 1: SmartIntentClassifier
   ├─ EmbeddingEngine (sbert/TF-IDF/BOW)
   ├─ Local LLM (ollama, ≤3B params)
   └─ Remote LLM (fallback)
   ↓
Stage 2: Context inference
```

### 3. EvoEngine (`cores/v1/evo_engine.py`)

**Pipeline execution z walidacją:**
```
execute → validate → (fail → reflect → fix → retry)
```

**Result validation:**
- `success` - skill działa poprawnie
- `partial` - częściowy sukces (np. pusty STT)
- `fail` - błąd wymagający naprawy

### 4. SkillManager (`cores/v1/skill_manager.py`)

**Skill lifecycle:**
```
load → preflight check → execute → validate → evolve
```

**Preflight checks:**
- Syntax validation
- Import check
- Interface compliance

### 5. ProviderSelector (`cores/v1/provider_selector.py`)

**ProviderChain:**
```python
build_chain() → select_with_fallback() → record_failure/success()
```

**Auto-degradation:**
- 3 failures → demotion
- 2 successes → recovery
- Cooldown: 300s

## Struktura skillów

### Hierarchia folderów
```
skills/
  {capability}/
    manifest.json           # Metadane capability
    providers/
      {provider}/
        stable/             # Stabilna wersja
          skill.py
          meta.json
        latest/             # Ostatnia ewolucja
          skill.py
          meta.json
        archive/            # Archiwum wersji
          v{N}/
```

### Przykład skillu
```python
#!/usr/bin/env python3
"""Skill opis"""

def get_info():
    return {
        "name": "skill_name",
        "version": "v1",
        "description": "Opis funkcji"
    }

def execute(params: dict) -> dict:
    """Wykonaj akcję skillu."""
    result = ...  # Logika biznesowa
    return {
        "success": True,
        "result": result
    }
```

## System pamięci

### UserMemory (`cores/v1/user_memory.py`)

**Storage:**
- Lokalizacja: `state["user_memory"]["directives"]`
- Format: `{id, text, added, priority}`
- Persistence: `.evo_state.json`

### Intent Training

**Plik:** `intent_training.json`

**Struktura:**
```json
{
  "embeddings": [...],
  "intents": [...],
  "examples": [...],
  "corrections": []
}
```

## Konfiguracja modeli

### `config/models.json`

```json
{
  "free_models": [...],
  "paid_models": [...],
  "local_preferred": [...],
  "provider_scores": {...},
  "speed_tiers": {...}
}
```

### Zmienne środowiskowe

| Zmienna | Opis |
|---------|------|
| `OPENROUTER_API_KEY` | Klucz API dla tieru płatnego |
| `EVO_VERBOSE` | Włącza verbose logging (1/0) |
| `EVO_DISABLE_LOCAL` | Wyłącza modele lokalne (1/0) |

## Flow przetwarzania

### 1. Intent Detection
```
User input → IntentEngine.analyze() → (action, skill, confidence)
```

### 2. Skill Execution
```
SkillManager.exec_skill() →
  preflight_check() →
  load_and_run() →
  _validate_result()
```

### 3. Error Handling
```
Validation fail →
  EvolutionGuard.detect() →
  strategy: auto_fix_imports | rewrite | evolve →
  LLM generates fix →
  smart_evolve() →
  retry
```

### 4. Logging

**NFO Decorator Logging:**
- SQLite: `logs/nfo/skills.db`
- JSONL: `logs/nfo/skills.jsonl`

**Pipeline Logging:**
```
[PIPE] Intent: use → stt | goal: transcribe_audio
[PIPE] Execute: stt v1 (attempt 1/3)
[PIPE] Validate: success
[PIPE] ✓ Goal achieved
```

## Skalowalność

### ResourceMonitor

**Monitoruje:**
- CPU/RAM/GPU/Disk
- Dostępność pakietów Python
- Wymagania modeli ML

### A/B Core Management

- Core A: stable
- Core B: experimental
- Automatic rollback na degradację

## Rozszerzalność

### Tworzenie nowego skillu

1. **Automatycznie:**
   ```
   /create moj_skill
   ```

2. **Manualnie:**
   ```bash
   mkdir -p skills/moj_skill/v1
   touch skills/moj_skill/v1/skill.py
   touch skills/moj_skill/v1/meta.json
   ```

3. **Szablon skill.py:**
   ```python
   def get_info(): return {"name": "moj_skill", "version": "v1"}
   def execute(params): return {"success": True}
   ```

## Bezpieczeństwo

### Shell Skill
- BLOCKED_COMMANDS: `rm -rf /`, `mkfs`, `dd if=/dev/zero`
- Interactive stdin passthrough dla sudo/passwd

### API Keys
- Storage: `.evo_state.json` (lokalny plik)
- Validation: automatyczna przy `/apikey`
- Masking: w logach pokazywany tylko prefix

## Debugowanie

### Komendy diagnostyczne

```bash
# Status systemu
coreskill status

# Logi
ls logs/
cat logs/nfo/skills.jsonl

# Health check
python3 main.py --check
```

### Verbose mode

```bash
EVO_VERBOSE=1 python3 main.py
```

Pokazuje:
- Wybór modelu LLM
- Pełne prompty
- Fallback reasons
- Response lengths
