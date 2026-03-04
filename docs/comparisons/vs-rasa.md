# CoreSkill vs Rasa — Szczegółowe porównanie

## Przegląd

| | CoreSkill | Rasa |
|---|-----------|------|
| **Twórca** | WronAI | Rasa Technologies |
| **Architektura** | Ewolucyjna (text2pipeline) | NLU pipeline + dialog management |
| **Licencja** | MIT | Dual (OSS Apache 2.0 + commercial CALM) |
| **Cena** | Darmowy | Od $35K/rok (Growth) |
| **Klienci** | Early adopters | Banki, telekomy, healthcare |
| **Nisza** | Autonomiczna automatyzacja | Konwersacyjna AI (regulowane branże) |
| **Status** | Wczesna faza | Produkcja (dojrzały) |

## Filozofia architektury

### Rasa: NLU Pipeline + Dialog Management
Rasa to framework do budowy **konwersacyjnych asystentów AI** z zaawansowanym pipeline'em NLU:

```
User input → Tokenizer → Featurizer → Intent Classifier → Entity Extractor
                                          ↓
                                   Dialog Manager → Action Server → Response
```

**CALM** (Conversational AI with Language Models) to komercyjne rozszerzenie łączące tradycyjny NLU z LLM fallback.

**Nisza:** Regulowane branże (banking, healthcare, telecom) wymagające on-premise deployment i kontroli nad klasyfikacją.

### CoreSkill: Ewolucyjna automatyzacja
CoreSkill łączy klasyfikację intencji z **ewolucyjnym silnikiem skillów** — nie tylko rozumie co użytkownik chce, ale sam tworzy i naprawia zdolności potrzebne do realizacji.

## Porównanie cech

### 1. Klasyfikacja intencji — najważniejsza wspólna płaszczyzna

| Aspekt | CoreSkill | Rasa |
|--------|-----------|------|
| **Podejście** | 3-tier ML (embedding → local LLM → remote LLM) | Pipeline NLU (DIET classifier) |
| **Training data** | ~100+ przykładów + self-learning | Setki/tysiące oznaczonych przykładów |
| **Entity extraction** | ⚠️ Podstawowy (z LLM) | ✅ Zaawansowany (DIET, SpaCy, regex) |
| **Self-training** | ✅ Uczenie z korekt + sukcesów | ❌ Wymaga re-trenowania |
| **Confidence** | Threshold 0.40 (intent), 0.70 (sbert) | Konfigurowalne per-intent |
| **Wielojęzyczność** | ✅ PL/EN natywnie | ✅ Wielojęzyczny (z konfiguracją) |
| **LLM fallback** | ✅ Wbudowany (tier 2/3) | ✅ CALM (komercyjny) |

**Werdykt:** Rasa ma bardziej dojrzały i konfigurowlany NLU pipeline. CoreSkill ma unikalną cechę **self-training** — uczy się z korekt bez re-deploymentu.

### 2. Dialog management

| Aspekt | CoreSkill | Rasa |
|--------|-----------|------|
| **Stories/rules** | ❌ Brak (intent → skill dispatch) | ✅ Stories + rules + forms |
| **Context tracking** | ✅ Topic tracking + conversation history | ✅ Tracker + slots |
| **Multi-turn** | ⚠️ Bazowy (konwersacja + pamięć) | ✅ Zaawansowany (formy, sloty, branching) |
| **Custom actions** | Skills (auto-evolving) | Action server (statyczny Python) |

**Werdykt:** Rasa ma zdecydowanie lepszy dialog management z stories, formami i slotami. CoreSkill nie ma formalnego systemu zarządzania dialogiem.

### 3. Autonomia i self-healing

| Aspekt | CoreSkill | Rasa |
|--------|-----------|------|
| **Samo-ewolucja** | ✅ Pełna (mutacja + walidacja + rollback) | ❌ |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ❌ |
| **Self-training NLU** | ✅ Automatyczne z korekt | ❌ (wymaga re-train + deploy) |
| **Proaktywny monitoring** | ✅ Scheduler + drift | ❌ |
| **Auto-create actions** | ✅ LLM generuje skills | ❌ |
| **Quality gates** | ✅ 5-check pipeline | ❌ |

