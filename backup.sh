#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }
mkdir -p "$ROOT/backups"
STAMP=$(date +%Y%m%d-%H%M%S)
cd "$ROOT/docker"
docker compose --env-file ../.env exec -T postgres pg_dump -U "$(grep '^POSTGRES_USER=' ../.env | cut -d= -f2)" "$(grep '^POSTGRES_DB=' ../.env | cut -d= -f2)" > "$ROOT/backups/nebula-$STAMP.sql"
echo "Backup: $ROOT/backups/nebula-$STAMP.sql"
