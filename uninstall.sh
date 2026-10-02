#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }
cd "$ROOT/docker"
docker compose --env-file ../.env down || true
systemctl disable --now nebulaxblood.service 2>/dev/null || true
rm -f /etc/systemd/system/nebulaxblood.service
systemctl daemon-reload
echo "Nebula services stopped. Persistent Docker volumes and .env were retained. Remove them manually only if you are sure you want to delete data."
