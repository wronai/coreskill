# CoreSkill vs LangGraph — Szczegółowe porównanie

## Przegląd

| | CoreSkill | LangGraph |
|---|-----------|-----------|
| **Twórca** | WronAI | LangChain Inc. |
| **Architektura** | Ewolucyjna (text2pipeline) | Graf stanów (state machine) |
| **Licencja** | MIT | MIT |
| **Cena** | Darmowy | Darmowy + LangSmith $39/seat/mies. |
| **GitHub Stars** | Nowy projekt | ~15K |
| **Wycena firmy** | — | $1.25B (po rundzie $125M, X 2025) |
| **Klienci** | Early adopters | LinkedIn, Uber, Klarna |
| **Status** | Wczesna faza | Produkcja (LangGraph 1.0, X 2025) |

## Filozofia architektury

### LangGraph: Kontrola przez grafy
LangGraph to framework oparty na **grafach stanów** (state machines), gdzie programista definiuje węzły (nodes) i krawędzie (edges) reprezentujące przepływ agenta. Każdy węzeł to funkcja, a krawędzie definiują warunki przejścia.

```
[Node A] --condition--> [Node B] --always--> [Node C]
     └--condition--> [Node D]
```

**Zalety:** Pełna kontrola nad przepływem, deterministyczne zachowanie, łatwe debugowanie.
**Wady:** Wymaga ręcznego definiowania każdego ścieżki, brak adaptacji runtime.

### CoreSkill: Ewolucja przez mutację
CoreSkill stosuje architekturę **text2pipeline** z ewolucyjnym cyklem:

```
detect → execute → validate → (fail → diagnose → mutate → retry)
```

**Zalety:** Automatyczna adaptacja, self-healing, brak potrzeby definiowania grafów.
**Wady:** Mniejsza deterministyczność, trudniejsze do przewidzenia zachowanie.

## Porównanie cech

### 1. Orkiestracja agentów

| Aspekt | CoreSkill | LangGraph |
|--------|-----------|-----------|
| **Model** | Pipeline ewolucyjny | Graf stanów |
| **Definiowanie przepływu** | Automatyczne (intent → skill) | Ręczne (nodes + edges) |
| **Warunkowe przejścia** | Implicit (walidacja wyniku) | Explicit (edge conditions) |
| **Równoległość** | Sekwencyjna (DAG w pipeline) | Natywna (parallel branches) |
| **Checkpoint/resume** | Stan w .evo_state.json | Wbudowany checkpointing |
| **Human-in-the-loop** | CLI interactive | Natywny (interrupt_before/after) |

**Werdykt:** LangGraph wygrywa w scenariuszach wymagających precyzyjnej kontroli przepływu. CoreSkill wygrywa gdy przepływ powinien się sam adaptować.

### 2. Samo-naprawa i odporność

| Aspekt | CoreSkill | LangGraph |
|--------|-----------|-----------|
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ Brak |
| **Auto-rollback** | ✅ Wersjonowanie stable/latest/archive | ❌ Manual checkpoint restore |
| **Retry z ewolucją** | ✅ Diagnoza + mutacja kodu + retry | ⚠️ Prosty retry (bez mutacji) |
| **Drift detection** | ✅ DriftDetector module | ❌ Brak |
| **Health monitoring** | ✅ ProactiveScheduler (background) | ❌ Zewnętrzne (LangSmith) |
| **Quality gates** | ✅ 5-check SkillQualityGate | ❌ Brak |

**Werdykt:** CoreSkill ma fundamentalną przewagę — LangGraph nie posiada żadnego wbudowanego mechanizmu samo-naprawy. Użytkownicy LangGraph polegają na zewnętrznym monitoringu (LangSmith) i ręcznej interwencji.

### 3. Zarządzanie LLM

| Aspekt | CoreSkill | LangGraph |
|--------|-----------|-----------|
| **Routing** | 3-tier (free → local → paid) + UCB1 bandit | Konfiguracja per-node |
| **Failover** | Automatyczny z cooldown/blacklist | Ręczny (przez konfigurację) |
| **Lokalne modele** | ✅ Auto-discovery Ollama | ⚠️ Manualna konfiguracja |
| **Koszt optymalizacji** | ✅ Automatyczny (najtańszy tier first) | ❌ Odpowiedzialność programisty |
| **Rate limit handling** | ✅ 60s cooldown + tier switch | ⚠️ Retry bez tier switch |

**Werdykt:** CoreSkill ma bardziej zaawansowany routing LLM "out of the box". LangGraph wymaga dodatkowej konfiguracji (np. LiteLLM) dla podobnej funkcjonalności.

### 4. Klasyfikacja intencji

| Aspekt | CoreSkill | LangGraph |
|--------|-----------|-----------|
| **Wbudowana** | ✅ SmartIntentClassifier (3-tier ML) | ❌ Brak |
| **Self-training** | ✅ Uczenie z korekt użytkownika | ❌ N/A |
| **Obsługa wielojęzyczna** | ✅ PL/EN natywnie | ❌ Zależy od LLM |

**Werdykt:** CoreSkill ma wbudowaną inteligentną klasyfikację. W LangGraph programista musi sam zaimplementować logikę routingu zapytań.

### 5. Ekosystem i narzędzia

| Aspekt | CoreSkill | LangGraph |
|--------|-----------|-----------|
| **Observability** | NFO logging (SQLite + JSONL) | LangSmith ($39/seat) |
| **Debugging** | /reflect, /health, verbose mode | LangSmith tracing |
| **Marketplace** | Registry lokalne | LangChain Hub |
| **Integracje** | Skills (modularny system) | 700+ integracji LangChain |
| **Dokumentacja** | Wczesna faza | Obszerna, production-grade |

**Werdykt:** LangGraph ma ogromną przewagę w ekosystemie — 700+ integracji, LangSmith, LangChain Hub, i aktywną społeczność 34.5M pobrań/miesiąc.

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz systemu, który **sam się naprawia** bez interwencji operatora
- ✅ Chcesz **automatyczne tworzenie i ewolucję** funkcjonalności (skills)
- ✅ Twoje środowisko jest **resource-constrained** (local-first, darmowe modele)
- ✅ Potrzebujesz **proaktywnego monitoringu** zdrowia systemu
- ✅ Pracujesz z **polskojęzycznymi** użytkownikami
- ✅ Chcesz **tryb głosowy** (STT/TTS) out of the box

## Kiedy wybrać LangGraph?

- ✅ Potrzebujesz **deterministycznej kontroli** nad przepływem agenta
- ✅ Budujesz **złożone multi-agent** systemy z precyzyjnymi przejściami
- ✅ Wymagasz **human-in-the-loop** z granularnym checkpoint/resume
- ✅ Potrzebujesz **ekosystemu 700+ integracji** LangChain
- ✅ Produkcyjne wdrożenie z **enterprise observability** (LangSmith)
- ✅ Twoja organizacja już korzysta z **LangChain**

## Potencjalna synergia

CoreSkill i LangGraph nie muszą się wykluczać. Możliwa integracja:
- CoreSkill jako **self-healing wrapper** wokół LangGraph grafów
- LangGraph jako **orkiestrator** z CoreSkill skills jako nodes
- Wspólne LLM routing (CoreSkill tiered → LangGraph nodes)

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
