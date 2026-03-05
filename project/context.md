# System Architecture Analysis

## Overview

- **Project**: coreskill
- **Language**: python
- **Files**: 148
- **Lines**: 48625
- **Functions**: 1601
- **Classes**: 195
- **Avg CC**: 4.8
- **Critical (CC≥10)**: 201

## Architecture

### backend/ (1 files, 766L, 24 functions)

- `main.py` — 766L, 24 methods, CC↑17

### cores/v1/ (47 files, 17787L, 679 functions)

- `auto_repair.py` — 858L, 29 methods, CC↑30
- `self_reflection.py` — 462L, 12 methods, CC↑28
- `resource_monitor.py` — 201L, 12 methods, CC↑26
- `system_identity.py` — 271L, 9 methods, CC↑26
- `preflight.py` — 425L, 17 methods, CC↑25
- _42 more files_

### cores/v1/intent/ (6 files, 1716L, 37 functions)

- `__init__.py` — 518L, 17 methods, CC↑35
- `ensemble.py` — 110L, 4 methods, CC↑13
- `local_llm.py` — 171L, 5 methods, CC↑10
- `embedding.py` — 172L, 7 methods, CC↑9
- `knn_classifier.py` — 126L, 4 methods, CC↑6
- _1 more files_

### cores/v1/prompts/ (1 files, 184L, 11 functions)

- `__init__.py` — 184L, 11 methods, CC↑11

### cores/v1/self_healing/ (2 files, 681L, 28 functions)

- `diagnostics.py` — 288L, 11 methods, CC↑18
- `__init__.py` — 393L, 17 methods, CC↑9

### root/ (6 files, 1205L, 49 functions)

- `core.py` — 609L, 29 methods, CC↑74
- `cli.py` — 329L, 7 methods, CC↑23
- `main.py` — 110L, 5 methods, CC↑10
- `skill.py` — 88L, 8 methods, CC↑5
- `__init__.py` — 24L, 0 methods, CC↑0
- _1 more files_

### scripts/ (4 files, 1169L, 23 functions)

- `generate_manifests.py` — 199L, 4 methods, CC↑23
- `simulate.py` — 551L, 10 methods, CC↑22
- `benchmark_system.py` — 344L, 8 methods, CC↑15
- `get_openrouter_key.py` — 75L, 1 methods, CC↑5

### seeds/ (2 files, 382L, 31 functions)

- `core_v1.py` — 357L, 27 methods, CC↑54
- `echo_skill_v1.py` — 25L, 4 methods, CC↑1

### skills/_health_/v1/ (1 files, 454L, 16 functions)

- `skill.py` — 454L, 16 methods, CC↑12

### skills/account_creator/v1/ (1 files, 438L, 16 functions)

- `skill.py` — 438L, 16 methods, CC↑18

### skills/auto/v1/ (1 files, 311L, 9 functions)

- `skill.py` — 311L, 9 methods, CC↑13

### skills/auto/v2/ (1 files, 322L, 17 functions)

- `skill.py` — 322L, 17 methods, CC↑23

### skills/benchmark/v2/ (1 files, 416L, 18 functions)

- `skill.py` — 416L, 18 methods, CC↑26

### skills/benchmark/v3/ (1 files, 428L, 17 functions)

- `skill.py` — 428L, 17 methods, CC↑26

### skills/calculator_advanced/v1/ (1 files, 368L, 14 functions)

- `skill.py` — 368L, 14 methods, CC↑14

### skills/chat/v1/ (1 files, 135L, 5 functions)

- `skill.py` — 135L, 5 methods, CC↑23

### skills/clipboard/v1/ (1 files, 228L, 8 functions)

- `skill.py` — 228L, 8 methods, CC↑8

### skills/content_search/providers/default/stable/ (1 files, 199L, 10 functions)

- `skill.py` — 199L, 10 methods, CC↑15

### skills/converter/v1/ (1 files, 384L, 11 functions)

- `skill.py` — 384L, 11 methods, CC↑11

### skills/core_loader/v1/ (1 files, 84L, 4 functions)

- `skill.py` — 84L, 4 methods, CC↑4

