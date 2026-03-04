# CoreSkill vs AutoGPT — Szczegółowe porównanie

## Przegląd

| | CoreSkill | AutoGPT |
|---|-----------|---------|
| **Twórca** | WronAI | Significant Gravitas |
| **Architektura** | Ewolucyjna (text2pipeline) | Autonomiczna pętla + visual builder |
| **Licencja** | Apache 2.0 | MIT |
| **Cena** | Darmowy | Darmowy + cloud beta |
| **GitHub Stars** | Nowy projekt | ~182K (najwyżej w kategorii) |
| **Historia** | 2024+ | Marzec 2023 (pionier autonomicznych agentów) |
| **Status** | Wczesna faza | Aktywny (pivot na visual platform) |

## Filozofia architektury

### AutoGPT: Od eksperymentu do platformy
AutoGPT startował jako **eksperymentalny autonomiczny agent** — prosta pętla think→act→observe, która zdobyła 182K stars. Od tego czasu przeszedł transformację:

- **Faza 1 (2023):** Eksperymentalna pętla autonomiczna — "daj LLM cel i patrz co robi"
- **Faza 2 (2024-2025):** Agent Builder — visual drag-and-drop platform z marketplace'em
- **Faza 3 (2025+):** Platforma low-code dla nie-technicznych użytkowników

**Obecny focus:** Visual builder + marketplace, skierowany do low-code users.

### CoreSkill: Ewolucja dla deweloperów
CoreSkill pozostaje **developer-centric** — CLI-first, kod-first, z naciskiem na autonomiczną ewolucję, a nie wizualny builder.

## Porównanie cech

### 1. Autonomia

| Aspekt | CoreSkill | AutoGPT |
|--------|-----------|---------|
| **Model autonomii** | Ewolucyjny (mutacja kodu) | Pętla (think→act→observe) |
| **Tworzenie zdolności** | ✅ LLM generuje + testuje + ewoluuje | ⚠️ Marketplace (gotowe bloki) |
| **Samo-naprawa** | ✅ 5-fazowy AutoRepair | ❌ Brak |
| **Samo-ewolucja** | ✅ Mutacja + quality gates | ❌ Brak |
| **Refleksja** | ✅ SelfReflection + FailureTracker | ⚠️ Podstawowa (LLM-based) |
| **Proaktywność** | ✅ Background scheduler | ❌ Reaktywny |

**Werdykt:** CoreSkill ma głębszą autonomię — nie tylko działa autonomicznie, ale **sam się naprawia i ewoluuje**. AutoGPT potrafi działać autonomicznie, ale nie naprawia ani nie mutuje swojego kodu.

### 2. Interfejs użytkownika

| Aspekt | CoreSkill | AutoGPT |
|--------|-----------|---------|
| **Primary UI** | CLI (terminal) | Visual builder (web) |
| **Target user** | Developer | Low-code / biznes |
| **Konfiguracja** | Kod + auto-discovery | Drag-and-drop |
| **Marketplace** | ❌ Registry lokalne | ✅ Agent marketplace |
| **Tryb głosowy** | ✅ STT/TTS natywne | ❌ |

**Werdykt:** AutoGPT lepszy dla użytkowników nietechnicznych. CoreSkill lepszy dla deweloperów.

### 3. Architektura techniczna

| Aspekt | CoreSkill | AutoGPT |
|--------|-----------|---------|
| **Modularność** | 30+ modułów (evo_engine, intent, skills...) | Monolityczny agent + blocks |
| **Skill system** | ✅ Ewoluujący (stable/latest/archive) | Blocks (statyczne) |
| **Provider chain** | ✅ Auto-degradacja + UCB1 | ❌ Single provider |
| **Intent classification** | ✅ 3-tier ML | ❌ LLM-only |
| **LLM routing** | ✅ Free→Local→Paid | ⚠️ Wymaga API key |
| **Local-first** | ✅ Ollama auto-discovery | ❌ Wymaga OpenAI/cloud API |

**Werdykt:** CoreSkill bardziej modularny i elastyczny technicznie. AutoGPT prostszy koncepcyjnie, ale mniej konfigurowalny.

### 4. Odporność produkcyjna

| Aspekt | CoreSkill | AutoGPT |
|--------|-----------|---------|
| **Self-healing** | ✅ Pełny cykl naprawy | ❌ |
| **Quality gates** | ✅ 5-check pipeline | ❌ |
| **Drift detection** | ✅ DriftDetector | ❌ |
| **Health monitoring** | ✅ ProactiveScheduler | ❌ |
| **Rollback** | ✅ Wersjonowanie + snapshots | ❌ |
| **Repair journal** | ✅ Uczenie z napraw | ❌ |

**Werdykt:** CoreSkill znacznie bardziej gotowy na produkcję pod kątem niezawodności. AutoGPT ewoluował w stronę platformy, nie robustności runtime.

### 5. Koszt i dostępność

| Aspekt | CoreSkill | AutoGPT |
|--------|-----------|---------|
| **Framework** | Darmowy | Darmowy |
| **LLM koszty** | Minimalne (free + local) | Wyższe (wymaga API) |
| **Cloud** | Self-hosted only | Cloud beta (pricing TBD) |
| **Offline mode** | ✅ Pełny (Ollama) | ❌ |

## Kiedy wybrać CoreSkill?

- ✅ Jesteś **deweloperem** i preferujesz CLI + kod
- ✅ Potrzebujesz systemu, który **sam się naprawia** i **ewoluuje**
- ✅ Chcesz działać **offline** lub z minimalnymi kosztami LLM
- ✅ Potrzebujesz **production-grade reliability** (rollback, quality gates)
- ✅ Chcesz **tryb głosowy** natywnie
- ✅ Budujesz **automatyzację DevOps/SRE**

## Kiedy wybrać AutoGPT?

- ✅ Twoi użytkownicy są **nietechniczni** i potrzebują visual builder
- ✅ Chcesz korzystać z **marketplace** gotowych agentów
- ✅ Potrzebujesz **web UI** zamiast CLI
- ✅ Budujesz **prototyp** i chcesz szybko eksperymentować
- ✅ Community size ma znaczenie (182K stars = duża widoczność)

## Wspólne korzenie, różne ścieżki

AutoGPT i CoreSkill mają wspólną inspirację — **autonomiczne agenty AI**. Jednak ewoluowały w różnych kierunkach:

| | AutoGPT | CoreSkill |
|---|---------|-----------|
| **Kierunek** | Low-code platforma | Developer framework |
| **Innowacja** | Visual builder + marketplace | Self-evolution + self-healing |
| **Target** | Szeroki rynek | Nisza DevOps/SRE |

AutoGPT poszedł w stronę **demokratyzacji** (każdy może budować agenta), CoreSkill w stronę **autonomicznej niezawodności** (agent sam się utrzymuje).

---

*Porównanie oparte na stanie z marca 2026*

[← Powrót do przeglądu](README.md)
