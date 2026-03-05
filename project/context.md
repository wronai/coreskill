# System Architecture Analysis

## Overview

- **Project**: /home/tom/github/wronai/coreskill
- **Analysis Mode**: static
- **Total Functions**: 1720
- **Total Classes**: 209
- **Modules**: 170
- **Entry Points**: 1578

## Architecture by Module

### cores.v1.core
- **Functions**: 69
- **File**: `core.py`

### cores.v1.metrics_collector
- **Functions**: 32
- **Classes**: 4
- **File**: `metrics_collector.py`

### cores.v1.auto_repair
- **Functions**: 29
- **Classes**: 2
- **File**: `auto_repair.py`

### core
- **Functions**: 29
- **Classes**: 6
- **File**: `core.py`

### cores.v1.skill_manager
- **Functions**: 28
- **Classes**: 1
- **File**: `skill_manager.py`

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

### backend.main
- **Functions**: 24
- **Classes**: 4
- **File**: `main.py`

### cores.v1.intent_engine
- **Functions**: 23
- **Classes**: 1
- **File**: `intent_engine.py`

### cores.v1.evo_engine
- **Functions**: 23
- **Classes**: 2
- **File**: `evo_engine.py`

### cores.v1.session_config
- **Functions**: 23
- **Classes**: 2
- **File**: `session_config.py`

### cores.v1.smart_intent
- **Functions**: 22
- **Classes**: 3
- **File**: `smart_intent.py`

### skills.document_publisher.v1.skill
- **Functions**: 22
- **Classes**: 1
- **File**: `skill.py`

### TODO2.main
- **Functions**: 21
- **Classes**: 4
- **File**: `main.py`

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

### skills.web_automation.v1.skill
- **Functions**: 19
- **Classes**: 1
- **File**: `skill.py`

### skills.benchmark.v2.skill
- **Functions**: 18
- **Classes**: 1
- **File**: `skill.py`

## Key Entry Points

Main execution flows into the system:

### core.main
- **Calls**: core.load_state, Supervisor, core.cpr, core.cpr, core.cpr, core.cpr, core.save_state, state.get

### seeds.core_v1.main
- **Calls**: seeds.core_v1.load_state, Supervisor, seeds.core_v1.cpr, seeds.core_v1.cpr, seeds.core_v1.cpr, seeds.core_v1.cpr, seeds.core_v1.save_state, state.get

### examples.automations.task_management_automation.task_management_automation
> Complete task management workflow.
- **Calls**: print, print, print, print, examples.automations.task_management_automation.run_skill, list_result.get, print, examples.automations.task_management_automation.run_skill

### examples.automations.social_media_automation.social_media_automation
> Complete social media content workflow.
- **Calls**: print, print, print, examples.automations.social_media_automation.run_skill, content_result.get, print, examples.automations.social_media_automation.run_skill, analysis_result.get

### examples.automations.network_monitoring_automation.network_monitoring_automation
> Complete network monitoring workflow.
- **Calls**: print, print, print, targets.items, print, print, print, examples.automations.network_monitoring_automation.generate_network_report

### scripts.simulate.Simulator._final_report
- **Calls**: print, print, print, len, sum, cores.v1.prompts.PromptManager.list, print, print

### cores.v1.self_reflection.SelfReflection.run_diagnostic
> Uruchom pełną diagnostykę systemu.
- **Calls**: cores.v1.config.cpr, self._diagnostics.check_llm_health, findings.append, self._diagnostics.check_system_commands, findings.append, self._diagnostics.check_tts_backend, findings.append, self._diagnostics.check_disk_space

### backend.main.websocket_chat
- **Calls**: app.websocket, log.info, ws.accept, str, ws.send_json, active_connections.pop, chat_histories.pop, uuid.uuid4

### scripts.get_openrouter_key.main
- **Calls**: OpenRouterAutomationSkill, print, print, print, print, print, print, print

