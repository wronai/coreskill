# Refaktoryzacja: Rozdzielenie wiedzy LLM od wiedzy systemu

## Problem (root cause)

```
User: "pogadajmy głosowo"
  → IntentEngine: "use: stt"
  → STT skill: CRASH "name 'shutil' is not defined"
  → Ewolucja v6→v7→v8→v9: TEN SAM BŁĄD
  → LLM fallback: "Nie mam możliwości komunikacji głosowej"  ← ŹRÓDŁO PROBLEMU
```

**Dlaczego LLM mówi "nie umiem"?**  
Bo system prompt nie mówi LLM-owi że jest rdzeniem evo-engine.
LLM myśli że jest zwykłym chatbotem i odpowiada swoją wiedzą
("jestem modelem tekstowym, nie generuję mowy").

**Dlaczego ewolucja nie naprawia?**  
Bo LLM generuje nowy kod bez `import shutil`, preflight tego nie sprawdza,
i error fingerprint nie jest śledzony — więc system próbuje tego samego 3x.


## Architektura: 3 Warstwy Wiedzy

```
┌─────────────────────────────────────────────┐
│  Warstwa 3: LLM (wiedza ogólna)             │
│  • Rozumie język naturalny                  │
│  • Generuje tekst / kod                     │
│  • NIE wie co system potrafi                │
│  • NIE wie które skille działają            │
└────────────────────┬────────────────────────┘
                     │ system prompt (dynamiczny!)
┌────────────────────▼────────────────────────┐
│  Warstwa 2: System Identity (NOWA)          │
│  • WIE co system potrafi (capability list)  │
│  • WIE które skille działają (health check) │
│  • Buduje system prompt DLA LLM             │
│  • Generuje fallback messages               │
│  • Routuje intencje do skilli               │
└────────────────────┬────────────────────────┘
                     │ exec_skill(), preflight
┌────────────────────▼────────────────────────┐
│  Warstwa 1: Skille (zdolności fizyczne)     │
│  • TTS: mówi głosem                         │
│  • STT: słucha                              │
│  • web_search: szuka w internecie           │
│  • Mogą być zdrowe lub uszkodzone           │
└─────────────────────────────────────────────┘
```

**Kluczowa zasada:** LLM NIGDY nie odpowiada "nie umiem X" —
bo nie wie co system umie. System Identity mówi LLM-owi
co jest dostępne i jak reagować na awarie.


## Dokładne zmiany w core.py

### Zmiana 1: Importy (góra pliku)

```python
# Dodaj na górze core.py:
from system_identity import SystemIdentity, SkillStatus
from preflight import SkillPreflight, EvolutionGuard
```


### Zmiana 2: Inicjalizacja w main() (~linia 1600+)

```python
# BYŁO:
def main():
    state = load_state()
    ...
    sm = SkillManager(llm, log)
    evo = EvoEngine(sm, llm, log)

# JEST:
def main():
    state = load_state()
    ...
    sm = SkillManager(llm, log)
    evo = EvoEngine(sm, llm, log)

    # NOWE: System Identity + Preflight + Evolution Guard
    identity = SystemIdentity(skill_manager=sm)
    preflight = SkillPreflight()
    evo_guard = EvolutionGuard()

    # Sprawdź zdrowie skilli na starcie
    identity.refresh_statuses()
```


### Zmiana 3: System Prompt (w chat loop, ~linia 1700+)

```python
# BYŁO (statyczny prompt — LLM nie wie o skillach):
sys_prompt = (
    "Jestes asystentem AI evo-engine. "
    "Pomagasz tworzyc skills i automatyzujesz zadania. "
    f"Dostepne skills: {json.dumps(list(skills.keys()))}."
)

# JEST (dynamiczny prompt — LLM wie co system potrafi):
sys_prompt = identity.build_system_prompt()
```

**Efekt:**
- LLM dostaje listę zdolności z ich statusem (DZIAŁA/USZKODZONY)
- LLM dostaje instrukcję: "nigdy nie mów 'nie umiem', mów 'skill wymaga naprawy'"
- LLM wie że jest RDZENIEM systemu, nie chatbotem


### Zmiana 4: handle_request() fallback (~linia 1400+)

