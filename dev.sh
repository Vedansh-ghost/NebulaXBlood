#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -r "$ROOT/nebula-core/requirements.txt"
DATABASE_URL="sqlite:///$ROOT/nebula-core/nebula.db" "$ROOT/.venv/bin/uvicorn" main:app --app-dir "$ROOT/nebula-core" --host 127.0.0.1 --port 8000
