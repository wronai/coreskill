# evo-engine: Propozycja Refaktoryzacji

## Status Quo

Analiza `analysis.toon` i `evolution.toon` pokazuje:

- `cores/v1/core.py` = **1755 linii, 8 klas, CC=122** (god module)
- 7 skilli: echo, tts, stt, devops, deps, web_search, git_ops
- Brak mechanizmu wariantow implementacji tego samego skilla
- Brak resource-aware routing (system nie wie co komputer "moze")

Kluczowe problemy do rozwiazania:
1. Jak TTS moze miec 3 implementacje (espeak / pyttsx3 / coqui-ai) i system sam wybiera?
2. Jak rozbic god module na czytelne warstwy?
3. Jak system staje sie bardziej autonomiczny?


## 1. Skill Variants: Capability-Based Architecture

### Problem

Dzisiejsza struktura:

```
skills/
  tts/v1/skill.py      <- jedna implementacja, wersjonowanie = ewolucja
  tts/v2/skill.py      <- "lepsza" ale nadpisuje v1
```

`v1 -> v2 -> v3` to **ewolucja** tego samego kodu. Ale co jesli chcemy:
- `espeak` (lekki, 0 deps, niska jakosc)
- `pyttsx3` (srednia jakosc, wymaga pip)
- `coqui-tts` (neuronowy, wymaga GPU, najlepsza jakosc)

To nie sa wersje - to sa **warianty** (providery) tej samej zdolnosci.

### Rozwiazanie: Capability + Provider + Tier

```
skills/
  tts/                           <- capability (zdolnosc)
    manifest.json                <- deklaracja capability + lista providerow
    providers/
      espeak/                    <- provider: lekki
        v1/skill.py
        v2/skill.py              <- ewolucja espeak
        meta.json                <- tier: "lite", deps: ["espeak"], resources: {}
      pyttsx3/                   <- provider: sredni
        v1/skill.py
        meta.json                <- tier: "standard", deps: ["pyttsx3"]
      coqui/                     <- provider: ciezki/neuronowy
        v1/skill.py
        meta.json                <- tier: "premium", resources: {gpu: true, ram_mb: 2048}
```

### manifest.json

```json
{
  "capability": "tts",
  "description": "Text-to-Speech: zamienia tekst na mowe",
  "interface": {
    "input": {"text": "str", "lang": "str"},
    "output": {"spoken": "bool", "method": "str", "audio_path": "str|null"}
  },
  "providers": ["espeak", "pyttsx3", "coqui"],
  "default_provider": "espeak",
  "selection_strategy": "best_available"
}
```

### meta.json (per provider)

```json
{
  "provider": "coqui",
  "tier": "premium",
  "quality_score": 9,
  "requirements": {
    "python_packages": ["TTS>=0.20"],
    "system_packages": ["ffmpeg"],
    "gpu": true,
    "min_ram_mb": 2048,
    "min_disk_mb": 500
  },
  "fallback_to": "pyttsx3",
  "tags": ["neural", "high-quality", "slow-first-run"]
}
```

### Provider Selection Algorithm

```python
class ProviderSelector:
    """Wybiera najlepszy provider dla danej capability."""

    def select(self, capability: str, context: dict = None) -> str:
        manifest = self.load_manifest(capability)
        providers = self.list_providers(capability)
        
        # 1. Filtruj: ktore providery MOGA dzialac na tym systemie?
        available = []
        for p in providers:
            meta = self.load_meta(capability, p)
            if self.check_requirements(meta.get("requirements", {})):
                available.append((p, meta))
        
        if not available:
            # Zadnego nie mozna uruchomic - fallback do domyslnego
            return manifest.get("default_provider", providers[0])
        
        # 2. Sortuj po quality_score (malejaco)
        available.sort(key=lambda x: x[1].get("quality_score", 0), reverse=True)
        
        # 3. Jesli context ma "prefer_fast" - wybierz tier=lite
        if context and context.get("prefer_fast"):
            for p, meta in available:
                if meta.get("tier") == "lite":
                    return p
        
        # 4. Zwroc najlepsza jakosciowo dostepna opcje
        return available[0][0]

    def check_requirements(self, reqs: dict) -> bool:
        """Sprawdza czy system spelnia wymagania."""
        # GPU check
        if reqs.get("gpu"):
            if not self.has_gpu():
                return False
        # RAM check
        min_ram = reqs.get("min_ram_mb", 0)
        if min_ram and self.available_ram_mb() < min_ram:
            return False
        # Python packages
        for pkg in reqs.get("python_packages", []):
            name = pkg.split(">=")[0].split("==")[0]
            try:
                __import__(name)
            except ImportError:
                return False
        # System commands
        for cmd in reqs.get("system_packages", []):
            if not shutil.which(cmd):
                return False
        return True
```

