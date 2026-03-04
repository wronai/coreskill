# Rozwiązywanie problemów

## Częste problemy

### 1. "No API key for OpenRouter"

**Przyczyna:** Brak klucza API dla tieru płatnego.

**Rozwiązania:**

```bash
# 1. Ustaw zmienną środowiskową
export OPENROUTER_API_KEY="sk-or-v1-..."

# 2. Lub w powłoce CoreSkill
/apikey sk-or-v1-...

# 3. Sprawdź czy działa
/models  # Powinien pokazać modele płatne
```

### 2. "Model not responding / Timeout"

**Przyczyna:** Model jest na cooldown lub przeciążony.

**Rozwiązania:**

```bash
# Sprawdź status modeli
/models

# Wymuś model lokalny
/model ollama/qwen2.5-coder:3b

# Lub wyłącz problematyczne tier
export EVO_DISABLE_LOCAL=0  # Używaj local
```

### 3. "Skill failed / Skill error"

**Diagnostyka:**

```bash
# Sprawdź health wszystkich skilli
/health

# Szczegóły konkretnego skillu
/diagnose nazwa_skillu

# Sprawdź logi
cat logs/nfo/skills.jsonl | grep nazwa_skillu

# Napraw
/fix nazwa_skillu

# Lub ewoluuj
/evolve nazwa_skillu
```

### 4. "STT nie działa / nie słyszy"

**Sprawdź:**

```bash
# 1. Czy mikrofon działa?
arecord -d 5 test.wav && aplay test.wav

# 2. Czy vosk-transcriber jest zainstalowany?
which vosk-transcriber

# 3. Zainstaluj jeśli brak
pip install vosk

# 4. Sprawdź w powłoce
/stt 5
```

### 5. "TTS nie działa"

**Sprawdź:**

```bash
# 1. Czy espeak jest zainstalowany?
espeak "test" -v pl

# 2. Zainstaluj jeśli brak
sudo apt install espeak-ng

# 3. Sprawdź providera
/providers set tts espeak
```

### 6. "IntentEngine źle rozpoznaje intencje"

**Poprawki:**

```bash
# Popraw błąd
/correct "tekst który źle zrozumiano" poprawny_skill

# Sprawdź profil
/profile

# Zresetuj training (ostrożnie!)
rm intent_training.json
```

### 7. "Wolne odpowiedzi"

**Przyczyny i rozwiązania:**

| Przyczyna | Rozwiązanie |
|-----------|-------------|
| Duży model zdalny | `/model ollama/gemma2:2b` - użyj małego lokalnego |
| Za dużo modeli | `export EVO_DISABLE_LOCAL=0` - ogranicz do darmowych |
| Długa historia | `/clear` - wyczyść konwersację |
| Wolny komputer | Zamknij inne aplikacje |

### 8. "Git push rejected - large files"

**Rozwiązanie:**

```bash
# Sprawdź duże pliki
git ls-files | xargs ls -lh | grep -E "[0-9]+M"

# Usuń z git (zostaw lokalnie)
git rm --cached models/models--sentence-transformers*

# Zaktualizuj .gitignore
echo "models/" >> .gitignore

# Commit i push
git commit -m "Remove large model files"
git push
```

### 9. "Permission denied"

**Rozwiązania:**

```bash
# State file
chmod 600 .evo_state.json

# Logi
chmod 755 logs/

# Skille
chmod 755 skills/
chmod 644 skills/*/v1/skill.py
```

### 10. "Import error / Module not found"

**Dla skilli:**

```python
# W skillu - obsłuż brakujący import:
try:
    import requests
except ImportError:
    return {
        "success": False,
        "error": "Missing dependency: requests",
        "suggestion": "pip install requests"
    }
```

**Globalnie:**

```bash
# Zainstaluj brakujące
pip install -r requirements.txt

# Lub konkretny pakiet
pip install nazwa_pakietu
```

## Diagnostyka systemu

### Sprawdź status

```bash
coreskill status
```

Pokazuje:
- Stan systemu (klucze w .evo_state.json)
- Liczbę logów
- Rozmiar cache
- Aktywne dyrektywy
- AdaptiveResourceMonitor pressure score
- ProviderChain status

### Sprawdź logi

```bash
# Ostatnie logi
tail -50 logs/nfo/skills.jsonl

# Błędy konkretnego skillu
grep '"skill":"tts"' logs/nfo/skills.jsonl | grep error

# SQLite query
python3 -c "
import sqlite3
conn = sqlite3.connect('logs/nfo/skills.db')
c = conn.cursor()
c.execute('SELECT * FROM calls WHERE exception IS NOT NULL ORDER BY timestamp DESC LIMIT 5')
for row in c.fetchall():
    print(row)
"

# Evolution journal - tracking ewolucji skilli
tail -30 logs/evo/evo_journal.jsonl

# Repair journal - historia napraw
cat logs/repair/repair_journal.jsonl | jq '.'

### Sprawdź modele

```bash
# Dostępne modele
/models

# Szczegóły tierów
# free:X/Y - X dostępnych z Y
# local:X/Y - X dostępnych z Y  
# paid:X/Y - X dostępnych z Y (wymaga API key)
```

### Sprawdź providery

```bash
# Status providerów
/providers

# ProviderChain status (fallback chain)
/chain

# Przykładowy output:
# TTS: espeak (lite) ✓
# STT: vosk (available) ✓
#      whisper (needs GPU) ✗
```

### Komendy diagnostyczne i naprawcze

```bash
# Diagnostyka konkretnego skillu
/diagnose nazwa_skillu

# Napraw skill
/fix nazwa_skillu

