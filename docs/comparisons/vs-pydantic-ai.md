# CoreSkill vs PydanticAI — Szczegółowe porównanie

## Przegląd

| | CoreSkill | PydanticAI |
|---|-----------|------------|
| **Twórca** | WronAI | Pydantic Team (Samuel Colvin) |
| **Architektura** | Ewolucyjna (text2pipeline) | Type-safe agent framework |
| **Licencja** | MIT | MIT |
| **Cena** | Darmowy | Darmowy |
| **GitHub Stars** | Nowy projekt | ~5K (nowy, grudzień 2024) |
| **Focus** | Autonomiczna automatyzacja | Type-safe AI agents |
| **Status** | Wczesna faza | Nowy, szybki rozwój |

## Filozofia architektury

### PydanticAI: Type-safe agent framework
PydanticAI to framework od twórców **Pydantic** (najpopularniejszej walidacji w Pythonie). Cała architektura opiera się na typach — modele, narzędzia, wyniki są silnie typowane.

```python
from pydantic_ai import Agent

agent = Agent(
    'openai:gpt-4o',
    result_type=UserProfile,  # Pydantic model
    system_prompt='Extract user profile from text',
)

result = agent.run_sync('John is 25 years old')
print(result.data)  # Fully typed UserProfile
```

**Kluczowe cechy:**
- **Type safety:** Wszystko oparte na Pydantic models
- **Dependency injection:** `deps_type` dla kontekstu
- **Result validation:** Automatyczna walidacja wyników
- **Streamed responses:** Natywne streaming

### CoreSkill: Ewolucyjna automatyzacja
CoreSkill nie wymaga silnego typowania — zamiast tego **sam tworzy i naprawia kod** realizujący zadania.

```
Zapytanie użytkownika → Intent → Auto-create skill (jeśli potrzeba) → Execute → Validate → Evolve
```

## Porównanie cech

### 1. Type safety

| Aspekt | CoreSkill | PydanticAI |
|--------|-----------|------------|
| **Typing** | Luźny (dict-based) | ✅ Silny (Pydantic models) |
| **Result validation** | ✅ SkillValidator | ✅ Pydantic native |
| **Schema generation** | ⚠️ Manual (SkillManifest) | ✅ Automatic from types |
| **Static type checking** | ❌ | ✅ mypy/pyright compatible |
| **IDE support** | ⚠️ Podstawowy | ✅ Excellent (autocomplete) |

**Werdykt:** PydanticAI wygrywa pod kątem type safety i DX (developer experience).

### 2. Agent architecture

| Aspekt | CoreSkill | PydanticAI |
|--------|-----------|------------|
| **Model agenta** | Ewolucyjny skill | ✅ Type-safe agent |
| **Narzędzia (tools)** | Skills (auto-evolving) | ✅ `@agent.tool` decorator |
| **Dependency injection** | ❌ | ✅ Native (`deps_type`) |
| **Context/pamięć** | UserMemory + state | ✅ `RunContext` |
| **Multi-agent** | ❌ | ⚠️ Możliwe |

**Werdykt:** PydanticAI ma lepszy model agenta z DI i kontekstem. CoreSkill ma autonomiczną ewolucję.

### 3. Autonomia i self-healing

| Aspekt | CoreSkill | PydanticAI |
|--------|-----------|------------|
| **Samo-ewolucja** | ✅ Pełna (mutacja kodu) | ❌ |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ |
| **Auto-create skills** | ✅ LLM generuje | ❌ |
| **Quality gates** | ✅ 5-check pipeline | ⚠️ Pydantic validation |
| **Proaktywny monitoring** | ✅ Scheduler | ❌ |

**Werdykt:** CoreSkill ma fundamentalną przewagę w autonomii.

### 4. Developer Experience

| Aspekt | CoreSkill | PydanticAI |
|--------|-----------|------------|
| **Krzywa uczenia** | Średnia | ✅ Niska (jeśli znasz Pydantic) |
| **Dokumentacja** | Wczesna | ✅ Excellent |
| **API design** | CLI + Python | ✅ Clean, Pythonic |
| **Debugging** | NFO logging + /reflect | ⚠️ Standard Python |
| **Polish support** | ✅ Native | ⚠️ |

### 5. LLM Management

| Aspekt | CoreSkill | PydanticAI |
|--------|-----------|------------|
| **Model support** | Ollama + OpenRouter | ✅ OpenAI, Anthropic, Gemini, Ollama |
| **Fallback** | ✅ 3-tier + UCB1 | ⚠️ Manual |
| **Cost optimization** | ✅ Free-first | ❌ |
| **Local-first** | ✅ Native | ✅ Ollama support |

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz **autonomicznego agenta**, który sam się rozwija
- ✅ System musi **sam się naprawiać** po awariach
- ✅ Chcesz **minimalną konserwację** (self-evolving)
- ✅ Budujesz **automatyzację IT/DevOps** z trybem głosowym
- ✅ Priorytetem jest **niezawodność** (rollback, monitoring)
- ✅ Pracujesz z **polskojęzycznymi** użytkownikami

## Kiedy wybrać PydanticAI?

- ✅ Cenisz **type safety** i walidację Pydantic
- ✅ Twój zespół zna Pydantic
- ✅ Budujesz **aplikację produkcyjną** wymagającą solidnego typowania
- ✅ Chcesz **dependency injection** w agentach
- ✅ Streaming jest kluczowy
- ✅ Zależy Ci na **świetnym IDE support** (autocomplete, type hints)

## Potencjalna synergia

PydanticAI i CoreSkill mogą się uzupełniać:
- PydanticAI jako **frontend** (type-safe API)
- CoreSkill jako **backend** (self-healing execution)
- Wspólne: Pydantic models dla walidacji wyników w CoreSkill

## Podsumowanie

| | CoreSkill | PydanticAI |
|---|-----------|------------|
| **Philosophy** | Autonomous reliability | Type-safe AI |
| **Best for** | Self-healing automation | Type-safe applications |
| **Polish** | ✅ Native | ⚠️ |
| **Learning curve** | Medium | ✅ Low |

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
