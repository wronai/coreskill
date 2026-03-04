# System Architecture Analysis

## Overview

- **Project**: .
- **Analysis Mode**: static
- **Total Functions**: 655
- **Total Classes**: 140
- **Modules**: 140
- **Entry Points**: 0

## Architecture by Module

### cores.v1.core
- **Functions**: 37
- **File**: `core.py`

### cores.v1.intent_engine
- **Functions**: 26
- **Classes**: 1
- **File**: `intent_engine.py`

### cores.v1.skill_manager
- **Functions**: 21
- **Classes**: 1
- **File**: `skill_manager.py`

### TODO1.preflight
- **Functions**: 17
- **Classes**: 3
- **File**: `preflight.py`

### cores.v1.preflight
- **Functions**: 17
- **Classes**: 3
- **File**: `preflight.py`

### skills.git_ops.v1.skill
- **Functions**: 15
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.provider_selector
- **Functions**: 13
- **Classes**: 2
- **File**: `provider_selector.py`

### cores.v1.llm_client
- **Functions**: 13
- **Classes**: 1
- **File**: `llm_client.py`

### TODO1.system_identity
- **Functions**: 12
- **Classes**: 2
- **File**: `system_identity.py`

### cores.v1.resource_monitor
- **Functions**: 12
- **Classes**: 1
- **File**: `resource_monitor.py`

### skills.web_search.providers.duckduckgo.v1.skill
- **Functions**: 12
- **Classes**: 2
- **File**: `skill.py`

### cores.v1.supervisor
- **Functions**: 10
- **Classes**: 1
- **File**: `supervisor.py`

### skills.devops.v1.skill
- **Functions**: 10
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.system_identity
- **Functions**: 9
- **Classes**: 2
- **File**: `system_identity.py`

### skills.deps.v2.skill
- **Functions**: 9
- **Classes**: 1
- **File**: `skill.py`

### skills.stt.providers.vosk.v7.skill
- **Functions**: 9
- **Classes**: 1
- **File**: `skill.py`

### cores.v1.logger
- **Functions**: 8
- **Classes**: 1
- **File**: `logger.py`

### skills.deps.v1.skill
- **Functions**: 8
- **Classes**: 1
- **File**: `skill.py`

### skills.stt.providers.vosk.v6.skill
- **Functions**: 8
- **Classes**: 1
- **File**: `skill.py`

### skills.stt.providers.vosk.v3.skill
- **Functions**: 8
- **Classes**: 1
- **File**: `skill.py`

## Key Entry Points

Main execution flows into the system:

## Process Flows

Key execution flows identified:

## Key Classes

