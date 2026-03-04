# CoreSkill vs Haystack — Szczegółowe porównanie

## Przegląd

| | CoreSkill | Haystack |
|---|-----------|----------|
| **Twórca** | WronAI | deepset |
| **Architektura** | Ewolucyjna (text2pipeline) | Pipeline RAG-first |
| **Licencja** | MIT | Apache 2.0 |
| **Cena** | Darmowy | Custom enterprise (deepset Cloud) |
| **GitHub Stars** | Nowy projekt | ~24K |
| **Klienci** | Early adopters | Airbus, The Economist, Netflix |
| **Wyróżnienia** | — | Gartner Cool Vendor in AI Engineering 2024 |
| **Status** | Wczesna faza | Produkcja |

## Filozofia architektury

### Haystack: Pipeline RAG-first
Haystack to framework zbudowany wokół **pipeline'ów przetwarzania dokumentów** — od ingestii, przez indeksowanie, aż po retrieval-augmented generation. Każdy komponent to typowany blok z jasno zdefiniowanymi wejściami/wyjściami.

```
[DocumentStore] → [Retriever] → [PromptBuilder] → [Generator] → [Answer]
```

**Nisza:** Wyszukiwanie w dokumentach, Q&A na własnych danych, RAG applications.
**Zalety:** Silny typing, walidacja pipeline, bogaty ekosystem komponentów.
**Wady:** Wąski fokus na RAG, brak ogólnej autonomii agenta.

### CoreSkill: Ogólny agent ewolucyjny
CoreSkill jest **generalnym** frameworkiem agentowym — nie skupia się na jednym use case, lecz na zdolności adaptacji do dowolnych zadań.

## Porównanie cech

### 1. Pipeline vs Ewolucja

| Aspekt | CoreSkill | Haystack |
|--------|-----------|----------|
| **Typ pipeline** | Ewolucyjny (detect→execute→validate→mutate) | Deklaratywny (DAG komponentów) |
| **Komponent** | Skill (Python module, ewoluujący) | Component (typowany, statyczny) |
| **Walidacja** | Runtime (SkillQualityGate) | Compile-time (type checking) |
| **Nowe komponenty** | ✅ Auto-create przez LLM | ❌ Ręczne tworzenie |
| **Hot-swap** | ✅ Provider chain + auto-degradacja | ⚠️ Pipeline rebuild |

**Werdykt:** Haystack ma silniejszą walidację statyczną. CoreSkill ma dynamiczną adaptację runtime.

### 2. Specjalizacja RAG vs Ogólność

| Aspekt | CoreSkill | Haystack |
|--------|-----------|----------|
| **Document stores** | ❌ Brak natywnego | ✅ 10+ (Elasticsearch, Pinecone, Weaviate...) |
| **Retrieval** | ❌ Brak natywnego | ✅ BM25, embedding, hybrid |
| **Embeddings** | ⚠️ Dla intencji (sbert/TF-IDF) | ✅ Pełne (document + query) |
| **RAG pipeline** | ❌ Trzeba stworzyć skill | ✅ Core use case |
| **Ogólne zadania** | ✅ Shell, TTS, STT, git, devops... | ⚠️ Głównie NLP/RAG |
| **Auto-tworzenie zdolności** | ✅ | ❌ |

**Werdykt:** Haystack zdecydowanie lepszy do RAG i document Q&A. CoreSkill lepszy do ogólnych zadań automatyzacyjnych.

### 3. Autonomia i self-healing

| Aspekt | CoreSkill | Haystack |
|--------|-----------|----------|
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ |
| **Self-evolution** | ✅ Mutacja kodu + quality gates | ❌ |
| **Proaktywny monitoring** | ✅ Scheduler + drift detection | ❌ (deepset Cloud monitoring) |
| **Auto-diagnostics** | ✅ SelfReflection engine | ❌ |
| **Rollback** | ✅ stable/latest/archive | ❌ Pipeline version control |

**Werdykt:** CoreSkill ma pełną autonomię. Haystack polega na zewnętrznym monitoringu (deepset Cloud).

### 4. Deployment i enterprise

| Aspekt | CoreSkill | Haystack |
|--------|-----------|----------|
| **Local-first** | ✅ Ollama + offline | ⚠️ Cloud-first |
| **Managed cloud** | ❌ | ✅ deepset Cloud |
| **Enterprise support** | ❌ | ✅ Konsulting (4h/mies. w Starter) |
| **API** | CLI + Python | REST API + Python |
| **Europejski focus** | ❌ | ✅ (Berlin, GDPR-ready) |

**Werdykt:** Haystack lepszy dla europejskich enterprise z potrzebami RAG i GDPR compliance.

### 5. Ekosystem

| Aspekt | CoreSkill | Haystack |
|--------|-----------|----------|
| **Komponenty** | ~15 wbudowanych skills | 50+ oficjalnych komponentów |
| **Integracje** | Ollama, OpenRouter | 10+ document stores, 5+ LLM providers |
| **Społeczność** | Mała | Aktywna (Discord, GitHub) |
| **Dokumentacja** | Wczesna | Obszerna, production-grade |
| **Tutoriale** | Podstawowe | Rozbudowane (cookbook) |

## Kiedy wybrać CoreSkill?

- ✅ Budujesz **ogólnego agenta** automatyzacyjnego (nie tylko RAG)
- ✅ Potrzebujesz **self-healing** i autonomicznej naprawy
- ✅ Chcesz system, który **sam tworzy nowe zdolności**
- ✅ Priorytet to **local-first** z minimalnymi kosztami
- ✅ Potrzebujesz **trybu głosowego** (STT/TTS)
- ✅ Chcesz **proaktywny monitoring** zdrowia systemu

## Kiedy wybrać Haystack?

- ✅ Twój główny use case to **RAG / Q&A na dokumentach**
- ✅ Potrzebujesz **document stores** (Elasticsearch, Pinecone, Weaviate)
- ✅ Wymagasz **enterprise support** z europejskim focusem (GDPR)
- ✅ Chcesz **typowane pipeline'y** z walidacją compile-time
- ✅ Potrzebujesz **managed cloud** (deepset Cloud)
- ✅ Twoja aplikacja jest **NLP-centric** (przetwarzanie tekstu)

## Uzupełniające się role

Haystack i CoreSkill adresują **różne problemy**:
- **Haystack** = specjalista od RAG i przetwarzania dokumentów
- **CoreSkill** = generalista od autonomicznej automatyzacji

Możliwa integracja: CoreSkill skill wrappujący Haystack pipeline dla zadań RAG.

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
