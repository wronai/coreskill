# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/coreskill/evo-engine
- **Analysis Mode**: static
- **Total Functions**: 471
- **Total Classes**: 62
- **Modules**: 55
- **Entry Points**: 441

## Architecture by Module

### cores.v1.core
- **Functions**: 49
- **File**: `core.py`

### cores.v1.smart_intent
- **Functions**: 29
- **Classes**: 5
- **File**: `smart_intent.py`

### cores.v1.provider_selector
- **Functions**: 26
- **Classes**: 3
- **File**: `provider_selector.py`

### cores.v1.skill_manager
- **Functions**: 24
- **Classes**: 1
- **File**: `skill_manager.py`

### cores.v1.preflight
- **Functions**: 17
- **Classes**: 3
- **File**: `preflight.py`

### skills.benchmark.v1.skill
- **Functions**: 16
- **Classes**: 3
- **File**: `skill.py`

### skills.git_ops.v1.skill
- **Functions**: 15
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.intent_engine
- **Functions**: 14
- **Classes**: 1
- **File**: `intent_engine.py`

### cores.v1.llm_client
- **Functions**: 14
- **Classes**: 1
- **File**: `llm_client.py`

### cores.v1.resource_monitor
- **Functions**: 12
- **Classes**: 1
- **File**: `resource_monitor.py`

### skills.web_search.providers.duckduckgo.v1.skill
- **Functions**: 12
- **Classes**: 2
- **File**: `skill.py`

### cores.v1.user_memory
- **Functions**: 10
- **Classes**: 1
- **File**: `user_memory.py`

### cores.v1.supervisor
- **Functions**: 10
- **Classes**: 1
- **File**: `supervisor.py`

### cores.v1.garbage_collector
- **Functions**: 10
- **Classes**: 1
- **File**: `garbage_collector.py`

### skills.stt.providers.vosk.archive.v7.skill
- **Functions**: 10
- **Classes**: 1
- **File**: `skill.py`

### skills.devops.v1.skill
- **Functions**: 10
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.system_identity
- **Functions**: 9
- **Classes**: 2
- **File**: `system_identity.py`

### skills.openrouter.v1.skill
- **Functions**: 9
- **Classes**: 1
- **File**: `skill.py`

### skills.deps.v2.skill
- **Functions**: 9
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.logger
- **Functions**: 8
- **Classes**: 1
- **File**: `logger.py`

## Key Entry Points

Main execution flows into the system:

### cores.v1.core.main
- **Calls**: cores.v1.skill_logger.init_nfo, cores.v1.config.load_state, cores.v1.core._check_restart_loop, Logger, Supervisor, cores.v1.config.cpr, cores.v1.config.cpr, cores.v1.config.cpr

### cores.v1.evo_engine.EvoEngine._execute_with_validation
> Pipeline: preflight → execute → validate result → reflect → retry if needed.
- **Calls**: set, self.sm.latest_v, range, self.sm.latest_v, cores.v1.config.cpr, self.log.core, cores.v1.config.cpr, self.sm.exec_skill

### cores.v1.evo_engine.EvoEngine._autonomous_stt_repair
> Autonomous diagnosis and repair for STT empty transcription.
Returns (fixed, message, new_result).
- **Calls**: cores.v1.config.cpr, any, cores.v1.config.cpr, shutil.which, cores.v1.config.cpr, Path, cores.v1.config.cpr, cores.v1.config.cpr

### cores.v1.llm_client.LLMClient.chat
- **Calls**: self._is_available, bool, self._build_error_msg, os.environ.get, print, print, print, enumerate

### cores.v1.skill_manager.SkillManager.smart_evolve
> Evolve skill using devops diagnosis + deps alternatives.
- **Calls**: self.latest_v, self.skill_path, p.read_text, self.diagnose_skill, diag.get, self.get_health_context, self.log.learn_summary, cores.v1.utils.clean_code

