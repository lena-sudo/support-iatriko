#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
    set -a
    . ./.env
    set +a
fi

if [ ! -d ".venv" ]; then
    python3 -m venv .venv
    .venv/bin/pip install --upgrade pip
    .venv/bin/pip install -r requirements.txt
fi

exec .venv/bin/streamlit run app.py --server.port 8510 --server.headless true