### skills/currency_converter_gbp_to_jpy/v2/ (1 files, 130L, 4 functions)

- `skill.py` — 130L, 4 methods, CC↑16

### skills/currency_converter_gbp_to_jpy/v3/ (1 files, 125L, 4 functions)

- `skill.py` — 125L, 4 methods, CC↑15

### skills/deps/providers/default/stable/ (1 files, 194L, 11 functions)

- `skill.py` — 194L, 11 methods, CC↑19

### skills/devops/providers/default/stable/ (1 files, 243L, 11 functions)

- `skill.py` — 243L, 11 methods, CC↑8

### skills/diagnostic_runner/v1/ (1 files, 150L, 9 functions)

- `skill.py` — 150L, 9 methods, CC↑11

### skills/document_editor/v1/ (1 files, 470L, 15 functions)

- `skill.py` — 470L, 15 methods, CC↑17

### skills/document_publisher/v1/ (1 files, 547L, 22 functions)

- `skill.py` — 547L, 22 methods, CC↑9

### skills/document_reader/v1/ (1 files, 466L, 16 functions)

- `skill.py` — 466L, 16 methods, CC↑10

### skills/document_search/v1/ (1 files, 468L, 15 functions)

- `skill.py` — 468L, 15 methods, CC↑22

### skills/echo/providers/default/stable/ (1 files, 84L, 4 functions)

- `skill.py` — 84L, 4 methods, CC↑7

### skills/echo/v8/ (1 files, 84L, 4 functions)

- `skill.py` — 84L, 4 methods, CC↑7

### skills/echo/v9/ (1 files, 102L, 4 functions)

- `skill.py` — 102L, 4 methods, CC↑9

### skills/email_client/v1/ (1 files, 357L, 16 functions)

- `skill.py` — 357L, 16 methods, CC↑10

### skills/evo_engine_bootstrap/v1/ (1 files, 74L, 4 functions)

- `skill.py` — 74L, 4 methods, CC↑4

### skills/evo_engine_bootstrap/v2/ (1 files, 81L, 4 functions)

- `skill.py` — 81L, 4 methods, CC↑4

### skills/file_manager/v1/ (1 files, 293L, 12 functions)

- `skill.py` — 293L, 12 methods, CC↑12

### skills/first_installment/v1/ (1 files, 77L, 4 functions)

- `skill.py` — 77L, 4 methods, CC↑5

### skills/first_installment/v2/ (1 files, 81L, 4 functions)

- `skill.py` — 81L, 4 methods, CC↑5

### skills/gbp_to_jpy_converter/v8/ (1 files, 130L, 4 functions)

- `skill.py` — 130L, 4 methods, CC↑12

### skills/gbp_to_jpy_converter/v9/ (1 files, 135L, 4 functions)

- `skill.py` — 135L, 4 methods, CC↑13

### skills/git_ops/v1/ (1 files, 142L, 15 functions)

- `skill.py` — 142L, 15 methods, CC↑4

### skills/health/v1/ (1 files, 129L, 4 functions)

- `skill.py` — 129L, 4 methods, CC↑15

### skills/interior_inspection/v2/ (1 files, 120L, 6 functions)

- `skill.py` — 120L, 6 methods, CC↑5

### skills/invalid_input_handler/v1/ (1 files, 113L, 4 functions)

- `skill.py` — 113L, 4 methods, CC↑17

### skills/json_validator/v8/ (1 files, 152L, 4 functions)

- `skill.py` — 152L, 4 methods, CC↑5

### skills/json_validator/v9/ (1 files, 152L, 4 functions)

- `skill.py` — 152L, 4 methods, CC↑5

### skills/kalkulator/v47/ (1 files, 127L, 7 functions)

- `skill.py` — 127L, 7 methods, CC↑9

### skills/kalkulator/v48/ (1 files, 4L, 3 functions)

- `skill.py` — 4L, 3 methods, CC↑1

### skills/kalkulator/v49/ (1 files, 4L, 3 functions)

- `skill.py` — 4L, 3 methods, CC↑1

### skills/kalkulator/v50/ (1 files, 4L, 3 functions)

- `skill.py` — 4L, 3 methods, CC↑1

