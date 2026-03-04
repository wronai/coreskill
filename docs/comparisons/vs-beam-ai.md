# CoreSkill vs Beam AI — Szczegółowe porównanie

## Przegląd

| | CoreSkill | Beam AI |
|---|-----------|---------|
| **Twórca** | WronAI | Beam AI |
| **Architektura** | Ewolucyjna (text2pipeline) | Self-learning agents (back-office) |
| **Licencja** | Apache 2.0 (open-source) | Proprietary (SaaS) |
| **Cena** | Darmowy | Enterprise (custom pricing) |
| **Focus** | Developer framework (generalny) | Back-office process automation |
| **Status** | Wczesna faza | Komercyjna platforma |

## Dlaczego to porównanie jest ważne

Beam AI to **jedyna platforma na rynku**, która explicite marketuje "self-learning agents" — agentów, które uczą się autonomicznie z każdej interakcji. To czyni go **koncepcyjnie najbliższym** CoreSkill spośród wszystkich komercyjnych konkurentów.

## Filozofia architektury

### Beam AI: Self-learning dla back-office
Beam AI buduje agentów, którzy **autonomicznie się uczą** z każdej interakcji i poprawiają swoją skuteczność w procesach back-office:

- **Zamknięta platforma SaaS** (brak open-source)
- **Focus na back-office:** HR, finanse, operacje, łańcuch dostaw
- **Self-learning:** Agenci uczą się z każdej transakcji
- **Enterprise-grade:** Compliance, audit trail, SSO

### CoreSkill: Self-evolution open-source
CoreSkill oferuje **otwartą** architekturę samouczenia się:

- **Open-source framework** (MIT)
- **Generalny agent:** Automatyzacja, DevOps, IT ops, głos
- **Self-evolution:** Mutacja kodu skillów, nie tylko parametrów
- **Self-healing:** Naprawa kodu, nie tylko powtarzanie

## Porównanie podejść do "self-learning"

### Kluczowa różnica: Parametry vs Kod

| Aspekt | CoreSkill | Beam AI |
|--------|-----------|---------|
| **Co się uczy?** | Kod skillów (mutacja Python) | Parametry procesu |
| **Mechanizm** | LLM generuje/naprawia kod | ML na historii interakcji |
| **Głębokość** | ✅ Może zmienić logikę biznesową | ⚠️ Optymalizuje istniejącą |
| **Ryzyko** | Wyższe (kod mutuje) | Niższe (parametry się dostosowują) |
| **Quality gates** | ✅ 5-check pipeline + rollback | ⚠️ Nieznane (proprietary) |
| **Transparentność** | ✅ Open-source (widoczna ewolucja) | ❌ Black box (proprietary) |

### CoreSkill: Ewolucja kodu
```
Błąd → Diagnoza → LLM generuje nowy kod → Quality gate → Deploy lub Rollback
```
CoreSkill **zmienia sam kod** — to głębsza forma adaptacji, ale też wyższe ryzyko (dlatego quality gates i rollback są kluczowe).

### Beam AI: Optymalizacja parametrów
```
Interakcja → Analiza wyniku → Dostosowanie parametrów → Lepsza kolejna interakcja
```
Beam AI **dostosowuje parametry** istniejących procesów — bezpieczniejsze, ale ograniczone do optymalizacji, nie innowacji.

## Porównanie cech

### 1. Self-healing i autonomia

| Aspekt | CoreSkill | Beam AI |
|--------|-----------|---------|
| **Self-learning** | ✅ IntentEngine + RepairJournal | ✅ Core feature |
| **Self-healing** | ✅ 5-fazowy AutoRepair | ⚠️ Retry + escalation |
| **Self-evolution** | ✅ Mutacja kodu skillów | ⚠️ Parametr tuning |
| **Proaktywny monitoring** | ✅ Scheduler + drift | ⚠️ Nieznane |
| **Quality gates** | ✅ 5-check pipeline | ⚠️ Proprietary |
| **Rollback** | ✅ stable/latest/archive | ⚠️ Nieznane |

### 2. Deployment i dostępność

| Aspekt | CoreSkill | Beam AI |
|--------|-----------|---------|
| **Open-source** | ✅ MIT | ❌ Proprietary |
| **Self-hosted** | ✅ | ❌ SaaS only |
| **Local-first** | ✅ Ollama offline | ❌ Cloud |
| **Koszt** | Darmowy | Enterprise pricing |
| **Customization** | ✅ Pełna (kod źródłowy) | ⚠️ Przez konfigurację |

### 3. Use cases

| Aspekt | CoreSkill | Beam AI |
|--------|-----------|---------|
| **Back-office** | ⚠️ Możliwy (skills) | ✅ Core focus |
| **DevOps/SRE** | ✅ Core focus | ❌ |
| **IT automation** | ✅ Shell, deps, git_ops | ⚠️ |
| **HR/Finance** | ❌ | ✅ |
| **Customer support** | ⚠️ | ⚠️ |
| **Voice** | ✅ STT/TTS natywne | ❌ |

### 4. Transparentność

| Aspekt | CoreSkill | Beam AI |
|--------|-----------|---------|
| **Kod źródłowy** | ✅ Otwarty | ❌ Zamknięty |
| **Jak się uczy?** | ✅ Widoczne (journal, logs) | ❌ Black box |
| **Co zmienił?** | ✅ Git diff (skill versions) | ❌ |
| **Dlaczego zmienił?** | ✅ Reflection + journal | ❌ |
| **Audytowalność** | ✅ JSONL + SQLite | ⚠️ Enterprise audit |

**Werdykt:** CoreSkill ma ogromną przewagę w transparentności — open-source z pełnym audit trail ewolucji. Beam AI to black box.

## Kiedy wybrać CoreSkill?

- ✅ Potrzebujesz **open-source** z pełną kontrolą
- ✅ Chcesz **widzieć** jak system się uczy (transparentność)
- ✅ Budujesz automatyzację **DevOps/SRE/IT**
- ✅ Chcesz działać **offline** / **local-first**
- ✅ Budżet jest **ograniczony** (brak enterprise licensing)
- ✅ Potrzebujesz **głębokiej ewolucji** (mutacja kodu, nie tylko parametrów)

## Kiedy wybrać Beam AI?

- ✅ Automatyzujesz **back-office** (HR, finanse, operacje)
- ✅ Potrzebujesz **managed SaaS** bez zarządzania infrastrukturą
- ✅ Wymagasz **enterprise compliance** out of the box
- ✅ Wolisz **bezpieczniejszą** adaptację (parametry, nie kod)
- ✅ Masz budżet na **enterprise pricing**
- ✅ Nie potrzebujesz **open-source** ani transparentności uczenia

## Strategiczna perspektywa

CoreSkill i Beam AI są **koncepcyjnymi kuzynami** — oba wierzą w agentów, którzy się uczą. Kluczowe różnice:

| | CoreSkill | Beam AI |
|---|-----------|---------|
| **Model biznesowy** | Open-source framework | Proprietary SaaS |
| **Głębokość adaptacji** | Mutacja kodu (głęboka) | Optymalizacja parametrów (płytka) |
| **Transparentność** | Pełna (open-source) | Brak (black box) |
| **Target market** | DevOps/SRE, developers | Back-office, enterprise ops |

Beam AI waliduje **rynkową potrzebę** na self-learning agents, co jest pozytywnym sygnałem dla CoreSkill. Jednak adresują **różne segmenty** i **różne głębokości** adaptacji.

---

*Porównanie oparte na stanie z marca 2026*

[← Powrót do przeglądu](README.md)
