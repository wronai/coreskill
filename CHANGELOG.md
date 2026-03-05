## [1.0.2] - 2026-03-05

### Summary

refactor(docs): code analysis engine

### Docs

- docs: update README
- docs: update context.md
- docs: update context.md
- docs: update context.md

### Config

- config: update goal.yaml

### Other

- update backend/tests/test_backend.py
- scripts: update project.sh
- update project/analysis.toon
- update project/batch_1/analysis.toon
- update project/batch_1/evolution.toon
- update project/calls.mmd
- update project/calls.png
- update project/compact_flow.mmd
- update project/compact_flow.png
- update project/dashboard.html
- ... and 10 more


## [1.0.2] - 2026-03-04

### Summary

feat(docs): Complete documentation, CLI, API testing, and packaging updates
feat(skills): Add 5 utility skills (file_manager, process_manager, clipboard, qr_generator, url_codec)
feat(skills): Add 12 office worker skills (document_reader, notes, converter, task_manager, text_summarizer, calculator_advanced, network_tools, document_search, document_editor, social_media_manager, account_creator, document_publisher)
feat(pipeline): Add 4 complex multi-step pipelines with variable substitution
feat(automation): Add web_automation (Playwright), email_client (IMAP/SMTP), openrouter_automation
feat(integration): Add ksef_integration for Polish KSeF system

### New Utility Skills

- **file_manager**: File operations (list, copy, move, delete, organize, find, info) using stdlib only
- **process_manager**: Process management (list, find, kill, info) using /proc and ps fallback
- **clipboard**: Clipboard operations (copy, paste, clear) with xclip/xsel/wl-copy/pbcopy support
- **qr_generator**: QR code generation using qrencode or python-qrcode fallback
- **url_codec**: URL encoding/decoding, base64, HTML entities using stdlib only

### New Office Worker Skills

- **document_reader**: Extract text from PDF, DOCX, TXT, MD files with multiple fallback methods
- **notes**: Personal note taking with tags, search, and organization (stored in ~/.evo_notes/)
- **converter**: Unit conversions (length, weight, temperature, data, time), time zones, currencies
- **task_manager**: Task and reminder management with priorities, due dates, categories, and search
- **text_summarizer**: Summarize long texts using extractive methods with keyword extraction
- **calculator_advanced**: Advanced calculator with variables, formulas, scientific functions, equation solver
- **network_tools**: Network diagnostics (ping, DNS lookup, port check, HTTP status)
- **document_search**: Search documents by content, name, metadata, find duplicates
- **document_editor**: Edit documents: find/replace, insert, delete, merge, split, templates
- **social_media_manager**: Create posts, schedule content, generate hashtags, analyze text
- **account_creator**: Generate passwords, validate emails/usernames, create account data
- **document_publisher**: Generate HTML from docs, create indexes, version control, share links

### New Automation Skills

- **web_automation**: Browser automation using Playwright (navigate, click, type, screenshot, extract)
- **email_client**: Email IMAP/SMTP operations (read, search, send, extract links)
- **openrouter_automation**: Automated OpenRouter login and API key retrieval via email + browser

### New Integration Skills

- **ksef_integration**: Integration with Polish KSeF (Krajowy System e-Faktur) for electronic invoices

### New Pipelines

- **daily_briefing**: Time → Tasks stats → Create daily briefing note
- **research_and_summarize**: Web search → Fetch content → Save as note
- **file_analysis_report**: List files → Read document → Save analysis
- **system_health_check**: System info → Processes → QR code → Clipboard

### Features

- feat(cli): Add coreskill CLI with status, logs reset, cache reset commands
- feat(api): Create openrouter_api_test skill with automatic API key validation
- feat(llm): Add verbose logging for model selection with API key warnings
- feat(state): Fix save_state() to merge changes instead of overwriting
- feat(gitignore): Add models/ to gitignore for large model files

### Documentation

- docs: Complete rewrite of README.md with current features
- docs: Create architecture.md with system design
- docs: Create api_reference.md with API documentation
- docs: Create creating_skills.md with skill development guide
- docs: Create configuration.md with configuration options
- docs: Create troubleshooting.md with common issues
- docs: Create examples/ folder with usage examples

### Packaging

- feat(packaging): Create Python package structure (__init__.py, setup.py, MANIFEST.in)
- feat(packaging): Add entry points for coreskill CLI
- feat(packaging): Update requirements.txt with dependencies

### API Key Management

- feat(apikey): Add automatic API key validation on /apikey command
- feat(apikey): Show detailed status for invalid/rate-limited/payment errors
- feat(apikey): Prevent saving invalid API keys
- feat(apikey): Auto-refresh paid models list after successful validation

### Fixes

- fix(state): save_state() now merges changes instead of overwriting entire file
- fix(gitignore): Add models/ to prevent pushing large model files
- fix(llm): Add warning when paid models unavailable due to missing API key

---

## [1.0.1] - 2026-03-03

### Summary

refactor(docs): deep code analysis engine with 7 supporting modules

### Docs

- docs: update README

### Config

- config: update goal.yaml

### Other

- update .evo_state.json
- update .gitignore
- update .idea/.gitignore
- update Dockerfile.core
- update core.py
- update core_v1.py
- update cores/v1/core.py
- update echo_skill_v1.py
- update main.py
- update seeds/core_v1.py
- ... and 5 more


