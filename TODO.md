# TODO / Roadmap CoreSkill

## Sprint 3: Core Refinement (WIP)

### Documentation
- [x] Update README.md with current features
- [x] Create architecture.md
- [x] Create api_reference.md  
- [x] Create creating_skills.md
- [x] Create configuration.md
- [x] Create troubleshooting.md
- [x] Create examples/ folder with usage examples
- [ ] Split smart_intent.py god-module (low priority)

### CLI
- [x] Create coreskill CLI entry point
- [x] Add coreskill logs reset command
- [x] Add coreskill cache reset command
- [x] Add coreskill status command

### API Testing
- [x] Create openrouter_api_test skill
- [x] Add API key validation on receipt

### Packaging
- [x] Create Python package structure
- [x] Update setup.py with entry points
- [x] Create MANIFEST.in

## Sprint 4: Future Enhancements

### Performance
- [ ] Cache intent embeddings on disk
- [ ] Parallel skill execution for independent steps
- [ ] Async LLM calls with asyncio

### Features
- [ ] Web UI (Streamlit/Gradio)
- [ ] REST API server
- [ ] Multi-user support
- [ ] Skill marketplace
- [ ] Automatic skill documentation generation

### Testing
- [ ] Increase test coverage to 90%
- [ ] Property-based testing
- [ ] Performance benchmarks
- [ ] Stress testing

### Security
- [ ] Sandboxing skill execution
- [ ] API key encryption
- [ ] Audit logging
- [ ] Rate limiting per user

## Backlog

### Nice to have
- [ ] Git integration for skill versioning
- [ ] Docker optimization
- [ ] Cloud deployment templates (AWS/GCP/Azure)
- [ ] Mobile app companion
- [ ] Voice wake word detection
- [ ] Real-time collaboration

### Technical debt
- [ ] Refactor evo_engine.py (too large)
- [ ] Unify error handling across skills
- [ ] Standardize meta.json schema
- [ ] Improve type hints coverage

## Completed Sprints

### Sprint 1: Skill Versioning ✅
- [x] EvolutionGarbageCollector
- [x] stable/latest/archive structure
- [x] ProviderChain auto-degradation
- [x] 208 tests passing

### Sprint 2: Provider Architecture ✅
- [x] Core split into modules
- [x] ProviderSelector with ResourceMonitor
- [x] Multi-provider skills (TTS, STT)
- [x] Capability/provider architecture

### Sprint 1.5: Smart Intent ✅
- [x] SmartIntentClassifier with ML
- [x] EmbeddingEngine (sbert + fallback)
- [x] 198 tests passing

### Pre-sprint: Core Features ✅
- [x] LLMClient with tiered routing
- [x] EvoEngine with validation
- [x] IntentEngine v2
- [x] UserMemory with persistence
- [x] Voice mode with persistence
- [x] NFO logging system
- [x] CLI with status/logs/cache commands

## Notes

Priority levels:
- P0: Critical, blocks release
- P1: Important, should be in next sprint
- P2: Nice to have, backlog
- P3: Future idea

Current focus: Documentation and packaging for v1.0 release.
