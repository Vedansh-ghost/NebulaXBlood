#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
[[ $EUID -eq 0 ]] || { echo "Run as root."; exit 1; }
cd "$ROOT"
[[ -f .env ]] || { echo "No Nebula installation found."; exit 1; }
cp .env ".env.backup.$(date +%Y%m%d-%H%M%S)"
rm -rf "$ROOT/public"/*
cp -a "$ROOT"/*.html "$ROOT"/*.css "$ROOT"/*.js "$ROOT"/assets "$ROOT"/panel "$ROOT"/admin "$ROOT"/public/ 2>/dev/null || true
cd docker
docker compose --env-file ../.env up -d --build
echo "Nebula updated."