### skills/ksef_integration/v1/ (1 files, 354L, 16 functions)

- `skill.py` — 354L, 16 methods, CC↑8

### skills/llm/v1/ (1 files, 139L, 4 functions)

- `skill.py` — 139L, 4 methods, CC↑10

### skills/llm/v2/ (1 files, 147L, 5 functions)

- `skill.py` — 147L, 5 methods, CC↑10

### skills/llm_router/v1/ (1 files, 124L, 7 functions)

- `skill.py` — 124L, 7 methods, CC↑7

### skills/local_computer_discovery/v3/ (1 files, 315L, 13 functions)

- `skill.py` — 315L, 13 methods, CC↑17

### skills/network_info/v1/ (1 files, 73L, 3 functions)

- `skill.py` — 73L, 3 methods, CC↑8

### skills/network_tools/v1/ (1 files, 360L, 11 functions)

- `skill.py` — 360L, 11 methods, CC↑15

### skills/notes/v1/ (1 files, 330L, 16 functions)

- `skill.py` — 330L, 16 methods, CC↑11

### skills/openrouter/v1/ (1 files, 287L, 11 functions)

- `skill.py` — 287L, 11 methods, CC↑13

### skills/openrouter_automation/v1/ (1 files, 909L, 24 functions)

- `skill.py` — 909L, 24 methods, CC↑26

### skills/password_generator/v5/ (1 files, 95L, 4 functions)

- `skill.py` — 95L, 4 methods, CC↑6

### skills/password_generator/v6/ (1 files, 83L, 4 functions)

- `skill.py` — 83L, 4 methods, CC↑4

### skills/pound_to_yen_converter/v10/ (1 files, 100L, 4 functions)

- `skill.py` — 100L, 4 methods, CC↑14

### skills/pound_to_yen_converter/v8/ (1 files, 95L, 6 functions)

- `skill.py` — 95L, 6 methods, CC↑3

### skills/pound_to_yen_converter/v9/ (1 files, 89L, 4 functions)

- `skill.py` — 89L, 4 methods, CC↑5

### skills/process_manager/v1/ (1 files, 263L, 10 functions)

- `skill.py` — 263L, 10 methods, CC↑13

### skills/qr_generator/v1/ (1 files, 186L, 9 functions)

- `skill.py` — 186L, 9 methods, CC↑6

### skills/separator_line/v1/ (1 files, 53L, 4 functions)

- `skill.py` — 53L, 4 methods, CC↑2

### skills/shell/v2/ (1 files, 240L, 11 functions)

- `skill.py` — 240L, 11 methods, CC↑8

### skills/shell/v3/ (1 files, 219L, 6 functions)

- `skill.py` — 219L, 6 methods, CC↑28

### skills/social_media_manager/v1/ (1 files, 442L, 21 functions)

- `skill.py` — 442L, 21 methods, CC↑9

### skills/stt/providers/vosk/stable/ (1 files, 299L, 10 functions)

- `skill.py` — 299L, 10 methods, CC↑18

### skills/system_info/v3/ (1 files, 85L, 4 functions)

- `skill.py` — 85L, 4 methods, CC↑7

### skills/system_info/v4/ (1 files, 97L, 4 functions)

- `skill.py` — 97L, 4 methods, CC↑9

### skills/task_manager/v1/ (1 files, 478L, 18 functions)

- `skill.py` — 478L, 18 methods, CC↑12

### skills/text_processor_/v6/ (1 files, 61L, 4 functions)

- `skill.py` — 61L, 4 methods, CC↑5

### skills/text_processor_/v7/ (1 files, 61L, 4 functions)

- `skill.py` — 61L, 4 methods, CC↑5

### skills/text_summarizer/v1/ (1 files, 244L, 10 functions)

- `skill.py` — 244L, 10 methods, CC↑11

### skills/time/v1/ (1 files, 112L, 3 functions)

- `skill.py` — 112L, 3 methods, CC↑3

### skills/tts/providers/coqui/stable/ (1 files, 28L, 3 functions)

- `skill.py` — 28L, 3 methods, CC↑2

### skills/tts/providers/espeak/stable/ (1 files, 93L, 6 functions)

