# System Architecture Analysis

## Overview

- **Project**: .
- **Analysis Mode**: static
- **Total Functions**: 1563
- **Total Classes**: 193
- **Modules**: 161
- **Entry Points**: 0

## Architecture by Module

### cores.v1.core
- **Functions**: 63
- **File**: `core.py`

### root.core
- **Functions**: 29
- **Classes**: 6
- **File**: `core.py`

### scripts_cores_seeds.core
- **Functions**: 29
- **Classes**: 6
- **File**: `core.py`

### skills_examples.core
- **Functions**: 29
- **Classes**: 6
- **File**: `core.py`

### cores.v1.reflection_engine
- **Functions**: 27
- **Classes**: 4
- **File**: `reflection_engine.py`

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

### cores.v1.evo_engine
- **Functions**: 23
- **Classes**: 2
- **File**: `evo_engine.py`

### cores.v1.session_config
- **Functions**: 23
- **Classes**: 2
- **File**: `session_config.py`

### skills.document_publisher.v1.skill
- **Functions**: 22
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.drift_detector
- **Functions**: 21
- **Classes**: 3
- **File**: `drift_detector.py`

### skills.social_media_manager.v1.skill
- **Functions**: 21
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.evo_journal
- **Functions**: 20
- **Classes**: 2
- **File**: `evo_journal.py`

### cores.v1.smart_intent
- **Functions**: 20
- **Classes**: 3
- **File**: `smart_intent.py`

### cores.v1.metrics_collector
- **Functions**: 19
- **Classes**: 4
- **File**: `metrics_collector.py`

### skills.web_automation.v1.skill
- **Functions**: 19
- **Classes**: 1
- **File**: `skill.py`

### skills.task_manager.v1.skill
- **Functions**: 18
- **Classes**: 1
- **File**: `skill.py`