### main.bootstrap
- **Calls**: main.log, main.load_state, state.get, state.get, main.log, str, str, d.mkdir

### cores.v1.evo_engine.EvoEngine.handle_request
> Full pipeline: analyze → execute/create/evolve → validate. No user prompts.
- **Calls**: analysis.get, analysis.get, analysis.get, analysis.get, cores.v1.config.cpr, self.log.core, self.llm.analyze_need, isinstance

### cores.v1.evo_engine.EvoEngine._try_fallback_providers
> Try alternative providers from the chain when primary fails.
- **Calls**: self.provider_chain.select_with_fallback, self.sm._active_provider, cores.v1.config.cpr, cores.v1.config.cpr, len, cores.v1.config.cpr, self.sm.provider_selector.get_skill_path, cores.v1.config.cpr

### cores.v1.preflight.SkillPreflight.check_imports
> Stage 2: Do all imports resolve? Detect missing stdlib imports.
- **Calls**: set, set, ast.walk, PreflightResult, ast.parse, isinstance, PreflightResult, skill_path.exists

### cores.v1.intent_engine.IntentEngine.analyze
> ML-based intent detection.

Flow:
  Stage 0: Trivial filter
  Stage 1: SmartIntentClassifier (embedding → local LLM → remote LLM)
  Stage 2: Context i
- **Calls**: user_msg.strip, stripped.split, self._build_context, self._classifier.classify, self._recent_topic, self.record_unhandled, isinstance, list

### cores.v1.preflight.SkillPreflight.auto_fix_imports
> Auto-fix missing stdlib imports by adding them at the top.
- **Calls**: set, ast.walk, code.split, enumerate, None.join, ast.parse, isinstance, line.strip

### skills.shell.v1.skill.ShellSkill.execute
- **Calls**: None.strip, None.strip, min, input_data.get, print, int, os.path.expanduser, self._is_interactive

### cores.v1.core._cmd_models
- **Calls**: cores.v1.config.cpr, cores.v1.llm_client.discover_models, cores.v1.llm_client._detect_ollama_models, cores.v1.config.cpr, cores.v1.config.cpr, cores.v1.config.cpr, cores.v1.config.cpr, None.join

### cores.v1.skill_manager.SkillManager.create_skill
- **Calls**: self.latest_v, self._active_provider, sd.mkdir, self.log.learn_summary, cores.v1.utils.clean_code, None.write_text, None.write_text, None.write_text

### skills.git_ops.v1.skill.GitOpsSkill.execute
> evo-engine interface.
- **Calls**: input_data.get, input_data.get, dispatch.get, fn, self.init, self.status, self.add, self.commit

### skills.stt.providers.vosk.stable.skill.STTSkill.execute
- **Calls**: int, params.get, params.get, int, params.get, params.get, self._transcribe_vosk, isinstance

### skills.stt.providers.vosk.archive.v6.skill.STTSkill.execute
- **Calls**: int, params.get, params.get, int, params.get, params.get, self._transcribe_vosk, isinstance

### skills.stt.providers.vosk.archive.v3.skill.STTSkill.execute
- **Calls**: int, params.get, params.get, int, params.get, params.get, self._transcribe_vosk, isinstance

### skills.stt.providers.vosk.archive.v7.skill.STTSkill.execute
- **Calls**: int, params.get, params.get, int, params.get, params.get, self._transcribe_vosk, isinstance

### skills.stt.providers.vosk.archive.v1.skill.STTSkill.execute
- **Calls**: int, params.get, params.get, int, params.get, params.get, self._transcribe_vosk, isinstance

### cores.v1.preflight.EvolutionGuard.is_stub_skill
> Detect if skill is a stub (placeholder/test implementation).
Conservative: only flag clearly non-functional code.
Real skills with subprocess/os/urlli
- **Calls**: skill_path.read_text, any, re.search, l.strip, len, len, re.search, skill_path.exists