```python
# BYŁO (LLM generuje fallback — mówi "nie umiem"):
cpr(C.RE, f"Nie udalo sie: {goal}")
cpr(C.D, "Sprobuje odpowiedziec tekstowo.")
# Potem LLM: "Nie mam możliwości komunikacji głosowej" ← ŹLE

# JEST (system generuje fallback — mówi co jest zepsute):
fallback_msg = identity.build_fallback_message(
    skill_name, error=str(last_error), attempts=attempt
)
cpr(C.YE, fallback_msg)
# "Skill 'stt' ma błąd: shutil not defined. Naprawiam..." ← DOBRZE

# Jeśli trzeba dać LLM-owi kontekst do odpowiedzi:
conv.append({
    "role": "system",
    "content": (
        f"Skill '{skill_name}' jest tymczasowo uszkodzony. "
        f"NIE mow ze nie umiesz. Powiedz ze naprawiasz skill "
        f"i zaproponuj alternatywe."
    )
})
```


### Zmiana 5: exec_skill() pre-flight (~linia 800+)

```python
# BYŁO (bezpośrednie ładowanie — crash na runtime):
def exec_skill(self, name, input_data=None, version=None):
    ...
    spec = importlib.util.spec_from_file_location(...)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # ← CRASH: "name 'shutil' is not defined"

# JEST (preflight check → auto-fix → ładowanie):
def exec_skill(self, name, input_data=None, version=None):
    ...
    p = self.skill_path(name, v)

    # PRE-FLIGHT CHECK
    pf_result = preflight.check_all(p)
    if not pf_result.ok:
        if pf_result.stage == "imports" and pf_result.details.get("missing_imports"):
            # Auto-fix: dodaj brakujące importy
            code = p.read_text()
            fixed = preflight.auto_fix_imports(code)
            if fixed != code:
                p.write_text(fixed)
                self.log.skill(name, "auto_fix", f"Fixed imports: {pf_result.details['missing_imports']}")
                pf_result = preflight.check_all(p)  # re-check

        if not pf_result.ok:
            return {
                "success": False,
                "error": f"Preflight: {pf_result.error}",
                "stage": pf_result.stage,
            }

    # Teraz ładuj i wykonaj
    spec = importlib.util.spec_from_file_location(...)
    ...
```


### Zmiana 6: smart_evolve() evolution guard (~linia 900+)

```python
# BYŁO (LLM generuje ten sam błąd):
def smart_evolve(self, name, error_info, ...):
    ...
    prompt = f"Fix this skill:\n{old_code}\nError: {error_info}"
    new_code = self.llm.gen_code(prompt)
    # → LLM generuje kod BEZ import shutil → ten sam crash

# JEST (guard + lepszy prompt + preflight nowego kodu):
def smart_evolve(self, name, error_info, extra_context="", ...):
    ...
    # 1. Sprawdź czy błąd się powtarza
    strategy = evo_guard.suggest_strategy(name, str(error_info))

    if strategy["strategy"] == "auto_fix_imports":
        # Nie pytaj LLM — po prostu napraw importy
        code = p.read_text()
        fixed = preflight.auto_fix_imports(code)
        if fixed != code:
            p.write_text(fixed)
            return True, f"Auto-fixed imports in {name}"

    # 2. Dodaj historię błędów do prompta
    error_history = evo_guard.build_evolution_prompt_context(name, str(error_info))
    skill_reqs = identity.build_skill_context_for_llm(name)

    prompt = (
        f"{skill_reqs}\n\n"
        f"{error_history}\n\n"
        f"Napraw ten skill:\n```python\n{old_code}\n```\n"
        f"Blad: {error_info}\n\n"
        f"PAMIETAJ: Dodaj WSZYSTKIE importy na gorze pliku!"
    )
    new_code = self.llm.gen_code(prompt)

    # 3. Preflight nowego kodu PRZED zapisem
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
        f.write(new_code)
        tmp_path = Path(f.name)

    pf_result = preflight.check_all(tmp_path)
    if not pf_result.ok:
        # Auto-fix i sprawdź ponownie
        fixed = preflight.auto_fix_imports(new_code)
        tmp_path.write_text(fixed)
        pf_result = preflight.check_all(tmp_path)

        if not pf_result.ok:
            tmp_path.unlink()
            evo_guard.record_error(name, str(error_info), version)
            return False, f"Evolved code failed preflight: {pf_result.error}"

        new_code = fixed

    tmp_path.unlink()

    # 4. Zapisz nową wersję
    nd.mkdir(parents=True, exist_ok=True)
    (nd / "skill.py").write_text(new_code)
    evo_guard.record_error(name, str(error_info), version)  # track
    ...
```


