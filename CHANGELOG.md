## [2.0.0] - 2026-03-04

### Summary

Major release: full modular architecture with 40+ core modules, ML-based intent classification,
self-healing pipeline, adaptive resource monitoring, and 258 tests.

### Architecture — Core Split

- refactor: Split monolithic `core.py` (1783 lines) into 40+ focused modules in `cores/v1/`
- feat: Thin `core.py` with dispatch table pattern (COMMANDS dict) + `_boot()` initialization
- feat: `__init__.py` re-exports everything for backward compatibility
- feat: `main.py` loads package via `importlib.import_module("cores.v1.core")`

### Intent Classification — ML-based

- feat(intent): `SmartIntentClassifier` — 3-tier ML classification (embedding → local LLM → remote LLM)
- feat(intent): `EmbeddingEngine` — sentence-transformers (sbert) with TF-IDF/BOW fallback
- feat(intent): `LocalLLMClassifier` — ollama-based classification with auto-model selection
- feat(intent): `intent/` subpackage with `embedding.py`, `local_llm.py`, `ensemble.py`, `knn_classifier.py`, `training.py`
- feat(intent): ~100+ Polish/English intent training examples, learnable from corrections
- feat(intent): Persistent training data in `intent_training.json`
- refactor(intent): Replaced hardcoded keywords with ML as primary classifier

### Self-Healing Pipeline

- feat: `AutoRepair` — 5-phase self-healing loop (DIAGNOSE → PLAN → FIX → VERIFY → REFLECT)
- feat: `SelfReflection` — autonomous diagnostics (LLM, system, mic, TTS, disk, vosk, skills health)
- feat: `RepairJournal` — persistent trial database with error signature matching and known fixes
- feat: `StableSnapshot` — skill version management (stable/latest/archive/branches)
- feat: `EvolutionGuard` — error fingerprinting + strategy suggestions
- feat: `SkillPreflight` — syntax/imports/interface validation with auto_fix_imports
- feat: `FailureTracker` — global cross-skill failure tracking (threshold=3)
- feat: `LearnedRepairStrategy` — ML-based repair strategy selection (DecisionTree from sklearn)

### Provider Architecture

- feat: `ProviderSelector` — resource-aware provider selection with scoring
- feat: `ProviderChain` — ordered fallback chains with auto-demotion after 3 failures
- feat: `UCB1BanditSelector` — multi-armed bandit for optimal provider selection
- feat: `ResourceMonitor` — CPU/RAM/GPU/disk detection for provider requirements
- feat: Capability/provider structure: `skills/{cap}/providers/{prov}/stable|latest|archive/`
- feat: Multi-provider skills: TTS (espeak, pyttsx3, coqui), STT (vosk, whisper)

### Monitoring & Scheduling

- feat: `AdaptiveResourceMonitor` — EWMA trend detection, pressure scoring, alert thresholds with hysteresis
- feat: `ProactiveScheduler` — threading-based background tasks (resource alerts 30s, GC 3600s, health 300s)
- feat: `EvolutionGarbageCollector` — stub detection, version cleanup, migration to stable/latest/archive

### Quality & Validation

- feat: `QualityGate` — skill quality validation before registration (preflight, health, test, output, complexity)
- feat: `SkillValidator` — plugin registry for skill-specific result validation (stt, shell, tts, web_search)
- feat: `EvolutionJournal` — tracks evolutionary iterations with quality/speed metrics (JSONL + summary)

### Configuration & Identity

- feat: `SessionConfig` — hot-swappable providers/models during conversation via natural language
- feat: `ConfigGenerator` — dynamic config generation via LLM for missing files
- feat: `SystemIdentity` — dynamic system prompt with capability status (DZIAŁA/USZKODZONY)
- feat: `UserMemory` — persistent long-term memory for user preferences/directives
- feat: Voice mode persistence — auto-enter voice loop on boot if preference saved

### Infrastructure

- feat: `EventBus` — lightweight pub/sub (blinker signals) decoupling AutoRepair ↔ EvoEngine ↔ SelfReflection
- feat: `FuzzyCommandRouter` — typo-tolerant slash command dispatch (rapidfuzz)
- feat: `resilience.py` — tenacity retry decorators (retry_llm, retry_skill, retry_io) + structlog logging
- feat: `skill_logger.py` — NFO decorator logging with SQLite + JSONL sinks for all skills
- feat: `STTAutoTestPipeline` — Chain of Responsibility pattern for STT diagnostics (6 steps)