### skills.openrouter.v1.skill.OpenRouterSkill._search_models
> Search models by query string.
- **Calls**: None.lower, params.get, params.get, scored.sort, self._fetch_models, model.get, results.append, len

### skills.benchmark.v1.skill.BenchmarkSkill._recommend_models
> Recommend best models for a specific goal.
- **Calls**: params.get, params.get, params.get, params.get, self.GOAL_PROFILES.get, self._get_candidate_models, scored_models.sort, self._apply_constraints

### cores.v1.core._cmd_autotune
> Auto-tune: benchmark models and select optimal one: /autotune [goal]
- **Calls**: cores.v1.config.cpr, benchmark_execute, result.get, cores.v1.config.cpr, cores.v1.config.cpr, cores.v1.config.cpr, cores.v1.config.save_state, logger.core

### cores.v1.skill_manager.SkillManager.latest_v
- **Calls**: self._active_provider, d.iterdir, vs.sort, d.exists, prov_dir.is_dir, None.exists, None.exists, prov_dir.iterdir

### skills.stt.providers.vosk.archive.v7.skill.check_readiness
> Multi-level readiness check: deps, hardware, resources.
- **Calls**: vosk_cache.is_dir, sorted, issues.append, issues.append, issues.append, issues.append, bool, shutil.which

### cores.v1.core._cmd_health
> Show skill readiness/health status: /health [skill_name]
- **Calls**: sorted, sm.readiness_check, r.get, r.get, r.get, r.get, r.get, cores.v1.config.cpr

### cores.v1.intent_engine.IntentEngine._extract_shell_command
> Extract actual shell command from message or context.
- **Calls**: msg.lower, any, ul.split, msg.strip, reversed, None.strip, ul.split, m.get

### cores.v1.evo_engine.EvoEngine.evolve_skill
> Create + evolutionary test loop for new skills.
- **Calls**: cores.v1.config.cpr, self.log.core, cores.v1.config.cpr, self.sm.create_skill, cores.v1.config.cpr, range, self.log.core, self.sm.rollback

### cores.v1.skill_manager.SkillManager._load_and_run
> Load skill module and execute. Returns result dict.
- **Calls**: importlib.util.spec_from_file_location, importlib.util.module_from_spec, spec.loader.exec_module, cores.v1.skill_logger.inject_logging, dir, hasattr, str, hasattr

## Process Flows

Key execution flows identified:

### Flow 1: main
```
main [cores.v1.core]
  └─> _check_restart_loop
      └─ →> cpr
      └─ →> cpr
  └─ →> init_nfo
  └─ →> load_state
```

### Flow 2: _execute_with_validation
```
_execute_with_validation [cores.v1.evo_engine.EvoEngine]
  └─ →> cpr
```

### Flow 3: _autonomous_stt_repair
```
_autonomous_stt_repair [cores.v1.evo_engine.EvoEngine]
  └─ →> cpr
  └─ →> cpr
```

### Flow 4: chat
```
chat [cores.v1.llm_client.LLMClient]
```

### Flow 5: smart_evolve
```
smart_evolve [cores.v1.skill_manager.SkillManager]
```

### Flow 6: bootstrap
```
bootstrap [main]
  └─> log
  └─> load_state
```

### Flow 7: handle_request
```
handle_request [cores.v1.evo_engine.EvoEngine]
  └─ →> cpr
```

### Flow 8: _try_fallback_providers
```
_try_fallback_providers [cores.v1.evo_engine.EvoEngine]
  └─ →> cpr
  └─ →> cpr
```

### Flow 9: check_imports
```
check_imports [cores.v1.preflight.SkillPreflight]
```

### Flow 10: analyze
```
analyze [cores.v1.intent_engine.IntentEngine]
```

## Key Classes

