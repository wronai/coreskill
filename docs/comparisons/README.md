# CoreSkill vs Konkurencja — Porównanie

Szczegółowe porównanie CoreSkill (evo-engine) z wiodącymi frameworkami i platformami AI agentów na rynku.

## Zbiorcza tabela porównawcza

| Cecha | CoreSkill | LangGraph | CrewAI | MS Agent | Haystack | AutoGPT | Rasa | Botpress | LlamaIndex | DSPy | PydanticAI | Agno | ControlFlow |
|-------|-----------|-----------|--------|--------------------|----------|---------|------|----------|
| **Architektura** | Ewolucyjna (text2pipeline) | Graf stanów | Role-based multi-agent | Multi-agent konwersacje | Pipeline RAG | Autonomiczna pętla | NLU pipeline | LLMz engine | Data framework | LLM programming | Type-safe agents | Agent UI | Workflow orchestration |
| **Samo-ewolucja skillów** | ✅ Pełna | ❌ | ❌ | ❌ | ❌ | ⚠️ Marketplace | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Samo-naprawa** | ✅ 5-fazowa | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Ograniczona | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Proaktywny monitoring** | ✅ Scheduler + drift | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Klasyfikacja intencji** | ✅ 3-tier ML | ❌ Ręczna | ❌ Ręczna | ❌ Ręczna | ❌ Ręczna | ⚠️ LLM-only | ✅ NLU | ⚠️ LLM-only | ❌ | ❌ | ❌ | ⚠️ LLM | ❌ |
| **Tiered LLM routing** | ✅ Free→Local→Paid | ⚠️ LiteLLM | ⚠️ Config | ⚠️ Azure | ⚠️ Config | ⚠️ Single | ❌ Własny NLU | ⚠️ Pass-through | ⚠️ Config | ⚠️ Config | ⚠️ Config | ⚠️ Config | ⚠️ Config |
| **Tryb głosowy STT/TTS** | ✅ Natywny | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Kanały | ✅ Integracje | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Local-first** | ✅ Ollama offline | ❌ Cloud | ❌ Cloud | ⚠️ Azure | ⚠️ Cloud | ⚠️ Wymaga API | ✅ On-prem | ❌ Cloud | ⚠️ Cloud | ✅ Local | ✅ Local | ⚠️ Cloud | ✅ Local |
| **Quality gates** | ✅ 5-check | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Pydantic | ❌ | ⚠️ Task valid |
| **Provider chain** | ✅ Auto-degradacja | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Licencja** | MIT | MIT | MIT | MIT | Apache 2.0 | MIT | Dual | Proprietary | MIT | MIT | MIT | MIT | Apache 2.0 |
| **Cena** | Darmowy | Darmowy + $39 | $99-120K/rok | Darmowy | Custom | Darmowy | Od $35K/rok | Od $89/mies | Od $15/mies | Darmowy | Darmowy | Darmowy + cloud | Darmowy |
| **GitHub Stars** | Nowy | ~15K | ~40K | ~55K | ~24K | ~182K | ~19K | ~13K | ~40K | ~20K | ~5K | ~5K | ~2K |
| **Dojrzałość** | Wczesna | Produkcja | Produkcja | Przejściowa | Produkcja | Aktywny | Produkcja | Produkcja | Produkcja | Szybki rozwój | Nowy | Szybki rozwój | Wczesna |

## Unikalne cechy CoreSkill

### 🧬 Ewolucyjny silnik skillów
Żaden z konkurentów nie oferuje pełnego cyklu ewolucyjnego: **detect → execute → validate → mutate → retry** z automatycznym rollbackiem i journal-based learning.

### 🏥 5-fazowa samo-naprawa
AutoRepair: DIAGNOSE → PLAN → FIX → VERIFY → REFLECT z RepairJournal uczącym się z poprzednich napraw (KnownFix pattern matching).

### 📡 Proaktywny scheduler
Jedyna cecha **genuinely rare** w całym ekosystemie — background health checks, periodic GC, drift detection. Brak odpowiednika w LangGraph, CrewAI, AutoGen ani żadnym innym frameworku.

### 🎯 3-tierowa klasyfikacja intencji z self-training
Kaskada: embedding (sbert/TF-IDF) → local LLM (ollama ≤3B) → remote LLM, z automatycznym uczeniem się z korekt użytkownika.

### 🎰 UCB1 Bandit Provider Selection
Adaptacyjny wybór providerów oparty na algorytmie UCB1 multi-armed bandit — żaden konkurent nie stosuje exploration/exploitation do wyboru providerów.

## Szczegółowe porównania

| Rozwiązanie | Typ | Artykuł |
|-------------|-----|---------|
| LangGraph (LangChain) | Framework OSS | [CoreSkill vs LangGraph](vs-langgraph.md) |
| CrewAI | Framework OSS | [CoreSkill vs CrewAI](vs-crewai.md) |
| Microsoft Agent Framework | Framework OSS | [CoreSkill vs Microsoft Agent Framework](vs-microsoft-agent-framework.md) |
| Haystack | Framework OSS | [CoreSkill vs Haystack](vs-haystack.md) |
| AutoGPT | Platforma OSS | [CoreSkill vs AutoGPT](vs-autogpt.md) |
| Rasa | Platforma komercyjna | [CoreSkill vs Rasa](vs-rasa.md) |
| Botpress | Platforma komercyjna | [CoreSkill vs Botpress](vs-botpress.md) |
| Beam AI | Platforma komercyjna | [CoreSkill vs Beam AI](vs-beam-ai.md) |
| LlamaIndex | Framework OSS (RAG) | [CoreSkill vs LlamaIndex](vs-llamaindex.md) |
| DSPy | Framework OSS (LLM programming) | [CoreSkill vs DSPy](vs-dspy.md) |
| PydanticAI | Framework OSS (type-safe) | [CoreSkill vs PydanticAI](vs-pydantic-ai.md) |
| Agno | Framework OSS (Agent UI) | [CoreSkill vs Agno](vs-agno.md) |
| ControlFlow | Framework OSS (workflow) | [CoreSkill vs ControlFlow](vs-controlflow.md) |

## Podsumowanie pozycjonowania

```
                    Kontrola przepływu
                         ▲
                         │
              LangGraph  │  MS Agent Framework
                    ●    │    ●
           ControlFlow ●  │    ● DSPy
                         │
   Prostota ◄────────────┼────────────► Autonomia
                         │
              CrewAI ●   │        ● CoreSkill
                         │
        PydanticAI ●     │   ● AutoGPT
              Agno ●    │
              Haystack ● │
           LlamaIndex ●  │
                         ▼
                    Automatyzacja
```

**CoreSkill** zajmuje unikalną pozycję w kwadrancie **wysoka autonomia + wysoka automatyzacja** — tam, gdzie żaden z obecnych liderów rynku nie jest silny. LangGraph sprzedaje kontrolę, CrewAI prostotę, Microsoft integrację z ekosystemem — nikt nie posiada narracji **"autonomous reliability"**.

**Grupy frameworków:**
- **Kontrola/Workflow:** LangGraph, ControlFlow, MS Agent Framework, DSPy
- **Prostota:** CrewAI, PydanticAI, Agno
- **Automatyzacja danych:** Haystack, LlamaIndex
- **Autonomia:** CoreSkill, AutoGPT

---

*Ostatnia aktualizacja: marzec 2025*
*Źródło danych rynkowych: Compass Competitive Landscape Report*
