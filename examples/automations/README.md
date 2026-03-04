# CoreSkill Automations Examples

Kompleksowe przykłady automatyzacji biurowych wykorzystujących dostępne skille.

## 📋 Dostępne Automatyzacje

### 1. Document Processing Pipeline (`document_processing_pipeline.py`)
**Skille:** document_search, document_editor, document_publisher

Automatyzuje przepływ pracy dokumentów:
- Indeksowanie dokumentów w folderze
- Konwersja do HTML z spisem treści
- Tworzenie wersji backup
- Generowanie raportu

```bash
python3 examples/automations/document_processing_pipeline.py /home/user/documents
```

---

### 2. Social Media Automation (`social_media_automation.py`)
**Skille:** social_media_manager, text_summarizer

Automatyzuje zarządzanie treścią social media:
- Generowanie postów na podstawie tematu
- Analiza tekstu pod kątem optymalizacji
- Planowanie publikacji
- Tracking hashtagów

```bash
python3 examples/automations/social_media_automation.py "AI w biznesie" "tomorrow 9am"
```

---

### 3. Account Creation Automation (`account_creation_automation.py`)
**Skille:** account_creator

Automatyzuje tworzenie kont internetowych:
- Generowanie bezpiecznych haseł
- Walidacja email i username
- Tworzenie pełnych danych konta
- Przechowywanie credentials (hashowane)

```bash
python3 examples/automations/account_creation_automation.py github user@example.com
```

---

### 4. OpenRouter API Key Automation (`openrouter_api_key_automation.py`)
**Skille:** web_automation, email_client, openrouter_automation

Automatyzuje pobieranie API key:
- Łączenie z serwerem email (IMAP)
- Wyszukiwanie wiadomości od OpenRouter
- Pobieranie linku aktywacyjnego
- Automatyczne logowanie i ekstrakcja API key

```bash
# Demo mode
python3 examples/automations/openrouter_api_key_automation.py --demo

# Production (wymaga zmiennych środowiskowych)
EMAIL_USER=user@example.com EMAIL_PASS=pass python3 examples/automations/openrouter_api_key_automation.py
```

---

### 5. KSeF Invoice Automation (`ksef_invoice_automation.py`)
**Skille:** ksef_integration, document_search

Automatyzuje obsługę KSeF (Polski system e-faktur):
- Logowanie do KSeF (token lub certyfikat)
- Pobieranie faktur
- Wysyłanie faktur
- Przetwarzanie wsadowe

```bash
python3 examples/automations/ksef_invoice_automation.py --token YOUR_TOKEN --action get_invoices
python3 examples/automations/ksef_invoice_automation.py --token YOUR_TOKEN --action batch --dir /invoices
```

---

### 6. Network Monitoring Automation (`network_monitoring_automation.py`)
**Skille:** network_tools, document_publisher

Automatyzuje monitorowanie sieci:
- Testy ping do kluczowych serwerów
- DNS lookup
- Sprawdzanie portów
- Generowanie raportu HTML

```bash
python3 examples/automations/network_monitoring_automation.py
```

---

### 7. Task Management Automation (`task_management_automation.py`)
**Skille:** task_manager, document_reader

Automatyzuje zarządzanie zadaniami:
- Tworzenie zadań z priorytetami
- Kategoryzowanie
- Wyszukiwanie i filtrowanie
- Raporty tygodniowe

```bash
python3 examples/automations/task_management_automation.py
```

---

## 🎯 Dodatkowe Możliwości Automatyzacji

Na podstawie posiadanych skilli można tworzyć:

### Automatyzacje Dokumentowe
- **Archiwizacja dokumentów** - wyszukiwanie, indeksowanie, kompresja
- **Konwersja formatów** - PDF ↔ DOCX ↔ HTML ↔ TXT
- **Wyszukiwanie duplikatów** - analiza i deduplikacja
- **Generowanie raportów** - z podsumowaniami tekstu

### Automatyzacje Sieciowe
- **Monitoring serwerów** - ping, porty, HTTP status
- **Diagnostyka DNS** - lookup, reverse lookup
- **Testy łączności** - automatyczne testy i alerty

### Automatyzacje Systemowe
- **Zarządzanie procesami** - listowanie, zabijanie, monitoring
- **Organizacja plików** - sortowanie, czyszczenie, backup
- **QR kody** - generowanie kodów dla dokumentów

### Automatyzacje Biurowe
- **Przetwarzanie tekstu** - podsumowania, analiza sentymentu
- **Konwersje jednostek** - waluty, jednostki miary, strefy czasowe
- **Zarządzanie notatkami** - tworzenie, tagowanie, wyszukiwanie

### Automatyzacje Web
- **Browser automation** - nawigacja, klikanie, wypełnianie formularzy
- **Email automation** - pobieranie, wysyłanie, ekstrakcja linków
- **Web scraping** - ekstrakcja danych ze stron

---

## 🔧 Jak Tworzyć Własne Automatyzacje

### Podstawowa struktura:

```python
#!/usr/bin/env python3
import sys
import json
import subprocess

def run_skill(skill_name, action, params):
    """Execute a skill."""
    input_data = {"action": action, **params}
    cmd = [
        sys.executable, "-c",
        f"""
import sys
sys.path.insert(0, 'skills/{skill_name}/v1')
from skill import execute
result = execute({json.dumps(input_data)})
print(json.dumps(result))
"""
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    return json.loads(result.stdout.strip().split('\n')[-1])

# Użycie
result = run_skill("document_search", "search_by_name", {
    "path": "/home/documents",
    "pattern": "*.pdf"
})
print(result)
```

---

## 📊 Lista Dostępnych Skilli

### Skille Biurowe (12)
- document_reader - czytanie PDF, DOCX, TXT, MD
- document_search - wyszukiwanie dokumentów
- document_editor - edycja dokumentów
- document_publisher - publikacja dokumentów
- notes - zarządzanie notatkami
- task_manager - zarządzanie zadaniami
- text_summarizer - podsumowania tekstu
- converter - konwersje jednostek
- calculator_advanced - kalkulator naukowy
- network_tools - diagnostyka sieci
- social_media_manager - zarządzanie social media
- account_creator - tworzenie kont

### Skille Systemowe (5)
- file_manager - operacje na plikach
- process_manager - zarządzanie procesami
- clipboard - operacje schowka
- qr_generator - generowanie QR kodów
- url_codec - kodowanie URL/base64

### Skille Automatyzacji (3)
- web_automation - automatyzacja przeglądarki (Playwright)
- email_client - operacje email (IMAP/SMTP)
- openrouter_automation - pobieranie API key

### Skille Integracji (1)
- ksef_integration - integracja z KSeF

**Łącznie: ~21 skilli gotowych do użycia!**

---

## 🚀 Szybki Start

1. **Zobacz wszystkie skille:**
   ```bash
   ls skills/
   ```

2. **Testuj pojedynczy skill:**
   ```bash
   cd skills/calculator_advanced/v1 && python3 skill.py
   ```

3. **Uruchom automatyzację:**
   ```bash
   cd examples/automations
   python3 network_monitoring_automation.py
   ```

---

## 📞 Wsparcie

W przypadku pytań lub problemów:
- Sprawdź dokumentację w folderze `docs/`
- Przejrzyj przykłady w `examples/automations/`
- Testuj pojedyncze skille przed tworzeniem pipeline'ów
