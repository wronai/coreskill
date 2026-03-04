# System Architecture Analysis

## Overview

- **Project**: .
- **Analysis Mode**: static
- **Total Functions**: 1064
- **Total Classes**: 145
- **Modules**: 113
- **Entry Points**: 0

## Architecture by Module

### cores.v1.core
- **Functions**: 58
- **File**: `core.py`

### skills.benchmark.v1.skill
- **Functions**: 32
- **Classes**: 3
- **File**: `skill.py`

### cores.v1.smart_intent
- **Functions**: 31
- **Classes**: 5
- **File**: `smart_intent.py`

### root.core
- **Functions**: 29
- **Classes**: 6
- **File**: `core.py`

### batch_1.core
- **Functions**: 29
- **Classes**: 6
- **File**: `core.py`

### seeds.core_v1
- **Functions**: 27
- **Classes**: 5
- **File**: `core_v1.py`

### cores.v1.provider_selector
- **Functions**: 26
- **Classes**: 3
- **File**: `provider_selector.py`

### cores.v1.auto_repair
- **Functions**: 24
- **Classes**: 2
- **File**: `auto_repair.py`

### cores.v1.skill_manager
- **Functions**: 24
- **Classes**: 1
- **File**: `skill_manager.py`

### cores.v1.session_config
- **Functions**: 23
- **Classes**: 2
- **File**: `session_config.py`

### cores.v1.evo_journal
- **Functions**: 20
- **Classes**: 2
- **File**: `evo_journal.py`

### cores.v1.self_reflection
- **Functions**: 20
- **Classes**: 3
- **File**: `self_reflection.py`

### cores.v1.metrics_collector
- **Functions**: 19
- **Classes**: 4
- **File**: `metrics_collector.py`

### cores.v1.evo_engine
- **Functions**: 17
- **Classes**: 2
- **File**: `evo_engine.py`

### cores.v1.preflight
- **Functions**: 17
- **Classes**: 3
- **File**: `preflight.py`

### cores.v1.self_healing
- **Functions**: 17
- **Classes**: 6
- **File**: `__init__.py`

### cores.v1.repair_journal
- **Functions**: 16
- **Classes**: 3
- **File**: `repair_journal.py`

### cores.v1.intent_engine
- **Functions**: 16
- **Classes**: 1
- **File**: `intent_engine.py`

### cores.v1.skill_schema
- **Functions**: 16
- **Classes**: 3
- **File**: `skill_schema.py`

