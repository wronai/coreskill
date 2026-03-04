# CoreSkill

Ewolucyjny system AI z ewoluującymi skillami. CoreSkill to inteligentny asystent, który potrafi samodzielnie tworzyć, naprawiać i rozwijać swoje zdolności (skills).

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🚀 Szybki start

### Instalacja

```bash
# Klonowanie repozytorium
git clone https://github.com/wronai/coreskill.git
cd coreskill

# Instalacja zależności
pip install -r requirements.txt

# Lub instalacja jako pakiet Python
pip install -e .
```

### Pierwsze uruchomienie

```bash
# Interaktywna powłoka
coreskill
coreskill --verbose

# Lub bez instalacji
python3 main.py
python3 main.py --verbose
```

## ✨ Kluczowe funkcje

- **🧠 Ewoluujące skille** - System tworzy i naprawia skille automatycznie
- **🎯 Inteligentne intencje** - Rozumie kontekst i intencje użytkownika
- **🔊 Tryb głosowy** - Pełna obsługa głosowa (STT/TTS)
- **💬 Wielojęzyczność** - Natywne wsparcie dla języka polskiego
- **⚡ Tiered LLM** - Automatyczny fallback między modelami (free → local → paid)
- **🧪 Testowanie API** - Automatyczna weryfikacja kluczy API

## 📚 Komendy CLI

```bash
coreskill                    # Uruchom interaktywną powłokę
coreskill status            # Pokaż status systemu
coreskill logs reset        # Usuń wszystkie logi
coreskill cache reset       # Wyczyść cache
```

## 🛠️ Dostępne komendy w powłoce

| Komenda | Opis |
|---------|------|
| `/help` | Lista wszystkich komend |
| `/apikey <key>` | Ustaw klucz OpenRouter (z auto-weryfikacją) |
| `/voice on/off` | Włącz/wyłącz tryb głosowy |
| `/models` | Pokaż dostępne modele LLM |
| `/autotune` | Automatyczny wybór najlepszego modelu |
| `/skills` | Lista zainstalowanych skillów |
| `/health` | Sprawdź stan skillów |
| `/evolve <skill>` | Ewoluuj skill |
| `/remember <tekst>` | Zapamiętaj preferencję |
| `/memories` | Pokaż zapamiętane dyrektywy |

## 🏗️ Architektura

### Core komponenty (`cores/v1/`)

- `evo_engine.py` - Silnik ewolucyjny
- `llm_client.py` - Klient LLM z tiered fallback
- `intent_engine.py` - Detekcja intencji (ML-based)
- `skill_manager.py` - Zarządzanie skillami
- `provider_selector.py` - Wybór providerów
- `user_memory.py` - Pamięć użytkownika

### Skille (`skills/`)

Skille są ewoluujące i mogą być tworzone automatycznie:

- `benchmark/` - Testowanie i benchmark modeli
- `deps/` - Zarządzanie zależnościami
- `echo/` - Testowy skill
- `git_ops/` - Operacje na gicie
- `llm_router/` - Zarządzanie modelami LLM
- `openrouter_api_test/` - Testowanie API OpenRouter
- `shell/` - Wykonywanie komend shell
- `stt/` - Speech-to-Text (różne providery)
- `tts/` - Text-to-Speech (różne providery)
- `web_search/` - Wyszukiwanie w sieci

## 📖 Dokumentacja

- [Architektura systemu](docs/architecture.md)
- [API Reference](docs/api_reference.md)
- [Tworzenie skillów](docs/creating_skills.md)
- [Konfiguracja](docs/configuration.md)
- [Rozwiązywanie problemów](docs/troubleshooting.md)
- [**Porównanie z konkurencją**](docs/comparisons/README.md) — CoreSkill vs LangGraph, CrewAI, AutoGPT, Rasa i inne

## 💡 Przykłady użycia

Zobacz folder `examples/`:
- `examples/basic/` - Podstawowe użycie
- `examples/advanced/` - Zaawansowane scenariusze
- `examples/skills/` - Tworzenie własnych skillów

## 🔧 Konfiguracja

### Zmienne środowiskowe

```bash
export OPENROUTER_API_KEY="sk-or-v1-..."  # Opcjonalnie, można też przez /apikey
export EVO_VERBOSE=1                        # Włącz verbose logging
export EVO_DISABLE_LOCAL=1                # Wyłącz modele lokalne
```

### Plik stanu `.evo_state.json`

Przechowuje:
- Klucz API
- Wybrany model LLM
- Preferencje użytkownika (pamięć)
- Cooldowny modeli

## 🧪 Testowanie

```bash
# Uruchom wszystkie testy
python3 -m pytest tests/

# Szybki check
python3 main.py --check
```

## 📋 TODO / Roadmap

Zobacz [TODO.md](TODO.md) i [CHANGELOG.md](CHANGELOG.md)

## 📄 Licencja

Apache License 2.0 - zobacz [LICENSE](LICENSE)

## 🤝 Wkład w projekt

1. Fork repozytorium
2. Stwórz branch (`git checkout -b feature/amazing`)
3. Commit zmiany (`git commit -m 'Add amazing feature'`)
4. Push (`git push origin feature/amazing`)
5. Otwórz Pull Request

---

**CoreSkill** - Think, evolve, create.

