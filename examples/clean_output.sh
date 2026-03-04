#!/bin/bash
# CoreSkill Clean Output - Czyste wyjście danych bez logów
# Użycie: source clean_output.sh lub ./clean_output.sh

# Ścieżka do coreskill
export CORESKILL="/home/tom/github/wronai/coreskill/coreskill"

# ============================================================
# FUNKCJE DO CZYSTEGO WYJŚCIA
# ============================================================

# Czyste wyjście JSON (bez formatowania)
json() {
    $CORESKILL "$@" --output=json 2>/dev/null
}

# Czysty tekst (najważniejsza wartość)
raw() {
    $CORESKILL "$@" --output=raw 2>/dev/null
}

# Czytelny tekst (klucz-wartość)
text() {
    $CORESKILL "$@" --output=text 2>/dev/null
}

# ============================================================
# FUNKCJE SPECJALISTYCZNE
# ============================================================

# Obliczenia matematyczne
calc() {
    local expr="$1"
    raw calculator_advanced calculate "{\"expression\": \"$expr\"}"
}

# Ping hosta
check_ping() {
    local host="${1:-google.com}"
    raw network_tools ping "{\"host\": \"$host\", \"count\": 2}"
}

# Sprawdź port
check_port() {
    local host="${1:-google.com}"
    local port="${2:-443}"
    raw network_tools check_port "{\"host\": \"$host\", \"port\": $port}"
}

# DNS lookup
dns() {
    local domain="${1:-google.com}"
    raw network_tools dns_lookup "{\"domain\": \"$domain\"}"
}

# Generuj hasło
mkpass() {
    local length="${1:-16}"
    raw account_creator generate_password "{\"length\": $length, \"memorable\": false}"
}

# Generuj łatwe do zapamiętania hasło
mkpass_mem() {
    local length="${1:-16}"
    raw account_creator generate_password "{\"length\": $length, \"memorable\": true}"
}

# Sprawdź email
validate_email() {
    local email="$1"
    local result=$(raw account_creator validate_email "{\"email\": \"$email\"}")
    [ "$result" = "valid" ] && return 0 || return 1
}

# Sprawdź siłę hasła
check_password() {
    local pass="$1"
    raw account_creator check_password_strength "{\"password\": \"$pass\"}"
}

# Znajdź pliki po nazwie
find_files() {
    local path="${1:-.}"
    local pattern="${2:-*}"
    raw document_search search_by_name "{\"path\": \"$path\", \"pattern\": \"$pattern\"}"
}

# Znajdź w treści plików
search_content() {
    local path="${1:-.}"
    local query="$2"
    raw document_search search_by_content "{\"path\": \"$path\", \"query\": \"$query\"}"
}

# Konwersja jednostek
convert() {
    local value="$1"
    local from="$2"
    local to="$3"
    local qty="${4:-length}"
    raw converter convert "{\"value\": $value, \"from_unit\": \"$from\", \"to_unit\": \"$to\", \"quantity\": \"$qty\"}"
}

# Lista plików w katalogu
lsk() {
    local path="${1:-.}"
    raw file_manager list "{\"path\": \"$path\"}"
}

# Informacje o pliku/file
file_info() {
    local file="$1"
    raw file_manager info "{\"path\": \"$file\"}"
}

# Podsumowanie tekstu
summarize() {
    local text="$1"
    local ratio="${2:-0.3}"
    raw text_summarizer summarize "{\"text\": \"$text\", \"ratio\": $ratio}"
}

# Słowa kluczowe z tekstu
keywords() {
    local text="$1"
    raw text_summarizer extract_keywords "{\"text\": \"$text\"}"
}

# Dodaj zadanie
add_task() {
    local title="$1"
    local priority="${2:-medium}"
    raw task_manager add_task "{\"title\": \"$title\", \"priority\": \"$priority\"}"
}

# Lista zadań
tasks() {
    raw task_manager list_tasks "{}"
}

# Generuj QR
make_qr() {
    local data="$1"
    local output="${2:-/tmp/qr.png}"
    raw qr_generator generate "{\"data\": \"$data\", \"output\": \"$output\"}"
}

# Koduj URL
url_encode() {
    local text="$1"
    raw url_codec encode_url "{\"text\": \"$text\"}"
}

# Dekoduj URL
url_decode() {
    local text="$1"
    raw url_codec decode_url "{\"text\": \"$text\"}"
}

# Base64 encode
b64_enc() {
    local text="$1"
    raw url_codec encode_base64 "{\"text\": \"$text\"}"
}

# Base64 decode
b64_dec() {
    local text="$1"
    raw url_codec decode_base64 "{\"text\": \"$text\"}"
}

# ============================================================
# PROMPTY NATURALNEGO JĘZYKA
# ============================================================

# Wykonaj komendę z naturalnego języka
ask() {
    local prompt="$*"
    raw prompt "$prompt"
}

# ============================================================
# EKSPORT DO ZMIENNYCH
# ============================================================

# Eksportuj wynik do zmiennej (bez wyświetlania)
export_calc() {
    local expr="$1"
    local var="$2"
    eval "$var=$(calc "$expr")"
}

export_pass() {
    local length="$1"
    local var="$2"
    eval "$var=$(mkpass "$length")"
}

export_dns() {
    local domain="$1"
    local var="$2"
    eval "$var=$(dns "$domain")"
}

# ============================================================
# PRZYKŁADY UŻYCIA
# ============================================================

if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    # Jeśli uruchomiono bezpośrednio - pokaż przykłady
    echo "=== CoreSkill Clean Output Functions ==="
    echo ""
    echo "Dostępne funkcje:"
    echo "  calc <expression>        - Obliczenia matematyczne"
    echo "  check_ping <host>        - Test ping"
    echo "  check_port <host> <port> - Sprawdź port"
    echo "  dns <domain>             - DNS lookup"
    echo "  mkpass [length]          - Generuj hasło"
    echo "  mkpass_mem [length]      - Generuj łatwe hasło"
    echo "  find_files <path> [pat]  - Znajdź pliki"
    echo "  search_content <p> <q>   - Szukaj w treści"
    echo "  convert <v> <f> <t> [q]  - Konwersja jednostek"
    echo "  lsk [path]               - Lista plików"
    echo "  summarize <text>         - Podsumowanie tekstu"
    echo "  keywords <text>          - Słowa kluczowe"
    echo "  add_task <title> [pri]   - Dodaj zadanie"
    echo "  tasks                    - Lista zadań"
    echo "  ask <prompt>             - Naturalny język"
    echo ""
    echo "Przykłady:"
    echo '  calc "2+2"'
    echo '  check_ping google.com'
    echo '  mkpass 20'
    echo '  find_files /tmp "*.pdf"'
    echo '  convert 100 fahrenheit celsius temperature'
    echo '  ask "calculate 15% of 200"'
    echo ""
    echo "Użycie w skryptach:"
    echo '  source /path/to/clean_output.sh'
    echo '  PASSWORD=$(mkpass 20)'
    echo '  echo "Generated: $PASSWORD"'
fi
