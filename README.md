# evo-engine - Evolutionary AI System

Self-healing dual-core AI system with LLM-driven skill building and pipeline orchestration.

## Quick Start

```bash
python3 main.py
# Wklej klucz API OpenRouter, następnie czatuj lub używaj komend /commands
```

Wymagany klucz API: [OpenRouter API Keys](https://openrouter.ai/keys)

## Architecture

```
evo-engine/
├── main.py              Bootstrap systemu
├── seeds/               Szablony początkowe
│   ├── core_v1.py       Implementacja jądra v1
│   └── echo_skill_v1.py Przykładowa umiejętność
├── cores/vN/            Wersjonowane jądra A/B
│   └── core.py          Główny silnik AI
├── skills/name/vN/      Wersjonowane umiejętności
│   ├── skill.py         Implementacja umiejętności
│   ├── meta.json        Metadane i checksum
│   └── Dockerfile       Kontener umiejętności
├── pipelines/*.json     Definicje pipeline'ów
├── logs/                Logi systemowe
└── .evo_state.json      Stan systemu
```

## Core Features

### 🧠 Dual-Core Architecture
- **A/B Core System**: Dwa niezależne jądra z automatycznym przełączaniem
- **Self-Healing**: Automatyczna regeneracja w przypadku awarii
- **Hot Swapping**: Bezproblemowa aktualizacja bez przestojów

### 🛠️ Skill Management
- **Versioned Skills**: Każda umiejętność ma wersje (v1, v2, v3...)
- **AI-Driven Creation**: LLM generuje kod umiejętności z opisu
- **Evolution**: Ulepszanie umiejętności na podstawie feedbacku
- **Rollback**: Szybki powrót do poprzedniej wersji

### 🔄 Pipeline Orchestration
- **Multi-Step Workflows**: Łączenie wielu umiejętności w pipeline'y
- **Data Flow**: Przekazywanie wyników między krokami
- **JSON Definitions**: Declaratywne definicje pipeline'ów

### 🐳 Container Support
- **Docker Compose**: Automatyczna generacja konfiguracji
- **Isolated Skills**: Każda umiejętność w osobnym kontenerze
- **Scalable Architecture**: Możliwość skalowania poziomego

## Commands Reference

### Skill Management
```bash
/skills                    # Lista wszystkich umiejętności
/create <name>            # Stwórz nową umiejętność
/run <name> [version]     # Uruchom umiejętność
/evolve <name>            # Ulepsz umiejętność
/rollback <name>          # Cofnij do poprzedniej wersji
```

### Pipeline Operations
```bash
/pipeline list            # Lista pipeline'ów
/pipeline create          # Stwórz nowy pipeline
/pipeline run <name>      # Uruchom pipeline
```

### System Management
```bash
/core                     # Status jąder A/B
/switch                   # Przełącz aktywne jądro
/model <model_name>       # Zmień model AI
/models                   # Lista dostępnych modeli
/compose                  # Generuj docker-compose.yml
/state                    # Pokaż stan systemu
/log                      # Ostatnie logi
/help                     # Pomoc
/quit                     # Wyjście
```

## Available Models

- `openrouter/stepfun/step-3.5-flash:free` (default)
- `openrouter/google/gemma-3-1b-it:free`
- `openrouter/meta-llama/llama-3.1-8b-instruct:free`
- `openrouter/qwen/qwen-2.5-72b-instruct:free`
- `openrouter/deepseek/deepseek-chat-v3-0324:free`
- `openrouter/google/gemini-2.0-flash-exp:free`

## Usage Examples

### Creating a Skill
```
/create translator
Describe 'translator': Translates text between languages using AI
```

### Running a Skill
```
/run translator v2
{"input": {"text": "Hello", "from": "en", "to": "pl"}}
```

### Building a Pipeline
```
/pipeline create
Name: content_processor
Describe: Analyze sentiment and translate text
```

### System Monitoring
```
/core
  A: v1 <-ACTIVE
  B: v2
/state
{
  "active_core": "A",
  "core_a_version": 1,
  "core_b_version": 2,
  "model": "openrouter/stepfun/step-3.5-flash:free"
}
```

## Development

### Adding New Seeds
1. Stwórz plik w `seeds/`
2. Bootstrap automatycznie skopiuje do odpowiednich lokalizacji

### Skill Template
```python
def get_info():
    return {"name": "skill_name", "version": "v1", "description": "..."}

def health_check():
    return True

class SkillClass:
    def execute(self, input_data):
        # Logic here
        return {"result": "...", "status": "ok"}

def execute(input_data):
    return SkillClass().execute(input_data)
```

## Security & Reliability

- **Checksum Verification**: Każda umiejętność ma weryfikację integralności
- **Isolated Execution**: Umiejętności działają w izolowanych kontenerach
- **Automatic Recovery**: System regeneruje się z awarii
- **Version Control**: Pełna historia zmian każdej umiejętności

## License

Apache License 2.0 - see [LICENSE](LICENSE) for details.

## Author

Created by **Tom Sapletta** - [tom@sapletta.com](mailto:tom@sapletta.com)
