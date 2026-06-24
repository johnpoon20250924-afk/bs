#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

echo "== KylinSafeOps runtime install =="
if ! command -v apt-get >/dev/null 2>&1; then
  echo "This script expects an apt-based Kylin/openKylin environment."
  exit 1
fi

if [ -d /run/ostree-booted ] || command -v ostree-pkgs-guard >/dev/null 2>&1; then
  cat <<'MSG'
This openKylin environment appears to be OSTree/Immutable.
Do not assume apt install is allowed here.

Recommended flow:
  1. Develop/build on Windows + Codex.
  2. Copy the project/artifacts into openKylin.
  3. Run: bash scripts/kylin_immutable_verify.sh
  4. Use the generated report and screenshots as real system proof.

If you are on a writable Kylin image and still want apt install, set:
  SAFEOPS_ALLOW_APT_INSTALL=true
MSG
  if [ "${SAFEOPS_ALLOW_APT_INSTALL:-false}" != "true" ]; then
    exit 2
  fi
fi

sudo apt-get update
sudo apt-get install -y \
  curl \
  iproute2 \
  lsof \
  procps \
  psmisc \
  python3 \
  python3-pip \
  python3-venv \
  unzip \
  nodejs \
  npm \
  nginx \
  apache2

if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements.txt

cd frontend
npm install
cd "$ROOT_DIR"

export SAFEOPS_MODE=real
bash scripts/check_kylin_compat.sh

echo
echo "Runtime ready."
echo "Backend: SAFEOPS_MODE=real bash scripts/start_backend_kylin.sh"
echo "Frontend: bash scripts/start_frontend_kylin.sh"
