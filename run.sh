#!/bin/bash

# ============================================================
# Performance Dashboard - Run Script
# Sets up the environment and starts the Flask server.
# The server auto-selects a free port and prints its URL below.
# ============================================================

set -e

# ---- Logging helpers ---------------------------------------
log()  { echo "[$(date '+%H:%M:%S')] [INFO]  $1"; }
warn() { echo "[$(date '+%H:%M:%S')] [WARN]  $1"; }
err()  { echo "[$(date '+%H:%M:%S')] [ERROR] $1" >&2; }

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$PROJECT_DIR/venv"

log "Project directory: $PROJECT_DIR"

# ---- Prerequisite checks -----------------------------------
log "Checking prerequisites..."

if ! command -v python3 >/dev/null 2>&1; then
    err "python3 is not installed or not on PATH. Install Python 3.11+ and retry."
    exit 1
fi
log "Found python3: $(python3 --version 2>&1)"

if ! command -v adb >/dev/null 2>&1; then
    warn "adb (Android Debug Bridge) not found on PATH."
    warn "The dashboard needs adb to talk to your device."
    warn "Install it with: brew install android-platform-tools (macOS)"
else
    log "Found adb: $(adb --version 2>&1 | head -n 1)"
    DEVICE_COUNT="$(adb devices | grep -w "device" | grep -v "List of devices" | wc -l | tr -d ' ')"
    if [ "$DEVICE_COUNT" -eq 0 ]; then
        warn "No Android devices detected. Connect a device with USB debugging enabled."
    else
        log "Detected $DEVICE_COUNT connected Android device(s)."
    fi
fi

# ---- Virtual environment -----------------------------------
if [ ! -d "$VENV_PATH" ]; then
    log "No virtual environment found. Creating one at: $VENV_PATH"
    python3 -m venv "$VENV_PATH"
else
    log "Using existing virtual environment: $VENV_PATH"
fi

log "Activating virtual environment..."
# shellcheck disable=SC1091
source "$VENV_PATH/bin/activate"

# ---- Dependencies ------------------------------------------
log "Installing/updating Python dependencies from requirements.txt..."
if pip install -r "$PROJECT_DIR/requirements.txt" > /tmp/perf_dashboard_pip.log 2>&1; then
    log "Dependencies are up to date."
else
    err "Dependency installation failed. See log below:"
    cat /tmp/perf_dashboard_pip.log >&2
    exit 1
fi

# ---- Launch ------------------------------------------------
log "Starting Performance Dashboard server..."
log "The server will pick a free port and print its URL below."
log "Tip: set a fixed port with 'PORT=8080 ./run.sh'."
echo "------------------------------------------------------------"
python3 "$PROJECT_DIR/server.py"
