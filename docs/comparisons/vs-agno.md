# CoreSkill vs Agno — Szczegółowe porównanie

## Przegląd

| | CoreSkill | Agno |
|---|-----------|------|
| **Twórca** | WronAI | Agno (dawniej Phidata) |
| **Architektura** | Ewolucyjna (text2pipeline) | Agent UI + workflow automation |
| **Licencja** | MIT | MIT |
| **Cena** | Darmowy | Darmowy + Agno Cloud (SaaS) |
| **GitHub Stars** | Nowy projekt | ~5K (dawniej Phidata) |
| **Focus** | Autonomiczna automatyzacja | Agent UI + web automation |
| **Status** | Wczesna faza | Szybki rozwój |

## Uwaga historyczna

Agno to nowa nazwa projektu **Phidata** (znany wcześniej jako Phidata). Projekt ewoluował z "AI assistants for data" do pełnoprawnej platformy agentów z UI.

## Filozofia architektury

### Agno: Agent UI + Web Automation
Agno to framework do budowy **agentów z interfejsem użytkownika** — szczególnie mocny w automatyzacji przeglądarki i web scraping.

```python
from agno.agent import Agent
from agno.tools.yfinance import YFinanceTools

agent = Agent(
    model=OpenAIChat(id="gpt-4o"),
    tools=[YFinanceTools(stock_price=True)],
    show_tool_calls=True,
    markdown=True,
)
```

**Kluczowe cechy:**
- **Playground UI:** Natywne web UI do interakcji z agentami
- **Browser automation:** Agno Browser (AI-assisted browsing)
- **Knowledge + Storage:** RAG z vector databases
- **Multi-user:** Obsługa wielu użytkowników

### CoreSkill: Ewolucyjna CLI-first automatyzacja
CoreSkill nie ma wbudowanego UI — jest **CLI-first** z autonomiczną ewolucją skillów.

```
CLI → IntentEngine → Skill (auto-evolve) → Execute → Validate
```

## Porównanie cech

### 1. Interfejs użytkownika

| Aspekt | CoreSkill | Agno |
|--------|-----------|------|
| **Primary UI** | CLI | ✅ Web UI (Playground) |
| **Browser automation** | ⚠️ Web search skill | ✅ Agno Browser |
| **API** | Python module | ✅ REST API |
| **Multi-user** | ❌ | ✅ Native |
| **Chat interface** | CLI + voice | ✅ Web chat |

**Werdykt:** Agno wygrywa pod kątem UI — ma wbudowany Playground. CoreSkill to CLI power-user tool.

### 2. Agenci i narzędzia

| Aspekt | CoreSkill | Agno |
|--------|-----------|------|
| **Model agenta** | Ewolucyjny skill | Class-based agent |
| **Tools** | Skills (auto-evolving) | ✅ 25+ gotowych narzędzi |
| **Web scraping** | ⚠️ Web search | ✅ Crawl4ai, Browser |
| **Knowledge (RAG)** | ❌ | ✅ Native |
| **Memory** | UserMemory | ✅ Native (sessions) |

**Werdykt:** Agno ma więcej gotowych narzędzi i RAG. CoreSkill ma auto-ewolucję skillów.

### 3. Autonomia i self-healing

| Aspekt | CoreSkill | Agno |
|--------|-----------|------|
| **Samo-ewolucja** | ✅ Mutacja kodu | ❌ |
| **Self-healing** | ✅ AutoRepair | ❌ |
| **Auto-create tools** | ✅ LLM generuje | ❌ |
| **Quality gates** | ✅ 5-check | ⚠️ Pydantic validation |
| **Proaktywny monitoring** | ✅ Scheduler | ❌ |

**Werdykt:** CoreSkill fundamentalnie bardziej autonomiczny.

### 4. Deployment

| Aspekt | CoreSkill | Agno |
|--------|-----------|------|
| **Self-hosted** | ✅ Native | ✅ Docker |
| **Managed cloud** | ❌ | ✅ Agno Cloud |
| **Local-first** | ✅ Ollama | ✅ Ollama |
| **Scalability** | Pojedynczy agent | ✅ Multi-agent + load balancing |

### 5. Developer Experience

| Aspekt | CoreSkill | Agno |
|--------|-----------|------|
| **Krzywa uczenia** | Średnia | ✅ Niska |
| **Dokumentacja** | Wczesna | ✅ Dobra |
| **Community** | Mała | Średnia (dawniej Phidata) |
| **Polish support** | ✅ Native | ⚠️ |

## Kiedy wybrać CoreSkill?

- ✅ Jesteś **power-userem** — preferujesz CLI nad web UI
- ✅ Potrzebujesz agenta, który **sam się naprawia** i **ewoluuje**
- ✅ System musi działać **offline** / **local-first**
- ✅ Budujesz **automatyzację IT/DevOps** z trybem głosowym
- ✅ Priorytetem jest **niezawodność** bez interwencji operatora

## Kiedy wybrać Agno?

- ✅ Chcesz **web UI** do interakcji z agentami
- ✅ Potrzebujesz **browser automation** (scraping, form filling)
- ✅ Wymagasz **multi-user** support
- ✅ Chcesz **gotowe narzędzia** (25+ integrations)
- ✅ **RAG + Knowledge base** są kluczowe
- ✅ Prefeferujesz **managed cloud** (Agno Cloud)

## Podsumowanie

| | CoreSkill | Agno |
|---|-----------|------|
| **Paradygmat** | CLI-first, self-healing | Web UI + automation |
| **Best for** | Autonomous automation | Interactive agents |
| **UI** | CLI | ✅ Web Playground |
| **Self-healing** | ✅ Full | ❌ |

---

*Porównanie oparte na stanie z marca 2025*

[← Powrót do przeglądu](README.md)
