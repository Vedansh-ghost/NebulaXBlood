#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
[[ $EUID -eq 0 ]] || { echo "Run as root: sudo $0"; exit 1; }
command -v apt-get >/dev/null || { echo "This installer currently supports Debian/Ubuntu VPSs."; exit 1; }
apt-get update
apt-get install -y ca-certificates curl git openssl
if ! command -v docker >/dev/null; then
  curl -fsSL https://get.docker.com | sh
fi
systemctl enable --now docker
read -rp "Nebula panel domain (e.g. panel.example.com): " DOMAIN
[[ -n "$DOMAIN" ]] || { echo "Domain is required."; exit 1; }
read -rp "PostgreSQL database name [nebula]: " DB_NAME; DB_NAME=${DB_NAME:-nebula}
read -rp "PostgreSQL user [nebula]: " DB_USER; DB_USER=${DB_USER:-nebula}
DB_PASS="$(openssl rand -hex 24)"
ADMIN_TOKEN="$(openssl rand -hex 32)"
WEBHOOK_SECRET="$(openssl rand -hex 32)"
mkdir -p "$ROOT/data" "$ROOT/public"
rm -rf "$ROOT/public"/*
cp -a "$ROOT"/*.html "$ROOT"/*.css "$ROOT"/*.js "$ROOT"/assets "$ROOT"/panel "$ROOT"/admin "$ROOT"/public/ 2>/dev/null || true
cat > "$ROOT/.env" <<ENV
NEBULA_DOMAIN=$DOMAIN
POSTGRES_DB=$DB_NAME
POSTGRES_USER=$DB_USER
POSTGRES_PASSWORD=$DB_PASS
DATABASE_URL=postgresql+psycopg://$DB_USER:$DB_PASS@postgres:5432/$DB_NAME
NEBULA_ADMIN_TOKEN=$ADMIN_TOKEN
PAYMENT_WEBHOOK_SECRET=$WEBHOOK_SECRET
NEBULA_NODE_NAME=local-node
NEBULA_AGENT_TOKEN=$ADMIN_TOKEN
NEBULA_DEFAULT_GAME_IMAGE=itzg/minecraft-server
NEBULA_DEFAULT_MEMORY=1g
NEBULA_SERVER_DOMAIN=$DOMAIN
ENV
chmod 600 "$ROOT/.env"
cd "$ROOT/docker"
docker compose --env-file ../.env up -d --build
cat >/etc/systemd/system/nebulaxblood.service <<UNIT
[Unit]
Description=NEBULAxBLOOD v2
After=docker.service
Requires=docker.service
[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=$ROOT/docker
ExecStart=/usr/bin/docker compose --env-file ../.env up -d
ExecStop=/usr/bin/docker compose --env-file ../.env down
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now nebulaxblood.service
printf '\nNEBULAxBLOOD v2 installed.\nPanel: https://%s\nAdmin token: %s\n\nCreate a DNS A/AAAA record for %s pointing to this VPS before/while Caddy obtains HTTPS.\nFor customer server hostnames, use a wildcard such as *.servers.%s if your DNS provider supports it.\n\nKeep the admin token private.\n' "$DOMAIN" "$ADMIN_TOKEN" "$DOMAIN" "$DOMAIN"
