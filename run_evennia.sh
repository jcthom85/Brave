#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GAME_DIR="$ROOT_DIR/brave_game"
VENV_BIN="$ROOT_DIR/.venv/bin"

export PATH="$VENV_BIN:$PATH"

cd "$GAME_DIR"
exec "$VENV_BIN/evennia" "$@"
