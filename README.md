# CoreSkill

Ewolucyjny system AI z samonaprawiającymi się skillami. CoreSkill to autonomiczny asystent, który samodzielnie tworzy, naprawia, ewoluuje i zarządza swoimi zdolnościami (skills) — z ML-based klasyfikacją intencji, self-healing pipeline i adaptacyjnym monitoringiem zasobów.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-258_passing-brightgreen.svg)]()

## Szybki start

### Instalacja

```bash
git clone https://github.com/wronai/coreskill.git
cd coreskill
pip install -r requirements.txt

# Lub jako pakiet Python
pip install -e .
```

### Uruchomienie

```bash
python3 main.py              # Interaktywna powłoka
python3 main.py --verbose    # Z verbose logging
python3 main.py --check      # Szybki health check

# Lub po instalacji pakietu
coreskill
coreskill status
coreskill logs reset
coreskill cache reset
```

### Zmienne środowiskowe

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."  # Opcjonalnie, można przez /apikey
export EVO_VERBOSE=1                        # Verbose logging
export EVO_TEXT_ONLY=1                      # Tryb tekstowy (bez audio)
export EVO_DISABLE_LOCAL=1                  # Wyłącz lokalne modele ollama
```

## Kluczowe funkcje

- **Ewoluujące skille** — system tworzy, testuje i naprawia skille automatycznie (35 skillów)
- **ML-based intencje** — SmartIntentClassifier (sbert embeddings → local LLM → remote LLM)
- **Self-healing** — AutoRepair z 5-fazową pętlą naprawczą (DIAGNOSE → PLAN → FIX → VERIFY → REFLECT)
- **3-tier LLM** — automatyczny fallback: free (OpenRouter) → local (ollama) → paid
- **Tryb głosowy** — bidirectional STT/TTS z auto-diagnostyką i persistent preferencjami
- **Multi-provider** — TTS (espeak/pyttsx3/coqui), STT (vosk/whisper) z UCB1 bandit selection
- **Adaptacyjny monitoring** — EWMA trend detection, pressure scoring, proaktywny scheduler
- **Wielojęzyczność** — natywne wsparcie PL/EN

## Architektura

### Core (`cores/v1/`) — 40+ modułów

| Moduł | Opis |
|-------|------|
| `core.py` | Cienki main() z dispatch table, boot sequence |
| `evo_engine.py` | Silnik ewolucyjny z walidacją pipeline |
| `llm_client.py` | LLMClient z 3-tier fallback (free → local → paid) |
| `intent_engine.py` | IntentEngine — deleguje do SmartIntentClassifier |
| `smart_intent.py` | SmartIntentClassifier — ML (sbert + local LLM + remote) |
| `intent/` | Subpakiet: embedding, local_llm, ensemble, knn, training |
| `skill_manager.py` | Zarządzanie skillami, preflight, evolve |
| `provider_selector.py` | ProviderSelector + ProviderChain (fallback chains) |
| `bandit_selector.py` | UCB1 multi-armed bandit dla provider selection |
| `resource_monitor.py` | CPU/RAM/GPU/disk detection |
| `adaptive_monitor.py` | AdaptiveResourceMonitor (EWMA, pressure score, alerty) |
| `proactive_scheduler.py` | Background tasks (GC, health checks, resource alerts) |
| `auto_repair.py` | AutoRepair — 5-fazowa samonaprawa |
| `self_reflection.py` | Autonomiczna diagnostyka (7 checks + LLM analysis) |
| `repair_journal.py` | Persistent baza prób napraw + known fixes |
| `learned_repair.py` | ML-based strategia napraw (DecisionTree) |
| `stable_snapshot.py` | Wersjonowanie skillów (stable/latest/archive/branches) |
| `garbage_collector.py` | Czyszczenie zbędnych wersji skillów |
| `quality_gate.py` | Walidacja jakości przed rejestracją skilla |
| `skill_validator.py` | Plugin registry dla walidacji wyników |
| `preflight.py` | SkillPreflight + EvolutionGuard |
| `evo_journal.py` | Dziennik ewolucji z metrykami jakości/szybkości |
| `system_identity.py` | Dynamiczny system prompt z statusem zdolności |
| `session_config.py` | Hot-swap konfiguracji w trakcie rozmowy |
| `config_generator.py` | Dynamiczna generacja brakujących konfigów via LLM |
| `user_memory.py` | Persistent pamięć długotrwała (dyrektywy/preferencje) |
| `voice_loop.py` | Pętla głosowa (STT/TTS bidirectional) |
| `stt_autotest.py` | STTAutoTestPipeline (Chain of Responsibility, 6 kroków) |
| `event_bus.py` | Pub/sub (blinker) — decoupling komponentów |
| `fuzzy_router.py` | FuzzyCommandRouter (rapidfuzz, tolerancja literówek) |
| `resilience.py` | tenacity retry + structlog structured logging |
| `skill_logger.py` | NFO logging (SQLite + JSONL) dla wszystkich skillów |
| `config.py` | Ścieżki, stałe, state management, tier modeli |
| `utils.py` | litellm setup, rich markdown, clean_code/clean_json |
| `logger.py` | Strukturalne logowanie per-skill/per-core |
| `supervisor.py` | Supervisor (A/B core management) |
| `pipeline_manager.py` | Pipeline management |

### Skille (`skills/`) — 35 skillów

**Bootstrap** (wbudowane): `deps`, `devops`, `echo`, `git_ops`, `llm_router`, `shell`

**Głos**: `tts` (espeak provider), `stt` (vosk provider)

**Narzędzia**: `web_search`, `benchmark`, `kalkulator`, `json_validator`, `password_generator`, `system_info`, `network_info`, `time`, `weather`, `content_search`

**Auto-tworzone** (przez system): `weather_gdansk`, `gbp_to_jpy_converter`, `text_processor_`, `local_computer_discovery`, `hw_test`, `actionchat`, `chat`, `diagnostic_runner`, i inne

**Testowe**: `openrouter_api_test`, `test_supervisor_probe`

Struktura wersjonowania: `skills/{capability}/providers/{provider}/stable|latest|archive/`

## Komendy (40+)

### Zarządzanie skillami
| Komenda | Opis |
|---------|------|
| `/skills` | Lista zainstalowanych skillów |
| `/create <name> [opis]` | Stwórz nowy skill |
| `/run <name> [input]` | Uruchom skill |
| `/test <name>` | Testuj skill |
| `/evolve <name> [feedback]` | Ewoluuj skill |
| `/rollback <name>` | Cofnij do poprzedniej wersji |
| `/health [name]` | Sprawdź stan skillów |
| `/diagnose <name>` | Diagnostyka skilla |

### Modele LLM
| Komenda | Opis |
|---------|------|
| `/model <name>` | Przełącz model |
| `/models` | Pokaż dostępne modele + tier status |
| `/models refresh` | Auto-discover modeli (OpenRouter + ollama) |
| `/autotune [goal] [profile]` | LIVE benchmark + auto-wybór modelu |
| `/apikey <key>` | Ustaw klucz OpenRouter (z weryfikacją) |

### Głos i hardware
| Komenda | Opis |
|---------|------|
| `/voice` | Wejdź w tryb głosowy (auto-save preferencji) |
| `/voice off` | Wyłącz tryb głosowy |
| `/stt [czas]` | Jednorazowe nagranie głosowe |
| `/hw [test]` | Diagnostyka sprzętowa (audio, devices, drivers) |

### Diagnostyka i naprawa
| Komenda | Opis |
|---------|------|
| `/reflect [skill]` | Uruchom autorefleksję systemu |
| `/fix [skill]` | Autonomiczna naprawa skilla |
| `/repairs [skill]` | Pokaż dziennik napraw |
| `/snapshot save\|restore\|list <skill>` | Zarządzanie wersjami |
| `/journal` | Dziennik ewolucji |
| `/gc [dry]` | Garbage collection wersji |

### Konfiguracja i pamięć
| Komenda | Opis |
|---------|------|
| `/config` | Pokaż konfigurację sesji |
| `/config <cat> <set> <val>` | Zmień ustawienie w locie |
| `/reload_config` | Przeładuj config/system.json |
| `/memories` | Pokaż zapamiętane dyrektywy |
| `/remember <tekst>` | Zapamiętaj preferencję |
| `/forget <id>` | Usuń dyrektywę |

### Uczenie i intencje
| Komenda | Opis |
|---------|------|
| `/correct <wrong> <right>` | Popraw ostatnią intencję |
| `/profile` | Profil użytkownika (topics, usage, corrections) |
| `/suggest` | Zasugeruj nowe skille na bazie nieobsłużonych intencji |
| `/topic` | Aktualny temat rozmowy |

### System
| Komenda | Opis |
|---------|------|
| `/providers` | Podsumowanie capability/provider |
| `/chain` | Łańcuchy fallback providerów |
| `/resources` | Snapshot zasobów systemowych |
| `/scan` | Skanuj zdolności systemu |
| `/core` | Status A/B core |
| `/state` | Pełny stan systemu (JSON) |
| `/pipeline list\|create\|run` | Zarządzanie pipeline'ami |
| `/compose` | Generuj docker-compose.yml |

## Konfiguracja

### Pliki konfiguracyjne (`config/`)

- `models.json` — lista modeli LLM per tier
- `system.json` — konfiguracja systemowa (limity, cooldowns, LLM params, filtry)
- `benchmark_results.json` — wyniki benchmarków modeli
- `intent_training_default.json` — domyślne dane treningowe intencji

### Plik stanu `.evo_state.json`

- Klucz API OpenRouter
- Wybrany model LLM + tier
- Preferencje użytkownika (UserMemory directives)
- Profil intencji (topics, corrections, skill_usage)
- Cooldowny modeli

### Konfiguracja w locie

Zmień providera/model w trakcie rozmowy:
```
> używaj lepszego TTS
> przełącz na gemini-pro
> /config tts provider coqui
```

## Testowanie

```bash
# Wszystkie testy (258)
python3 -m pytest tests/ -v

