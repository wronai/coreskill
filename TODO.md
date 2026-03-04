# TODO / Roadmap CoreSkill

## Current: Sprint 5 — Stabilization & Polish

### Performance (P1)
- [ ] Cache intent embeddings on disk (sbert model loads ~3s on startup)
- [ ] Async LLM calls with asyncio (currently blocking)
- [ ] Parallel skill execution for independent pipeline steps
- [ ] Reduce boot time (currently ~5-8s with all components)

### Code Quality (P1)
- [ ] Split `smart_intent.py` (929 lines) — extract EmbeddingEngine, LocalLLMClassifier
- [ ] Split `evo_engine.py` (817 lines) — extract validation, reflection triggers
- [ ] Standardize meta.json / manifest.json schema across all skills
- [ ] Improve type hints coverage in core modules
- [ ] Unify error handling across skills (currently ad-hoc per skill)

### Testing (P1)
- [ ] Increase test coverage to 90% (currently ~70% estimated)
- [ ] Property-based testing for intent classification
- [ ] Performance regression benchmarks
- [ ] Integration tests for full boot → request → response cycle

### Documentation (P2)
- [ ] Auto-generate skill API docs from meta.json + docstrings
- [ ] Add inline architecture diagrams (mermaid)
- [ ] Document EventBus event catalog
- [ ] Document QualityGate scoring criteria

## Sprint 6: Future Features

### User Interface (P2)
- [ ] Web UI (Streamlit/Gradio) for skill management
- [ ] REST API server for remote access
- [ ] Dashboard for monitoring (resource pressure, skill health, repair history)

### Multi-user (P3)
- [ ] Multi-user support with isolated state
- [ ] Skill marketplace (share/import skills)
- [ ] Rate limiting per user

### Security (P2)
- [ ] Sandboxing skill execution (subprocess isolation)
- [ ] API key encryption at rest
- [ ] Audit logging (who ran what, when)

### Voice (P2)
- [ ] Voice wake word detection (always-listening mode)
- [ ] Multi-language STT/TTS support (currently PL/EN)
- [ ] Streaming TTS (currently batch)

## Backlog (P3)

- [ ] Git integration for skill versioning (currently file-based snapshots)
- [ ] Docker optimization (multi-stage builds, smaller images)
- [ ] Cloud deployment templates (AWS/GCP/Azure)
- [ ] Mobile app companion
- [ ] Real-time collaboration (multi-user editing skills)
- [ ] Skill dependency graph visualization
- [ ] Auto-generated changelogs per skill

## Completed Sprints

### Sprint 4: Adaptive Systems ✅
- [x] AdaptiveResourceMonitor (EWMA trend detection, pressure scoring, hysteresis alerts)
- [x] ProactiveScheduler (threading-based, resource alerts 30s, GC 3600s, health 300s)
- [x] LearnedRepairStrategy (DecisionTree from sklearn, trained on RepairJournal)
- [x] UCB1BanditSelector (multi-armed bandit for provider selection)
- [x] resilience.py (tenacity retry + structlog structured logging)
- [x] EventBus (blinker pub/sub decoupling)
- [x] QualityGate (skill quality validation before registration)
- [x] SkillValidator (plugin registry for result validation)
- [x] FuzzyCommandRouter (rapidfuzz typo-tolerant dispatch)
- [x] SessionConfig (hot-swappable providers/models via natural language)
- [x] ConfigGenerator (LLM-generated configs for missing files)
- [x] 258 tests passing

### Sprint 3: Documentation & Packaging ✅
- [x] Complete docs rewrite (architecture, API reference, creating_skills, configuration, troubleshooting)
- [x] coreskill CLI (status, logs reset, cache reset)
- [x] openrouter_api_test skill with API key validation
- [x] Python package structure (setup.py, MANIFEST.in, entry points)
- [x] Examples folder

### Sprint 2: Self-Healing & Identity ✅
- [x] AutoRepair (5-phase: DIAGNOSE → PLAN → FIX → VERIFY → REFLECT)
- [x] SelfReflection (7 diagnostic checks + LLM analysis)
- [x] RepairJournal (persistent trial DB with known fixes)
- [x] StableSnapshot (stable/latest/archive/branches version management)
- [x] SystemIdentity (dynamic system prompt, capability status)
- [x] SkillPreflight + EvolutionGuard (auto_fix_imports, error fingerprinting)
- [x] UserMemory (persistent preferences, voice mode persistence)
- [x] EvolutionJournal (quality/speed metrics per evolution)
- [x] STTAutoTestPipeline (Chain of Responsibility, 6 diagnostic steps)
- [x] FailureTracker (global cross-skill threshold)

### Sprint 1: Skill Versioning & Providers ✅
- [x] EvolutionGarbageCollector (stub detection, cleanup, migration)
- [x] stable/latest/archive version structure
- [x] ProviderChain (auto-degradation after 3 failures, recovery after 2 successes)
- [x] ProviderSelector (resource-aware scoring)
- [x] ResourceMonitor (CPU/RAM/GPU/disk detection)
- [x] Capability/provider architecture (TTS, STT multi-provider)

### Sprint 1.5: Smart Intent ✅
- [x] SmartIntentClassifier (3-tier: embedding → local LLM → remote LLM)
- [x] EmbeddingEngine (sbert + TF-IDF/BOW fallback)
- [x] LocalLLMClassifier (auto-selects smallest ollama model)
- [x] intent/ subpackage (embedding, local_llm, ensemble, knn, training)
- [x] ~100+ PL/EN training examples, learnable from corrections

### Pre-sprint: Core Architecture ✅
- [x] Core split: monolithic core.py → 40+ focused modules
- [x] LLMClient (3-tier: free → local → paid)
- [x] EvoEngine (evolutionary loop with validation pipeline)
- [x] IntentEngine (multi-stage classification)
- [x] NFO logging system (SQLite + JSONL)
- [x] Shell skill (real-time streaming, interactive passthrough, safety blocks)
- [x] Voice loop (STT/TTS bidirectional, auto-diagnosis on silence)
- [x] Simulation infrastructure (Docker, 10 scenarios)

## Notes

Priority levels:
- **P0**: Critical, blocks release
- **P1**: Important, next sprint
- **P2**: Nice to have, planned
- **P3**: Future idea

Current state: **v2.0** — 40+ core modules, 35 skills, 258 tests, ML-based intent, self-healing pipeline.