### cores.v1.intent_engine.IntentEngine
> Multi-stage intent detection with conversation context and learning.
Stages:
  1. Topic tracking (vo
- **Methods**: 26
- **Key Methods**: cores.v1.intent_engine.IntentEngine.__init__, cores.v1.intent_engine.IntentEngine._detect_fast_model, cores.v1.intent_engine.IntentEngine._build_intent_prompt, cores.v1.intent_engine.IntentEngine._classify_fast, cores.v1.intent_engine.IntentEngine.save, cores.v1.intent_engine.IntentEngine._detect_topics, cores.v1.intent_engine.IntentEngine._update_topics, cores.v1.intent_engine.IntentEngine._recent_topic, cores.v1.intent_engine.IntentEngine._build_context, cores.v1.intent_engine.IntentEngine.record_skill_use

### cores.v1.skill_manager.SkillManager
- **Methods**: 19
- **Key Methods**: cores.v1.skill_manager.SkillManager.__init__, cores.v1.skill_manager.SkillManager._collect_versions, cores.v1.skill_manager.SkillManager.list_skills, cores.v1.skill_manager.SkillManager._is_rolled_back, cores.v1.skill_manager.SkillManager.latest_v, cores.v1.skill_manager.SkillManager._active_provider, cores.v1.skill_manager.SkillManager.skill_path, cores.v1.skill_manager.SkillManager.create_skill, cores.v1.skill_manager.SkillManager.diagnose_skill, cores.v1.skill_manager.SkillManager._raw_test

### skills.git_ops.v1.skill.GitOpsSkill
> Manage local git repos for skill development and versioning.
- **Methods**: 13
- **Key Methods**: skills.git_ops.v1.skill.GitOpsSkill.__init__, skills.git_ops.v1.skill.GitOpsSkill._run, skills.git_ops.v1.skill.GitOpsSkill.init, skills.git_ops.v1.skill.GitOpsSkill.status, skills.git_ops.v1.skill.GitOpsSkill.add, skills.git_ops.v1.skill.GitOpsSkill.commit, skills.git_ops.v1.skill.GitOpsSkill.log, skills.git_ops.v1.skill.GitOpsSkill.diff, skills.git_ops.v1.skill.GitOpsSkill.tag, skills.git_ops.v1.skill.GitOpsSkill.checkout

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
- **Methods**: 11
- **Key Methods**: cores.v1.llm_client.LLMClient.__init__, cores.v1.llm_client.LLMClient.tier_info, cores.v1.llm_client.LLMClient._is_available, cores.v1.llm_client.LLMClient._report_ok, cores.v1.llm_client.LLMClient._report_fail, cores.v1.llm_client.LLMClient.chat, cores.v1.llm_client.LLMClient._build_error_msg, cores.v1.llm_client.LLMClient._try_model, cores.v1.llm_client.LLMClient.gen_code, cores.v1.llm_client.LLMClient.gen_pipeline

### cores.v1.supervisor.Supervisor
> Manages core versions: can create coreB/C/D, test, promote, rollback.
- **Methods**: 10
- **Key Methods**: cores.v1.supervisor.Supervisor.__init__, cores.v1.supervisor.Supervisor.active, cores.v1.supervisor.Supervisor.active_version, cores.v1.supervisor.Supervisor.list_cores, cores.v1.supervisor.Supervisor.switch, cores.v1.supervisor.Supervisor.health, cores.v1.supervisor.Supervisor.create_next_core, cores.v1.supervisor.Supervisor.promote_core, cores.v1.supervisor.Supervisor.rollback_core, cores.v1.supervisor.Supervisor.recover

### cores.v1.preflight.EvolutionGuard
> Prevents evolution loops where the same error repeats.
Tracks error fingerprints and suggests strate
- **Methods**: 9
- **Key Methods**: cores.v1.preflight.EvolutionGuard.__init__, cores.v1.preflight.EvolutionGuard.fingerprint, cores.v1.preflight.EvolutionGuard.record_error, cores.v1.preflight.EvolutionGuard.is_repeating, cores.v1.preflight.EvolutionGuard.get_error_summary, cores.v1.preflight.EvolutionGuard.suggest_strategy, cores.v1.preflight.EvolutionGuard.build_evolution_prompt_context, cores.v1.preflight.EvolutionGuard.is_stub_skill, cores.v1.preflight.EvolutionGuard.check_execution_result

### TODO1.system_identity.SystemIdentity
> Builds dynamic system prompt that separates:
- What the SYSTEM can do (capabilities)
- What the LLM 
- **Methods**: 8
- **Key Methods**: TODO1.system_identity.SystemIdentity.__init__, TODO1.system_identity.SystemIdentity.refresh_statuses, TODO1.system_identity.SystemIdentity.get_status, TODO1.system_identity.SystemIdentity.build_system_prompt, TODO1.system_identity.SystemIdentity.build_fallback_message, TODO1.system_identity.SystemIdentity.build_skill_context_for_llm, TODO1.system_identity.SystemIdentity.detect_needed_capabilities, TODO1.system_identity.SystemIdentity.get_readiness_report

### cores.v1.logger.Logger
> Per-skill, per-core structured logging with learning.
- **Methods**: 8
- **Key Methods**: cores.v1.logger.Logger.__init__, cores.v1.logger.Logger._write, cores.v1.logger.Logger._entry, cores.v1.logger.Logger.core, cores.v1.logger.Logger.skill, cores.v1.logger.Logger.read_skill_log, cores.v1.logger.Logger.read_core_log, cores.v1.logger.Logger.learn_summary

### skills.devops.v1.skill.DevOpsSkill
> Test, validate and deploy skills in isolated subprocess.
- **Methods**: 8
- **Key Methods**: skills.devops.v1.skill.DevOpsSkill.check_syntax, skills.devops.v1.skill.DevOpsSkill.detect_imports, skills.devops.v1.skill.DevOpsSkill.check_deps, skills.devops.v1.skill.DevOpsSkill.find_system_alternatives, skills.devops.v1.skill.DevOpsSkill.test_skill, skills.devops.v1.skill.DevOpsSkill.health_check_skill, skills.devops.v1.skill.DevOpsSkill.generate_fix_prompt, skills.devops.v1.skill.DevOpsSkill.execute

### TODO1.preflight.EvolutionGuard
> Prevents evolution loops where the same error repeats.

PROBLEM: v6→v7→v8→v9 all with "shutil not de
- **Methods**: 7
- **Key Methods**: TODO1.preflight.EvolutionGuard.__init__, TODO1.preflight.EvolutionGuard.fingerprint, TODO1.preflight.EvolutionGuard.record_error, TODO1.preflight.EvolutionGuard.is_repeating, TODO1.preflight.EvolutionGuard.get_error_summary, TODO1.preflight.EvolutionGuard.suggest_strategy, TODO1.preflight.EvolutionGuard.build_evolution_prompt_context

### cores.v1.system_identity.SystemIdentity
> Builds dynamic system prompt that separates:
- What the SYSTEM can do (capabilities)
- What the LLM 
- **Methods**: 7
- **Key Methods**: cores.v1.system_identity.SystemIdentity.__init__, cores.v1.system_identity.SystemIdentity.refresh_statuses, cores.v1.system_identity.SystemIdentity.get_status, cores.v1.system_identity.SystemIdentity.build_system_prompt, cores.v1.system_identity.SystemIdentity.build_fallback_message, cores.v1.system_identity.SystemIdentity.build_skill_context_for_llm, cores.v1.system_identity.SystemIdentity.get_readiness_report

### skills.deps.v2.skill.DepsSkill
- **Methods**: 7
- **Key Methods**: skills.deps.v2.skill.DepsSkill.__init__, skills.deps.v2.skill.DepsSkill.check_system, skills.deps.v2.skill.DepsSkill.check_python_module, skills.deps.v2.skill.DepsSkill.pip_install, skills.deps.v2.skill.DepsSkill.execute, skills.deps.v2.skill.DepsSkill.get_info, skills.deps.v2.skill.DepsSkill.health_check

### cores.v1.evo_engine.EvoEngine
> Generic evolutionary algorithm:
1. Detect need → 2. Execute skill → 3. Validate goal → 4. If fail:
 
- **Methods**: 6
- **Key Methods**: cores.v1.evo_engine.EvoEngine.__init__, cores.v1.evo_engine.EvoEngine.handle_request, cores.v1.evo_engine.EvoEngine._execute_with_validation, cores.v1.evo_engine.EvoEngine._validate_result, cores.v1.evo_engine.EvoEngine._autonomous_stt_repair, cores.v1.evo_engine.EvoEngine.evolve_skill

### skills.deps.v1.skill.DepsSkill
> Detect, install and manage Python and system dependencies.
- **Methods**: 6
- **Key Methods**: skills.deps.v1.skill.DepsSkill.check_python_module, skills.deps.v1.skill.DepsSkill.check_system_command, skills.deps.v1.skill.DepsSkill.pip_install, skills.deps.v1.skill.DepsSkill.scan_system, skills.deps.v1.skill.DepsSkill.suggest_alternatives, skills.deps.v1.skill.DepsSkill.execute

### skills.stt.providers.vosk.v7.skill.STTSkill
- **Methods**: 6
- **Key Methods**: skills.stt.providers.vosk.v7.skill.STTSkill.__init__, skills.stt.providers.vosk.v7.skill.STTSkill._record_wav, skills.stt.providers.vosk.v7.skill.STTSkill._ensure_wav, skills.stt.providers.vosk.v7.skill.STTSkill._find_model_path, skills.stt.providers.vosk.v7.skill.STTSkill._transcribe_vosk, skills.stt.providers.vosk.v7.skill.STTSkill.execute

### TODO1.preflight.SkillPreflight
> Pre-flight validation for skill files.

Run BEFORE exec_skill() and BEFORE accepting evolved code.
- **Methods**: 5
- **Key Methods**: TODO1.preflight.SkillPreflight.check_all, TODO1.preflight.SkillPreflight.check_syntax, TODO1.preflight.SkillPreflight.check_imports, TODO1.preflight.SkillPreflight.check_interface, TODO1.preflight.SkillPreflight.auto_fix_imports

### cores.v1.preflight.SkillPreflight
> Pre-flight validation for skill files.
- **Methods**: 5
- **Key Methods**: cores.v1.preflight.SkillPreflight.check_all, cores.v1.preflight.SkillPreflight.check_syntax, cores.v1.preflight.SkillPreflight.check_imports, cores.v1.preflight.SkillPreflight.check_interface, cores.v1.preflight.SkillPreflight.auto_fix_imports

### skills.web_search.providers.duckduckgo.v1.skill.SimpleHTMLTextExtractor
> Extract visible text from HTML.
- **Methods**: 5
- **Key Methods**: skills.web_search.providers.duckduckgo.v1.skill.SimpleHTMLTextExtractor.__init__, skills.web_search.providers.duckduckgo.v1.skill.SimpleHTMLTextExtractor.handle_starttag, skills.web_search.providers.duckduckgo.v1.skill.SimpleHTMLTextExtractor.handle_endtag, skills.web_search.providers.duckduckgo.v1.skill.SimpleHTMLTextExtractor.handle_data, skills.web_search.providers.duckduckgo.v1.skill.SimpleHTMLTextExtractor.get_text
- **Inherits**: html.parser.HTMLParser

## Data Transformation Functions

Key functions that process and transform data:

### cores.v1.config._parse_models_override
- **Output to**: isinstance, isinstance, None.strip, x.strip, None.strip

### cores.v1.evo_engine.EvoEngine._validate_result
> Validate whether the skill result actually achieved the goal.
Returns {verdict: success|partial|fail
- **Output to**: result.get, result.get, isinstance, inner.get, inner.get

## Public API Surface

Functions exposed as public API (no underscore prefix):

- `cores.v1.core.main` - 81 calls
- `main.bootstrap` - 33 calls
- `TODO.migrate_skills.migrate_skill` - 33 calls
- `cores.v1.skill_manager.SkillManager.smart_evolve` - 31 calls
- `cores.v1.evo_engine.EvoEngine.handle_request` - 28 calls
- `TODO1.preflight.SkillPreflight.check_imports` - 27 calls
- `cores.v1.preflight.SkillPreflight.check_imports` - 27 calls
- `TODO1.preflight.SkillPreflight.auto_fix_imports` - 26 calls
- `cores.v1.preflight.SkillPreflight.auto_fix_imports` - 26 calls
- `skills.shell.v1.skill.ShellSkill.execute` - 26 calls
- `cores.v1.skill_manager.SkillManager.create_skill` - 23 calls
- `skills.stt.providers.vosk.v6.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.v3.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.v7.skill.STTSkill.execute` - 23 calls
- `skills.stt.providers.vosk.v1.skill.STTSkill.execute` - 23 calls
- `skills.git_ops.v1.skill.GitOpsSkill.execute` - 23 calls
- `cores.v1.preflight.EvolutionGuard.is_stub_skill` - 22 calls
- `cores.v1.intent_engine.IntentEngine.analyze` - 22 calls
- `cores.v1.skill_manager.SkillManager.latest_v` - 19 calls
- `cores.v1.evo_engine.EvoEngine.evolve_skill` - 19 calls
- `cores.v1.resource_monitor.ResourceMonitor.can_run` - 17 calls
- `cores.v1.llm_client.LLMClient.analyze_need` - 17 calls
- `cores.v1.pipeline_manager.PipelineManager.run_p` - 17 calls
- `TODO1.preflight.SkillPreflight.check_interface` - 15 calls
- `TODO1.preflight.patch_exec_skill` - 15 calls
- `TODO1.preflight.patch_smart_evolve` - 15 calls
- `cores.v1.preflight.SkillPreflight.check_interface` - 15 calls
- `cores.v1.logger.Logger.learn_summary` - 15 calls
- `cores.v1.skill_manager.SkillManager.list_skills` - 15 calls
- `TODO.migrate_skills.add_manifest_to_simple` - 14 calls
- `cores.v1.skill_logger.skill_health_summary` - 13 calls
- `cores.v1.skill_manager.SkillManager.rollback` - 13 calls
- `skills.web_search.providers.duckduckgo.v1.skill.WebSearchSkill.search_duckduckgo` - 13 calls
- `skills.devops.v1.skill.DevOpsSkill.detect_imports` - 13 calls
- `cores.v1.provider_selector.ProviderSelector.list_capabilities` - 12 calls
- `cores.v1.llm_client.LLMClient.chat` - 12 calls
- `cores.v1.pipeline_manager.PipelineManager.create_p` - 12 calls
- `cores.v1.skill_manager.SkillManager.exec_skill` - 12 calls
- `TODO.migrate_skills.main` - 11 calls
- `cores.v1.supervisor.Supervisor.create_next_core` - 11 calls

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