### cores.v1.skill_manager.SkillManager
- **Methods**: 22
- **Key Methods**: cores.v1.skill_manager.SkillManager.__init__, cores.v1.skill_manager.SkillManager._collect_versions, cores.v1.skill_manager.SkillManager.list_skills, cores.v1.skill_manager.SkillManager._is_rolled_back, cores.v1.skill_manager.SkillManager.latest_v, cores.v1.skill_manager.SkillManager._active_provider, cores.v1.skill_manager.SkillManager.skill_path, cores.v1.skill_manager.SkillManager.create_skill, cores.v1.skill_manager.SkillManager.diagnose_skill, cores.v1.skill_manager.SkillManager._raw_test

### cores.v1.intent_engine.IntentEngine
> Context-aware intent detection with ML-based classification.

Stages:
  0. Trivial filter (very shor
- **Methods**: 15
- **Key Methods**: cores.v1.intent_engine.IntentEngine.__init__, cores.v1.intent_engine.IntentEngine.classifier, cores.v1.intent_engine.IntentEngine.save, cores.v1.intent_engine.IntentEngine._update_topics_from_result, cores.v1.intent_engine.IntentEngine._recent_topic, cores.v1.intent_engine.IntentEngine._build_context, cores.v1.intent_engine.IntentEngine.record_skill_use, cores.v1.intent_engine.IntentEngine.record_correction, cores.v1.intent_engine.IntentEngine.record_success, cores.v1.intent_engine.IntentEngine.record_unhandled

### cores.v1.smart_intent.SmartIntentClassifier
> ML-based intent classifier for evo-engine.

Replaces all hardcoded _KW_* tuples with learnable embed
- **Methods**: 15
- **Key Methods**: cores.v1.smart_intent.SmartIntentClassifier.__init__, cores.v1.smart_intent.SmartIntentClassifier._training_path, cores.v1.smart_intent.SmartIntentClassifier._load_training_data, cores.v1.smart_intent.SmartIntentClassifier._save_training_data, cores.v1.smart_intent.SmartIntentClassifier.add_example, cores.v1.smart_intent.SmartIntentClassifier.learn_from_correction, cores.v1.smart_intent.SmartIntentClassifier.learn_from_success, cores.v1.smart_intent.SmartIntentClassifier._generate_variations, cores.v1.smart_intent.SmartIntentClassifier._ensure_embeddings, cores.v1.smart_intent.SmartIntentClassifier.classify

### skills.benchmark.v1.skill.BenchmarkSkill
> Analyzes and benchmarks LLM models for goal-based recommendations.
- **Methods**: 15
- **Key Methods**: skills.benchmark.v1.skill.BenchmarkSkill.__init__, skills.benchmark.v1.skill.BenchmarkSkill._load_config, skills.benchmark.v1.skill.BenchmarkSkill._get_models_from_tier, skills.benchmark.v1.skill.BenchmarkSkill.execute, skills.benchmark.v1.skill.BenchmarkSkill._recommend_models, skills.benchmark.v1.skill.BenchmarkSkill._get_candidate_models, skills.benchmark.v1.skill.BenchmarkSkill._calculate_model_score, skills.benchmark.v1.skill.BenchmarkSkill._estimate_context_length, skills.benchmark.v1.skill.BenchmarkSkill._determine_use_cases, skills.benchmark.v1.skill.BenchmarkSkill._apply_constraints

### cores.v1.provider_selector.ProviderChain
> Ordered provider fallback chain with auto-degradation.

Tracks failures per provider and automatical
- **Methods**: 13
- **Key Methods**: cores.v1.provider_selector.ProviderChain.__init__, cores.v1.provider_selector.ProviderChain._key, cores.v1.provider_selector.ProviderChain._get_stats, cores.v1.provider_selector.ProviderChain.build_chain, cores.v1.provider_selector.ProviderChain._reorder_by_fallback, cores.v1.provider_selector.ProviderChain.select_with_fallback, cores.v1.provider_selector.ProviderChain.select_best, cores.v1.provider_selector.ProviderChain.record_failure, cores.v1.provider_selector.ProviderChain.record_success, cores.v1.provider_selector.ProviderChain._cooldown_expired

### skills.git_ops.v1.skill.GitOpsSkill
> Manage local git repos for skill development and versioning.
- **Methods**: 13
- **Key Methods**: skills.git_ops.v1.skill.GitOpsSkill.__init__, skills.git_ops.v1.skill.GitOpsSkill._run, skills.git_ops.v1.skill.GitOpsSkill.init, skills.git_ops.v1.skill.GitOpsSkill.status, skills.git_ops.v1.skill.GitOpsSkill.add, skills.git_ops.v1.skill.GitOpsSkill.commit, skills.git_ops.v1.skill.GitOpsSkill.log, skills.git_ops.v1.skill.GitOpsSkill.diff, skills.git_ops.v1.skill.GitOpsSkill.tag, skills.git_ops.v1.skill.GitOpsSkill.checkout

### cores.v1.user_memory.UserMemory
> Persistent long-term memory for user preferences and directives.

Directives are short text notes th
- **Methods**: 12
- **Key Methods**: cores.v1.user_memory.UserMemory.__init__, cores.v1.user_memory.UserMemory.directives, cores.v1.user_memory.UserMemory.add, cores.v1.user_memory.UserMemory.remove, cores.v1.user_memory.UserMemory.clear_all, cores.v1.user_memory.UserMemory.voice_mode, cores.v1.user_memory.UserMemory.set_voice_mode, cores.v1.user_memory.UserMemory.has_directive, cores.v1.user_memory.UserMemory.build_system_context, cores.v1.user_memory.UserMemory.looks_like_preference

### cores.v1.resource_monitor.ResourceMonitor
> Detects CPU, RAM, GPU, disk, installed packages.
- **Methods**: 12
- **Key Methods**: cores.v1.resource_monitor.ResourceMonitor.__init__, cores.v1.resource_monitor.ResourceMonitor.snapshot, cores.v1.resource_monitor.ResourceMonitor._cpu_count, cores.v1.resource_monitor.ResourceMonitor._ram_total, cores.v1.resource_monitor.ResourceMonitor._ram_available, cores.v1.resource_monitor.ResourceMonitor._ram_from_proc, cores.v1.resource_monitor.ResourceMonitor._disk_free, cores.v1.resource_monitor.ResourceMonitor._detect_gpu, cores.v1.resource_monitor.ResourceMonitor._installed_packages, cores.v1.resource_monitor.ResourceMonitor.has_command

### cores.v1.provider_selector.ProviderSelector
> Selects the best available provider for a capability.
- **Methods**: 12
- **Key Methods**: cores.v1.provider_selector.ProviderSelector.__init__, cores.v1.provider_selector.ProviderSelector.list_capabilities, cores.v1.provider_selector.ProviderSelector.list_providers, cores.v1.provider_selector.ProviderSelector.load_manifest, cores.v1.provider_selector.ProviderSelector.load_meta, cores.v1.provider_selector.ProviderSelector.get_provider_info, cores.v1.provider_selector.ProviderSelector.select, cores.v1.provider_selector.ProviderSelector._check_runnable, cores.v1.provider_selector.ProviderSelector._score, cores.v1.provider_selector.ProviderSelector._fallback

### cores.v1.llm_client.LLMClient
> Tiered LLM routing: free remote → local (ollama) → paid remote.
- Rate-limited models get cooldown (
- **Methods**: 12
- **Key Methods**: cores.v1.llm_client.LLMClient.__init__, cores.v1.llm_client.LLMClient.tier_info, cores.v1.llm_client.LLMClient._is_available, cores.v1.llm_client.LLMClient._report_ok, cores.v1.llm_client.LLMClient._report_fail, cores.v1.llm_client.LLMClient.chat, cores.v1.llm_client.LLMClient._build_error_msg, cores.v1.llm_client.LLMClient._try_model, cores.v1.llm_client.LLMClient._get_unavailable_reason, cores.v1.llm_client.LLMClient.gen_code

### cores.v1.supervisor.Supervisor
> Manages core versions: can create coreB/C/D, test, promote, rollback.
- **Methods**: 10
- **Key Methods**: cores.v1.supervisor.Supervisor.__init__, cores.v1.supervisor.Supervisor.active, cores.v1.supervisor.Supervisor.active_version, cores.v1.supervisor.Supervisor.list_cores, cores.v1.supervisor.Supervisor.switch, cores.v1.supervisor.Supervisor.health, cores.v1.supervisor.Supervisor.create_next_core, cores.v1.supervisor.Supervisor.promote_core, cores.v1.supervisor.Supervisor.rollback_core, cores.v1.supervisor.Supervisor.recover

### cores.v1.garbage_collector.EvolutionGarbageCollector
> Cleans up failed evolution stubs, promotes stable versions.
- **Methods**: 10
- **Key Methods**: cores.v1.garbage_collector.EvolutionGarbageCollector.__init__, cores.v1.garbage_collector.EvolutionGarbageCollector.is_stub, cores.v1.garbage_collector.EvolutionGarbageCollector.is_broken, cores.v1.garbage_collector.EvolutionGarbageCollector.scan_versions, cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_provider, cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_legacy, cores.v1.garbage_collector.EvolutionGarbageCollector.migrate_to_stable_latest, cores.v1.garbage_collector.EvolutionGarbageCollector._copy_version, cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_all, cores.v1.garbage_collector.EvolutionGarbageCollector.summary

### cores.v1.preflight.EvolutionGuard
> Prevents evolution loops where the same error repeats.
Tracks error fingerprints and suggests strate
- **Methods**: 9
- **Key Methods**: cores.v1.preflight.EvolutionGuard.__init__, cores.v1.preflight.EvolutionGuard.fingerprint, cores.v1.preflight.EvolutionGuard.record_error, cores.v1.preflight.EvolutionGuard.is_repeating, cores.v1.preflight.EvolutionGuard.get_error_summary, cores.v1.preflight.EvolutionGuard.suggest_strategy, cores.v1.preflight.EvolutionGuard.build_evolution_prompt_context, cores.v1.preflight.EvolutionGuard.is_stub_skill, cores.v1.preflight.EvolutionGuard.check_execution_result

### cores.v1.smart_intent.EmbeddingEngine
> Sentence-transformers based embedding for intent similarity.

Uses paraphrase-multilingual-MiniLM-L1
- **Methods**: 8
- **Key Methods**: cores.v1.smart_intent.EmbeddingEngine.__init__, cores.v1.smart_intent.EmbeddingEngine.available, cores.v1.smart_intent.EmbeddingEngine._try_init, cores.v1.smart_intent.EmbeddingEngine.encode, cores.v1.smart_intent.EmbeddingEngine.similarity, cores.v1.smart_intent.EmbeddingEngine._bow_vector, cores.v1.smart_intent.EmbeddingEngine._normalize_pl, cores.v1.smart_intent.EmbeddingEngine.install_hint

### cores.v1.logger.Logger
> Per-skill, per-core structured logging with learning.
- **Methods**: 8
- **Key Methods**: cores.v1.logger.Logger.__init__, cores.v1.logger.Logger._write, cores.v1.logger.Logger._entry, cores.v1.logger.Logger.core, cores.v1.logger.Logger.skill, cores.v1.logger.Logger.read_skill_log, cores.v1.logger.Logger.read_core_log, cores.v1.logger.Logger.learn_summary

### skills.openrouter.v1.skill.OpenRouterSkill
> OpenRouter API client for discovering and ranking free LLM models.
- **Methods**: 8
- **Key Methods**: skills.openrouter.v1.skill.OpenRouterSkill.__init__, skills.openrouter.v1.skill.OpenRouterSkill.execute, skills.openrouter.v1.skill.OpenRouterSkill._fetch_models, skills.openrouter.v1.skill.OpenRouterSkill._score_model, skills.openrouter.v1.skill.OpenRouterSkill._discover_free, skills.openrouter.v1.skill.OpenRouterSkill._search_models, skills.openrouter.v1.skill.OpenRouterSkill._get_model_info, skills.openrouter.v1.skill.OpenRouterSkill._get_recommended_use

### skills.devops.v1.skill.DevOpsSkill
> Test, validate and deploy skills in isolated subprocess.
- **Methods**: 8
- **Key Methods**: skills.devops.v1.skill.DevOpsSkill.check_syntax, skills.devops.v1.skill.DevOpsSkill.detect_imports, skills.devops.v1.skill.DevOpsSkill.check_deps, skills.devops.v1.skill.DevOpsSkill.find_system_alternatives, skills.devops.v1.skill.DevOpsSkill.test_skill, skills.devops.v1.skill.DevOpsSkill.health_check_skill, skills.devops.v1.skill.DevOpsSkill.generate_fix_prompt, skills.devops.v1.skill.DevOpsSkill.execute

### cores.v1.system_identity.SystemIdentity
> Builds dynamic system prompt that separates:
- What the SYSTEM can do (capabilities)
- What the LLM 
- **Methods**: 7
- **Key Methods**: cores.v1.system_identity.SystemIdentity.__init__, cores.v1.system_identity.SystemIdentity.refresh_statuses, cores.v1.system_identity.SystemIdentity.get_status, cores.v1.system_identity.SystemIdentity.build_system_prompt, cores.v1.system_identity.SystemIdentity.build_fallback_message, cores.v1.system_identity.SystemIdentity.build_skill_context_for_llm, cores.v1.system_identity.SystemIdentity.get_readiness_report

### cores.v1.evo_engine.EvoEngine
> Generic evolutionary algorithm:
1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
 
- **Methods**: 7
- **Key Methods**: cores.v1.evo_engine.EvoEngine.__init__, cores.v1.evo_engine.EvoEngine.handle_request, cores.v1.evo_engine.EvoEngine._execute_with_validation, cores.v1.evo_engine.EvoEngine._try_fallback_providers, cores.v1.evo_engine.EvoEngine._validate_result, cores.v1.evo_engine.EvoEngine._autonomous_stt_repair, cores.v1.evo_engine.EvoEngine.evolve_skill

### skills.deps.v2.skill.DepsSkill
- **Methods**: 7
- **Key Methods**: skills.deps.v2.skill.DepsSkill.__init__, skills.deps.v2.skill.DepsSkill.check_system, skills.deps.v2.skill.DepsSkill.check_python_module, skills.deps.v2.skill.DepsSkill.pip_install, skills.deps.v2.skill.DepsSkill.execute, skills.deps.v2.skill.DepsSkill.get_info, skills.deps.v2.skill.DepsSkill.health_check

## Data Transformation Functions

Key functions that process and transform data:

### cores.v1.config._parse_models_override
- **Output to**: isinstance, isinstance, None.strip, x.strip, None.strip

### cores.v1.smart_intent.EmbeddingEngine.encode
> Encode texts to vectors.
- **Output to**: self._try_init, self._model.encode, None.toarray, TfidfVectorizer, None.toarray

### cores.v1.evo_engine.EvoEngine._validate_result
> Validate whether the skill result actually achieved the goal.
Returns {verdict: success|partial|fail
- **Output to**: result.get, result.get, isinstance, inner.get, inner.get

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `cores.v1.core.main` - 104 calls
- `cores.v1.llm_client.LLMClient.chat` - 37 calls
- `cores.v1.skill_manager.SkillManager.smart_evolve` - 36 calls
- `main.bootstrap` - 33 calls
- `cores.v1.evo_engine.EvoEngine.handle_request` - 30 calls
- `cores.v1.preflight.SkillPreflight.check_imports` - 27 calls
- `cores.v1.intent_engine.IntentEngine.analyze` - 26 calls
- `cores.v1.preflight.SkillPreflight.auto_fix_imports` - 26 calls
- `skills.shell.v1.skill.ShellSkill.execute` - 26 calls
- `cores.v1.skill_manager.SkillManager.create_skill` - 23 calls
- `skills.git_ops.v1.skill.GitOpsSkill.execute` - 23 calls
- `skills.stt.providers.vosk.stable.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.archive.v6.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.archive.v3.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.archive.v7.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.archive.v1.skill.STTSkill.execute` - 23 calls
- `cores.v1.preflight.EvolutionGuard.is_stub_skill` - 22 calls
- `cores.v1.skill_manager.SkillManager.latest_v` - 21 calls
- `skills.stt.providers.vosk.archive.v7.skill.check_readiness` - 21 calls
- `cores.v1.evo_engine.EvoEngine.evolve_skill` - 19 calls
- `cores.v1.resource_monitor.ResourceMonitor.can_run` - 17 calls
- `cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_legacy` - 17 calls
- `cores.v1.llm_client.LLMClient.analyze_need` - 17 calls
- `cores.v1.pipeline_manager.PipelineManager.run_p` - 17 calls
- `cores.v1.skill_manager.SkillManager.get_health_context` - 17 calls
- `cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_provider` - 16 calls
- `cores.v1.garbage_collector.EvolutionGarbageCollector.migrate_to_stable_latest` - 16 calls
- `cores.v1.preflight.SkillPreflight.check_interface` - 15 calls
- `cores.v1.logger.Logger.learn_summary` - 15 calls
- `cores.v1.skill_manager.SkillManager.list_skills` - 15 calls
- `cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_all` - 14 calls
- `cores.v1.garbage_collector.EvolutionGarbageCollector.summary` - 14 calls
- `cores.v1.provider_selector.ProviderSelector.load_meta` - 14 calls
- `cores.v1.skill_logger.skill_health_summary` - 13 calls
- `cores.v1.garbage_collector.EvolutionGarbageCollector.scan_versions` - 13 calls
- `cores.v1.smart_intent.LocalLLMClassifier.classify` - 13 calls
- `cores.v1.skill_manager.SkillManager.rollback` - 13 calls
- `skills.web_search.providers.duckduckgo.v1.skill.WebSearchSkill.search_duckduckgo` - 13 calls
- `skills.tts.providers.espeak.stable.skill.check_readiness` - 13 calls
- `skills.devops.v1.skill.DevOpsSkill.detect_imports` - 13 calls

## System Interactions

How components interact:

```mermaid
graph TD
    main --> init_nfo
    main --> load_state
    main --> _check_restart_loop
    main --> Logger
    main --> Supervisor
    _execute_with_valida --> set
    _execute_with_valida --> latest_v
    _execute_with_valida --> range
    _execute_with_valida --> cpr
    _autonomous_stt_repa --> cpr
    _autonomous_stt_repa --> any
    _autonomous_stt_repa --> which
    chat --> _is_available
    chat --> bool
    chat --> _build_error_msg
    chat --> get
    chat --> print
    smart_evolve --> latest_v
    smart_evolve --> skill_path
    smart_evolve --> read_text
    smart_evolve --> diagnose_skill
    smart_evolve --> get
    bootstrap --> log
    bootstrap --> load_state
    bootstrap --> get
    handle_request --> get
    handle_request --> cpr
    _try_fallback_provid --> select_with_fallback
    _try_fallback_provid --> _active_provider
    _try_fallback_provid --> cpr
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.