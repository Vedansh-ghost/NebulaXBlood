#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
command -v python3 >/dev/null || { echo "Python 3 is required"; exit 1; }
python3 -m venv "$ROOT/.venv"
"$ROOT/.venv/bin/pip" install -r "$ROOT/nebula-core/requirements.txt"
echo "Nebula installed locally. Start core with: $ROOT/.venv/bin/uvicorn main:app --app-dir $ROOT/nebula-core --host 0.0.0.0 --port 8000"
