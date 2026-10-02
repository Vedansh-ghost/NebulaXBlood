# NEBULAxBLOOD v2.0.0

Self-hostable Nebula hosting platform foundation built from the existing Nebula website.

## v2.0 includes
- Existing Nebula public website pages
- Customer Panel + Admin Panel
- Nebula Core API 2.0
- PostgreSQL database with SQLAlchemy
- Redis service for future/background workloads
- Authenticated Nebula Agent and node heartbeat
- Persistent provisioning job queue
- Docker-based game-server provisioning foundation
- VPS provisioning job contract / adapter boundary
- Signed payment webhook endpoint
- Caddy reverse proxy + automatic HTTPS
- One-command Debian/Ubuntu installer
- systemd service management
- Update + database backup scripts
- Same-origin production panel/API routing

## One-command installation
From a fresh Debian/Ubuntu VPS:

```bash
curl -fsSL https://YOUR-DOMAIN/install.sh | sudo bash
```

For the Git checkout/development release, run:

```bash
sudo ./installer/install.sh
```

The installer asks for the panel domain, installs Docker, creates PostgreSQL/Redis, generates secrets, starts Core/Agent/Caddy, and prints the admin token.

## DNS
Create an A/AAAA record for the panel domain pointing to the VPS before HTTPS is issued.
For game-server hostnames, a DNS wildcard such as `*.servers.example.com` can be used; automatic DNS-provider integration is a separate adapter.

## Update / backup
```bash
sudo ./update.sh
sudo ./backup.sh
```

## Development
```bash
./dev.sh
```
Then open `http://127.0.0.1:8000/docs`.

## v2.0 scope note
This is a major foundation release, not a claim that every future hosting feature is complete. VPS virtualization, provider-specific payment gateways, automatic DNS provider APIs, full customer identity/authentication, and advanced backups are deliberately kept behind adapters/future implementation work.