- `skill.py` — 93L, 6 methods, CC↑10

### skills/tts/providers/piper/stable/ (1 files, 269L, 10 functions)

- `skill.py` — 269L, 10 methods, CC↑17

### skills/tts/providers/pyttsx3/stable/ (1 files, 84L, 6 functions)

- `skill.py` — 84L, 6 methods, CC↑6

### skills/url_codec/v1/ (1 files, 184L, 10 functions)

- `skill.py` — 184L, 10 methods, CC↑7

### skills/weather/v2/ (1 files, 121L, 6 functions)

- `skill.py` — 121L, 6 methods, CC↑4

### skills/weather/v3/ (1 files, 119L, 6 functions)

- `skill.py` — 119L, 6 methods, CC↑4

### skills/weather_gdansk/v9/ (1 files, 161L, 8 functions)

- `skill.py` — 161L, 8 methods, CC↑10

### skills/web_automation/v1/ (1 files, 288L, 19 functions)

- `skill.py` — 288L, 19 methods, CC↑13

### skills/web_search/providers/duckduckgo/stable/ (1 files, 166L, 12 functions)

- `skill.py` — 166L, 12 methods, CC↑6

### skills/zarz_dzania/v7/ (1 files, 138L, 7 functions)

- `skill.py` — 138L, 7 methods, CC↑8

### skills/zarz_dzania/v8/ (1 files, 140L, 7 functions)

- `skill.py` — 140L, 7 methods, CC↑8

## Key Exports

- **SkillLoader** (class, CC̄=6.2)
- **main** (function, CC=74) ⚠ split
- **SkillManager** (class, CC̄=6.6)
  - `exec_skill` CC=19 ⚠ split
- **main** (function, CC=54) ⚠ split
- **IntentResult** (class, CC̄=6.0)
- **SmartIntentClassifier** (class, CC̄=6.1)
  - `classify` CC=35 ⚠ split
- **AutoRepair** (class, CC̄=7.9)
  - `_diagnose_skill` CC=30 ⚠ split
- **SelfReflection** (class, CC̄=8.1)
  - `run_diagnostic` CC=28 ⚠ split
- **ShellSkill** (class, CC̄=15.0)
  - `execute` CC=28 ⚠ split
- **ResourceMonitor** (class, CC̄=4.6)
  - `can_run` CC=26 ⚠ split
- **SystemIdentity** (class, CC̄=7.3)
  - `build_system_prompt` CC=26 ⚠ split
- **BenchmarkSkill** (class, CC̄=5.9)
  - `execute` CC=26 ⚠ split
  - `_recommend_models_live` CC=18 ⚠ split
- **BenchmarkSkill** (class, CC̄=6.1)
  - `execute` CC=26 ⚠ split
  - `_recommend_models_live` CC=18 ⚠ split
- **OpenRouterAutomationSkill** (class, CC̄=6.7)
  - `_get_browser_profiles` CC=26 ⚠ split
  - `get_api_key_from_session` CC=21 ⚠ split
- **SkillPreflight** (class, CC̄=13.0)
  - `check_imports` CC=20 ⚠ split
  - `auto_fix_imports` CC=25 ⚠ split
- **EvolutionGuard** (class, CC̄=6.2)
  - `is_stub_skill` CC=21 ⚠ split
- **IntentEngine** (class, CC̄=7.1)
  - `analyze` CC=18 ⚠ split
  - `_extract_shell_command` CC=18 ⚠ split
  - `_match_existing_skill` CC=18 ⚠ split
  - `_extract_config_target` CC=24 ⚠ split
- **LLMClient** (class, CC̄=9.2)
  - `_report_fail` CC=15 ⚠ split
  - `chat` CC=18 ⚠ split
  - `_try_model` CC=15 ⚠ split
  - `analyze_need` CC=24 ⚠ split
- **cmd_logs_reset** (function, CC=20) ⚠ split
- **cmd_cache_reset** (function, CC=23) ⚠ split
- **cmd_status** (function, CC=19) ⚠ split
- **SkillSchemaValidator** (class, CC̄=6.0)
  - `_validate_against_schema` CC=23 ⚠ split