# Szybki health check
python3 main.py --check

# Tylko intent testy
python3 -m pytest tests/test_e2e.py -k "Intent" -v

# Symulacja (Docker)
docker compose -f docker-compose.simulate.yml up simulate
```

## Dokumentacja

- [Architektura systemu](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Tworzenie skillów](docs/creating_skills.md)
- [Konfiguracja](docs/configuration.md)
- [Rozwiązywanie problemów](docs/troubleshooting.md)
- [TODO / Roadmap](TODO.md)
- [Changelog](CHANGELOG.md)

## Przykłady

```
> stwórz kalkulator
[PIPE] Intent: create → kalkulator
[PIPE] Execute: gen_code → kalkulator v1
[PIPE] ✓ Skill created: kalkulator

> policz 2+2
[PIPE] Intent: use → kalkulator | goal: calculate 2+2
[PIPE] Execute: kalkulator v1
### ✅ kalkulator — done
- result: 4

> powiedz coś po polsku
[PIPE] Intent: use → tts | goal: speak text
### ✅ tts — done

> porozmawiajmy głosowo
🔊 Zapamiętano: tryb głosowy włączony na stałe.
🎤 Nagrywam... (mów teraz)
```

## Licencja

MIT License — zobacz [LICENSE](LICENSE)

## Wkład w projekt

1. Fork repozytorium
2. Stwórz branch (`git checkout -b feature/amazing`)
3. Commit zmiany (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Otwórz Pull Request

---

**CoreSkill v2.0** — Think, evolve, self-heal.
