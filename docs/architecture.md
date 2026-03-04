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

### ResourceMonitor + AdaptiveResourceMonitor (`cores/v1/resource_monitor.py`, `cores/v1/adaptive_monitor.py`)

**ResourceMonitor** — statyczne sprawdzanie zasobów:
- GPU/RAM/CPU/Disk detection
- Sprawdzanie wymagań modeli ML
- Dostępność pakietów Python

**AdaptiveResourceMonitor** — dynamiczny monitoring (Sprint 4):
- EWMA tracker (alpha=0.3, 60-sample window)
- Background thread (5s interval)
- `pressure_score()` 0.0-1.0 (CPU 0.3, RAM 0.5, disk 0.2)
- Alert thresholds z hysteresis (CPU 85%/95%, RAM 80%/90%)
- Trend detection (rising/falling/stable)

### ProactiveScheduler (`cores/v1/proactive_scheduler.py`)

Task scheduling bez zewnętrznych zależności:
- Register/unregister/enable/disable tasks
- Domyślne zadania: resource_alerts (30s), periodic_gc (3600s), health_check (300s)
- 1s tick loop, error handling per task

## Autonomia i samonaprawa

### SelfReflection (`cores/v1/self_reflection.py`)

Autonomiczny system diagnostyczny:
- Aktywacja: skill failure, timeout (>30s), 3 consecutive failures
- **ReflectionEvent** — anomalie (skill_fail, timeout, stall)
- **DiagnosisReport** — findings, recommendations, auto_fixable
- `record_skill_outcome()` — tracking per skill, auto-trigger po 3 failach
- `run_diagnostic()` — 7 checks + LLM analysis
- `attempt_auto_fix()` — apt install + AutoRepair

### FailureTracker (`cores/v1/evo_engine.py`)

Global tracking cross-skill:
- THRESHOLD = 3 (consecutive failures OR unhandled events)
- `record_failure()`, `record_unhandled()`, `record_success()`
- `_run_auto_reflection()` — full diagnostic + auto-fix cycle

### AutoRepair + RepairJournal (`cores/v1/auto_repair.py`, `cores/v1/repair_journal.py`)

**AutoRepair** — 5-phase loop:
```
DIAGNOSE → PLAN → FIX → VERIFY → REFLECT
```
Strategie: strip_markdown, auto_fix_imports, add_interface, pip_install, rewrite_from_backup

**RepairJournal** — uczenie się z napraw:
- Storage: `logs/repair/repair_journal.jsonl`, `logs/repair/known_fixes.json`
- `record_attempt()`, `get_known_fix()`, `ask_llm_and_try()`
- KnownFix z confidence score (success/total ratio)

### StableSnapshot (`cores/v1/stable_snapshot.py`)

Wersjonowanie skilli:
```
skills/{cap}/providers/{prov}/
  stable/     — SACRED known-good
  latest/     — current working
  branches/bugfix_*/feature_* — eksperymenty
  archive/    — stare wersje
```
- `save_as_stable()`, `create_branch()`, `promote_branch()`, `restore_stable()`

### EvolutionJournal (`cores/v1/evo_journal.py`)

Tracking ewolucji:
- Storage: `logs/evo/evo_journal.jsonl`, `logs/evo/evo_journal_summary.json`
- `start_evolution()`, `finish_evolution()`, `reflect()`
- Cross-iteration learning — consult history dla avoid-patterns
- Quality scoring per iteration

## Provider System

### ProviderSelector + ProviderChain (`cores/v1/provider_selector.py`)

**ProviderSelector** — wybór providera na podstawie:
- ResourceMonitor.can_run(requirements)
- Scoring: quality*10 + tier*5, speed bonus (lite=30)
- Context: prefer_fast, prefer_quality, offline

**ProviderChain** (Sprint 2) — fallback chain:
- `build_chain()`, `select_with_fallback()`
- Auto-degradation: 3 failures → demotion, 2 successes → recovery
- Cooldown: 300s, FAILURE_THRESHOLD=3, SUCCESS_RECOVERY=2

### UCB1BanditSelector (`cores/v1/bandit_selector.py`)

ML-based provider selection (Sprint 4):
- UCB1 = mean_reward*0.6 + exploration*0.3 + base_score*0.1
- C=1.41 (sqrt(2)), MIN_PULLS=2 per arm
- `select(capability, providers, base_scores)`
- `record(capability, provider, reward, success)`

## Resilience & Logging

### Resilience Module (`cores/v1/resilience.py`)

Retry decorators z `tenacity`:
- `retry_llm()` — 3 attempts, exp backoff 1-8s
- `retry_skill()` — 2 attempts, 0.5s
- `retry_io()` — 3 attempts, 0.5-2s
- `with_retry()` — custom decorator
- Fallback no-op gdy tenacity missing

### Structured Logging (`cores/v1/resilience.py`)

`structlog` integration:
- `configure_structlog()` — ISO timestamps, console renderer
- `get_struct_logger()` — structlog lub stdlib fallback
- `_log_retry()` — hooks tenacity retries into structlog

### NFO Decorator Logging (`cores/v1/skill_logger.py`)

Two-layer approach:
1. Explicit `@nfo.logged` / `@nfo.log_call` na bootstrap skills
2. Auto-injection via `inject_logging(mod)` dla LLM-generated skills

Captured: function_name, args/kwargs, return_value, exception, duration_ms, traceback

## Skalowalność

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
