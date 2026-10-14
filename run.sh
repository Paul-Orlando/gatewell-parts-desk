#!/usr/bin/env bash
# Start the Gatewell Parts Desk on http://localhost:8000
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
if [ -f .env ]; then set -a; . ./.env; set +a; fi
echo "Gatewell Parts Desk: http://localhost:8000"
exec .venv/bin/python -m uvicorn app.server:app --port "${PORT:-8000}"