## Co te zmiany rozwiązują

### Przed refaktoryzacją:

```
User: "pogadajmy głosowo"
→ STT crash: "shutil not defined"
→ Ewolucja v7: ten sam crash
→ Ewolucja v8: ten sam crash
→ LLM: "Nie mam możliwości komunikacji głosowej"  ← ŹLE
```

### Po refaktoryzacji:

```
User: "pogadajmy głosowo"
→ SystemIdentity: potrzebne skille [stt, tts]
→ Preflight STT: FAIL "shutil not imported"
→ Auto-fix: dodaje "import shutil" → PASS
→ STT działa → TTS odpowiada głosem

LUB (jeśli skill realnie zepsuty):
→ STT crash po auto-fix
→ EvolutionGuard: "ten sam błąd 2x, zmień strategię"
→ Auto-fix imports zamiast LLM → naprawione
→ Fallback message: "Skill STT ma problem, naprawiam..."  ← DOBRZE
→ LLM NIE mówi "nie umiem" bo system prompt mu zabrania
```


## Dodatkowe mechanizmy obronne

### A. Startup Health Scan

```python
# W main(), po załadowaniu skilli:
identity.refresh_statuses()
report = identity.get_readiness_report()
if report["broken"]:
    cpr(C.YE, f"Uszkodzone skille: {', '.join(report['broken'])}")
    for skill_name in report["broken"]:
        # Próbuj auto-fix na starcie
        p = sm.skill_path(skill_name)
        if p:
            code = p.read_text()
            fixed = preflight.auto_fix_imports(code)
            if fixed != code:
                p.write_text(fixed)
                cpr(C.GR, f"  Auto-fixed: {skill_name}")
```

### B. Capability Routing (przed LLM analyze_need)

```python
# W chat loop, PRZED analyze_need:
needed_caps = identity.detect_needed_capabilities(user_input)
if needed_caps:
    # System wie co potrzebne — nie pytaj LLM
    analysis = {
        "action": "use_skill",
        "skill": needed_caps[0],
        "all_skills": needed_caps,
        "input": {"text": user_input},
        "source": "system_identity",
    }
else:
    # Niejednoznaczne — LLM decyduje
    analysis = llm.analyze_need(user_input, conv, skills)
```

### C. Voice Conversation Pipeline

```python
# Specjalny flow dla "pogadajmy głosowo":
if set(needed_caps) == {"stt", "tts"} or "stt" in needed_caps:
    # Krok 1: Włącz TTS (mówienie)
    tts_ok = sm.exec_skill("tts", {"text": "Słucham, mów..."})

    # Krok 2: Nasłuchuj (STT)
    stt_result = sm.exec_skill("stt", {"duration": 5})

    if stt_result.get("success"):
        # Krok 3: LLM przetwarza transkrypcję
        transcript = stt_result["result"]["text"]
        response = llm.chat([...transcript...])
        # Krok 4: TTS odpowiada głosem
        sm.exec_skill("tts", {"text": response})
    else:
        # Skill zepsuty — ale NIE mów "nie umiem"
        cpr(C.YE, identity.build_fallback_message("stt", stt_result.get("error")))
```


## Pliki do skopiowania

```
cores/v1/
  system_identity.py   ← NOWY: warstwa wiedzy systemu
  preflight.py         ← NOWY: pre-flight + evolution guard
  core.py              ← ZMIENIONY: 6 zmian opisanych wyżej
```


## Kolejność implementacji

| # | Co | Czas | Efekt |
|---|-----|------|-------|
| 1 | Skopiuj `system_identity.py` + `preflight.py` do `cores/v1/` | 1 min | — |
| 2 | Zmiana 2: inicjalizacja w `main()` | 5 min | system identity gotowe |
| 3 | Zmiana 3: dynamiczny system prompt | 5 min | LLM nie mówi "nie umiem" |
| 4 | Zmiana 5: preflight w `exec_skill()` | 15 min | koniec crash na runtime |
| 5 | Zmiana 6: evolution guard w `smart_evolve()` | 15 min | koniec pętli v6→v7→v8 |
| 6 | Zmiana 4: fallback message | 10 min | komunikaty "naprawiam" |
| 7 | Startup health scan | 5 min | auto-fix na starcie |

Łącznie: ~1h implementacji, zero zmian interfejsu użytkownika.
