# CoreSkill vs Konkurencja — Porównanie

Szczegółowe porównanie CoreSkill (evo-engine) z wiodącymi frameworkami AI agentów na rynku.

## Zbiorcza tabela porównawcza

| Cecha | CoreSkill | LangGraph | CrewAI | AutoGPT | ControlFlow | PydanticAI | MS Agent | DSPy |
|-------|-----------|-----------|--------|---------|-------------|------------|----------|------|
| **Architektura** | Ewolucyjna | Graf stanów | Role-based | Pętla autonomiczna | Workflow | Type-safe agents | Multi-agent | LLM programming |
| **Samo-ewolucja** | ✅ Pełna | ❌ | ❌ | ⚠️ Marketplace | ❌ | ❌ | ❌ | ❌ |
| **Samo-naprawa** | ✅ 5-fazowa | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Proaktywny monitoring** | ✅ Scheduler | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Klasyfikacja intencji** | ✅ 3-tier ML | ❌ Ręczna | ❌ Ręczna | ⚠️ LLM-only | ❌ | ❌ | ❌ Ręczna | ❌ |
| **Tiered LLM routing** | ✅ Free→Local→Paid | ⚠️ LiteLLM | ⚠️ Config | ⚠️ Single | ⚠️ Config | ⚠️ Config | ⚠️ Azure | ⚠️ Config |
| **Voice STT/TTS** | ✅ Natywny | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Local-first** | ✅ Ollama offline | ❌ Cloud | ❌ Cloud | ⚠️ Wymaga API | ✅ Local | ✅ Local | ⚠️ Azure | ✅ Local |
| **Quality gates** | ✅ 5-check | ❌ | ❌ | ❌ | ⚠️ Task valid | ⚠️ Pydantic | ❌ | ❌ |
| **Licencja** | MIT | MIT | MIT | MIT | Apache 2.0 | MIT | MIT | MIT |
| **Cena** | Darmowy | Darmowy + $39 | $99-120K/rok | Darmowy | Darmowy | Darmowy | Darmowy | Darmowy |
| **GitHub Stars** | Nowy | ~15K | ~40K | ~182K | ~2K | ~5K | ~55K | ~20K |
| **Dojrzałość** | Wczesna | Produkcja | Produkcja | Aktywny | Wczesna | Nowy | Przejściowa | Szybki rozwój |

## Unikalne cechy CoreSkill

### 🧬 Ewolucyjny silnik skillów
Pełny cykl: **detect → execute → validate → mutate → retry** z automatycznym rollbackiem.

### 🏥 5-fazowa samo-naprawa
DIAGNOSE → PLAN → FIX → VERIFY → REFLECT z RepairJournal uczącym się z poprzednich napraw.

### 📡 Proaktywny scheduler
Jedyna cecha genuinely rare — background health checks, periodic GC, drift detection.

### 🎯 3-tierowa klasyfikacja intencji
Embedding → local LLM → remote LLM z self-training.

### 🎰 UCB1 Bandit Provider Selection
Adaptacyjny wybór providerów oparty na multi-armed bandit.

## Szczegółowe porównania

| Rozwiązanie | Typ | Artykuł |
|-------------|-----|---------|
| LangGraph | Framework OSS | [CoreSkill vs LangGraph](vs-langgraph.md) |
| CrewAI | Framework OSS | [CoreSkill vs CrewAI](vs-crewai.md) |
| AutoGPT | Platforma OSS | [CoreSkill vs AutoGPT](vs-autogpt.md) |
| ControlFlow | Framework OSS | [CoreSkill vs ControlFlow](vs-controlflow.md) |
| PydanticAI | Framework OSS | [CoreSkill vs PydanticAI](vs-pydantic-ai.md) |
| Microsoft Agent Framework | Framework OSS | [CoreSkill vs MS Agent](vs-microsoft-agent-framework.md) |
| DSPy | Framework OSS | [CoreSkill vs DSPy](vs-dspy.md) |

## Podsumowanie pozycjonowania

```
                    Kontrola przepływu
                         ▲
                         │
              LangGraph  │  ControlFlow
                    ●    │    ●
           MS Agent ●    │    ● DSPy
                         │
   Prostota ◄────────────┼────────────► Autonomia
                         │
              CrewAI ●   │    ● CoreSkill
                         │         ● AutoGPT
        PydanticAI ●     │
                         ▼
                    Automatyzacja
```

**CoreSkill** zajmuje unikalną pozycję w kwadrancie **wysoka autonomia + wysoka automatyzacja** — tam, gdzie żaden z liderów nie jest silny.

---

*Ostatnia aktualizacja: marzec 2025*
