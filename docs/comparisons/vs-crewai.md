# CoreSkill vs CrewAI — Szczegółowe porównanie

## Przegląd

| | CoreSkill | CrewAI |
|---|-----------|--------|
| **Twórca** | WronAI | CrewAI Inc. |
| **Architektura** | Ewolucyjna (text2pipeline) | Role-based multi-agent |
| **Licencja** | Apache 2.0 | MIT |
| **Cena** | Darmowy | $99–$120K/rok |
| **GitHub Stars** | Nowy projekt | ~40K |
| **Finansowanie** | — | $18M Series A |
| **Adopcja** | Early adopters | 60% Fortune 500, 100K+ devów |
| **Status** | Wczesna faza | Produkcja |

## Filozofia architektury

### CrewAI: Zespoły agentów z rolami
CrewAI opiera się na metaforze **zespołu** — definiujesz agentów jako role (Researcher, Writer, Analyst) z celami i narzędziami. Agenci współpracują w ramach "crew" z określonym procesem (sekwencyjnym lub hierarchicznym).

```yaml
agents:
  - role: Researcher
    goal: Znajdź dane o rynku AI
    tools: [web_search, document_reader]
  - role: Writer
    goal: Napisz raport z wyników
    tools: [file_writer]
```

**Zalety:** Intuicyjny model mentalny, YAML-driven, szybki start.
**Wady:** Brak adaptacji runtime, agenci nie ewoluują.

### CoreSkill: Samodzielna ewolucja
CoreSkill nie definiuje ról — zamiast tego **automatycznie tworzy, testuje i ewoluuje** zdolności (skills) w odpowiedzi na potrzeby użytkownika.

```
Zapytanie użytkownika → Intent → Skill (lub auto-create) → Execute → Validate → (Evolve)
```

**Zalety:** Zero konfiguracji YAML, adaptacja w runtime, self-healing.
**Wady:** Mniej przewidywalny niż statyczny YAML config.

## Porównanie cech

### 1. Model agentów

| Aspekt | CoreSkill | CrewAI |
|--------|-----------|--------|
| **Definiowanie** | Automatyczne (intent-driven) | YAML config (role/goal/tools) |
| **Multi-agent** | Pojedynczy agent + ewolucja skillów | Wielu agentów z rolami |
| **Współpraca** | Pipeline (sekwencyjny) | Sequential / Hierarchical process |
| **Delegacja** | Provider chain (automatyczna) | Agent delegation (explicit) |
| **Pamięć** | UserMemory + state persistence | Short/Long-term memory |
| **Konfiguracja** | Zero-config (auto-discovery) | YAML agents + tasks |

**Werdykt:** CrewAI lepszy do scenariuszy multi-agent z jasno określonymi rolami. CoreSkill lepszy gdy potrzeby nie są z góry znane i system musi się adaptować.

### 2. Tworzenie i zarządzanie zdolnościami

| Aspekt | CoreSkill | CrewAI |
|--------|-----------|--------|
| **Tworzenie nowych** | ✅ Automatyczne (LLM gen + quality gate) | ❌ Ręczne (YAML + kod) |
| **Ewolucja** | ✅ smart_evolve z mutacją kodu | ❌ Ręczna aktualizacja |
| **Wersjonowanie** | ✅ stable/latest/archive + rollback | ❌ Brak |
| **Quality gates** | ✅ 5-check pipeline | ❌ Brak |
| **Deduplikacja** | ✅ SkillForge (semantic dedup) | ❌ N/A |
| **Garbage collection** | ✅ EvolutionGarbageCollector | ❌ N/A |

**Werdykt:** CoreSkill ma fundamentalną przewagę w zarządzaniu cyklem życia zdolności. CrewAI wymaga ręcznej pracy programisty przy każdej zmianie.

### 3. Odporność i niezawodność

| Aspekt | CoreSkill | CrewAI |
|--------|-----------|--------|
| **Self-healing** | ✅ AutoRepair (5-fazowy) | ❌ |
| **Retry** | ✅ Z ewolucją kodu między próbami | ⚠️ Prosty retry |
| **Health monitoring** | ✅ ProactiveScheduler (background) | ❌ |
| **Drift detection** | ✅ DriftDetector | ❌ |
| **Provider fallback** | ✅ ProviderChain + UCB1 | ❌ |
| **Auto-diagnostics** | ✅ SelfReflection engine | ❌ |

**Werdykt:** CoreSkill znacznie bardziej odporny na awarie — CrewAI polega na ręcznej interwencji przy problemach.

### 4. Łatwość użycia

| Aspekt | CoreSkill | CrewAI |
|--------|-----------|--------|
| **Time-to-first-value** | ~5 min (CLI, auto-discovery) | ~15 min (YAML setup) |
| **Krzywa uczenia** | Średnia (wiele modułów) | Niska (intuicyjne role) |
| **Visual editor** | ❌ | ✅ AMP Suite |
| **Serverless deploy** | ❌ | ✅ CrewAI Cloud |
| **Dokumentacja** | Wczesna faza | Obszerna |
| **Społeczność** | Mała | 100K+ certyfikowanych devów |

**Werdykt:** CrewAI wygrywa w łatwości onboardingu i dostępności narzędzi wizualnych. CoreSkill wymaga więcej wiedzy technicznej, ale oferuje mniej konfiguracji runtime.

### 5. Koszt operacyjny

| Aspekt | CoreSkill | CrewAI |
|--------|-----------|--------|
| **Framework** | Darmowy (MIT) | Darmowy (MIT) |
| **Cloud/SaaS** | Brak (self-hosted) | $99–$120K/rok |
| **LLM koszty** | Minimalne (local-first, free tier) | Zależne od providera |
| **Maintenance** | Niski (self-healing) | Średni (ręczna interwencja) |

**Werdykt:** CoreSkill tańszy w utrzymaniu dzięki local-first i self-healing. CrewAI droższy przy skalowaniu (licencje + cloud).

## Kiedy wybrać CoreSkill?

- ✅ System musi **sam tworzyć nowe zdolności** w odpowiedzi na potrzeby
- ✅ Potrzebujesz **self-healing** bez interwencji DevOps
- ✅ Budżet na LLM jest **ograniczony** (local-first, darmowe modele)
- ✅ Potrzebujesz **trybu głosowego** (STT/TTS)
- ✅ Chcesz system, który **uczy się z błędów** (RepairJournal, EvolutionJournal)
- ✅ Pracujesz solo lub w małym zespole

## Kiedy wybrać CrewAI?

- ✅ Masz **jasno określone role** agentów (Researcher, Writer, Analyst)
- ✅ Potrzebujesz **multi-agent collaboration** z delegacją zadań
- ✅ Chcesz **visual editor** do projektowania workflows
- ✅ Potrzebujesz **serverless deployment** (CrewAI Cloud)
- ✅ Twoja organizacja wymaga **enterprise support** i certyfikacji
- ✅ Priorytetem jest **szybki onboarding** zespołu

## Potencjalna synergia

- CoreSkill jako **backend self-healing** dla CrewAI agents
- CrewAI orchestration z CoreSkill **ewolucyjnymi tools**
- Wspólny **LLM routing** — CoreSkill tiered system pod CrewAI agents

---

*Porównanie oparte na stanie z marca 2026*

[← Powrót do przeglądu](README.md)