### cores.v1.evo_engine.EvoEngine.handle_request
> Full pipeline: analyze → execute/create/evolve → validate. No user prompts.
- **Calls**: analysis.get, analysis.get, analysis.get, analysis.get, cores.v1.config.cpr, self.log.core, self.failure_tracker.record_unhandled, self.llm.analyze_need

### scripts.simulate.Simulator.run_scenario
> Run a single scenario.
- **Calls**: scenario.get, scenario.get, print, print, print, SimulationResult, enumerate, result.finish

### cores.v1.skill_logger.get_markdown_logs
> Get logs formatted as markdown ready for LLM with code blocks.
- **Calls**: _SQLITE_PATH.exists, sqlite3.connect, conn.close, None.join, str, None.fetchall, None.fetchall, dict

### cores.v1.evo_engine.EvoEngine._autonomous_stt_repair
> Autonomous diagnosis and repair for STT empty transcription.
Returns (fixed, message, new_result).
- **Calls**: cores.v1.config.cpr, any, cores.v1.config.cpr, shutil.which, cores.v1.config.cpr, Path, cores.v1.config.cpr, cores.v1.config.cpr

### examples.openrouter_session_copy.main
- **Calls**: OpenRouterAutomationSkill, print, print, print, print, skill.list_available_browsers, print, browsers.get

### cores.v1.evo_engine.EvoEngine._exec_handle_failure
> Handle failure outcome. Returns True if should retry.
- **Calls**: cores.v1.config.cpr, seen_errors.add, self.evo_guard.record_error, self.journal.reflect, j_refl.get, j_refl.get, cores.v1.config.cpr, self.evo_guard.suggest_strategy

### TODO2.main.websocket_chat
- **Calls**: app.websocket, log.info, ws.accept, str, ws.send_json, active_connections.pop, chat_histories.pop, uuid.uuid4

### skills.benchmark.v2.skill.BenchmarkSkill._recommend_models_live
- **Calls**: params.get, params.get, params.get, self._get_models_from_tier, self._get_models_from_tier, live_results.sort, enumerate, self._get_model_param_size

### skills.benchmark.v3.skill.BenchmarkSkill._recommend_models_live
- **Calls**: params.get, params.get, params.get, self._get_models_from_tier, self._get_models_from_tier, live_results.sort, enumerate, self._get_model_param_size

### examples.automations.document_processing_pipeline.document_processing_pipeline
> Complete document processing workflow.
- **Calls**: print, print, print, examples.automations.document_processing_pipeline.run_skill, print, print, print, examples.automations.document_processing_pipeline.run_skill

### cores.v1.llm_client.LLMClient.chat
- **Calls**: self._is_available, bool, self._build_error_msg, os.environ.get, print, print, print, enumerate

### cores.v1.intent.SmartIntentClassifier.classify
> Classify user intent using 3-tier approach.

Args:
    user_msg: User message to classify
    skills: List of available skills
    context: Additional
- **Calls**: user_msg.strip, user_msg.lower, cores.v1.i18n.match_any_keyword, cores.v1.i18n.match_any_keyword, cores.v1.i18n.match_any_keyword, cores.v1.i18n.match_any_keyword, cores.v1.i18n.match_any_keyword, cores.v1.i18n.match_any_keyword

### skills.document_editor.v1.skill.DocumentEditorSkill.execute
> evo-engine interface.
- **Calls**: input_data.get, self.find_replace, input_data.get, input_data.get, input_data.get, input_data.get, input_data.get, input_data.get

### cores.v1.resource_monitor.ResourceMonitor.can_run
> Check if system meets requirements. Returns (bool, reason).
- **Calls**: requirements.get, requirements.get, requirements.get, requirements.get, requirements.get, requirements.get, requirements.get, requirements.get