- **generate_manifest_for_skill** (function, CC=23) ⚠ split
- **AutoSkillBuilder** (class, CC̄=4.9)
  - `_parse_command` CC=23 ⚠ split
- **ChatSkill** (class, CC̄=13.5)
  - `_generate_response` CC=23 ⚠ split
- **Simulator** (class, CC̄=11.0)
  - `run_scenario` CC=21 ⚠ split
  - `_final_report` CC=22 ⚠ split
- **DocumentSearchSkill** (class, CC̄=7.6)
  - `search_by_content` CC=15 ⚠ split
  - `search_by_metadata` CC=22 ⚠ split
- **EvoEngine** (class, CC̄=9.8)
  - `_run_auto_reflection` CC=19 ⚠ split
  - `_exec_handle_failure` CC=18 ⚠ split
  - `_try_fallback_providers` CC=17 ⚠ split
  - `_validate_result` CC=21 ⚠ split
  - `_autonomous_stt_repair` CC=20 ⚠ split
- **SessionConfig** (class, CC̄=5.4)
  - `handle_configure_intent` CC=21 ⚠ split
- **DriftDetector** (class, CC̄=7.9)
  - `_find_latest_version` CC=19 ⚠ split
- **DepsSkill** (class, CC̄=4.9)
  - `execute` CC=19 ⚠ split
- **EvolutionJournal** (class, CC̄=5.0)
  - `_suggest_strategy` CC=18 ⚠ split
- **ProviderSelector** (class, CC̄=7.7)
  - `select` CC=18 ⚠ split
  - `_score` CC=15 ⚠ split
  - `get_skill_path` CC=18 ⚠ split
- **DiagnosticEngine** (class, CC̄=6.5)
  - `full_scan` CC=18 ⚠ split
- **SkillManager** (class, CC̄=6.8)
  - `latest_v` CC=18 ⚠ split
- **AccountCreatorSkill** (class, CC̄=7.2)
  - `generate_password` CC=18 ⚠ split
- **STTSkill** (class, CC̄=9.7)
  - `_check_audio_level` CC=18 ⚠ split
- **EvolutionGarbageCollector** (class, CC̄=8.5)
  - `cleanup_legacy` CC=17 ⚠ split
- **MetricsCollector** (class, CC̄=5.0)
  - `get_anomalies` CC=17 ⚠ split
- **SkillQualityGate** (class, CC̄=5.8)
  - `_check_code_quality` CC=17 ⚠ split
- **SmartIntentClassifier** (class, CC̄=4.8)
  - `_tier1_embedding` CC=17 ⚠ split
- **DocumentEditorSkill** (class, CC̄=8.0)
  - `find_replace` CC=17 ⚠ split
  - `insert_text` CC=16 ⚠ split
  - `format_text` CC=17 ⚠ split
- **InvalidInputHandler** (class, CC̄=17.0)
  - `execute` CC=17 ⚠ split
- **LocalComputerDiscovery** (class, CC̄=6.1)
  - `execute` CC=17 ⚠ split
- **PiperTTSSkill** (class, CC̄=7.7)
  - `execute` CC=17 ⚠ split
- **SkillForge** (class, CC̄=5.9)
  - `_load_skill_description` CC=16 ⚠ split
- **StableSnapshot** (class, CC̄=6.5)
  - `validate_against_stable` CC=16 ⚠ split
- **CurrencyConverterGBPtoJPY** (class, CC̄=16.0)
  - `execute` CC=16 ⚠ split
- **detect_language** (function, CC=15) ⚠ split
- **count_skills_and_versions** (function, CC=15) ⚠ split
- **DuckDuckGoParser** (class, CC̄=7.8)
  - `handle_starttag` CC=15 ⚠ split
- **CurrencyConverterGBPtoJPY** (class, CC̄=15.0)
  - `execute` CC=15 ⚠ split
- **HealthSkill** (class, CC̄=15.0)
  - `execute` CC=15 ⚠ split
- **NetworkToolsSkill** (class, CC̄=7.2)
  - `check_http` CC=15 ⚠ split
