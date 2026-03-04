# CoreSkill vs DSPy — Szczegółowe porównanie

## Przegląd

| | CoreSkill | DSPy |
|---|-----------|------|
| **Twórca** | WronAI | Stanford University |
| **Architektura** | Ewolucyjna (text2pipeline) | Declarative programming dla LLM |
| **Licencja** | MIT | MIT |
| **Cena** | Darmowy | Darmowy |
| **GitHub Stars** | Nowy projekt | ~20K |
| **Historia** | 2024+ | 2023+ (Stanford AI Lab) |
| **Focus** | Autonomiczna automatyzacja | Programowanie LLM (prompt engineering 2.0) |
| **Status** | Wczesna faza | Szybki rozwój (akademiczny) |

## Filozofia architektury

### DSPy: Programowanie a nie promptowanie
DSPy to framework, który traktuje **LLM jako kompilator** — zamiast ręcznie pisać prompty, programista definiuje "Signatures" (wejście → wyjście), a DSPy automatycznie optymalizuje prompty i wybiera modele.

```python
class ExtractInfo(dspy.Signature):
    """Extract information from text."""
    text = dspy.InputField()
    entities = dspy.OutputField(desc="list of named entities")

# DSPy optimizes the prompt automatically
predictor = dspy.Predict(ExtractInfo)
```

**Nisza:** Zaawansowane aplikacje LLM wymagające optymalizacji promptów, few-shot learning, multi-hop reasoning.

### CoreSkill: Agentyczna ewolucja
CoreSkill nie optymalizuje promptów — **automatycznie tworzy i naprawia kod**, który realizuje zadania.

```python
# CoreSkill generates and evolves the actual implementation
user_query → IntentEngine → (auto-create skill) → EvoEngine → working code
```

## Porównanie cech

### 1. Abstrakcja LLM

| Aspekt | CoreSkill | DSPy |
|--------|-----------|------|
| **Poziom abstrakcji** | Agent/Skill | Program/Prompt |
| **Optymalizacja promptów** | ❌ Brak | ✅ Core feature (few-shot, bootstrap) |
| **Prompt compilation** | ❌ | ✅ Automatic prompt optimization |
| **Multi-hop reasoning** | ⚠️ Skill chaining | ✅ Native (ChainOfThought, ProgramOfThought) |
| **Module library** | Skills (evolving) | ✅ Predict, ChainOfThought, ProgramOfThought, ReAct |

**Werdykt:** DSPy znacznie bardziej zaawansowany w optymalizacji LLM. CoreSkill abstrahuje LLM jako narzędzie, nie jako główny obiekt.

### 2. Tworzenie kodu

| Aspekt | CoreSkill | DSPy |
|--------|-----------|------|
| **Auto-generowanie** | ✅ Pełne (mutacja kodu skillów) | ❌ |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ |
| **Quality gates** | ✅ 5-check pipeline | ❌ |
| **Wersjonowanie** | ✅ stable/latest/archive | ❌ |
| **Rollback** | ✅ Automatic | ❌ |

**Werdykt:** CoreSkill ma fundamentalną przewagę — generuje i naprawia sam kod, nie tylko optymalizuje prompty.

### 3. Autonomia i self-healing

| Aspekt | CoreSkill | DSPy |
|--------|-----------|------|
| **Samo-ewolucja** | ✅ Mutacja kodu | ❌ |
| **Self-healing** | ✅ AutoRepair | ❌ |
| **Proaktywny monitoring** | ✅ Scheduler + drift | ❌ |
| **Drift detection** | ✅ DriftDetector | ❌ |
| **Learning from errors** | ✅ RepairJournal | ❌ |

**Werdykt:** CoreSkill to system autonomiczny. DSPy to narzędzie do programowania LLM.

### 4. Use cases

| Aspekt | CoreSkill | DSPy |
|--------|-----------|------|
| **Chatbot/RAG** | ⚠️ Możliwy | ✅ Idealny |
| **Data extraction** | ⚠️ Skill | ✅ Core |
| **Classification** | ✅ 3-tier intent | ✅ Teleprompters |
| **Multi-hop QA** | ❌ | ✅ Best-in-class |
| **DevOps automation** | ✅ Core focus | ❌ |
| **Voice (STT/TTS)** | ✅ Native | ❌ |

### 5. Community i ekosystem

| Aspekt | CoreSkill | DSPy |
|--------|-----------|------|
| **Academic backing** | ❌ | ✅ Stanford AI Lab |
| **Research papers** | ❌ | ✅ 5+ papers |
| **Industry adoption** | Early | Growing (Databricks, etc.) |
| **Documentation** | Wczesna | Good |
| **Polish support** | ✅ Native | ⚠️ |

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz **autonomicznego agenta**, który działa bez nadzoru
- ✅ System musi **sam się naprawiać** po awariach
- ✅ Chcesz **minimalną konserwację** (self-evolving skills)
- ✅ Budujesz **automatyzację IT/DevOps**
- ✅ Potrzebujesz **trybu głosowego** (STT/TTS)
- ✅ Priorytetem jest **niezawodność** (quality gates, rollback)

## Kiedy wybrać DSPy?

- ✅ Budujesz **zaawansowane LLM applications**
- ✅ Potrzebujesz **optymalizacji promptów** (few-shot, bootstrap)
- ✅ **Multi-hop reasoning** jest kluczowy
- ✅ Chcesz **deklaratywne** podejście do LLM (zamiast manualnych promptów)
- ✅ Research/academic backing ma znaczenie
- ✅ Chcesz **eksperymentować** z różnymi modelami i strategiami

## Fundamentalna różnica

> **DSPy:** "Zaprogramuj LLM deklaratywnie, niech framework zoptymalizuje prompty"
> **CoreSkill:** "Postaw agenta, który sam napisze i naprawi kod realizujący zadanie"

DSPy to **narzędzie programistyczne** dla LLM. CoreSkill to **autonomiczny system** samonaprawialny.

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
