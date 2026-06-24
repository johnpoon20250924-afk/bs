#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

export SAFEOPS_MODE="${SAFEOPS_MODE:-auto}"
exec python3 -m backend.app.mcp_server --transport sse
