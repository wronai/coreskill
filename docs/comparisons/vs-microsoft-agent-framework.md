# CoreSkill vs Microsoft Agent Framework — Szczegółowe porównanie

## Przegląd

| | CoreSkill | Microsoft Agent Framework |
|---|-----------|--------------------------|
| **Twórca** | WronAI | Microsoft |
| **Poprzednicy** | — | AutoGen (54.7K ★) + Semantic Kernel (27.3K ★) |
| **Architektura** | Ewolucyjna (text2pipeline) | Multi-agent konwersacje + enterprise plugins |
| **Licencja** | MIT | MIT |
| **Cena** | Darmowy | Darmowy (OSS only, brak managed cloud) |
| **Status** | Wczesna faza | Przejściowa (GA planowane Q1 2026) |
| **Ekosystem** | Standalone | Głęboka integracja Azure |

## Filozofia architektury

### Microsoft: Konsolidacja dwóch światów
Microsoft Agent Framework łączy:
- **AutoGen**: Multi-agent konwersacje — agenci "rozmawiają" ze sobą, aby rozwiązać problem
- **Semantic Kernel**: Enterprise plugin architecture — typowany system pluginów z deep Azure integration

AutoGen weszło w tryb maintenance, a nowy framework ma dostarczyć najlepsze z obu światów.

### CoreSkill: Ewolucja autonomiczna
CoreSkill nie stawia na konwersacje między agentami, lecz na **jednego agenta**, który autonomicznie tworzy, naprawia i ewoluuje swoje zdolności.

## Porównanie cech

### 1. Model agentów

| Aspekt | CoreSkill | MS Agent Framework |
|--------|-----------|-------------------|
| **Paradygmat** | Pojedynczy agent + ewolucyjne skille | Multi-agent konwersacje |
| **Komunikacja** | User ↔ Agent (z skillami) | Agent ↔ Agent (konwersacyjna) |
| **Plugin system** | Skills (dynamiczne, ewoluujące) | Semantic Kernel plugins (statyczne, typowane) |
| **Typing** | Luźny (dict-based) | Silny (.NET/Python type system) |
| **Języki SDK** | Python | Python, C#, Java |

**Werdykt:** MS Agent Framework lepszy do enterprise z wieloma współpracującymi agentami. CoreSkill lepszy dla autonomicznego, samodzielnego agenta.

### 2. Integracja z ekosystemem

| Aspekt | CoreSkill | MS Agent Framework |
|--------|-----------|-------------------|
| **Cloud** | Agnostyczny (local-first) | Azure-native |
| **Enterprise SSO** | ❌ | ✅ Azure AD/Entra |
| **Bazy danych** | Plikowe (JSON/JSONL/SQLite) | Azure Cosmos DB, SQL Server |
| **CI/CD** | Docker + Makefile | Azure DevOps, GitHub Actions |
| **Compliance** | Brak | SOC 2, HIPAA (przez Azure) |
| **.NET support** | ❌ | ✅ Natywny |

**Werdykt:** MS Agent Framework wygrywa w scenariuszach enterprise z Azure. CoreSkill wygrywa w środowiskach niezależnych od chmury.

### 3. Autonomia i samo-naprawa

| Aspekt | CoreSkill | MS Agent Framework |
|--------|-----------|-------------------|
| **Samo-ewolucja** | ✅ Pełna (mutacja + walidacja) | ❌ Brak |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ Brak |
| **Proaktywny monitoring** | ✅ Scheduler + drift | ❌ Brak (Azure Monitor ext.) |
| **Auto-create skills** | ✅ LLM generates code | ❌ Ręczne tworzenie pluginów |
| **Quality gates** | ✅ 5-check pipeline | ❌ Brak |
| **Repair journal** | ✅ Uczenie z napraw | ❌ N/A |

**Werdykt:** CoreSkill ma pełną autonomię, której MS Agent Framework nie oferuje. Microsoft stawia na kontrolę, nie na autonomię.

### 4. LLM Management

| Aspekt | CoreSkill | MS Agent Framework |
|--------|-----------|-------------------|
| **Routing** | 3-tier + UCB1 bandit | Azure OpenAI primary |
| **Local models** | ✅ Ollama auto-discovery | ⚠️ Konfiguracja manualna |
| **Failover** | ✅ Automatyczny tier switch | ⚠️ Azure-level retry |
| **Cost optimization** | ✅ Free-first | ❌ Azure pricing |
| **Model agnostic** | ✅ OpenRouter + Ollama + any | ⚠️ Azure-centric |

**Werdykt:** CoreSkill bardziej elastyczny i tańszy w LLM routing. MS Agent Framework optymalizowany pod Azure OpenAI.

### 5. Dojrzałość i przyszłość

| Aspekt | CoreSkill | MS Agent Framework |
|--------|-----------|-------------------|
| **Stabilność API** | Wczesna (może się zmieniać) | Przejściowa (z AutoGen → nowy) |
| **Dokumentacja** | Wczesna faza | W budowie (migracja z AutoGen) |
| **Społeczność** | Mała | 82K+ stars (łącznie AutoGen+SK) |
| **Enterprise adoption** | ❌ | ✅ Microsoft customers |
| **Roadmap** | Ewolucja autonomii | Konsolidacja AutoGen + SK |

**Werdykt:** Oba projekty w fazie przejściowej. MS ma ogromną bazę użytkowników AutoGen do migracji.

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz **autonomicznego** agenta, który sam się naprawia i ewoluuje
- ✅ Nie jesteś zablokowany na **Azure** i chcesz vendor-agnostic
- ✅ Priorytetem jest **local-first** z minimalnymi kosztami LLM
- ✅ Potrzebujesz **proaktywnego monitoringu** bez zewnętrznych usług
- ✅ Chcesz tryb głosowy i wsparcie **polskiego** z box
- ✅ Jeden agent z wieloma zdolnościami > wielu agentów ze stałymi rolami

## Kiedy wybrać MS Agent Framework?

- ✅ Twoja organizacja jest na **Azure** i chcesz głęboką integrację
- ✅ Potrzebujesz **multi-agent konwersacji** (agenci rozwiązujący problem razem)
- ✅ Wymagasz **.NET/C#** oprócz Pythona
- ✅ Enterprise **compliance** (SOC 2, HIPAA) jest wymogiem
- ✅ Już korzystasz z **AutoGen** lub **Semantic Kernel**
- ✅ Potrzebujesz **typowanego plugin system** z walidacją compile-time

## Kluczowa różnica filozoficzna

> **Microsoft:** "Agenci powinni ze sobą rozmawiać, aby rozwiązać problem"
> **CoreSkill:** "Agent powinien sam ewoluować, aby rozwiązać problem"

To fundamentalna różnica w podejściu. MS stawia na **kooperację** wielu agentów, CoreSkill na **autonomiczną adaptację** jednego agenta.

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
