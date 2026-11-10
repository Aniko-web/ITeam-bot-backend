#!/usr/bin/env bash
set -e

# Alwaysdata FastAPI launcher script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if present
if [ -f "$SCRIPT_DIR/.venv/bin/activate" ]; then
    source "$SCRIPT_DIR/.venv/bin/activate"
elif [ -f "$SCRIPT_DIR/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/venv/bin/activate"
fi

# Alwaysdata sets $IP and $PORT. Fallback if running manually
HOST_IP="${IP:-0.0.0.0}"
HOST_PORT="${PORT:-8000}"

echo "Starting ITeam FastAPI backend on $HOST_IP:$HOST_PORT..."
exec python3 -m uvicorn app.main:app --host "$HOST_IP" --port "$HOST_PORT"
