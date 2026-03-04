# CoreSkill vs Konkurencja — Porównanie

Szczegółowe porównanie CoreSkill (evo-engine) z wiodącymi frameworkami i platformami AI agentów na rynku.

## Zbiorcza tabela porównawcza

| Cecha | CoreSkill | LangGraph | CrewAI | MS Agent Framework | Haystack | AutoGPT | Rasa | Botpress |
|-------|-----------|-----------|--------|--------------------|----------|---------|------|----------|
| **Architektura** | Ewolucyjna (text2pipeline) | Graf stanów | Role-based multi-agent | Multi-agent konwersacje | Pipeline RAG | Autonomiczna pętla | NLU pipeline | LLMz engine |
| **Samo-ewolucja skillów** | ✅ Pełna (mutacja + walidacja + rollback) | ❌ | ❌ | ❌ | ❌ | ⚠️ Marketplace | ❌ | ❌ |
| **Samo-naprawa** | ✅ 5-fazowa (diagnoza → plan → fix → weryfikacja → refleksja) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ⚠️ Ograniczona |
| **Proaktywny monitoring** | ✅ Scheduler + health checks + drift detection | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Klasyfikacja intencji** | ✅ 3-tier ML (embedding → local LLM → remote LLM) | ❌ Ręczna | ❌ Ręczna | ❌ Ręczna | ❌ Ręczna | ⚠️ LLM-only | ✅ NLU pipeline | ⚠️ LLM-only |
| **Tiered LLM routing** | ✅ Free → Local → Paid + UCB1 bandit | ⚠️ Przez LiteLLM | ⚠️ Konfiguracja | ⚠️ Azure-centric | ⚠️ Konfiguracja | ⚠️ Single model | ❌ Własny NLU | ⚠️ Pass-through |
| **Tryb głosowy (STT/TTS)** | ✅ Natywny (vosk/espeak) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ Kanały głosowe | ✅ Integracje |
| **Local-first** | ✅ Ollama + offline | ❌ Cloud-first | ❌ Cloud-first | ⚠️ Azure-first | ⚠️ Cloud-first | ⚠️ Wymaga API | ✅ On-premise | ❌ Cloud |
| **Quality gates** | ✅ 5-check pipeline | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Provider chain + fallback** | ✅ Auto-degradacja + UCB1 | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Licencja** | Apache 2.0 | MIT | MIT | MIT | Apache 2.0 | MIT | Dual (OSS + commercial) | Proprietary |
| **Cena** | Darmowy | Darmowy + $39/seat | $99–$120K/rok | Darmowy | Custom enterprise | Darmowy + cloud | Od $35K/rok | Od $89/mies. |
| **GitHub Stars** | Nowy projekt | ~15K | ~40K | ~55K | ~24K | ~182K | ~19K | ~13K |
| **Dojrzałość** | Wczesna faza | Produkcja (1.0) | Produkcja | Przejściowa | Produkcja | Aktywny | Produkcja | Produkcja |

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

## Podsumowanie pozycjonowania

```
                    Kontrola przepływu
                         ▲
                         │
              LangGraph  │  MS Agent Framework
                    ●    │    ●
                         │
   Prostota ◄────────────┼────────────► Autonomia
                         │
              CrewAI ●   │        ● CoreSkill
                         │
              Haystack ● │  AutoGPT ●
                         │
                         ▼
                    Automatyzacja
```

**CoreSkill** zajmuje unikalną pozycję w kwadrancie **wysoka autonomia + wysoka automatyzacja** — tam, gdzie żaden z obecnych liderów rynku nie jest silny. LangGraph sprzedaje kontrolę, CrewAI prostotę, Microsoft integrację z ekosystemem — nikt nie posiada narracji **"autonomous reliability"**.

---

*Ostatnia aktualizacja: marzec 2026*
*Źródło danych rynkowych: Compass Competitive Landscape Report*