### cores.v1.core._cmd_autotune
> Auto-tune: benchmark models with LIVE tests and select optimal: /autotune [goal] [profile] [--static]
- **Calls**: state.get, None.split, cores.v1.config.cpr, result.get, result.get, cores.v1.config.cpr, cores.v1.config.cpr, main.save_state

### skills.shell.v3.skill.ShellSkill.execute
- **Calls**: None.strip, None.strip, os.path.expanduser, print, cmd_lower.startswith, command.split, self._is_interactive, command.lower

### skills.web_automation.v1.skill.WebAutomationSkill.execute
> evo-engine interface.
- **Calls**: input_data.get, self.navigate, input_data.get, input_data.get, input_data.get, self.click, input_data.get, input_data.get

### cores.v1.core._cmd_apikey
> Set or show OpenRouter API key: /apikey [key]
- **Calls**: ctx.get, None.strip, cores.v1.config.cpr, main.save_state, cores.v1.config.cpr, cores.v1.config.cpr, cores.v1.config.cpr, state.get

### cores.v1.core._cmd_hw
> Hardware diagnostics: /hw [full|audio_input|audio_output|audio_loop|devices|drivers|pulse|usb|skill_hw]
- **Calls**: cores.v1.config.cpr, HWTestSkill, hw.execute, result.get, cores.v1.config.cpr, result.get, result.get, result.get

### scripts.generate_manifests.main
- **Calls**: argparse.ArgumentParser, parser.add_argument, parser.add_argument, parser.parse_args, print, print, BlueprintRegistry, cores.v1.skill_schema.get_schema_validation_stats

### main.bootstrap
- **Calls**: main.log, main.load_state, state.get, state.get, main.log, str, str, d.mkdir

## Process Flows

Key execution flows identified:

### Flow 1: main
```
main [core]
  └─> load_state
  └─> cpr
```

### Flow 2: task_management_automation
```
task_management_automation [examples.automations.task_management_automation]
  └─> run_skill
```

### Flow 3: social_media_automation
```
social_media_automation [examples.automations.social_media_automation]
  └─> run_skill
```

### Flow 4: network_monitoring_automation
```
network_monitoring_automation [examples.automations.network_monitoring_automation]
```

### Flow 5: _final_report
```
_final_report [scripts.simulate.Simulator]
```

### Flow 6: run_diagnostic
```
run_diagnostic [cores.v1.self_reflection.SelfReflection]
  └─ →> cpr
```

### Flow 7: websocket_chat
```
websocket_chat [backend.main]
```

### Flow 8: handle_request
```
handle_request [cores.v1.evo_engine.EvoEngine]
  └─ →> cpr
```

### Flow 9: run_scenario
```
run_scenario [scripts.simulate.Simulator]
```

### Flow 10: get_markdown_logs
```
get_markdown_logs [cores.v1.skill_logger]
```

## Key Classes

### cores.v1.auto_repair.AutoRepair
> Self-healing engine with task-based repair loop.

Flow per task:
    1. DIAGNOSE — identify exact is
- **Methods**: 28
- **Key Methods**: cores.v1.auto_repair.AutoRepair.__init__, cores.v1.auto_repair.AutoRepair.journal, cores.v1.auto_repair.AutoRepair._init_tiered_repair, cores.v1.auto_repair.AutoRepair._init_learned_strategy, cores.v1.auto_repair.AutoRepair.run_boot_repair, cores.v1.auto_repair.AutoRepair.repair_skill, cores.v1.auto_repair.AutoRepair._try_known_fix, cores.v1.auto_repair.AutoRepair.on_repair_requested, cores.v1.auto_repair.AutoRepair._scan_all_skills, cores.v1.auto_repair.AutoRepair._list_all_skills

