#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

PROJECT_VENV="$ROOT_DIR/.venv"
HOME_VENV="${SAFEOPS_LINUX_VENV:-$HOME/safeops-venv}"

if [ -f "$PROJECT_VENV/bin/activate" ]; then
  VENV_DIR="$PROJECT_VENV"
  echo "[safeops] using project Linux venv: $VENV_DIR"
elif [ -f "$HOME_VENV/bin/activate" ]; then
  VENV_DIR="$HOME_VENV"
  echo "[safeops] using home Linux venv: $VENV_DIR"
else
  if [ -d "$PROJECT_VENV/Scripts" ] || [ -d "$PROJECT_VENV/Lib" ]; then
    echo "[safeops] project .venv looks like a Windows venv; skipping it on openKylin."
  fi
  VENV_DIR="$HOME_VENV"
  echo "[safeops] creating Linux venv: $VENV_DIR"
  python3 -m venv "$VENV_DIR"
fi

source "$VENV_DIR/bin/activate"
python -m pip install -r backend/requirements.txt

export SAFEOPS_MODE="${SAFEOPS_MODE:-real}"
export BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
export BACKEND_PORT="${BACKEND_PORT:-8010}"

echo "[safeops] backend listen: http://$BACKEND_HOST:$BACKEND_PORT"
python -m uvicorn backend.app.main:app --host "$BACKEND_HOST" --port "$BACKEND_PORT"