# Historia napraw dla skillu
/repairs nazwa_skillu
/repairs            # Wszystkie naprawy

# Zarządzanie wersjami skilli
/snapshot save nazwa_skillu       # Zapisz current jako stable
/snapshot restore nazwa_skillu    # Przywróć stable
/snapshot list nazwa_skillu       # Pokaż branche
/snapshot compare nazwa_skillu    # Porównaj z stable

# Journal ewolucji
/journal            # Globalne statystyki
/journal nazwa_skillu  # Historia konkretnego skillu

# Garbage collector
/gc                 # Pokaż co byłoby usunięte (dry-run)
/gc --force         # Wykonaj cleanup

# Health check
/health             # Status wszystkich skilli
/health nazwa_skillu # Szczegóły konkretnego

## Debugowanie

### Verbose mode

```bash
# Maksymalne logowanie
EVO_VERBOSE=1 python3 main.py

# Lub w powłoce - verbose jest domyślnie pokazywane dla LLM calls
```

### Pipeline debug

```bash
# Widoczne kroki pipeline
[PIPE] Intent: use → tts | goal: speak
[PIPE] Execute: tts v1 (attempt 1/3)
[PIPE] Validate: success
[PIPE] ✓ Goal achieved
```

### Skill debug

```python
# W skillu - dodaj logging:
import logging
logger = logging.getLogger(__name__)

def execute(params):
    logger.debug(f"Params: {params}")
    # ...
    logger.info(f"Result: {result}")
    return result
```

## Resetowanie

### Miękki reset (cache)

```bash
# Wyczyść cache
coreskill cache reset

# Usuń logi
coreskill logs reset

# Wyczyść konwersację
/clear
```

### Twardy reset (stan)

```bash
# ⚠️ Uwaga: Usuwa API key, preferencje, pamięć!
coreskill state reset --force

# Lub manualnie:
mv .evo_state.json .evo_state.json.bak
```

### Totalny reset

```bash
# Zatrzymaj CoreSkill
# Usuń wszystko oprócz kodu:
rm -rf .evo_state.json logs/ .cache/ __pycache__/
rm -rf skills/*/latest/  # Usuń ewolucje

# Restart
python3 main.py
```

## Problemy z Ollama

### "Cannot connect to Ollama"

```bash
# Sprawdź czy Ollama działa
curl http://localhost:11434/api/tags

# Jeśli nie - uruchom:
ollama serve

# Lub:
sudo systemctl start ollama
```

### "Model not found in Ollama"

```bash
# Pobierz model
ollama pull llama3.2:3b

# Sprawdź dostępne
ollama list
```

### "Ollama timeout"

```bash
# Użyj mniejszego modelu
/model ollama/gemma2:2b

# Lub wyłącz local całkowicie
export EVO_DISABLE_LOCAL=1
```

## Problemy z OpenRouter

### "401 Unauthorized"

```bash
# Klucz niepoprawny lub wygasł
# Sprawdź na: https://openrouter.ai/keys
/apikey nowy-klucz
```

### "429 Rate limit"

```bash
# Zbyt wiele requestów
# Poczekaj 60s lub użyj innego modelu

# Sprawdź które modele mają cooldown
/models
```

### "402 Payment required"

```bash
# Brak środków na koncie
# Doładuj na: https://openrouter.ai/credits
```

## Problemy z pamięcią

### "Zapomniał preferencji"

Sprawdź czy `save_state()` działa:

```bash
# Sprawdź stan
cat .evo_state.json | grep user_memory

# Dodaj ręcznie jeśli brak
/remember "Zawsze rozmawiaj po polsku"
```

### "Voice mode nie zapisuje się"

```bash
# Sprawdź czy voice_mode jest w dyrektywach
/memories

# Powinno pokazać: "Zawsze rozmawiaj głosowo..."
# Jeśli nie - włącz ponownie:
/voice
```

## Zgłaszanie błędów

### Co zebrać:

```bash
# 1. Status
coreskill status > bug_report.txt

# 2. Logi (ostatnie 100 linii)
tail -100 logs/nfo/skills.jsonl >> bug_report.txt

# 3. Stan (usuń API key przed wysłaniem!)
cat .evo_state.json | grep -v api_key >> bug_report.txt

# 4. Wersja
cat VERSION >> bug_report.txt
```

### Gdzie zgłosić:

- GitHub Issues: https://github.com/wronai/coreskill/issues
- Dołącz `bug_report.txt`
- Opisz kroki do reprodukcji

## FAQ

### Q: Dlaczego używa darmowych modeli zamiast płatnych?

**A:** Brak klucza API lub klucz niepoprawny. Sprawdź:
```
/apikey  # Pokaże status
```

### Q: Dlaczego odpowiedzi są wolne?

**A:** Używa dużego zdalnego modelu. Przełącz na lokalny:
```
/model ollama/gemma2:2b
```

### Q: Jak wrócić do starej wersji skillu?

**A:** 
```
/rollback nazwa_skillu
```

### Q: Czy można użyć własnego modelu?

**A:** Tak, jeśli jest w Ollama:
```
ollama pull twoj-model
/model ollama/twoj-model
```

### Q: Gdzie są zapisywane logi?

**A:** 
- SQLite: `logs/nfo/skills.db`
- JSONL: `logs/nfo/skills.jsonl`
- Tekst: `logs/*.log`

### Q: Jak wyeksportować pamięć?

**A:**
```bash
# Eksport
cat .evo_state.json | jq '.user_memory.directives' > memory_backup.json

# Import (ręcznie edytuj .evo_state.json)
```
