# CoreSkill vs ControlFlow — Szczegółowe porównanie

## Przegląd

| | CoreSkill | ControlFlow |
|---|-----------|-------------|
| **Twórca** | WronAI | Prefect (starsi orkiestracji workflow) |
| **Architektura** | Ewolucyjna (text2pipeline) | Workflow-orchestrated agents |
| **Licencja** | MIT | Apache 2.0 |
| **Cena** | Darmowy | Darmowy |
| **GitHub Stars** | Nowy projekt | ~2K (nowy) |
| **Focus** | Autonomiczna automatyzacja | Agent orchestration + observability |
| **Status** | Wczesna faza | Wczesna, szybki rozwój |

## Filozofia architektury

### ControlFlow: Orkiestracja workflow dla agentów
ControlFlow to framework od twórców **Prefect** (popularnego narzędzia do orkiestracji workflow). Łączy on koncepty z Prefect z agentami AI — **workflow jako first-class citizen**.

```python
import controlflow as cf

@cf.flow  # Prefect-style flow decorator
def research_topic(topic: str):
    # Tasks z concrete outputs (type-safe)
    outline = cf.run("Create outline", objective=f"Outline for {topic}")
    content = cf.run("Write content", context=outline)
    return content
```

**Kluczowe cechy:**
- **@flow decorator:** Workflow jako główna abstrakcja
- **Tasks:** Concrete outputs z Pydantic models
- **Agents:** Specialized AI workers przypisane do tasków
- **Observability:** Prefect-native monitoring

### CoreSkill: Autonomiczna ewolucja bez workflow
CoreSkill nie definiuje workflow — zamiast tego **intent-driven execution** z autonomiczną ewolucją.

```
Zapytanie → IntentEngine → Skill (auto-evolve) → Execute → Validate → (retry/evolve)
```

## Porównanie cech

### 1. Workflow i orkiestracja

| Aspekt | CoreSkill | ControlFlow |
|--------|-----------|-------------|
| **Abstrakcja** | Intent-driven | ✅ Workflow-first (@flow) |
| **Task definition** | Implicit (skill execution) | ✅ Explicit @task |
| **Dependencies** | DAG w pipeline (sekwencyjny) | ✅ Native (Prefect-style) |
| **Parallel execution** | ⚠️ Ograniczony | ✅ Prefect-native |
| **Observability** | NFO logging | ✅ Prefect UI |

**Werdykt:** ControlFlow ma znacznie lepszą orkiestrację workflow. CoreSkill ma autonomiczną ewolucję.

### 2. Agenci

| Aspekt | CoreSkill | ControlFlow |
|--------|-----------|-------------|
| **Model agenta** | Pojedynczy ewolucyjny | ✅ Multi-agent (specialized) |
| **Agent assignment** | Automatic (Intent→Skill) | ✅ Explicit (task → agent) |
| **Specialization** | Skill-based | ✅ Agent personas |
| **Memory** | UserMemory + state | ✅ Task context |

**Werdykt:** ControlFlow lepszy do multi-agent z jasną specjalizacją. CoreSkill ma auto-ewolucję.

### 3. Autonomia i self-healing

| Aspekt | CoreSkill | ControlFlow |
|--------|-----------|-------------|
| **Samo-ewolucja** | ✅ Mutacja kodu | ❌ |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ⚠️ Retry (Prefect) |
| **Auto-create** | ✅ LLM generuje skills | ❌ |
| **Quality gates** | ✅ 5-check pipeline | ⚠️ Task validation |
| **Proaktywny monitoring** | ✅ Scheduler | ✅ Prefect scheduled runs |

**Werdykt:** CoreSkill ma głębszą autonomię. ControlFlow ma enterprise-grade observability.

### 4. Developer Experience

| Aspekt | CoreSkill | ControlFlow |
|--------|-----------|-------------|
| **Krzywa uczenia** | Średnia | ✅ Niska (jeśli znasz Prefect) |
| **Debugging** | /reflect, logs | ✅ Prefect UI |
| **Type safety** | Dict-based | ✅ Pydantic native |
| **Polish support** | ✅ Native | ⚠️ |

### 5. Ekosystem

| Aspekt | CoreSkill | ControlFlow |
|--------|-----------|-------------|
| **Orchestration** | Basic | ✅ Prefect-powered |
| **Observability** | SQLite/JSONL | ✅ Prefect Cloud |
| **Integracje** | 15+ skills | ✅ Prefect ecosystem |
| **Community** | Mała | Prefect community |

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz **autonomicznego agenta**, który sam się naprawia
- ✅ System musi **sam tworzyć nowe zdolności** (auto-create skills)
- ✅ Chcesz działać **offline** / **local-first** z minimalnymi kosztami
- ✅ Budujesz **automatyzację IT/DevOps** z trybem głosowym
- ✅ Priorytetem jest **niezawodność** (quality gates, rollback)

## Kiedy wybrać ControlFlow?

- ✅ Potrzebujesz **workflow orchestration** dla agentów
- ✅ Znasz **Prefect** i chcesz użyć podobnych konceptów
- ✅ **Multi-agent** z jasną specjalizacją tasków
- ✅ Wymagasz **enterprise observability** (Prefect UI/Cloud)
- ✅ **Parallel execution** i złożone dependencies
- ✅ Chcesz **type-safe** task definitions

## Potencjalna synergia

ControlFlow i CoreSkill mogą się uzupełniać:
- ControlFlow jako **orkiestrator** workflow
- CoreSkill jako **executor** z self-healing dla poszczególnych tasków
- Prefect UI do monitoringu + CoreSkill auto-repair

## Podsumowanie

| | CoreSkill | ControlFlow |
|---|-----------|-------------|
| **Philosophy** | Autonomous self-healing | Workflow orchestration |
| **Best for** | Self-evolving automation | Complex agent workflows |
| **Orchestration** | Basic | ✅ Prefect-powered |
| **Self-healing** | ✅ Full | ⚠️ Retry only |

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
