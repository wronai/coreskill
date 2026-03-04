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

**BaseSkill Integration:**
- Automatic `safe_execute()` wrapper with error handling
- Manifest-driven input validation
- Type normalization for params/results

### 5. SkillForge (`cores/v1/skill_forge.py`)

**Semantic deduplication + gated creation:**
```
user_query → should_create(query, skills) → decision
```

**Decision outcomes:**
- `"reuse:<skill>"` - istniejący skill pasuje (embedding similarity > 0.85)
- `"chat"` - konwersacyjne zapytanie, LLM obsługuje bezpośrednio
- `"budget_exceeded"` - zbyt wiele błędów tworzenia (max 10/h)
- `"new_skill_needed"` - tworzymy nowy skill

**Conversational detection:**
- Patterns PL/EN: greetings, questions, short responses
- Action verb detection for short queries
- Explicit creation keywords override

### 6. BaseSkill (`cores/v1/base_skill.py`)

**Abstract base class eliminating 55% boilerplate errors:**

```python
class MySkill(BaseSkill):
    name = "my_skill"
    version = "v1"
    description = "Does something useful"

    def execute(self, params: dict) -> dict:
        # Only implement business logic
        return {"success": True, "result": ...}
```

**Auto-provided:**
- `get_info()` - metadata from class attributes
- `health_check()` - default ok status
- `safe_execute()` - error handling + type normalization
- Manifest loading for defaults/validation

**SkillManifest:**
- YAML/JSON manifest loader
- Input schema validation
- Default value injection
- Scaffold generator for LLM prompts

### 7. ProviderSelector (`cores/v1/provider_selector.py`)

**ProviderChain:**
```python
build_chain() → select_with_fallback() → record_failure/success()
```

**Auto-degradation:**
- 3 failures → demotion
- 2 successes → recovery
- Cooldown: 300s

### 8. SmartIntentClassifier (`cores/v1/smart_intent.py`)

**3-tier ML classification:**
```
Stage 1: EmbeddingEngine (sbert/TF-IDF/BOW) → confidence ≥ 0.70?
Stage 2: Local LLM (ollama, ≤3B params) → fallback
Stage 3: Remote LLM (tiered) → final fallback
```

**Features:**
- ~100+ Polish/English intent examples (DEFAULT_TRAINING)
- Learnable: `learn_from_correction()`, `learn_from_success()`
- Persisted to `intent_training.json`

### 9. QualityGate (`cores/v1/quality_gate.py`)

**5-check quality evaluation:**
| Check | Weight | Description |
|-------|--------|-------------|
| preflight | 0.30 | Syntax + imports + interface |
| health_check | 0.15 | Runtime health validation |
| test_exec | 0.30 | Isolated subprocess execution |
| output_valid | 0.15 | Output schema validation |
| code_quality | 0.10 | Lines, functions, docstrings |

**MIN_QUALITY = 0.5** threshold for registration

### 10. SkillForge (`cores/v1/skill_forge.py`)

**Semantic deduplication + gated creation:**
```
user_query → should_create(query, skills) → decision
```

**Decisions:**
- `"reuse:<skill>"` - embedding similarity > 0.85
- `"chat"` - conversational, LLM handles directly
- `"budget_exceeded"` - max 10 creation errors/hour
- `"new_skill_needed"` - create new skill

### 11. RepairJournal (`cores/v1/repair_journal.py`)

**Persistent trial database:**
- **RepairAttempt** - skill, error_signature, fix_type, result
- **KnownFix** - proven patterns with confidence ratio
- Storage: `logs/repair/repair_journal.jsonl`

**Methods:**
- `get_known_fix(error)` - find best fix by pattern
- `ask_llm_and_try(skill, error)` - full repair cycle
- `record_attempt()` - learns from successes/failures

### 12. StableSnapshot (`cores/v1/stable_snapshot.py`)

**Version management:**
```
stable/     - SACRED known-good version
latest/     - current working
branches/   - bugfix_*, feature_*
archive/    - old versions (max 2)
```

**Operations:**
- `save_as_stable()` - promote current → stable
- `create_branch()` - branch from stable
- `promote_branch()` - branch → stable
- `restore_stable()` - rollback latest to stable

### 13. SelfReflection (`cores/v1/self_reflection.py`)

**Auto-diagnostic triggers:**
- Skill failure or timeout (>30s)
- 3 consecutive failures (any skill)
- Manual `/reflect` command

**Checks:**
- LLM availability, system commands, microphone, TTS
- Disk space, vosk model, skills health
- LLM analysis + `attempt_auto_fix()`

### 14. AdaptiveResourceMonitor (`cores/v1/adaptive_monitor.py`)

**EWMATracker (alpha=0.3, 60-sample window):**
- CPU/RAM/disk sampling (5s interval)
- `pressure_score()` 0.0-1.0
- Trend detection: rising/falling/stable
- Alert thresholds with hysteresis

### 15. ProactiveScheduler (`cores/v1/proactive_scheduler.py`)

**Default tasks:**
- `resource_alerts` - every 30s
- `periodic_gc` - every 3600s
- `health_check` - every 300s

### 16. UCB1BanditSelector (`cores/v1/bandit_selector.py`)

**Provider selection:**
```
UCB1 = mean_reward * 0.6 + exploration * 0.3 + base_score * 0.1
C = 1.41 (sqrt(2)), MIN_PULLS = 2
```

### 17. Resilience (`cores/v1/resilience.py`)

**Retry decorators:**
- `retry_llm` - 3 attempts, exp backoff 1-8s
- `retry_skill` - 2 attempts, 0.5s
- `retry_io` - 3 attempts, 0.5-2s

**Structured logging:**
- `configure_structlog()` with ISO timestamps
- `get_struct_logger(name)` - structlog or stdlib fallback

### 18. I18n (`cores/v1/i18n.py`)

**Multilingual support (~35 European languages):**
- Keyword database: TTS, STT, voice, search, shell, create, evolve, greetings, etc.
- `normalize_diacritics()` - Unicode NFD + special cases (ł, đ, ð, þ, ß, æ, œ, ø, ı)
- `detect_language()` - heuristic detection
- `match_any_keyword()` - smart matching with word-boundary for short keywords

**Used by:**
- SkillForge (conversational detection)
- IntentEngine (keyword prefilter)
- SmartIntentClassifier (multilingual embeddings)

### 19. SkillLogger (`cores/v1/skill_logger.py`)

**NFO logging for all skills:**
- `init_nfo()` - configures SQLite + JSONL sinks
- `inject_logging()` - auto-wraps skill functions
- `query_skill_errors()` - query recent errors
- `query_slow_calls()` - find performance anomalies

### 20. VoiceLoop (`cores/v1/voice_loop.py`)

**Voice mode handling:**
- STT/TTS bidirectional conversation
- 3-consecutive-silence auto-diagnosis
- Integration with STTAutotest pipeline

### 21. FuzzyRouter (`cores/v1/fuzzy_router.py`)

**Fuzzy command routing:**
- Approximate matching for user commands
- Typo tolerance
- Similarity-based skill suggestion

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