### Nazewnictwo: podsumowanie

| Pojecie | Znaczenie | Przyklad |
|---------|-----------|----------|
| **Capability** | Co system potrafi | `tts`, `stt`, `web_search` |
| **Provider** | Konkretna implementacja | `espeak`, `coqui`, `duckduckgo` |
| **Version** | Ewolucja tego samego providera | `v1`, `v2`, `v3` |
| **Tier** | Poziom zasobow/jakosci | `lite`, `standard`, `premium` |

Wywolanie:
```python
# System sam wybiera najlepszy provider
result = skill_manager.execute("tts", {"text": "Witaj"})

# Wymuszenie providera
result = skill_manager.execute("tts", {"text": "Witaj"}, provider="coqui")

# Preferencja szybkosci
result = skill_manager.execute("tts", {"text": "Witaj"}, context={"prefer_fast": True})
```


## 2. Rozbicie God Module: core.py (1755L -> 8 plikow)

Obecna struktura `core.py` zawiera 8 klas - kazda powinna byc osobnym plikiem.

### Docelowa struktura `cores/v1/`

```
cores/v1/
  __init__.py              <- eksportuje main()
  main.py                  <- chat loop (obecna main(), CC 122 -> ~15)
  llm_client.py            <- LLMClient (tiered routing)
  intent_engine.py         <- IntentEngine (keyword + LLM classification)
  skill_manager.py         <- SkillManager + ProviderSelector (NEW)
  evo_engine.py            <- EvoEngine (evolutionary loop)
  pipeline_manager.py      <- PipelineManager
  supervisor.py            <- Supervisor (A/B core management)
  logger.py                <- Logger
  resource_monitor.py      <- NEW: monitoruje CPU/RAM/GPU/dysk
  config.py                <- load_state, save_state, constants
  utils.py                 <- cpr, _clean, _clean_json
```

### Priorytet rozbicia (wg evolution.toon)

| # | Co | Dlaczego | Effort |
|---|-----|----------|--------|
| 1 | Wydziel `config.py` + `utils.py` | Brak zaleznosci, latwy start | 30min |
| 2 | Wydziel `logger.py` | Uzywany wszedzie, stabilny interfejs | 30min |
| 3 | Wydziel `llm_client.py` | CC=22, osobna odpowiedzialnosc | 1h |
| 4 | Wydziel `intent_engine.py` | CC=25 (_kw_classify), wymaga split | 1h |
| 5 | Wydziel `skill_manager.py` | CC=19, dodaj ProviderSelector | 2h |
| 6 | Wydziel `evo_engine.py` | CC=16, ewolucja + walidacja | 1h |
| 7 | Wydziel `supervisor.py` + `pipeline_manager.py` | Niska CC, proste | 30min |
| 8 | Rozbij `main()` CC=122 | Chat loop -> dispatch table | 2h |


## 3. Resource Monitor: system wie co "moze"

Nowy modul `resource_monitor.py` ktory umozliwia resource-aware selection:

```python
class ResourceMonitor:
    """Monitoruje zasoby systemowe dla skill selection."""

    def snapshot(self) -> dict:
        """Zwraca aktualny stan zasobow."""
        import psutil
        import shutil

        snap = {
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
            "ram_total_mb": psutil.virtual_memory().total // (1024*1024),
            "ram_available_mb": psutil.virtual_memory().available // (1024*1024),
            "disk_free_mb": shutil.disk_usage("/").free // (1024*1024),
            "gpu": self._detect_gpu(),
            "network": self._check_network(),
        }
        return snap

    def _detect_gpu(self) -> dict:
        """Sprawdza dostepnosc GPU (CUDA/ROCm)."""
        try:
            import torch
            if torch.cuda.is_available():
                return {
                    "available": True,
                    "name": torch.cuda.get_device_name(0),
                    "vram_mb": torch.cuda.get_device_properties(0).total_mem // (1024*1024)
                }
        except ImportError:
            pass
        # Fallback: nvidia-smi
        try:
            r = subprocess.run(["nvidia-smi", "--query-gpu=name,memory.total",
                               "--format=csv,noheader"], capture_output=True, text=True)
            if r.returncode == 0:
                parts = r.stdout.strip().split(", ")
                return {"available": True, "name": parts[0],
                        "vram_mb": int(parts[1].replace(" MiB",""))}
        except FileNotFoundError:
            pass
        return {"available": False}

    def can_run(self, requirements: dict) -> tuple[bool, str]:
        """Sprawdza czy system moze uruchomic skill z danymi wymaganiami."""
        snap = self.snapshot()

        if requirements.get("gpu") and not snap["gpu"]["available"]:
            return False, "GPU required but not available"
        if requirements.get("min_ram_mb", 0) > snap["ram_available_mb"]:
            return False, f"Need {requirements['min_ram_mb']}MB RAM, have {snap['ram_available_mb']}MB"
        if requirements.get("min_disk_mb", 0) > snap["disk_free_mb"]:
            return False, f"Need {requirements['min_disk_mb']}MB disk, have {snap['disk_free_mb']}MB"
        return True, "OK"
```


