# CoreSkill vs LlamaIndex — Szczegółowe porównanie

## Przegląd

| | CoreSkill | LlamaIndex |
|---|-----------|------------|
| **Twórca** | WronAI | LlamaIndex Inc. |
| **Architektura** | Ewolucyjna (text2pipeline) | Data framework dla LLM |
| **Licencja** | MIT | MIT |
| **Cena** | Darmowy | Darmowy + LlamaCloud od $15/mies. |
| **GitHub Stars** | Nowy projekt | ~40K |
| **Finansowanie** | — | $47M Series B |
| **Focus** | Autonomiczna automatyzacja | Retrieval-Augmented Generation (RAG) |
| **Status** | Wczesna faza | Produkcja |

## Filozofia architektury

### LlamaIndex: Dane jako first-class citizen
LlamaIndex to framework zbudowany wokół **indeksowania i retrievalu danych** dla LLM. Centralnym konceptem są "Data Loaders", "Indexes" i "Query Engines".

```
Dokumenty → Loaders → Indexes (Vector/Tree/Keyword) → Query Engine → LLM → Odpowiedź
```

**Nisza:** Budowanie systemów RAG, chatbotów na dokumentach, knowledge base applications.

### CoreSkill: Autonomiczna ewolucja
CoreSkill nie skupia się na danych — skupia się na **samodzielnym agencie**, który tworzy i naprawia swoje zdolności w odpowiedzi na potrzeby użytkownika.

```
Zapytanie użytkownika → Intent → Skill (auto-create jeśli potrzeba) → Execute → Validate → Evolve
```

## Porównanie cech

### 1. Dane i RAG

| Aspekt | CoreSkill | LlamaIndex |
|--------|-----------|------------|
| **Data ingestion** | ❌ Brak natywnego | ✅ 100+ data connectors |
| **Vector stores** | ❌ Brak natywnego | ✅ 15+ (Pinecone, Weaviate, Chroma...) |
| **RAG pipeline** | ❌ Trzeba stworzyć skill | ✅ Core feature |
| **Embeddings** | ⚠️ Tylko dla intencji | ✅ Pełne zarządzanie |
| **Indexes** | ❌ | ✅ Vector, Tree, Keyword, Knowledge Graph |
| **Auto-optimization** | ❌ | ✅ Index tuning |

**Werdykt:** LlamaIndex zdecydowanie lepszy do RAG i przetwarzania dokumentów.

### 2. Autonomia i self-healing

| Aspekt | CoreSkill | LlamaIndex |
|--------|-----------|------------|
| **Samo-ewolucja** | ✅ Pełna (mutacja kodu) | ❌ |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ |
| **Auto-create skills** | ✅ LLM generuje + testuje | ❌ |
| **Quality gates** | ✅ 5-check pipeline | ❌ |
| **Proaktywny monitoring** | ✅ Scheduler + drift | ❌ |

**Werdykt:** CoreSkill ma fundamentalną przewagę w autonomii. LlamaIndex wymaga manualnej pracy.

### 3. Agenci i workflow

| Aspekt | CoreSkill | LlamaIndex |
|--------|-----------|------------|
| **Agents** | Pojedynczy ewolucyjny agent | ✅ Agent framework (React, OpenAI) |
| **Multi-agent** | ❌ | ✅ Multi-agent workflows |
| **Workflow** | Pipeline (sekwencyjny) | ✅ LlamaParse + pipelines |
| **Tool calling** | Skills (auto-evolving) | ✅ Function calling |
| **Observability** | NFO logging | ✅ LlamaTrace (OpenTelemetry) |

**Werdykt:** LlamaIndex ma lepszy multi-agent i workflow tooling. CoreSkill ma autonomiczne skille.

### 4. Deployment i ekosystem

| Aspekt | CoreSkill | LlamaIndex |
|--------|-----------|------------|
| **Local-first** | ✅ Native (Ollama) | ⚠️ Cloud-first |
| **Managed cloud** | ❌ | ✅ LlamaCloud |
| **Observability** | SQLite + JSONL | ✅ OpenTelemetry native |
| **Integracje** | 10+ skills | ✅ 100+ data connectors |
| **Enterprise** | ❌ | ✅ SOC 2, HIPAA |

### 5. Koszt operacyjny

| Aspekt | CoreSkill | LlamaIndex |
|--------|-----------|------------|
| **Framework** | Darmowy | Darmowy |
| **Cloud** | Self-hosted only | Od $15/mies. (LlamaCloud) |
| **LLM koszty** | Minimalne (free + local) | Zależne od setup |

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz agenta, który **sam się naprawia** i **ewoluuje**
- ✅ Budujesz **automatyzację** (DevOps, IT ops), nie system RAG
- ✅ Chcesz **minimalne koszty** (local-first, darmowe modele)
- ✅ Potrzebujesz **trybu głosowego** (STT/TTS)
- ✅ Chcesz działać **offline**

## Kiedy wybrać LlamaIndex?

- ✅ Budujesz **system RAG** na dokumentach
- ✅ Potrzebujesz **100+ data connectors**
- ✅ Wymagasz **vector stores** (Pinecone, Weaviate, etc.)
- ✅ Chcesz **enterprise observability** (OpenTelemetry)
- ✅ Potrzebujesz **managed cloud** (LlamaCloud)
- ✅ **Multi-agent workflows** są kluczowe

## Uzupełniające się role

LlamaIndex i CoreSkill adresują **różne problemy**:
- **LlamaIndex** = ekspert od RAG i danych
- **CoreSkill** = ekspert od autonomicznej automatyzacji

Możliwa integracja: CoreSkill skill wrappujący LlamaIndex dla zadań wymagających RAG.

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
