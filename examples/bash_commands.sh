#!/bin/bash
# CoreSkill Non-Interactive Bash Examples
# Przykłady nieinteraktywnych komend CLI dla automatyzacji

# ============================================================
# USTAW ŚCIEŻKĘ DO CORESKILL
# ============================================================
CORESKILL="/home/tom/github/wronai/coreskill/coreskill"

# ============================================================
# 1. CZYSTE WYJŚCIE DLA SKRYPTÓW (RAW OUTPUT)
# ============================================================

echo "=== 1. CZYSTE WYJŚCIE DLA SKRYPTÓW ==="

# Pobierz wynik obliczenia jako liczbę (bez logów)
RESULT=$($CORESKILL calculator_advanced calculate '{"expression": "2+2"}' --output=raw)
echo "2+2 = $RESULT"

# Sprawdź czy port jest otwarty (0/1 lub open/closed)
PORT_STATUS=$($CORESKILL network_tools check_port '{"host": "google.com", "port": 443}' --output=raw)
echo "Port 443: $PORT_STATUS"

# Pobierz IP z DNS jako lista
IPS=$($CORESKILL network_tools dns_lookup '{"domain": "google.com"}' --output=raw)
echo "Google IPs: $IPS"

# Wygeneruj hasło (czysty tekst)
PASSWORD=$($CORESKILL account_creator generate_password '{"length": 16, "memorable": false}' --output=raw)
echo "Generated password: $PASSWORD"

# ============================================================
# 2. PIPELINING - ŁĄCZENIE KOMEND
# ============================================================

echo ""
echo "=== 2. PIPELINING - ŁĄCZENIE KOMEND ==="

# Znajdź pliki PDF i przetwór je
FILES=$($CORESKILL document_search search_by_name '{"path": "/tmp", "pattern": "*.pdf"}' --output=raw)
for file in $FILES; do
    echo "Processing: $file"
done

# Ping -> sprawdź czy online -> dodaj do raportu
PING_RESULT=$($CORESKILL network_tools ping '{"host": "8.8.8.8", "count": 1}' --output=raw)
if [[ $PING_RESULT == *"1/1"* ]]; then
    echo "Google DNS is ONLINE"
else
    echo "Google DNS is OFFLINE"
fi

# ============================================================
# 3. JSON OUTPUT DLA PRZETWARZANIA
# ============================================================

echo ""
echo "=== 3. JSON OUTPUT DLA PRZETWARZANIA ==="

# Pobierz JSON i przetwórz z jq (jeśli dostępny)
JSON_RESULT=$($CORESKILL calculator_advanced calculate '{"expression": "sqrt(256)"}' --output=json)
echo "Full JSON: $JSON_RESULT"

# Eksportuj do pliku
$CORESKILL network_tools ping '{"host": "github.com", "count": 3}' --output=json > /tmp/ping_result.json
echo "Saved to /tmp/ping_result.json"

# ============================================================
# 4. NATURAL LANGUAGE PROMPTS
# ============================================================

echo ""
echo "=== 4. NATURAL LANGUAGE PROMPTS ==="

# Prompt: oblicz
$CORESKILL prompt "calculate 15% of 250" --output=raw

# Prompt: ping
$CORESKILL prompt "ping google.com" --output=raw

# Prompt: hasło
$CORESKILL prompt "generate 20 character password" --output=raw

# Prompt: szukaj plików
$CORESKILL prompt "find all txt files in /tmp" --output=raw

# ============================================================
# 5. PRZYKŁADY PRZYDATNE W SKRYPTACH
# ============================================================

echo ""
echo "=== 5. PRZYKŁADY UŻYTECZNE W SKRYPTACH ==="

# Sprawdź czy email jest valid
validate_email() {
    local email=$1
    local result=$($CORESKILL account_creator validate_email "{\"email\": \"$email\"}" --output=raw)
    if [ "$result" = "valid" ]; then
        return 0
    else
        return 1
    fi
}

if validate_email "test@example.com"; then
    echo "Email is valid"
else
    echo "Email is invalid"
fi

# Generuj hasło i zapisz do zmiennej
get_password() {
    local length=${1:-16}
    $CORESKILL account_creator generate_password "{\"length\": $length, \"memorable\": false}" --output=raw
}

NEW_PASS=$(get_password 20)
echo "New password length: ${#NEW_PASS}"

