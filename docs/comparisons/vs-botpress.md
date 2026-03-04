# CoreSkill vs Botpress — Szczegółowe porównanie

## Przegląd

| | CoreSkill | Botpress |
|---|-----------|----------|
| **Twórca** | WronAI | Botpress Inc. |
| **Architektura** | Ewolucyjna (text2pipeline) | AI-native agent platform (LLMz) |
| **Licencja** | MIT | Proprietary (cloud) |
| **Cena** | Darmowy | Darmowy start ($5 AI credit) → $89/mies. (Plus) → $495/mies. (Team) |
| **Finansowanie** | — | $25M Series B |
| **Przychody** | — | >$10M ARR (2025), podwajane co kwartał |
| **Klienci** | Early adopters | Shell, Kia, Electronic Arts |
| **Status** | Wczesna faza | Produkcja (dynamiczny wzrost) |

## Filozofia architektury

### Botpress: AI-native platforma z LLMz
Botpress przeszedł radykalną transformację — z open-source chatbot buildera do **AI-native agent platform** z autorskim silnikiem **LLMz**:

- **LLMz engine:** Autonomiczny silnik konwersacyjny oparty na LLM
- **Visual builder:** Drag-and-drop budowanie agentów
- **Zero markup na tokenach:** Botpress nie nalicza marży na koszty LLM
- **Knowledge base:** Natywna integracja z bazami wiedzy

**Target:** Firmy budujące chatboty i agentów konwersacyjnych na skalę enterprise.

### CoreSkill: Developer-first ewolucja
CoreSkill to **framework CLI-first** dla deweloperów, z autonomiczną ewolucją skillów zamiast wizualnego buildera.

## Porównanie cech

### 1. Podejście do budowania agentów

| Aspekt | CoreSkill | Botpress |
|--------|-----------|----------|
| **Primary interface** | CLI + kod Python | Visual builder (web) |
| **Target user** | Developer | Developer + biznes |
| **Konfiguracja** | Auto-discovery + minimal config | Visual drag-and-drop |
| **Knowledge base** | ❌ (skill-based) | ✅ Natywna (upload docs) |
| **Templates** | ❌ | ✅ Gotowe szablony agentów |
| **Deployment** | Self-hosted (local) | Cloud-native |

**Werdykt:** Botpress lepszy do szybkiego budowania agentów konwersacyjnych bez pisania kodu. CoreSkill lepszy dla deweloperów chcących pełnej kontroli i autonomii.

### 2. Autonomia i self-healing

| Aspekt | CoreSkill | Botpress |
|--------|-----------|----------|
| **Samo-ewolucja** | ✅ Pełna (mutacja + walidacja + rollback) | ❌ |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ⚠️ Ograniczona (retry) |
| **Proaktywny monitoring** | ✅ Scheduler + drift detection | ❌ (dashboard analytics) |
| **Auto-create skills** | ✅ LLM generuje + testuje | ❌ Ręczne w visual builder |
| **Quality gates** | ✅ 5-check pipeline | ❌ |
| **Self-training NLU** | ✅ Automatyczne | ⚠️ Analytics-driven (ręczne) |

**Werdykt:** CoreSkill fundamentalnie bardziej autonomiczny. Botpress polega na ludzkim operatorze do iteracji.

### 3. LLM Management

| Aspekt | CoreSkill | Botpress |
|--------|-----------|----------|
| **LLM routing** | ✅ 3-tier + UCB1 bandit | ⚠️ Single provider (z wyborem) |
| **Cost model** | Free → Local → Paid | Pass-through (0% markup) |
| **Local models** | ✅ Ollama native | ❌ Cloud only |
| **Failover** | ✅ Automatyczny tier switch | ⚠️ Manual provider switch |
| **Offline** | ✅ | ❌ |

**Werdykt:** CoreSkill ma bardziej zaawansowany i tańszy LLM routing. Botpress unikalny z zerową marżą na tokenach, ale wymaga internetu.

### 4. Kanały i integracje

| Aspekt | CoreSkill | Botpress |
|--------|-----------|----------|
| **Web widget** | ❌ | ✅ |
| **Messenger/WhatsApp** | ❌ | ✅ |
| **Slack/Teams** | ❌ | ✅ |
| **Telefon** | ❌ | ⚠️ (przez integracje) |
| **CLI** | ✅ Primary | ⚠️ (API) |
| **STT/TTS natywne** | ✅ | ❌ |
| **Webhooks** | ❌ | ✅ |
| **API** | Python module | REST API |

**Werdykt:** Botpress ma zdecydowanie więcej kanałów komunikacji. CoreSkill ma natywny tryb głosowy.

### 5. Pricing i koszt operacyjny

| Aspekt | CoreSkill | Botpress |
|--------|-----------|----------|
| **Koszt start** | $0 | $0 ($5 AI credit) |
| **Koszt rosnący** | ~$0 (local LLM) | $89–$495/mies. + tokeny |
| **LLM markup** | Brak (bezpośredni dostęp) | 0% markup (unikalne!) |
| **Self-hosting** | ✅ | ❌ (cloud only) |
| **Enterprise** | Brak | Custom pricing |

**Werdykt:** CoreSkill tańszy (self-hosted, local LLM). Botpress uczciwy na tokenach (0% markup), ale wymaga subskrypcji.

### 6. Analytics i monitoring

| Aspekt | CoreSkill | Botpress |
|--------|-----------|----------|
| **Conversation analytics** | ⚠️ Bazowe (logi) | ✅ Zaawansowane (dashboard) |
| **Skill/agent health** | ✅ ProactiveScheduler | ⚠️ (Uptime monitoring) |
| **Drift detection** | ✅ DriftDetector | ❌ |
| **User insights** | ⚠️ UserMemory | ✅ Conversation analytics |
| **A/B testing** | ⚠️ Supervisor (core A/B) | ✅ |

## Kiedy wybrać CoreSkill?

- ✅ Jesteś **deweloperem** i chcesz pełnej kontroli
- ✅ Potrzebujesz systemu, który **sam się naprawia** i **ewoluuje**
- ✅ Chcesz działać **offline** / **local-first**
- ✅ Budujesz **automatyzację** (nie chatbota)
- ✅ Budżet jest **zerowy** (darmowe modele + self-hosted)
- ✅ Potrzebujesz **natywnego STT/TTS**

## Kiedy wybrać Botpress?

- ✅ Budujesz **chatbota** lub konwersacyjnego agenta
- ✅ Potrzebujesz **visual builder** (drag-and-drop)
- ✅ Wymagasz **multi-channel** (web, Messenger, WhatsApp, Slack)
- ✅ Chcesz **knowledge base** z upload dokumentów
- ✅ Twoi użytkownicy końcowi to **klienci** (B2C)
- ✅ Cenisz **0% markup** na tokenach LLM
- ✅ Potrzebujesz **analytics dashboard** out of the box

## Fundamentalna różnica

> **Botpress:** "Zbuduj chatbota wizualnie i deployuj na wszystkich kanałach"
> **CoreSkill:** "Postaw autonomicznego agenta, który sam się rozwija i naprawia"

Botpress to **platforma do budowania konwersacji**, CoreSkill to **framework do budowania samonaprawiających się systemów**. Różne produkty dla różnych problemów.

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