### skills.benchmark.v2.skill
- **Functions**: 18
- **Classes**: 1
- **File**: `skill.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

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

### cores.v1.skill_manager.SkillManager
- **Methods**: 22
- **Key Methods**: cores.v1.skill_manager.SkillManager.__init__, cores.v1.skill_manager.SkillManager._collect_versions, cores.v1.skill_manager.SkillManager.list_skills, cores.v1.skill_manager.SkillManager._is_rolled_back, cores.v1.skill_manager.SkillManager.latest_v, cores.v1.skill_manager.SkillManager._active_provider, cores.v1.skill_manager.SkillManager.skill_path, cores.v1.skill_manager.SkillManager.create_skill, cores.v1.skill_manager.SkillManager.diagnose_skill, cores.v1.skill_manager.SkillManager._raw_test

### cores.v1.reflection_engine.ReflectionRuleEngine
> Engine that evaluates and executes declarative reflection rules.
- **Methods**: 19
- **Key Methods**: cores.v1.reflection_engine.ReflectionRuleEngine.__init__, cores.v1.reflection_engine.ReflectionRuleEngine._load_rules, cores.v1.reflection_engine.ReflectionRuleEngine._register_default_actions, cores.v1.reflection_engine.ReflectionRuleEngine.reload_rules, cores.v1.reflection_engine.ReflectionRuleEngine.record_failure, cores.v1.reflection_engine.ReflectionRuleEngine.record_success, cores.v1.reflection_engine.ReflectionRuleEngine.evaluate_rules, cores.v1.reflection_engine.ReflectionRuleEngine._match_trigger, cores.v1.reflection_engine.ReflectionRuleEngine._get_priority, cores.v1.reflection_engine.ReflectionRuleEngine.execute_action

### skills.document_publisher.v1.skill.DocumentPublisherSkill
> Document publishing and sharing system.
- **Methods**: 19
- **Key Methods**: skills.document_publisher.v1.skill.DocumentPublisherSkill.__init__, skills.document_publisher.v1.skill.DocumentPublisherSkill._load_index, skills.document_publisher.v1.skill.DocumentPublisherSkill._save_index, skills.document_publisher.v1.skill.DocumentPublisherSkill._read_file, skills.document_publisher.v1.skill.DocumentPublisherSkill.generate_html, skills.document_publisher.v1.skill.DocumentPublisherSkill._markdown_to_html, skills.document_publisher.v1.skill.DocumentPublisherSkill._plain_text_to_html, skills.document_publisher.v1.skill.DocumentPublisherSkill._escape_html, skills.document_publisher.v1.skill.DocumentPublisherSkill._apply_default_template, skills.document_publisher.v1.skill.DocumentPublisherSkill._apply_minimal_template

### skills.social_media_manager.v1.skill.SocialMediaManagerSkill
> Social media content management and scheduling.
- **Methods**: 18
- **Key Methods**: skills.social_media_manager.v1.skill.SocialMediaManagerSkill.__init__, skills.social_media_manager.v1.skill.SocialMediaManagerSkill._ensure_defaults, skills.social_media_manager.v1.skill.SocialMediaManagerSkill._load_posts, skills.social_media_manager.v1.skill.SocialMediaManagerSkill._save_posts, skills.social_media_manager.v1.skill.SocialMediaManagerSkill._load_templates, skills.social_media_manager.v1.skill.SocialMediaManagerSkill.create_post, skills.social_media_manager.v1.skill.SocialMediaManagerSkill.schedule_post, skills.social_media_manager.v1.skill.SocialMediaManagerSkill._parse_relative_time, skills.social_media_manager.v1.skill.SocialMediaManagerSkill.generate_content, skills.social_media_manager.v1.skill.SocialMediaManagerSkill._generate_key_points

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

### cores.v1.evo_engine.EvoEngine
> Generic evolutionary algorithm:
1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
 
- **Methods**: 16
- **Key Methods**: cores.v1.evo_engine.EvoEngine.__init__, cores.v1.evo_engine.EvoEngine.set_reflection, cores.v1.evo_engine.EvoEngine.handle_request, cores.v1.evo_engine.EvoEngine._run_auto_reflection, cores.v1.evo_engine.EvoEngine._execute_with_validation, cores.v1.evo_engine.EvoEngine._exec_prepare, cores.v1.evo_engine.EvoEngine._exec_attempt, cores.v1.evo_engine.EvoEngine._exec_handle_success, cores.v1.evo_engine.EvoEngine._exec_handle_partial, cores.v1.evo_engine.EvoEngine._exec_handle_failure

### skills.web_automation.v1.skill.WebAutomationSkill
> Browser automation using Playwright.
- **Methods**: 16
- **Key Methods**: skills.web_automation.v1.skill.WebAutomationSkill.__init__, skills.web_automation.v1.skill.WebAutomationSkill._ensure_playwright, skills.web_automation.v1.skill.WebAutomationSkill._get_page, skills.web_automation.v1.skill.WebAutomationSkill.navigate, skills.web_automation.v1.skill.WebAutomationSkill.click, skills.web_automation.v1.skill.WebAutomationSkill.type, skills.web_automation.v1.skill.WebAutomationSkill.fill, skills.web_automation.v1.skill.WebAutomationSkill.extract_text, skills.web_automation.v1.skill.WebAutomationSkill.get_attribute, skills.web_automation.v1.skill.WebAutomationSkill.screenshot

### cores.v1.smart_intent.SmartIntentClassifier
> ML-based intent classifier for evo-engine.

Replaces all hardcoded _KW_* tuples with learnable embed
- **Methods**: 15
- **Key Methods**: cores.v1.smart_intent.SmartIntentClassifier.__init__, cores.v1.smart_intent.SmartIntentClassifier._training_path, cores.v1.smart_intent.SmartIntentClassifier._load_training_data, cores.v1.smart_intent.SmartIntentClassifier._save_training_data, cores.v1.smart_intent.SmartIntentClassifier.add_example, cores.v1.smart_intent.SmartIntentClassifier.learn_from_correction, cores.v1.smart_intent.SmartIntentClassifier.learn_from_success, cores.v1.smart_intent.SmartIntentClassifier._generate_variations, cores.v1.smart_intent.SmartIntentClassifier._ensure_embeddings, cores.v1.smart_intent.SmartIntentClassifier.classify

### cores.v1.drift_detector.DriftDetector
> Detects drift between manifest declarations and runtime state.
- **Methods**: 15
- **Key Methods**: cores.v1.drift_detector.DriftDetector.__init__, cores.v1.drift_detector.DriftDetector.quality_gate, cores.v1.drift_detector.DriftDetector.detect, cores.v1.drift_detector.DriftDetector.detect_all, cores.v1.drift_detector.DriftDetector._check_interface_drift, cores.v1.drift_detector.DriftDetector._check_version_drift, cores.v1.drift_detector.DriftDetector._check_provider_drift, cores.v1.drift_detector.DriftDetector._check_quality_drift, cores.v1.drift_detector.DriftDetector._find_latest_version, cores.v1.drift_detector.DriftDetector._count_versions

### cores.v1.intent.SmartIntentClassifier
> 3-tier ML intent classifier:
1. Embeddings (sbert/tf-idf/bow) — fastest, 90%+ accuracy
2. Local LLM 
- **Methods**: 15
- **Key Methods**: cores.v1.intent.SmartIntentClassifier.__init__, cores.v1.intent.SmartIntentClassifier._load_training, cores.v1.intent.SmartIntentClassifier._rebuild_skill_vectors, cores.v1.intent.SmartIntentClassifier.classify, cores.v1.intent.SmartIntentClassifier._embedding_classify, cores.v1.intent.SmartIntentClassifier._cosine_classify, cores.v1.intent.SmartIntentClassifier._extract_model_target, cores.v1.intent.SmartIntentClassifier._llm_classify, cores.v1.intent.SmartIntentClassifier._record_use, cores.v1.intent.SmartIntentClassifier.learn_from_correction

### skills.task_manager.v1.skill.TaskManagerSkill
> Task and reminder management.
- **Methods**: 15
- **Key Methods**: skills.task_manager.v1.skill.TaskManagerSkill.__init__, skills.task_manager.v1.skill.TaskManagerSkill._ensure_storage, skills.task_manager.v1.skill.TaskManagerSkill._load_tasks, skills.task_manager.v1.skill.TaskManagerSkill._save_tasks, skills.task_manager.v1.skill.TaskManagerSkill._parse_due_date, skills.task_manager.v1.skill.TaskManagerSkill.add, skills.task_manager.v1.skill.TaskManagerSkill.list_tasks, skills.task_manager.v1.skill.TaskManagerSkill.complete, skills.task_manager.v1.skill.TaskManagerSkill.delete, skills.task_manager.v1.skill.TaskManagerSkill.update

### skills.benchmark.v2.skill.BenchmarkSkill
> Analyzes and benchmarks LLM models for goal-based recommendations.
- **Methods**: 15
- **Key Methods**: skills.benchmark.v2.skill.BenchmarkSkill.__init__, skills.benchmark.v2.skill.BenchmarkSkill._load_config, skills.benchmark.v2.skill.BenchmarkSkill._get_models_from_tier, skills.benchmark.v2.skill.BenchmarkSkill._get_api_key, skills.benchmark.v2.skill.BenchmarkSkill._get_cached_recommendations, skills.benchmark.v2.skill.BenchmarkSkill.execute, skills.benchmark.v2.skill.BenchmarkSkill._recommend_models_live, skills.benchmark.v2.skill.BenchmarkSkill._get_model_param_size, skills.benchmark.v2.skill.BenchmarkSkill.BENCHMARK_PROFILES, skills.benchmark.v2.skill.BenchmarkSkill._call_model_for_benchmark

### cores.v1.self_reflection.SelfReflection
> Autonomiczny silnik autorefleksji systemu evo-engine.
- **Methods**: 14
- **Key Methods**: cores.v1.self_reflection.SelfReflection.__init__, cores.v1.self_reflection.SelfReflection.journal, cores.v1.self_reflection.SelfReflection.snapshot, cores.v1.self_reflection.SelfReflection.start_operation, cores.v1.self_reflection.SelfReflection.end_operation, cores.v1.self_reflection.SelfReflection.record_skill_outcome, cores.v1.self_reflection.SelfReflection.check_stall, cores.v1.self_reflection.SelfReflection._trigger_event, cores.v1.self_reflection.SelfReflection.run_diagnostic, cores.v1.self_reflection.SelfReflection._print_report

### cores.v1.stable_snapshot.StableSnapshot
> Manages stable/bugfix/feature versions of skills.

Key principles:
- Stable is SACRED — only promote
- **Methods**: 14
- **Key Methods**: cores.v1.stable_snapshot.StableSnapshot.__init__, cores.v1.stable_snapshot.StableSnapshot.save_as_stable, cores.v1.stable_snapshot.StableSnapshot.create_branch, cores.v1.stable_snapshot.StableSnapshot.promote_branch, cores.v1.stable_snapshot.StableSnapshot.restore_stable, cores.v1.stable_snapshot.StableSnapshot.validate_against_stable, cores.v1.stable_snapshot.StableSnapshot.list_branches, cores.v1.stable_snapshot.StableSnapshot._detect_provider, cores.v1.stable_snapshot.StableSnapshot._find_current_version, cores.v1.stable_snapshot.StableSnapshot._copy_skill_files

### skills.auto.v2.skill.AutoSkillBuilder
- **Methods**: 14
- **Key Methods**: skills.auto.v2.skill.AutoSkillBuilder.execute, skills.auto.v2.skill.AutoSkillBuilder._parse_command, skills.auto.v2.skill.AutoSkillBuilder._execute_command, skills.auto.v2.skill.AutoSkillBuilder._get_weather, skills.auto.v2.skill.AutoSkillBuilder._get_time, skills.auto.v2.skill.AutoSkillBuilder._get_date, skills.auto.v2.skill.AutoSkillBuilder._translate_text, skills.auto.v2.skill.AutoSkillBuilder._calculate_expression, skills.auto.v2.skill.AutoSkillBuilder._speak_text, skills.auto.v2.skill.AutoSkillBuilder._search_web

### skills.benchmark.v3.skill.BenchmarkSkill
> Analyzes and benchmarks LLM models for goal-based recommendations.
- **Methods**: 14
- **Key Methods**: skills.benchmark.v3.skill.BenchmarkSkill.__init__, skills.benchmark.v3.skill.BenchmarkSkill._load_config, skills.benchmark.v3.skill.BenchmarkSkill._get_models_from_tier, skills.benchmark.v3.skill.BenchmarkSkill._get_api_key, skills.benchmark.v3.skill.BenchmarkSkill._get_cached_recommendations, skills.benchmark.v3.skill.BenchmarkSkill._call_model_for_benchmark, skills.benchmark.v3.skill.BenchmarkSkill.execute, skills.benchmark.v3.skill.BenchmarkSkill._recommend_models_live, skills.benchmark.v3.skill.BenchmarkSkill._get_model_param_size, skills.benchmark.v3.skill.BenchmarkSkill._compare_models

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

### cores.v1.base_skill.SkillManifest.validate_input
> Validate params against manifest input schema. Returns list of errors.
- **Output to**: errors.append, inp.type.rstrip, TYPE_MAP.get, errors.append, isinstance

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

### cores.v1.pipeline_manager.PipelineManager._process_input
> Process input dict, substituting variables in all string values.
- **Output to**: isinstance, isinstance, self._process_input, isinstance, input_data.items

### cores.v1.logger.Logger._format_markdown
> Format entry as markdown with code blocks.
- **Output to**: entry.get, entry.get, entry.get, entry.get, None.join

### cores.v1.proactive_scheduler.ProactiveScheduler.format_status
> Human-readable status summary.
- **Output to**: self.status, None.join, lines.append, len

### cores.v1.intent.embedding.EmbeddingEngine.encode
> Encode texts to vectors.
- **Output to**: self._try_init, self._model.encode, None.toarray, TfidfVectorizer, None.toarray

### skills.converter.v1.skill.ConverterSkill.convert_unit
> Convert between units.
- **Output to**: self.UNITS.items, round, str

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `core.main` - 147 calls
- `seeds.core_v1.main` - 108 calls
- `scripts.benchmark_system.run_all_benchmarks` - 63 calls
- `cores.v1.self_reflection.SelfReflection.run_diagnostic` - 53 calls
- `cores.v1.evo_engine.EvoEngine.handle_request` - 49 calls
- `cores.v1.intent_engine.IntentEngine.analyze` - 48 calls
- `cores.v1.core.main` - 48 calls
- `scripts.simulate.Simulator.run_scenario` - 47 calls
- `cores.v1.skill_logger.get_markdown_logs` - 44 calls
- `cores.v1.skill_manager.SkillManager.smart_evolve` - 43 calls
- `cores.v1.intent.SmartIntentClassifier.classify` - 43 calls
- `cores.v1.metrics_collector.MetricsCollector.compute_system_health` - 41 calls
- `cores.v1.llm_client.LLMClient.chat` - 37 calls
- `skills.document_editor.v1.skill.DocumentEditorSkill.execute` - 37 calls
- `cli.cmd_cache_reset` - 36 calls
- `cores.v1.resource_monitor.ResourceMonitor.can_run` - 36 calls
- `skills.shell.v3.skill.ShellSkill.execute` - 36 calls
- `skills.web_automation.v1.skill.WebAutomationSkill.execute` - 36 calls
- `scripts.generate_manifests.main` - 34 calls
- `main.bootstrap` - 33 calls
- `cores.v1.skill_manager.SkillManager.create_skill` - 33 calls
- `skills.shell.v2.skill.ShellSkill.execute` - 33 calls
- `examples.skills.01_create.main` - 33 calls
- `cores.v1.evo_engine.EvoEngine.evolve_skill` - 32 calls
- `examples.advanced.01_pipeline.main` - 32 calls
- `cores.v1.system_identity.SystemIdentity.build_system_prompt` - 31 calls
- `cli.cmd_status` - 30 calls
- `cores.v1.base_skill.SkillManifest.from_dict` - 30 calls
- `skills.account_creator.v1.skill.AccountCreatorSkill.execute` - 30 calls
- `skills.task_manager.v1.skill.TaskManagerSkill.execute` - 30 calls
- `cli.cmd_logs_reset` - 29 calls
- `skills.text_summarizer.v1.skill.TextSummarizerSkill.summarize` - 29 calls
- `skills.document_editor.v1.skill.DocumentEditorSkill.find_replace` - 29 calls
- `cores.v1.repair_journal.RepairJournal.ask_llm_and_try` - 28 calls
- `scripts.simulate.Simulator.run_all` - 27 calls
- `cores.v1.preflight.SkillPreflight.check_imports` - 27 calls
- `skills.document_publisher.v1.skill.DocumentPublisherSkill.generate_html` - 27 calls
- `skills.document_search.v1.skill.DocumentSearchSkill.search_by_content` - 27 calls
- `skills.email_client.v1.skill.EmailClientSkill.execute` - 27 calls
- `cores.v1.preflight.SkillPreflight.auto_fix_imports` - 26 calls

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