### LLM Management

- feat: `LLMClient` — 3-tier fallback: free (OpenRouter :free) → local (ollama) → paid (OpenRouter)
- feat: Auto-detect ollama models on startup, rate-limit cooldowns (not permanent blacklist)
- feat: Code-only model rejection (deepseek-coder, starcoder, codellama, etc.)
- feat: LLM hallucination detection — strips fake skill invocations from chat responses
- feat: `/autotune` — LIVE benchmark with real API calls for optimal model selection

### Commands (40+)

- `/skills`, `/create`, `/run`, `/test`, `/evolve`, `/rollback` — skill management
- `/model`, `/models`, `/autotune`, `/benchmark` — LLM management
- `/voice`, `/stt`, `/hw`, `/hwtest` — voice & hardware
- `/config`, `/reload_config` — session configuration
- `/health`, `/diagnose`, `/reflect`, `/fix` — diagnostics & repair
- `/memories`, `/remember`, `/forget` — persistent memory
- `/providers`, `/chain`, `/resources` — provider management
- `/journal`, `/repairs`, `/snapshot`, `/gc` — evolution tracking
- `/correct`, `/profile`, `/suggest`, `/topic` — intent learning
- `/pipeline`, `/compose`, `/core`, `/switch`, `/scan` — system management
- `/apikey`, `/state`, `/log`, `/learn` — administration

### Skills (35)

- Bootstrap: `deps`, `devops`, `echo`, `git_ops`, `llm_router`, `shell`
- Voice: `tts` (espeak provider), `stt` (vosk provider)
- Tools: `web_search`, `benchmark`, `kalkulator`, `json_validator`, `password_generator`, `system_info`, `network_info`, `time`, `weather`, `content_search`
- Auto-created: `weather_gdansk`, `gbp_to_jpy_converter`, `text_processor_`, `local_computer_discovery`, `hw_test`, `actionchat`, `chat`, `diagnostic_runner`, and more
- Testing: `openrouter_api_test`, `test_supervisor_probe`

### Simulation

- feat: `scripts/simulate.py` — 10 scenarios (create, use, evolve, chat, multi-turn)
- feat: `Dockerfile.simulate` + `docker-compose.simulate.yml` — containerized simulation
- result: 60% scenario success, 100% intent accuracy on targeted tests

### Testing

- 258 tests (pytest), 8 skipped (hardware-dependent)
- Coverage: IntentEngine, ProviderSelector, ResourceMonitor, SkillManager, EvoEngine, ProviderChain, GarbageCollector, SmartIntentClassifier, Preflight, EvolutionGuard, SystemIdentity, UserMemory, VoiceMode, HWTest

### Bug Fixes

- fix(llm): `self.llm.complete()` → `self.llm.chat()` throughout (LLMClient has no complete())
- fix(shell): Accept both `params['command']` and `params['text']` keys
- fix(model): Reject code-only models persisted in state (deepseek-coder caused nonsensical output)
- fix(stt): Extract transcribed text from STT outcome (was showing "done" without text)
- fix(state): `save_state()` merges changes instead of overwriting
- fix(identity): Fallback messages ("skill ma błąd") instead of LLM saying "nie umiem"
- fix(halucination): Detect and strip fake skill invocations from LLM responses

---

## [1.0.2] - 2026-03-04

### Summary

feat(docs): Documentation, CLI, API testing, and packaging updates

### Features

- feat(cli): coreskill CLI with status, logs reset, cache reset commands
- feat(api): openrouter_api_test skill with automatic API key validation
- feat(state): save_state() merges changes instead of overwriting

### Documentation

- docs: Complete rewrite of README.md, architecture.md, api_reference.md
- docs: creating_skills.md, configuration.md, troubleshooting.md
- docs: examples/ folder with usage examples

### Packaging

- feat: Python package structure (__init__.py, setup.py, MANIFEST.in)
- feat: Entry points for coreskill CLI

---

## [1.0.1] - 2026-03-03

### Summary

Initial release with core engine and basic skill infrastructure.

- Core evolutionary engine with LLM integration
- Basic skill creation and evolution
- State persistence via .evo_state.json