## 4. Autonomia: Self-Healing Loop

### Problem

System reaguje na usera, ale nie naprawia sie sam. Jesli skill TTS padnie, user musi rucznie `/rollback`.

### Rozwiazanie: Background Health Loop

```python
class AutonomousLoop:
    """Okresowo sprawdza zdrowie systemu i naprawia problemy."""

    def __init__(self, skill_mgr, evo_engine, resource_mon, logger):
        self.sm = skill_mgr
        self.evo = evo_engine
        self.rm = resource_mon
        self.log = logger
        self.interval_sec = 60

    def tick(self):
        """Jeden cykl sprawdzenia - wywolywany co interval_sec."""

        # 1. Health check wszystkich skilli
        for cap_name in self.sm.list_capabilities():
            provider = self.sm.active_provider(cap_name)
            result = self.sm.health_check(cap_name, provider)
            if not result["healthy"]:
                self.log.core("warn", f"{cap_name}/{provider} unhealthy: {result['error']}")
                self._handle_unhealthy(cap_name, provider, result)

        # 2. Sprawdz czy sa lepsze providery dostepne
        self._check_upgrades()

        # 3. Sprawdz nieobslugiwane intencje -> zasugeruj nowe skille
        self._check_unhandled_intents()

    def _handle_unhealthy(self, cap, provider, result):
        """Reaguj na niezdrawy skill."""
        # a) Proba naprawy (deps install, retry)
        fixed = self.evo.try_fix(cap, provider, result["error"])
        if fixed:
            self.log.core("info", f"Auto-fixed {cap}/{provider}")
            return

        # b) Fallback do innego providera
        meta = self.sm.load_meta(cap, provider)
        fallback = meta.get("fallback_to")
        if fallback and self.sm.provider_exists(cap, fallback):
            self.sm.set_active_provider(cap, fallback)
            self.log.core("warn", f"Switched {cap}: {provider} -> {fallback}")
            return

        # c) Rollback wersji
        self.sm.rollback(cap, provider)
        self.log.core("warn", f"Rolled back {cap}/{provider}")

    def _check_upgrades(self):
        """Sprawdz czy system zyskal zasoby (np. ktos zainstalowal GPU driver)."""
        for cap_name in self.sm.list_capabilities():
            current = self.sm.active_provider(cap_name)
            best = self.sm.select_best_provider(cap_name)
            if best != current:
                current_q = self.sm.quality_score(cap_name, current)
                best_q = self.sm.quality_score(cap_name, best)
                if best_q > current_q:
                    self.log.core("info",
                        f"Upgrade available: {cap_name} {current}(q={current_q}) -> {best}(q={best_q})")
                    # Auto-upgrade jesli roznica > 2 punkty
                    if best_q - current_q >= 2:
                        self.sm.set_active_provider(cap_name, best)
                        self.log.core("info", f"Auto-upgraded {cap_name} -> {best}")

    def _check_unhandled_intents(self):
        """Analizuj logi - jesli user wielokrotnie prosi o cos czego nie ma, zaproponuj."""
        # IntentEngine zbiera "unhandled" intencje
        # Po 3+ probach tego samego -> sugestia nowego skilla
        pass
```


## 5. Nowa Struktura Katalogow (docelowa)