### cores.v1.intent
- **Functions**: 16
- **Classes**: 1
- **File**: `__init__.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### skills.benchmark.v1.skill.BenchmarkSkill
> Analyzes and benchmarks LLM models for goal-based recommendations.
- **Methods**: 29
- **Key Methods**: skills.benchmark.v1.skill.BenchmarkSkill.__init__, skills.benchmark.v1.skill.BenchmarkSkill._load_config, skills.benchmark.v1.skill.BenchmarkSkill._get_models_from_tier, skills.benchmark.v1.skill.BenchmarkSkill._get_api_key, skills.benchmark.v1.skill.BenchmarkSkill._load_benchmark_results, skills.benchmark.v1.skill.BenchmarkSkill._save_benchmark_results, skills.benchmark.v1.skill.BenchmarkSkill._update_benchmark_results, skills.benchmark.v1.skill.BenchmarkSkill._get_cached_recommendations, skills.benchmark.v1.skill.BenchmarkSkill.execute, skills.benchmark.v1.skill.BenchmarkSkill._recommend_models

### cores.v1.session_config.SessionConfig
> User-facing configuration manager.

This is a SESSION-ONLY layer - changes are NOT persisted to disk
- **Methods**: 25
- **Key Methods**: cores.v1.session_config.SessionConfig.__init__, cores.v1.session_config.SessionConfig.CATEGORIES, cores.v1.session_config.SessionConfig.PROVIDER_TIERS, cores.v1.session_config.SessionConfig.get, cores.v1.session_config.SessionConfig.set, cores.v1.session_config.SessionConfig.reset, cores.v1.session_config.SessionConfig.on_change, cores.v1.session_config.SessionConfig._notify, cores.v1.session_config.SessionConfig.handle_configure_intent, cores.v1.session_config.SessionConfig._configure_llm

### cores.v1.auto_repair.AutoRepair
> Self-healing engine with task-based repair loop.

Flow per task:
    1. DIAGNOSE — identify exact is
- **Methods**: 22
- **Key Methods**: cores.v1.auto_repair.AutoRepair.__init__, cores.v1.auto_repair.AutoRepair._init_learned_strategy, cores.v1.auto_repair.AutoRepair.run_boot_repair, cores.v1.auto_repair.AutoRepair.repair_skill, cores.v1.auto_repair.AutoRepair.on_repair_requested, cores.v1.auto_repair.AutoRepair._scan_all_skills, cores.v1.auto_repair.AutoRepair._list_all_skills, cores.v1.auto_repair.AutoRepair._diagnose_skill, cores.v1.auto_repair.AutoRepair._get_skill_path, cores.v1.auto_repair.AutoRepair._execute_repair_task

### cores.v1.self_reflection.SelfReflection
> Autonomiczny silnik autorefleksji systemu evo-engine.
- **Methods**: 22
- **Key Methods**: cores.v1.self_reflection.SelfReflection.__init__, cores.v1.self_reflection.SelfReflection.journal, cores.v1.self_reflection.SelfReflection.snapshot, cores.v1.self_reflection.SelfReflection.start_operation, cores.v1.self_reflection.SelfReflection.end_operation, cores.v1.self_reflection.SelfReflection.record_skill_outcome, cores.v1.self_reflection.SelfReflection.check_stall, cores.v1.self_reflection.SelfReflection._trigger_event, cores.v1.self_reflection.SelfReflection.run_diagnostic, cores.v1.self_reflection.SelfReflection._check_llm_health

### cores.v1.skill_manager.SkillManager
- **Methods**: 22
- **Key Methods**: cores.v1.skill_manager.SkillManager.__init__, cores.v1.skill_manager.SkillManager._collect_versions, cores.v1.skill_manager.SkillManager.list_skills, cores.v1.skill_manager.SkillManager._is_rolled_back, cores.v1.skill_manager.SkillManager.latest_v, cores.v1.skill_manager.SkillManager._active_provider, cores.v1.skill_manager.SkillManager.skill_path, cores.v1.skill_manager.SkillManager.create_skill, cores.v1.skill_manager.SkillManager.diagnose_skill, cores.v1.skill_manager.SkillManager._raw_test

### cores.v1.evo_journal.EvolutionJournal
> Persistent journal for evolutionary cycles.

Tracks:
  - Per-skill evolution history (iterations, sc
- **Methods**: 17
- **Key Methods**: cores.v1.evo_journal.EvolutionJournal.__init__, cores.v1.evo_journal.EvolutionJournal._load_summary, cores.v1.evo_journal.EvolutionJournal._save_summary, cores.v1.evo_journal.EvolutionJournal._append_entry, cores.v1.evo_journal.EvolutionJournal.start_evolution, cores.v1.evo_journal.EvolutionJournal.finish_evolution, cores.v1.evo_journal.EvolutionJournal.reflect, cores.v1.evo_journal.EvolutionJournal.get_skill_history, cores.v1.evo_journal.EvolutionJournal.get_global_stats, cores.v1.evo_journal.EvolutionJournal.format_report

### cores.v1.intent_engine.IntentEngine
> Context-aware intent detection with ML-based classification.

Stages:
  0. Trivial filter (very shor
- **Methods**: 17
- **Key Methods**: cores.v1.intent_engine.IntentEngine.__init__, cores.v1.intent_engine.IntentEngine.classifier, cores.v1.intent_engine.IntentEngine.save, cores.v1.intent_engine.IntentEngine._update_topics_from_result, cores.v1.intent_engine.IntentEngine._recent_topic, cores.v1.intent_engine.IntentEngine._build_context, cores.v1.intent_engine.IntentEngine.record_skill_use, cores.v1.intent_engine.IntentEngine.record_correction, cores.v1.intent_engine.IntentEngine.record_success, cores.v1.intent_engine.IntentEngine.record_unhandled

### cores.v1.repair_journal.RepairJournal
> Persistent journal of all repair attempts with LLM-powered learning.

Stores JSONL at logs/repair/re
- **Methods**: 16
- **Key Methods**: cores.v1.repair_journal.RepairJournal.__init__, cores.v1.repair_journal.RepairJournal.record_attempt, cores.v1.repair_journal.RepairJournal.record_success, cores.v1.repair_journal.RepairJournal.get_known_fix, cores.v1.repair_journal.RepairJournal.get_failed_fixes, cores.v1.repair_journal.RepairJournal.get_history, cores.v1.repair_journal.RepairJournal.get_stats, cores.v1.repair_journal.RepairJournal.ask_llm_diagnosis, cores.v1.repair_journal.RepairJournal.ask_llm_and_try, cores.v1.repair_journal.RepairJournal._error_signature

### cores.v1.smart_intent.SmartIntentClassifier
> ML-based intent classifier for evo-engine.

Replaces all hardcoded _KW_* tuples with learnable embed
- **Methods**: 15
- **Key Methods**: cores.v1.smart_intent.SmartIntentClassifier.__init__, cores.v1.smart_intent.SmartIntentClassifier._training_path, cores.v1.smart_intent.SmartIntentClassifier._load_training_data, cores.v1.smart_intent.SmartIntentClassifier._save_training_data, cores.v1.smart_intent.SmartIntentClassifier.add_example, cores.v1.smart_intent.SmartIntentClassifier.learn_from_correction, cores.v1.smart_intent.SmartIntentClassifier.learn_from_success, cores.v1.smart_intent.SmartIntentClassifier._generate_variations, cores.v1.smart_intent.SmartIntentClassifier._ensure_embeddings, cores.v1.smart_intent.SmartIntentClassifier.classify

### cores.v1.intent.SmartIntentClassifier
> 3-tier ML intent classifier:
1. Embeddings (sbert/tf-idf/bow) — fastest, 90%+ accuracy
2. Local LLM 
- **Methods**: 15
- **Key Methods**: cores.v1.intent.SmartIntentClassifier.__init__, cores.v1.intent.SmartIntentClassifier._load_training, cores.v1.intent.SmartIntentClassifier._rebuild_skill_vectors, cores.v1.intent.SmartIntentClassifier.classify, cores.v1.intent.SmartIntentClassifier._embedding_classify, cores.v1.intent.SmartIntentClassifier._cosine_classify, cores.v1.intent.SmartIntentClassifier._extract_model_target, cores.v1.intent.SmartIntentClassifier._llm_classify, cores.v1.intent.SmartIntentClassifier._record_use, cores.v1.intent.SmartIntentClassifier.learn_from_correction

### cores.v1.stable_snapshot.StableSnapshot
> Manages stable/bugfix/feature versions of skills.

Key principles:
- Stable is SACRED — only promote
- **Methods**: 14
- **Key Methods**: cores.v1.stable_snapshot.StableSnapshot.__init__, cores.v1.stable_snapshot.StableSnapshot.save_as_stable, cores.v1.stable_snapshot.StableSnapshot.create_branch, cores.v1.stable_snapshot.StableSnapshot.promote_branch, cores.v1.stable_snapshot.StableSnapshot.restore_stable, cores.v1.stable_snapshot.StableSnapshot.validate_against_stable, cores.v1.stable_snapshot.StableSnapshot.list_branches, cores.v1.stable_snapshot.StableSnapshot._detect_provider, cores.v1.stable_snapshot.StableSnapshot._find_current_version, cores.v1.stable_snapshot.StableSnapshot._copy_skill_files

### cores.v1.provider_selector.ProviderChain
> Ordered provider fallback chain with auto-degradation.

Tracks failures per provider and automatical
- **Methods**: 13
- **Key Methods**: cores.v1.provider_selector.ProviderChain.__init__, cores.v1.provider_selector.ProviderChain._key, cores.v1.provider_selector.ProviderChain._get_stats, cores.v1.provider_selector.ProviderChain.build_chain, cores.v1.provider_selector.ProviderChain._reorder_by_fallback, cores.v1.provider_selector.ProviderChain.select_with_fallback, cores.v1.provider_selector.ProviderChain.select_best, cores.v1.provider_selector.ProviderChain.record_failure, cores.v1.provider_selector.ProviderChain.record_success, cores.v1.provider_selector.ProviderChain._cooldown_expired

### cores.v1.proactive_scheduler.ProactiveScheduler
> Thread-based periodic task scheduler.

Usage:
    scheduler = ProactiveScheduler()
    scheduler.reg
- **Methods**: 13
- **Key Methods**: cores.v1.proactive_scheduler.ProactiveScheduler.__init__, cores.v1.proactive_scheduler.ProactiveScheduler.register, cores.v1.proactive_scheduler.ProactiveScheduler.unregister, cores.v1.proactive_scheduler.ProactiveScheduler.enable, cores.v1.proactive_scheduler.ProactiveScheduler.disable, cores.v1.proactive_scheduler.ProactiveScheduler.start, cores.v1.proactive_scheduler.ProactiveScheduler.stop, cores.v1.proactive_scheduler.ProactiveScheduler.is_running, cores.v1.proactive_scheduler.ProactiveScheduler._tick, cores.v1.proactive_scheduler.ProactiveScheduler._execute_task

### skills.git_ops.v1.skill.GitOpsSkill
> Manage local git repos for skill development and versioning.
- **Methods**: 13
- **Key Methods**: skills.git_ops.v1.skill.GitOpsSkill.__init__, skills.git_ops.v1.skill.GitOpsSkill._run, skills.git_ops.v1.skill.GitOpsSkill.init, skills.git_ops.v1.skill.GitOpsSkill.status, skills.git_ops.v1.skill.GitOpsSkill.add, skills.git_ops.v1.skill.GitOpsSkill.commit, skills.git_ops.v1.skill.GitOpsSkill.log, skills.git_ops.v1.skill.GitOpsSkill.diff, skills.git_ops.v1.skill.GitOpsSkill.tag, skills.git_ops.v1.skill.GitOpsSkill.checkout

### cores.v1.quality_gate.SkillQualityGate
> Validates skill quality before registration.
Each check contributes a weight to the final score.
- **Methods**: 12
- **Key Methods**: cores.v1.quality_gate.SkillQualityGate.__init__, cores.v1.quality_gate.SkillQualityGate.evaluate, cores.v1.quality_gate.SkillQualityGate.should_register, cores.v1.quality_gate.SkillQualityGate.compare, cores.v1.quality_gate.SkillQualityGate._check_preflight, cores.v1.quality_gate.SkillQualityGate._check_manifest_schema, cores.v1.quality_gate.SkillQualityGate._check_health, cores.v1.quality_gate.SkillQualityGate._check_test_exec, cores.v1.quality_gate.SkillQualityGate._check_output, cores.v1.quality_gate.SkillQualityGate._check_code_quality

### cores.v1.resource_monitor.ResourceMonitor
> Detects CPU, RAM, GPU, disk, installed packages.
- **Methods**: 12
- **Key Methods**: cores.v1.resource_monitor.ResourceMonitor.__init__, cores.v1.resource_monitor.ResourceMonitor.snapshot, cores.v1.resource_monitor.ResourceMonitor._cpu_count, cores.v1.resource_monitor.ResourceMonitor._ram_total, cores.v1.resource_monitor.ResourceMonitor._ram_available, cores.v1.resource_monitor.ResourceMonitor._ram_from_proc, cores.v1.resource_monitor.ResourceMonitor._disk_free, cores.v1.resource_monitor.ResourceMonitor._detect_gpu, cores.v1.resource_monitor.ResourceMonitor._installed_packages, cores.v1.resource_monitor.ResourceMonitor.has_command

### cores.v1.user_memory.UserMemory
> Persistent long-term memory for user preferences and directives.

Directives are short text notes th
- **Methods**: 12
- **Key Methods**: cores.v1.user_memory.UserMemory.__init__, cores.v1.user_memory.UserMemory.directives, cores.v1.user_memory.UserMemory.add, cores.v1.user_memory.UserMemory.remove, cores.v1.user_memory.UserMemory.clear_all, cores.v1.user_memory.UserMemory.voice_mode, cores.v1.user_memory.UserMemory.set_voice_mode, cores.v1.user_memory.UserMemory.has_directive, cores.v1.user_memory.UserMemory.build_system_context, cores.v1.user_memory.UserMemory.looks_like_preference

### cores.v1.provider_selector.ProviderSelector
> Selects the best available provider for a capability.
- **Methods**: 12
- **Key Methods**: cores.v1.provider_selector.ProviderSelector.__init__, cores.v1.provider_selector.ProviderSelector.list_capabilities, cores.v1.provider_selector.ProviderSelector.list_providers, cores.v1.provider_selector.ProviderSelector.load_manifest, cores.v1.provider_selector.ProviderSelector.load_meta, cores.v1.provider_selector.ProviderSelector.get_provider_info, cores.v1.provider_selector.ProviderSelector.select, cores.v1.provider_selector.ProviderSelector._check_runnable, cores.v1.provider_selector.ProviderSelector._score, cores.v1.provider_selector.ProviderSelector._fallback

### cores.v1.llm_client.LLMClient
> Tiered LLM routing: free remote → local (ollama) → paid remote.
- Rate-limited models get cooldown (
- **Methods**: 12
- **Key Methods**: cores.v1.llm_client.LLMClient.__init__, cores.v1.llm_client.LLMClient.tier_info, cores.v1.llm_client.LLMClient._is_available, cores.v1.llm_client.LLMClient._report_ok, cores.v1.llm_client.LLMClient._report_fail, cores.v1.llm_client.LLMClient.chat, cores.v1.llm_client.LLMClient._build_error_msg, cores.v1.llm_client.LLMClient._try_model, cores.v1.llm_client.LLMClient._get_unavailable_reason, cores.v1.llm_client.LLMClient.gen_code

### cores.v1.garbage_collector.EvolutionGarbageCollector
> Cleans up failed evolution stubs, promotes stable versions.
- **Methods**: 11
- **Key Methods**: cores.v1.garbage_collector.EvolutionGarbageCollector.__init__, cores.v1.garbage_collector.EvolutionGarbageCollector.is_stub, cores.v1.garbage_collector.EvolutionGarbageCollector.is_broken, cores.v1.garbage_collector.EvolutionGarbageCollector.scan_versions, cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_provider, cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_legacy, cores.v1.garbage_collector.EvolutionGarbageCollector.migrate_to_stable_latest, cores.v1.garbage_collector.EvolutionGarbageCollector._copy_version, cores.v1.garbage_collector.EvolutionGarbageCollector.trim_archive, cores.v1.garbage_collector.EvolutionGarbageCollector.cleanup_all

## Data Transformation Functions

Key functions that process and transform data:

### scripts.benchmark_system.validate_manifest_schemas
> Check which manifests are valid JSON.
- **Output to**: skills_dir.iterdir, skills_dir.exists, skill_dir.name.startswith, manifest.exists, json.loads

### cores.v1.config._parse_models_override
- **Output to**: isinstance, isinstance, None.strip, x.strip, None.strip

### cores.v1.evo_journal.EvolutionJournal.format_report
> Human-readable evolution report.
- **Output to**: self.get_global_stats, stats.get, None.join, lines.append, None.join

### cores.v1.repair_journal.RepairJournal.format_report
> Human-readable repair report.
- **Output to**: self.get_stats, self.get_history, None.join, lines.append, lines.append

### cores.v1.auto_repair.AutoRepair.validate_model
> Check if a model is suitable for chat (not code-only).
Returns (valid: bool, reason: str).
- **Output to**: model_name.lower

### cores.v1.adaptive_monitor.AdaptiveResourceMonitor.format_status
> One-line status string for display.
- **Output to**: self.snapshot

### cores.v1.skill_validator._validate_stt
> STT-specific validation: check for hardware errors, silence, empty transcription.
- **Output to**: result.get, isinstance, inner.get, inner.get, ValidationResult

### cores.v1.skill_validator._validate_shell
> Shell-specific validation: check exit code.
- **Output to**: result.get, inner.get, isinstance, ValidationResult, inner.get

### cores.v1.skill_validator._validate_tts
> TTS-specific validation: check for error field.
- **Output to**: result.get, inner.get, isinstance, ValidationResult

### cores.v1.skill_validator._validate_web_search
> Web search validation: check for empty results, especially local network queries.
- **Output to**: result.get, inner.get, None.lower, any, isinstance

### cores.v1.skill_validator.SkillValidator.validate
> Validate a skill execution result.

1. Check outer success flag
2. Check inner success flag
3. Run s
- **Output to**: result.get, ValidationResult, result.get, ValidationResult, isinstance

### cores.v1.skill_schema.SkillSchemaValidator.validate_manifest
> Validate a skill manifest against schema.
- **Output to**: self._validate_against_schema

### cores.v1.skill_schema.SkillSchemaValidator.validate_output
> Validate skill execute() output.
- **Output to**: self._validate_against_schema

### cores.v1.skill_schema.SkillSchemaValidator.validate_file
> Validate a manifest.json file.
- **Output to**: path.exists, ValidationResult, json.loads, self.validate_manifest, path.read_text

### cores.v1.skill_schema.SkillSchemaValidator._validate_against_schema
> Internal validation using simple schema checking.
- **Output to**: self._schemas.get, schema.get, ValidationResult, None.items, None.items

### cores.v1.skill_schema.validate_manifest_file
> Quick validation of a manifest.json file.
- **Output to**: SkillSchemaValidator, validator.validate_file

### cores.v1.smart_intent.EmbeddingEngine.encode
> Encode texts to vectors.
- **Output to**: self._try_init, self._model.encode, None.toarray, TfidfVectorizer, None.toarray

### cores.v1.stable_snapshot.StableSnapshot.validate_against_stable
> Compare current version against stable reference.

Returns: {"matches": bool, "diff_lines": int, "he
- **Output to**: self._find_current_version, stable_skill.read_text, current_skill.read_text, cores.v1.prompts.PromptManager.list, self._check_health

### cores.v1.evo_engine.EvoEngine._validate_result
> Validate whether the skill result actually achieved the goal.
Returns {verdict: success|partial|fail
- **Output to**: result.get, result.get, isinstance, inner.get, inner.get

### cores.v1.session_config.SessionConfig.format_change_feedback
> Format configuration change for user feedback.
- **Output to**: category_names.get

### cores.v1.logger.Logger._format_markdown
> Format entry as markdown with code blocks.
- **Output to**: entry.get, entry.get, entry.get, entry.get, None.join

### cores.v1.proactive_scheduler.ProactiveScheduler.format_status
> Human-readable status summary.
- **Output to**: self.status, None.join, lines.append, len

### skills.kalkulator.v47.skill.Kalkulator._validate_expression
- **Output to**: ast.walk, ast.parse, isinstance, ValueError, isinstance

### skills.gbp_to_jpy_converter.v5.skill.parse_amount_from_text
- **Output to**: text.lower, replacements.items, re.findall, text_lower.replace, float

### skills.gbp_to_jpy_converter.v4.skill.parse_amount_from_text
- **Output to**: text.lower, replacements.items, re.findall, text_lower.replace, float

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `core.main` - 147 calls
- `seeds.core_v1.main` - 108 calls
- `scripts.benchmark_system.run_all_benchmarks` - 63 calls
- `cores.v1.self_reflection.SelfReflection.run_diagnostic` - 53 calls
- `cores.v1.intent_engine.IntentEngine.analyze` - 48 calls
- `scripts.simulate.Simulator.run_scenario` - 47 calls
- `cores.v1.core.main` - 45 calls
- `cores.v1.skill_logger.get_markdown_logs` - 44 calls
- `cores.v1.skill_manager.SkillManager.smart_evolve` - 43 calls
- `cores.v1.intent.SmartIntentClassifier.classify` - 43 calls
- `cores.v1.evo_engine.EvoEngine.handle_request` - 42 calls
- `cores.v1.metrics_collector.MetricsCollector.compute_system_health` - 41 calls
- `cores.v1.llm_client.LLMClient.chat` - 37 calls
- `cli.cmd_cache_reset` - 36 calls
- `cores.v1.resource_monitor.ResourceMonitor.can_run` - 36 calls
- `scripts.generate_manifests.main` - 34 calls
- `main.bootstrap` - 33 calls
- `skills.shell.v2.skill.ShellSkill.execute` - 33 calls
- `examples.skills.01_create.main` - 33 calls
- `cores.v1.evo_engine.EvoEngine.evolve_skill` - 32 calls
- `examples.advanced.01_pipeline.main` - 32 calls
- `cores.v1.system_identity.SystemIdentity.build_system_prompt` - 31 calls
- `cores.v1.skill_manager.SkillManager.create_skill` - 31 calls
- `cli.cmd_status` - 30 calls
- `cli.cmd_logs_reset` - 29 calls
- `cores.v1.repair_journal.RepairJournal.ask_llm_and_try` - 28 calls
- `scripts.simulate.Simulator.run_all` - 27 calls
- `cores.v1.preflight.SkillPreflight.check_imports` - 27 calls
- `skills.shell.v1.skill.ShellSkill.execute` - 27 calls
- `skills.benchmark.v1.skill.BenchmarkSkill.execute` - 27 calls
- `cores.v1.preflight.SkillPreflight.auto_fix_imports` - 26 calls
- `seeds.core_v1.SkillManager.exec_skill` - 26 calls
- `scripts.generate_manifests.generate_manifest_for_skill` - 25 calls
- `cores.v1.skill_logger.get_health_markdown` - 25 calls
- `skills.local_computer_discovery.v3.skill.LocalComputerDiscovery.execute` - 24 calls
- `cli.main_cli` - 23 calls
- `scripts.benchmark_system.main` - 23 calls
- `skills.git_ops.v1.skill.GitOpsSkill.execute` - 23 calls
- `skills.stt.providers.vosk.archive.v6.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.archive.v7.skill.STTSkill.execute` - 23 calls

## System Interactions

How components interact:

```mermaid
graph TD
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.