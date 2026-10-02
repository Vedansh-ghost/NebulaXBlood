# NEBULAxBLOOD v2.0.0

## What changed
- Production-oriented Docker Compose stack with Core, Agent, PostgreSQL, Redis and Caddy.
- One-command VPS installer with generated secrets, systemd service and automatic HTTPS through Caddy.
- SQLAlchemy database layer supporting PostgreSQL and SQLite development mode.
- Agent authentication with per-node tokens and heartbeat.
- Persistent provisioning job queue.
- Docker-based game-server provisioning foundation through the Nebula Agent.
- Signed payment webhook endpoint.
- Update and database-backup scripts.
- Same-origin Panel/Admin API configuration for domain deployments.
- Versioned Core API (`2.0.0`).

## Still adapter/foundation work
- VPS virtualization requires a dedicated libvirt/VM adapter and OS-image/network implementation.
- DNS automation requires a DNS-provider integration (for example Cloudflare API credentials).
- Production payment gateways require provider-specific credentials and webhook configuration.
- Authentication/UI permissions need a full customer identity system before public multi-tenant use.

## Install
```bash
sudo ./installer/install.sh
```

## Update
```bash
sudo ./update.sh
```

## Backup
```bash
sudo ./backup.sh
```