```
evo-engine/
  main.py                          <- bootstrap (bez zmian)
  build_core.py                    <- generator core (do wyrzucenia po stabilizacji)

  cores/
    v1/
      __init__.py
      main.py                      <- chat loop (dispatch table zamiast if/elif)
      config.py                    <- state, constants
      utils.py                     <- cpr, _clean
      logger.py                    <- Logger
      llm_client.py                <- LLMClient (tiered)
      intent_engine.py             <- IntentEngine
      skill_manager.py             <- SkillManager + ProviderSelector
      evo_engine.py                <- EvoEngine (evolutionary loop)
      pipeline_manager.py          <- PipelineManager
      supervisor.py                <- Supervisor (A/B)
      resource_monitor.py          <- ResourceMonitor (NEW)
      autonomous_loop.py           <- AutonomousLoop (NEW)

  skills/
    echo/
      manifest.json
      providers/
        default/v1/skill.py

    tts/
      manifest.json                <- capability declaration
      providers/
        espeak/
          v1/skill.py              <- tier: lite, 0 deps
          meta.json
        pyttsx3/
          v1/skill.py              <- tier: standard
          meta.json
        coqui/
          v1/skill.py              <- tier: premium, GPU
          meta.json

    stt/
      manifest.json
      providers/
        vosk/
          v1/skill.py              <- tier: standard, offline
          meta.json
        whisper/
          v1/skill.py              <- tier: premium, GPU
          meta.json

    web_search/
      manifest.json
      providers/
        duckduckgo/v1/skill.py     <- tier: lite, no API key
        google/v1/skill.py         <- tier: standard, needs key
        brave/v1/skill.py          <- tier: standard, needs key

    devops/
      manifest.json
      providers/
        default/v1/skill.py

    deps/
      manifest.json
      providers/
        default/v1/skill.py

    git_ops/
      manifest.json
      providers/
        default/v1/skill.py

  pipelines/
  registry/
  logs/
```


## 6. Migracja: 3 Fazy

### Faza 1: Core Split (1-2 dni)

Cel: rozbic `core.py` 1755L na 8+ plikow. Zero zmian funkcjonalnych.

1. Wyodrebnij `config.py`, `utils.py`, `logger.py`
2. Wyodrebnij `llm_client.py`, `intent_engine.py`
3. Wyodrebnij `skill_manager.py`, `evo_engine.py`
4. Wyodrebnij `supervisor.py`, `pipeline_manager.py`
5. Rozbij `main()` CC=122 na dispatch table
6. `__init__.py` re-eksportuje `main()`
7. Testy: `python3 main.py --check` dziala jak wczesniej

### Faza 2: Capability/Provider (1-2 dni)

Cel: nowa struktura skill z manifest.json i providerami.

1. Dodaj `manifest.json` do kazdego skilla
2. Przeorganizuj `skills/tts/` na `providers/espeak/v1/`
3. Dodaj `ProviderSelector` do `skill_manager.py`
4. Dodaj `ResourceMonitor`
5. Zmodyfikuj `exec_skill()` -> wybiera provider automatycznie
6. Backward compatible: `/run tts` nadal dziala (wybiera najlepszy)
7. Nowe: `/run tts --provider coqui` wymusza

### Faza 3: Autonomia (1 dzien)

Cel: system naprawia sie sam.

1. `AutonomousLoop` w osobnym watku
2. Auto-fallback przy awarii providera
3. Auto-upgrade przy pojawieniu sie zasobow
4. Analiza unhandled intents -> sugestie nowych skilli
5. Periodic health check + raport


## 7. Odpowiedzi na pytania

### Czy warianty maja rozna nazwe?

**Nie.** Capability (zdolnosc) ma jedna nazwe: `tts`. Providery maja swoje: `espeak`, `coqui`.
User mowi: "powiedz cos" -> system routuje do `tts` -> ProviderSelector wybiera `espeak` lub `coqui`.

### Jak z wersjonowaniem?

Kazdy provider ma osobne wersje:
- `tts/providers/espeak/v1` -> `v2` -> `v3` (ewolucja espeak)
- `tts/providers/coqui/v1` -> `v2` (ewolucja coqui)

Rollback dziala per-provider.

### Jak dodac nowy provider?

System moze to zrobic sam:
1. User mowi: "chce lepsza jakosc TTS"
2. IntentEngine wykrywa: `evolve_skill` + `tts`
3. EvoEngine sprawdza ResourceMonitor
4. Jesli GPU dostepne -> LLM generuje `tts/providers/coqui/v1/skill.py`
5. DevOps testuje -> jesli OK, dodaje do manifest.json
6. ProviderSelector automatycznie wybierze coqui (bo quality_score=9)

### Jak system radzi sobie z problemami?

```
User request -> IntentEngine.analyze()
  -> skill exists?
     YES -> ProviderSelector.select(best for this system)
            -> execute
            -> fail? -> try fallback provider
                     -> fail? -> auto-evolve (LLM fix)
                              -> fail? -> rollback
                                       -> fail? -> log + inform user
     NO  -> EvoEngine.evolve_skill(create new)
            -> DevOps.test()
            -> OK? -> register + execute
            -> FAIL? -> LLM diagnose + retry (max 3x)
```
