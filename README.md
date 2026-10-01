# NEBULAxBLOOD

Self-hostable Nebula platform starter built from the existing static website.

## Included
- Existing Nebula public website pages
- Nebula Core API starter
- Nebula Panel starter
- Nebula Admin starter
- Nebula Agent starter
- Game/VPS plan model
- Order -> provisioning record flow
- PostgreSQL production schema starter
- Docker Compose development stack
- Installer

## Local test
```bash
./installer/install.sh
source .venv/bin/activate
uvicorn nebula-core.main:app --app-dir nebula-core --reload --host 127.0.0.1 --port 8000
```
Open `http://127.0.0.1:8000/docs` for the API and serve the website/panel with any static HTTP server.

## Important
This repository is a foundation/MVP, not a production hosting engine yet. The next implementation stage is secure authentication, a real queue, Docker/VM provisioning, agent authentication, tunnel networking, payments/webhooks, backups, and production PostgreSQL/Redis.
