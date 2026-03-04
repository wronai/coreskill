#!/usr/bin/env bash
# ============================================================================
# CoreSkill Desktop Launcher
# ============================================================================
# Tries in order:
#   1. Chrome/Chromium --app mode (zero install, fastest)
#   2. Electron (if installed)
#   3. xdg-open / open (system browser fallback)
# ============================================================================

set -euo pipefail

URL="${CORESKILL_URL:-http://localhost:3000}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.chat.yml"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()  { echo -e "${BLUE}[CoreSkill]${NC} $*"; }
ok()   { echo -e "${GREEN}[CoreSkill]${NC} $*"; }
warn() { echo -e "${YELLOW}[CoreSkill]${NC} $*"; }
err()  { echo -e "${RED}[CoreSkill]${NC} $*"; }

# --- Ensure Docker services are running ---
ensure_docker() {
    if ! command -v docker &>/dev/null; then
        err "Docker not found. Install: https://docs.docker.com/get-docker/"
        exit 1
    fi

    # Check if backend is healthy
    if curl -sf "$URL/health" &>/dev/null 2>&1; then
        ok "Backend already running at $URL"
        return 0
    fi

    log "Starting Docker services..."
    docker compose -f "$COMPOSE_FILE" up -d --build

    # Wait for backend health
    log "Waiting for backend..."
    for i in $(seq 1 30); do
        if curl -sf "http://localhost:8000/health" &>/dev/null 2>&1; then
            ok "Backend ready!"
            return 0
        fi
        sleep 2
    done

    warn "Backend may still be starting. Opening anyway..."
}

# --- Find Chrome/Chromium ---
find_chrome() {
    local candidates=(
        "google-chrome-stable"
        "google-chrome"
        "chromium-browser"
        "chromium"
        "/usr/bin/google-chrome-stable"
        "/usr/bin/chromium-browser"
        "/snap/bin/chromium"
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
        "/Applications/Chromium.app/Contents/MacOS/Chromium"
    )

    for cmd in "${candidates[@]}"; do
        if command -v "$cmd" &>/dev/null 2>&1 || [ -x "$cmd" ]; then
            echo "$cmd"
            return 0
        fi
    done
    return 1
}

# --- Launch as desktop app ---
launch() {
    ensure_docker

    # Try 1: Chrome --app mode
    local chrome
    if chrome=$(find_chrome); then
        ok "Opening as desktop app (Chrome --app mode)..."
        "$chrome" \
            --app="$URL" \
            --window-size=1024,768 \
            --class=CoreSkill \
            --user-data-dir="/tmp/coreskill-chrome-profile" \
            &>/dev/null &
        disown
        return 0
    fi

    # Try 2: Electron
    if [ -d "$SCRIPT_DIR/electron-app" ] && command -v npx &>/dev/null; then
        ok "Opening as desktop app (Electron)..."
        cd "$SCRIPT_DIR/electron-app"
        npx electron . &>/dev/null &
        disown
        return 0
    fi

    # Try 3: System browser fallback
    warn "Chrome not found. Opening in default browser..."
    if command -v xdg-open &>/dev/null; then
        xdg-open "$URL"
    elif command -v open &>/dev/null; then
        open "$URL"
    else
        err "Cannot open browser. Navigate to: $URL"
    fi
}

launch