### cores.v1.skill_manager.SkillManager
- **Methods**: 26
- **Key Methods**: cores.v1.skill_manager.SkillManager.__init__, cores.v1.skill_manager.SkillManager._collect_versions, cores.v1.skill_manager.SkillManager.list_skills, cores.v1.skill_manager.SkillManager._is_rolled_back, cores.v1.skill_manager.SkillManager.latest_v, cores.v1.skill_manager.SkillManager._active_provider, cores.v1.skill_manager.SkillManager.skill_path, cores.v1.skill_manager.SkillManager.create_skill, cores.v1.skill_manager.SkillManager.diagnose_skill, cores.v1.skill_manager.SkillManager._raw_test

### cores.v1.session_config.SessionConfig
> User-facing configuration manager.

This is a SESSION-ONLY layer - changes are NOT persisted to disk
- **Methods**: 25
- **Key Methods**: cores.v1.session_config.SessionConfig.__init__, cores.v1.session_config.SessionConfig.CATEGORIES, cores.v1.session_config.SessionConfig.PROVIDER_TIERS, cores.v1.session_config.SessionConfig.get, cores.v1.session_config.SessionConfig.set, cores.v1.session_config.SessionConfig.reset, cores.v1.session_config.SessionConfig.on_change, cores.v1.session_config.SessionConfig._notify, cores.v1.session_config.SessionConfig.handle_configure_intent, cores.v1.session_config.SessionConfig._configure_llm

### cores.v1.intent_engine.IntentEngine
> Context-aware intent detection with ML-based classification.