- **SkillManifest** (class, CC̄=7.2)
- **AdvancedCalculatorSkill** (class, CC̄=5.9)
- **PoundToYenConverter** (class, CC̄=14.0)
- **EventBus** (class, CC̄=7.0)
- **AutoSkillBuilder** (class, CC̄=9.3)
- **GBPToJPYConverter** (class, CC̄=13.0)
- **OpenRouterSkill** (class, CC̄=6.9)
- **ProcessManagerSkill** (class, CC̄=7.6)
- **HealthSkill** (class, CC̄=6.9)
- **FileManagerSkill** (class, CC̄=7.9)
- **TaskManagerSkill** (class, CC̄=5.3)
- **ConverterSkill** (class, CC̄=6.1)
- **DiagnosticRunner** (class, CC̄=5.2)
- **TextSummarizerSkill** (class, CC̄=5.6)
- **LocalLLMClassifier** (class, CC̄=6.5)
- **DocumentReaderSkill** (class, CC̄=5.2)
- **LLMExecutor** (class, CC̄=5.5)
- **EspeakTTSSkill** (class, CC̄=5.0)
- **WeatherGdanskParser** (class, CC̄=5.8)
- **WeatherGdanskSkill** (class, CC̄=9.0)
- **EchoSkill** (class, CC̄=9.0)
- **Kalkulator** (class, CC̄=5.2)
- **SystemInfoSkill** (class, CC̄=9.0)
- **ClipboardSkill** (class, CC̄=7.2)
- **DevOpsSkill** (class, CC̄=5.9)
- **ShellSkill** (class, CC̄=5.3)
- **ZarzadzaniaSkill** (class, CC̄=5.2)
- **FileManagerSkill** (class, CC̄=5.2)
- **EchoSkill** (class, CC̄=7.0)
- **EchoSkill** (class, CC̄=7.0)
- **SystemInfoSkill** (class, CC̄=7.0)
- **PasswordGenerator** (class, CC̄=6.0)
- **FirstInstallmentSkill** (class, CC̄=5.0)
- **JsonValidator** (class, CC̄=5.0)
- **JsonValidator** (class, CC̄=5.0)
- **PoundToYenConverter** (class, CC̄=5.0)
- **TextProcessor** (class, CC̄=5.0)
- **TextProcessor** (class, CC̄=5.0)

## Hotspots (High Fan-Out)

- **boot** — fan-out=61: Initialize all components. Returns (cmd_ctx, conv, memory) tuple.
- **main** — fan-out=55: Orchestrates 55 calls
- **main** — fan-out=40: Orchestrates 40 calls
- **websocket_chat** — fan-out=32: Orchestrates 32 calls
- **run_all_benchmarks** — fan-out=30: Run complete benchmark suite.
- **OpenRouterAutomationSkill.get_api_key_from_session** — fan-out=27: Copy API key from existing browser session (user already logged in).

Uses nlp2c
- **SelfReflection.run_diagnostic** — fan-out=26: Uruchom pełną diagnostykę systemu.

## Refactoring Priorities

| # | Action | Impact | Effort |
|---|--------|--------|--------|
| 1 | Split ResourceMonitor.can_run (CC=26 → target CC<10) | high | low |
| 2 | Split SelfReflection.run_diagnostic (CC=28 → target CC<10) | high | low |
| 3 | Split AutoRepair._diagnose_skill (CC=30 → target CC<10) | high | low |
| 4 | Split SystemIdentity.build_system_prompt (CC=26 → target CC<10) | high | low |
| 5 | Split SkillPreflight.auto_fix_imports (CC=25 → target CC<10) | high | low |
| 6 | Split SmartIntentClassifier.classify (CC=35 → target CC<10) | high | low |
| 7 | Split OpenRouterAutomationSkill._get_browser_profiles (CC=26 → target CC<10) | high | low |
| 8 | Split ShellSkill.execute (CC=28 → target CC<10) | high | low |
| 9 | Split main (CC=74 → target CC<10) | high | low |
| 10 | Split BenchmarkSkill.execute (CC=26 → target CC<10) | high | low |

## Context for LLM

When suggesting changes:
1. Start from hotspots and high-CC functions
2. Follow refactoring priorities above
3. Maintain public API surface — keep backward compatibility
4. Prefer minimal, incremental changes

