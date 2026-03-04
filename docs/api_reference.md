# API Reference

## CoreSkill Public API

### Importowanie modułów

```python
from coreskill import LLMClient, SkillManager, EvoEngine, IntentEngine
```

## LLMClient

### Inicjalizacja

```python
from cores.v1.llm_client import LLMClient

llm = LLMClient(
    api_key="sk-or-v1-...",  # Opcjonalnie
    model="openrouter/meta-llama/llama-3.3-70b-instruct:free"
)
```

### Metody

#### `chat(messages, temperature=0.7, max_tokens=4096)`

Wykonuje chat completion z automatycznym fallbackiem.

```python
result = llm.chat(
    messages=[
        {"role": "system", "content": "You are helpful"},
        {"role": "user", "content": "Hello"}
    ],
    temperature=0.7,
    max_tokens=4096
)
```

**Returns:** `str` - odpowiedź modelu

#### `get_available_models(tier=None)`

Zwraca dostępne modele.

```python
# Wszystkie modele
all_models = llm.get_available_models()

# Tylko free tier
free_models = llm.get_available_models(tier="free")

# Tylko local
local_models = llm.get_available_models(tier="local")
```

#### `set_model(model_name)`

Ustawia aktywny model.

```python
llm.set_model("ollama/llama3.2:3b")
```

## SkillManager

### Inicjalizacja

```python
from cores.v1.skill_manager import SkillManager

sm = SkillManager(skills_dir="./skills")
```

### Metody

#### `exec_skill(name, action="execute", params={})`

Wykonuje skill z walidacją preflight.

```python
result = sm.exec_skill(
    name="tts",
    action="execute",
    params={"text": "Hello world"}
)

# Result format:
# {
#     "success": True,
#     "result": {...},
#     "duration_ms": 123
# }
```

#### `smart_evolve(name, goal, llm_client)`

Ewoluuje skill używając LLM.

```python
sm.smart_evolve(
    name="moj_skill",
    goal="Dodaj obsługę formatowania markdown",
    llm_client=llm
)
```

#### `check_health(name)`

Sprawdza health skilla.

```python
health = sm.check_health("tts")
# Returns: {"status": "ok", "errors": [], "warnings": []}
```

#### `list_skills()`

Lista wszystkich skillów.

```python
skills = sm.list_skills()
# Returns: ["tts", "stt", "shell", ...]
```

## EvoEngine

### Inicjalizacja

```python
from cores.v1.evo_engine import EvoEngine

evo = EvoEngine(
    skill_manager=sm,
    llm_client=llm,
    intent_engine=intent
)
```

### Metody

#### `handle_request(goal, context={})`

Obsługuje request z pipeline'em.

```python
result = evo.handle_request(
    goal="Przeczytaj mi artykuł o Pythonie",
    context={"voice_mode": True}
)
```

#### `evolve_skill(name, goal, iterations=3)`

Ewoluuje skill iteracyjnie.

```python
evo.evolve_skill(
    name="web_search",
    goal="Popraw wyszukiwanie DuckDuckGo",
    iterations=3
)
```

## IntentEngine

### Inicjalizacja

```python
from cores.v1.intent_engine import IntentEngine

intent = IntentEngine(skills={"tts": {...}, "stt": {...}})
```

### Metody

#### `analyze(text, skills, conversation=[])`

Analizuje intencję tekstu.

```python
analysis = intent.analyze(
    text="Przeczytaj mi to na głos",
    skills={"tts": {...}, "stt": {...}},
    conversation=[]
)

# Returns:
# {
#     "action": "use",
#     "skill": "tts",
#     "confidence": 0.85,
#     "goal": "Przeczytaj tekst na głos"
# }
```

#### `record_correction(text, correct_skill)`

Rejestruje poprawkę do uczenia.

```python
intent.record_correction(
    text="Przeczytaj mi to",
    correct_skill="tts"  # Poprzednio wykryło "stt"
)
```

## UserMemory

### Inicjalizacja

```python
from cores.v1.user_memory import UserMemory
from cores.v1.config import load_state

state = load_state()
memory = UserMemory(state)
```

### Metody

#### `add(text, priority="high")`

Dodaje dyrektywę.

```python
memory.add("Zawsze rozmawiaj po polsku", priority="high")
```

#### `remove(id)`

Usuwa dyrektywę.

```python
memory.remove(1)
```

#### `build_system_context()`

Buduje kontekst dla LLM.

```python
context = memory.build_system_context()
# Returns: "WAŻNE — trwałe preferencje użytkownika: ..."
```

#### `display()`

Wyświetla wszystkie dyrektywy.

```python
memory.display()
```