Stages:
  0. Trivial filter (very shor
- **Methods**: 24
- **Key Methods**: cores.v1.intent_engine.IntentEngine.__init__, cores.v1.intent_engine.IntentEngine.classifier, cores.v1.intent_engine.IntentEngine.save, cores.v1.intent_engine.IntentEngine._update_topics_from_result, cores.v1.intent_engine.IntentEngine._recent_topic, cores.v1.intent_engine.IntentEngine._build_context, cores.v1.intent_engine.IntentEngine.record_skill_use, cores.v1.intent_engine.IntentEngine.record_correction, cores.v1.intent_engine.IntentEngine.record_success, cores.v1.intent_engine.IntentEngine.record_unhandled

### cores.v1.metrics_collector.MetricsCollector
> Collect and persist performance metrics.
- **Methods**: 24
- **Key Methods**: cores.v1.metrics_collector.MetricsCollector.__init__, cores.v1.metrics_collector.MetricsCollector._ensure_dirs, cores.v1.metrics_collector.MetricsCollector.record_skill_execution, cores.v1.metrics_collector.MetricsCollector.get_skill_metrics, cores.v1.metrics_collector.MetricsCollector.get_skill_health, cores.v1.metrics_collector.MetricsCollector.record_operation, cores.v1.metrics_collector.MetricsCollector.get_operation_stats, cores.v1.metrics_collector.MetricsCollector.save_system_snapshot, cores.v1.metrics_collector.MetricsCollector.load_system_snapshot, cores.v1.metrics_collector.MetricsCollector._count_skills

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

### cores.v1.smart_intent.SmartIntentClassifier
> ML-based intent classifier for evo-engine.

Replaces all hardcoded _KW_* tuples with learnable embed
- **Methods**: 17
- **Key Methods**: cores.v1.smart_intent.SmartIntentClassifier.__init__, cores.v1.smart_intent.SmartIntentClassifier._training_path, cores.v1.smart_intent.SmartIntentClassifier._load_training_data, cores.v1.smart_intent.SmartIntentClassifier._save_training_data, cores.v1.smart_intent.SmartIntentClassifier.add_example, cores.v1.smart_intent.SmartIntentClassifier.learn_from_correction, cores.v1.smart_intent.SmartIntentClassifier.learn_from_success, cores.v1.smart_intent.SmartIntentClassifier._generate_variations, cores.v1.smart_intent.SmartIntentClassifier._ensure_embeddings, cores.v1.smart_intent.SmartIntentClassifier._keyword_prefilter

### cores.v1.autonomy_loop.AutonomyLoop
> Closed-loop orchestrator: scan → triage → repair → verify → record.

Components (all optional, grace
- **Methods**: 16
- **Key Methods**: cores.v1.autonomy_loop.AutonomyLoop.__init__, cores.v1.autonomy_loop.AutonomyLoop.run_cycle, cores.v1.autonomy_loop.AutonomyLoop._phase_scan, cores.v1.autonomy_loop.AutonomyLoop._phase_triage, cores.v1.autonomy_loop.AutonomyLoop._phase_repair, cores.v1.autonomy_loop.AutonomyLoop._repair_system, cores.v1.autonomy_loop.AutonomyLoop._phase_verify, cores.v1.autonomy_loop.AutonomyLoop._phase_record, cores.v1.autonomy_loop.AutonomyLoop.scheduled_cycle, cores.v1.autonomy_loop.AutonomyLoop.enable

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

### skills.benchmark.v2.skill.BenchmarkSkill
> Analyzes and benchmarks LLM models for goal-based recommendations.
- **Methods**: 15
- **Key Methods**: skills.benchmark.v2.skill.BenchmarkSkill.__init__, skills.benchmark.v2.skill.BenchmarkSkill._load_config, skills.benchmark.v2.skill.BenchmarkSkill._get_models_from_tier, skills.benchmark.v2.skill.BenchmarkSkill._get_api_key, skills.benchmark.v2.skill.BenchmarkSkill._get_cached_recommendations, skills.benchmark.v2.skill.BenchmarkSkill.execute, skills.benchmark.v2.skill.BenchmarkSkill._recommend_models_live, skills.benchmark.v2.skill.BenchmarkSkill._get_model_param_size, skills.benchmark.v2.skill.BenchmarkSkill.BENCHMARK_PROFILES, skills.benchmark.v2.skill.BenchmarkSkill._call_model_for_benchmark

### skills.task_manager.v1.skill.TaskManagerSkill
> Task and reminder management.
- **Methods**: 15
- **Key Methods**: skills.task_manager.v1.skill.TaskManagerSkill.__init__, skills.task_manager.v1.skill.TaskManagerSkill._ensure_storage, skills.task_manager.v1.skill.TaskManagerSkill._load_tasks, skills.task_manager.v1.skill.TaskManagerSkill._save_tasks, skills.task_manager.v1.skill.TaskManagerSkill._parse_due_date, skills.task_manager.v1.skill.TaskManagerSkill.add, skills.task_manager.v1.skill.TaskManagerSkill.list_tasks, skills.task_manager.v1.skill.TaskManagerSkill.complete, skills.task_manager.v1.skill.TaskManagerSkill.delete, skills.task_manager.v1.skill.TaskManagerSkill.update

### cores.v1.quality_gate.SkillQualityGate
> Validates skill quality before registration.
Each check contributes a weight to the final score.
- **Methods**: 14
- **Key Methods**: cores.v1.quality_gate.SkillQualityGate.__init__, cores.v1.quality_gate.SkillQualityGate.evaluate, cores.v1.quality_gate.SkillQualityGate.should_register, cores.v1.quality_gate.SkillQualityGate.compare, cores.v1.quality_gate.SkillQualityGate.on_skill_changed, cores.v1.quality_gate.SkillQualityGate._check_preflight, cores.v1.quality_gate.SkillQualityGate._check_manifest_schema, cores.v1.quality_gate.SkillQualityGate._check_drift, cores.v1.quality_gate.SkillQualityGate._check_health, cores.v1.quality_gate.SkillQualityGate._check_test_exec

### cores.v1.self_reflection.SelfReflection
> Autonomiczny silnik autorefleksji systemu evo-engine.
- **Methods**: 14
- **Key Methods**: cores.v1.self_reflection.SelfReflection.__init__, cores.v1.self_reflection.SelfReflection.journal, cores.v1.self_reflection.SelfReflection.snapshot, cores.v1.self_reflection.SelfReflection.start_operation, cores.v1.self_reflection.SelfReflection.end_operation, cores.v1.self_reflection.SelfReflection.record_skill_outcome, cores.v1.self_reflection.SelfReflection.check_stall, cores.v1.self_reflection.SelfReflection._trigger_event, cores.v1.self_reflection.SelfReflection.run_diagnostic, cores.v1.self_reflection.SelfReflection._print_report

## Data Transformation Functions

Key functions that process and transform data:

### examples.check_clipboard_api_key.validate_openrouter_api_key
> Sprawdź czy tekst jest poprawnym API key OpenRouter.
Format: sk-or-v1-[64 znaki hex]
- **Output to**: re.match, re.findall, text.startswith, len, len

### scripts.benchmark_system.validate_manifest_schemas
> Check which manifests are valid JSON.
- **Output to**: skills_dir.iterdir, skills_dir.exists, skill_dir.name.startswith, manifest.exists, json.loads

### cores.v1.autonomy_loop.AutonomyLoop.format_report
> Human-readable report of all cycles.
- **Output to**: enumerate, sum, sum, sum, lines.append

### cores.v1.config._parse_models_override
- **Output to**: isinstance, isinstance, None.strip, x.strip, None.strip

### cores.v1.repair_journal.RepairJournal.format_report
> Human-readable repair report.
- **Output to**: self.get_stats, self.get_history, None.join, lines.append, lines.append

### cores.v1.evo_journal.EvolutionJournal.format_report
> Human-readable evolution report.
- **Output to**: self.get_global_stats, stats.get, None.join, lines.append, None.join

### cores.v1.intent_engine.IntentEngine._process_ml_result
> Process successful ML classification result and build analysis.
- **Output to**: bool, self.log.core, result.to_analysis, self._update_topics_from_result, self._extract_shell_command

### cores.v1.adaptive_monitor.AdaptiveResourceMonitor.format_status
> One-line status string for display.
- **Output to**: self.snapshot

### cores.v1.auto_repair.AutoRepair.validate_model
> Check if a model is suitable for chat (not code-only).
Returns (valid: bool, reason: str).
- **Output to**: model_name.lower

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

### cores.v1.core._process_chat_input
> Process chat input through IntentEngine and EvoEngine.
- **Output to**: cmd_ctx.get, conv.append, logger.core, sm.list_skills, intent.analyze

### cores.v1.pipeline_manager.PipelineManager._process_input
> Process input dict, substituting variables in all string values.
- **Output to**: isinstance, isinstance, self._process_input, isinstance, input_data.items

## Behavioral Patterns

### recursion_get
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: cores.v1.prompts.PromptManager.get

### recursion_render
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: cores.v1.prompts.PromptManager.render

### recursion_get_metadata
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: cores.v1.prompts.PromptManager.get_metadata

### recursion_clear_cache
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: cores.v1.prompts.PromptManager.clear_cache

### recursion_execute
- **Type**: recursion
- **Confidence**: 0.90
- **Functions**: skills.pound_to_yen_converter.v9.skill.PoundToYenConverter.execute

### state_machine_EmailClientSkill
- **Type**: state_machine
- **Confidence**: 0.70
- **Functions**: skills.email_client.v1.skill.EmailClientSkill.__init__, skills.email_client.v1.skill.EmailClientSkill.connect, skills.email_client.v1.skill.EmailClientSkill._list_folders, skills.email_client.v1.skill.EmailClientSkill.list_folders, skills.email_client.v1.skill.EmailClientSkill.search

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `core.main` - 147 calls
- `seeds.core_v1.main` - 108 calls
- `examples.automations.task_management_automation.task_management_automation` - 80 calls
- `scripts.benchmark_system.run_all_benchmarks` - 63 calls
- `examples.automations.social_media_automation.social_media_automation` - 59 calls
- `examples.automations.network_monitoring_automation.network_monitoring_automation` - 56 calls
- `cores.v1.self_reflection.SelfReflection.run_diagnostic` - 53 calls
- `backend.main.websocket_chat` - 51 calls
- `scripts.get_openrouter_key.main` - 49 calls
- `cores.v1.evo_engine.EvoEngine.handle_request` - 49 calls
- `scripts.simulate.Simulator.run_scenario` - 47 calls
- `cores.v1.skill_logger.get_markdown_logs` - 44 calls
- `examples.openrouter_session_copy.main` - 41 calls
- `TODO2.main.websocket_chat` - 39 calls
- `examples.automations.document_processing_pipeline.document_processing_pipeline` - 38 calls
- `cores.v1.llm_client.LLMClient.chat` - 37 calls
- `cores.v1.intent.SmartIntentClassifier.classify` - 37 calls
- `skills.document_editor.v1.skill.DocumentEditorSkill.execute` - 37 calls
- `cli.cmd_cache_reset` - 36 calls
- `cores.v1.resource_monitor.ResourceMonitor.can_run` - 36 calls
- `skills.shell.v3.skill.ShellSkill.execute` - 36 calls
- `skills.web_automation.v1.skill.WebAutomationSkill.execute` - 36 calls
- `scripts.generate_manifests.main` - 34 calls
- `main.bootstrap` - 33 calls
- `cores.v1.skill_manager.SkillManager.create_skill` - 33 calls
- `examples.skills.01_create.main` - 33 calls
- `examples.automations.ksef_invoice_automation.ksef_invoice_automation` - 33 calls
- `cores.v1.evo_engine.EvoEngine.evolve_skill` - 32 calls
- `examples.advanced.01_pipeline.main` - 32 calls
- `examples.check_clipboard_api_key.main` - 31 calls
- `cores.v1.i18n.detect_language` - 31 calls
- `cores.v1.system_identity.SystemIdentity.build_system_prompt` - 31 calls
- `cli.cmd_status` - 30 calls
- `cores.v1.base_skill.SkillManifest.from_dict` - 30 calls
- `skills.account_creator.v1.skill.AccountCreatorSkill.execute` - 30 calls
- `skills.task_manager.v1.skill.TaskManagerSkill.execute` - 30 calls
- `cli.cmd_logs_reset` - 29 calls
- `skills.text_summarizer.v1.skill.TextSummarizerSkill.summarize` - 29 calls
- `skills.document_editor.v1.skill.DocumentEditorSkill.find_replace` - 29 calls
- `cores.v1.repair_journal.RepairJournal.ask_llm_and_try` - 28 calls

## System Interactions

How components interact:

```mermaid
graph TD
    main --> load_state
    main --> Supervisor
    main --> cpr
    task_management_auto --> print
    task_management_auto --> run_skill
    social_media_automat --> print
    social_media_automat --> run_skill
    social_media_automat --> get
    network_monitoring_a --> print
    network_monitoring_a --> items
    _final_report --> print
    _final_report --> len
    _final_report --> sum
    run_diagnostic --> cpr
    run_diagnostic --> check_llm_health
    run_diagnostic --> append
    run_diagnostic --> check_system_command
    websocket_chat --> websocket
    websocket_chat --> info
    websocket_chat --> accept
    websocket_chat --> str
    websocket_chat --> send_json
    main --> OpenRouterAutomation
    main --> print
    handle_request --> get
    handle_request --> cpr
    run_scenario --> get
    run_scenario --> print
    get_markdown_logs --> exists
    get_markdown_logs --> connect
```

## Reverse Engineering Guidelines

1. **Entry Points**: Start analysis from the entry points listed above
2. **Core Logic**: Focus on classes with many methods
3. **Data Flow**: Follow data transformation functions
4. **Process Flows**: Use the flow diagrams for execution paths
5. **API Surface**: Public API functions reveal the interface

## Context for LLM

Maintain the identified architectural patterns and public API surface when suggesting changes.