**Werdykt:** CoreSkill ma fundamentalną przewagę w autonomii. Rasa wymaga ludzkiego ML engineer do utrzymania i ewolucji modelu NLU.

### 4. Deployment i compliance

| Aspekt | CoreSkill | Rasa |
|--------|-----------|------|
| **On-premise** | ✅ Native (local-first) | ✅ Core feature |
| **Cloud managed** | ❌ | ✅ Rasa Cloud |
| **HIPAA** | ❌ | ✅ |
| **SOC 2** | ❌ | ✅ |
| **GDPR** | ⚠️ (local = data stays local) | ✅ Explicit compliance |
| **Enterprise SSO** | ❌ | ✅ |
| **Audit trail** | ⚠️ Logi (JSONL/SQLite) | ✅ Enterprise audit |

**Werdykt:** Rasa zdecydowanie lepszy do regulowanych branż. CoreSkill advantage: dane nigdy nie opuszczają maszyny (local-first).

### 5. Kanały komunikacji

| Aspekt | CoreSkill | Rasa |
|--------|-----------|------|
| **CLI** | ✅ Primary | ✅ (debug) |
| **Web** | ❌ | ✅ Widget, REST API |
| **Slack/Teams/etc.** | ❌ | ✅ 10+ kanałów |
| **Głos (STT/TTS)** | ✅ Natywny (vosk/espeak) | ⚠️ Przez integracje |
| **Telefon** | ❌ | ✅ (Twilio, Vonage) |

**Werdykt:** Rasa ma znacznie więcej kanałów. CoreSkill ma natywny tryb głosowy bez dodatkowych integracji.

### 6. Koszt

| Aspekt | CoreSkill | Rasa |
|--------|-----------|------|
| **Framework** | Darmowy (MIT) | OSS darmowy / CALM od $35K/rok |
| **NLU training** | Automatyczny (self-learning) | Wymaga ML engineer |
| **LLM koszty** | Minimalne (free + local) | Zależne od CALM konfiguracji |
| **Total roczny** | ~$0 (self-hosted) | $35K–$300K+ |

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz agenta, który **sam tworzy i naprawia** swoje zdolności
- ✅ Nie masz budżetu na **$35K+/rok** licencji
- ✅ Chcesz NLU, które **samo się uczy** bez re-trenowania
- ✅ Budujesz **automatyzację** (DevOps, IT ops), nie chatbota
- ✅ Potrzebujesz **trybu głosowego** natywnie
- ✅ Chcesz działać **offline** z lokalnymi modelami

## Kiedy wybrać Rasa?

- ✅ Budujesz **konwersacyjnego asystenta** (chatbot, voicebot)
- ✅ Twoja branża wymaga **compliance** (HIPAA, SOC 2, GDPR)
- ✅ Potrzebujesz **zaawansowanego dialog management** (formy, sloty, story flows)
- ✅ Wymagasz **multi-channel** (web, Slack, Teams, telefon)
- ✅ Masz zespół **ML engineers** do utrzymania modeli NLU
- ✅ **On-premise** deployment jest wymogiem regulacyjnym
- ✅ Obsługujesz **500K+ konwersacji/rok** i potrzebujesz skalowalności

## Kluczowa różnica

> **Rasa:** "Zbuduj konwersacyjnego AI asystenta z pełną kontrolą nad NLU"
> **CoreSkill:** "Postaw autonomicznego agenta, który sam się rozwija i naprawia"

Rasa to **specjalista od konwersacji** w regulowanych branżach. CoreSkill to **generalista od autonomicznej automatyzacji**. Są to komplementarne, nie konkurencyjne podejścia.

---

*Porównanie oparte na stanie z marca 2026*

[← Powrót do przeglądu](README.md)