## Configuration

### State Management

```python
from cores.v1.config import load_state, save_state

# Load state
state = load_state()

# Modify
state["api_key"] = "new-key"

# Save (merges with existing)
save_state(state)
```

### Paths

```python
from cores.v1.config import (
    ROOT,           # Project root
    SKILLS_DIR,     # skills/ folder
    STATE_FILE,     # .evo_state.json
    LOGS_DIR        # logs/ folder
)
```

## Skill Interface

### Wymagane funkcje

Każdy skill musi implementować:

```python
def get_info() -> dict:
    """Zwraca metadane skilla."""
    return {
        "name": "skill_name",
        "version": "v1",
        "description": "Opis co skill robi"
    }

def execute(params: dict) -> dict:
    """Wykonuje akcję skilla."""
    # ... logika ...
    return {
        "success": True,      # bool - czy się udało
        "result": {...},       # dane wynikowe
        "error": None         # string jeśli błąd
    }
```

### Optional: klasa Skill

```python
class MySkill:
    def __init__(self):
        self.name = "my_skill"
    
    def get_info(self):
        return {"name": self.name, "version": "v1"}
    
    def execute(self, params):
        return {"success": True, "result": "done"}

def get_info():
    return MySkill().get_info()

def execute(params):
    return MySkill().execute(params)
```

## Event System

### NFO Logging

```python
from cores.v1.skill_logger import get_skill_logger

logger = get_skill_logger("my_skill")

@logger.log_call
def my_function():
    pass
```

### Query logs

```python
from cores.v1.skill_logger import (
    query_skill_errors,
    query_slow_calls,
    skill_health_summary
)

# Get recent errors
errors = query_skill_errors("tts", last_n=10)

# Get slow calls
slow = query_slow_calls(threshold_ms=1000, last_n=5)

# Health summary
health = skill_health_summary("tts")
# Returns: {"total_calls": 100, "errors": 2, "error_rate": 0.02, ...}
```

## Error Handling

### Standardowe kody błędów

```python
{
    "success": False,
    "error": "Opis błędu",
    "error_type": "import_error",  # lub: syntax_error, runtime_error, etc.
    "suggestion": "Jak naprawić"
}
```

### EvolutionGuard

```python
from cores.v1.preflight import EvolutionGuard

guard = EvolutionGuard()
guard.record_error("tts", error_fingerprint)
strategy = guard.suggest_strategy(error_fingerprint)
# Returns: "auto_fix_imports" | "install_deps" | "rewrite" | "evolve"
```

## CLI Commands

### Programatyczne użycie

```python
from cli import cmd_logs_reset, cmd_cache_reset
import argparse

# Reset logs
args = argparse.Namespace()
cmd_logs_reset(args)

# Reset cache
args = argparse.Namespace(full=False)
cmd_cache_reset(args)
```

## Typowe patterny

### 1. Pipeline execution

```python
# Detect intent
analysis = intent.analyze(user_input, skills)

# Execute skill
if analysis["action"] == "use":
    result = sm.exec_skill(
        analysis["skill"],
        params={"text": analysis["goal"]}
    )
    
    # Handle result
    if result["success"]:
        print(result["result"])
    else:
        # Auto-fix
        evo.evolve_skill(analysis["skill"], result["error"])
```

### 2. Memory + Context

```python
# Build context
memory_context = memory.build_system_context()

# Create LLM messages
messages = [
    {"role": "system", "content": SYSTEM_PROMPT + "\n" + memory_context},
    {"role": "user", "content": user_input}
]

# Call LLM
response = llm.chat(messages)
```

### 3. Skill creation

```python
# Auto-create skill
from cores.v1.evo_engine import EvoEngine

evo = EvoEngine(sm, llm, intent)
code = evo.generate_skill(
    name="calculator",
    description="Simple calculator with + - * /"
)

# Save
sm.save_skill("calculator", code)
```

## Constants

### W `cores/v1/config.py`

```python
TIER_FREE = "free"
TIER_LOCAL = "local"
TIER_PAID = "paid"

COOLDOWN_RATE_LIMIT = 60  # seconds
MAX_EVO_ITERATIONS = 5
```

## Utils

### Code cleaning

```python
from cores.v1.utils import clean_code, clean_json

# Remove markdown fences
code = clean_code("```python\nprint('hello')\n```")
# Returns: "print('hello')"

# Parse JSON
json_obj = clean_json('{"key": "value"}')
```

### Colors

```python
from cores.v1.config import C

print(f"{C.GREEN}Success!{C.RESET}")
print(f"{C.RED}Error!{C.RESET}")
print(f"{C.DIM}Muted text{C.RESET}")
```