# ============================================================
# 6. AUTOMATYZACJE CRON / SCHEDULER
# ============================================================

echo ""
echo "=== 6. PRZYKŁADY DO CRONA ==="

# Sprawdź dostępność serwera i zapisz do logu
# (dodaj do crontab: */5 * * * * /path/to/coreskill_cron.sh)
check_server() {
    local host=$1
    local logfile=$2
    local result=$($CORESKILL network_tools ping "{\"host\": \"$host\", \"count\": 2}" --output=raw)
    echo "$(date): $host - $result" >> "$logfile"
}

# Przykład użycia w cron:
# check_server "google.com" "/var/log/uptime.log"

# ============================================================
# 7. PIPE MODE (stdin)
# ============================================================

echo ""
echo "=== 7. PIPE MODE (stdin) ==="

# Prześlij dane przez pipe
echo '{"host": "8.8.8.8", "count": 2}' | $CORESKILL pipe network_tools ping --output=raw

# Zapisz wynik do zmiennej
IP_RESULT=$(echo '{"domain": "github.com"}' | $CORESKILL pipe network_tools dns_lookup --output=raw)
echo "GitHub IP: $IP_RESULT"

# ============================================================
# 8. KONWERSJA I FORMATOWANIE
# ============================================================

echo ""
echo "=== 8. KONWERSJA I FORMATOWANIE ==="

# Zamiana jednostek - wynik jako liczba
TEMP_C=$($CORESKILL converter convert '{"value": 100, "from_unit": "fahrenheit", "to_unit": "celsius", "quantity": "temperature"}' --output=raw)
echo "100°F = ${TEMP_C}°C"

# Przeliczanie walut (symulowane)
PLN=$($CORESKILL converter convert '{"value": 100, "from_unit": "USD", "to_unit": "PLN", "quantity": "currency"}' --output=raw)
echo "100 USD = ${PLN} PLN"

# Konwersja danych
BYTES=$($CORESKILL converter convert '{"value": 1, "from_unit": "GB", "to_unit": "MB", "quantity": "data"}' --output=raw)
echo "1 GB = ${BYTES} MB"

# ============================================================
# 9. PRZETWARZANIE PLIKÓW
# ============================================================

echo ""
echo "=== 9. PRZETWARZANIE PLIKÓW ==="

# Pobierz listę plików
list_files() {
    local path=$1
    $CORESKILL file_manager list "{\"path\": \"$path\"}" --output=raw
}

# Sprawdź duplikaty
find_duplicates() {
    local path=$1
    $CORESKILL document_search find_duplicates "{\"path\": \"$path\"}" --output=json
}

# ============================================================
# 10. ALIASY I SKRÓTY
# ============================================================

echo ""
echo "=== 10. REKOMENDOWANE ALIASY ==="

# Dodaj do ~/.bashrc lub ~/.zshrc:
cat << 'EOF'

# CoreSkill aliases
alias cs='$CORESKILL'
alias cs-calc='$CORESKILL calculator_advanced calculate --output=raw'
alias cs-ping='$CORESKILL network_tools ping --output=raw'
alias cs-pass='$CORESKILL account_creator generate_password --output=raw'
alias cs-find='$CORESKILL document_search search_by_name --output=raw'
alias cs-prompt='$CORESKILL prompt --output=raw'

# Przykłady użycia aliasów:
# cs-calc '{"expression": "2^10"}'
# cs-ping '{"host": "google.com"}'
# cs-pass '{"length": 20}'
# cs-find '{"path": "/tmp", "pattern": "*.pdf"}'
# cs-prompt "calculate 15% of 200"

EOF

# ============================================================
# PODSUMOWANIE
# ============================================================

echo ""
echo "=== PODSUMOWANIE ==="
echo "Najważniejsze komendy:"
echo ""
echo "  CZYSTE DANE:"
echo "    coreskill <skill> <action> <json> --output=raw"
echo ""
echo "  JSON DLA PRZETWARZANIA:"
echo "    coreskill <skill> <action> <json> --output=json"
echo ""
echo "  NATURALNY JEZYK:"
echo "    coreskill prompt 'znajdz pliki pdf w /tmp'"
echo ""
echo "  PIPE:"
echo "    echo '{...}' | coreskill pipe <skill> <action>"
echo ""
echo "  ALIAS:"
echo "    alias cs='coreskill'"
echo ""
