# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ZabbixScreen is a lightweight Zabbix monitoring dashboard display system. Single-container deployment (Nginx + FastAPI + SQLite), optimized for operations center big-screen display. This is a **greenfield project** — the detailed design document is [项目设计方案-ZabbixScreen-v1.1.md](项目设计方案-ZabbixScreen-v1.1.md), which is the authoritative reference for all architecture, API, and database decisions.

**Core principle**: Do less, do it well. Focus on Zabbix-only data, big-screen visualization, and a Webhook alert export for external AI engines. No Prometheus, no AI built-in, no multi-channel notifications.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Vue 3.4+ + Vite 5+ + TypeScript (strict), Element Plus 2.x, ECharts 5.4+, Pinia 2.x |
| Backend | Python 3.11+ + FastAPI 0.110+, uvicorn, SQLAlchemy 2.0 + aiosqlite, APScheduler 3.x |
| Database | SQLite with **WAL mode** (file: `/app/data/zabbixscreen.db`) |
| Deployment | Single Docker container (Nginx :80 → FastAPI :5001), multi-arch (linux/amd64, linux/arm64) |
| Auth | JWT (access_token 30min, refresh_token 7d), bcrypt for user passwords, AES-128-CBC for Zabbix credentials |

## Development Commands

### Backend

```bash
cd backend
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python ../scripts/init_db.py                       # Initialize SQLite database + default data
uvicorn main:app --reload --host 0.0.0.0 --port 5001
# Swagger docs at http://localhost:5001/docs
```

### Frontend

```bash
cd frontend
npm install
npm run dev                        # Vite dev server at http://localhost:5173, proxies /api → :5001
npm run build                      # Production build to dist/
```

### Docker (local dev)

```bash
docker-compose -f docker-compose.dev.yml up --build   # http://localhost:8088
```

### Docker (multi-arch production build)

```bash
docker buildx create --name multiarch-builder --use
docker buildx build --platform linux/amd64,linux/arm64 --tag your-registry/zabbixscreen:latest --push .
```

## Architecture

### Backend Layering (strict 3-layer)

```
api/       → Route handlers only: validate request, call service, format response. Never contains business logic.
services/  → All business logic: Zabbix API client, data aggregation, alert engine, webhook sender, scheduler.
models/    → SQLAlchemy ORM models only.
utils/     → Cross-cutting: JWT helpers, in-memory TTL cache.
```

**Key service modules**:
- `zabbix_client.py` — Zabbix API wrapper (login, host/item/history/trigger queries). Manages Zabbix auth token caching (TTL 3600s), auto re-login on failure. Compatible with Zabbix 5.x/6.x/7.x API differences.
- `data_aggregator.py` — Merges data from multiple Zabbix sources, computes TOP N rankings, status counts. Results cached in memory (TTL = refresh interval).
- `alert_engine.py` — Polls Zabbix triggers every 60s, matches against alert rules, writes alert_records.
- `webhook_sender.py` — Builds standardized JSON payload (v1.0 schema), POSTs to configured endpoints, exponential backoff retry (10s→20s→40s, max 3 retries), logs all attempts.
- `scheduler.py` — APScheduler jobs: data aggregation (every 30s), alert detection (every 60s), data cleanup (daily 03:00).

### Frontend Architecture

Standard Vue 3 SPA: `views/` → `components/` → `stores/` (Pinia) → `api/` (Axios layer).
- All API calls go through `src/api/` modules — never use Axios directly in components.
- `src/api/request.ts` — Axios instance with 401 interceptor (auto-redirect to /login).
- `src/utils/format.ts` — Unit formatting (bytes→GB, Hz→GHz, etc.)
- `src/utils/zabbix.ts` — Zabbix item key → Chinese name/unit mapping.

### Container Architecture

Single container runs two processes via **supervisor**:
- Nginx :80 — serves Vue static files + reverse proxies `/api/*` to uvicorn
- uvicorn :5001 (internal only) — FastAPI with 1 worker

This approach is chosen over multi-container for simplicity — the app is lightweight enough that process separation within one container is sufficient.

### API Response Convention

All endpoints use `/api/v1/` prefix. Unified response:
```json
{ "code": 0, "message": "success", "data": {} }
```

Business error codes: `1001` param error, `1002` unauthorized, `1003` not found, `2001` Zabbix connection failed, `2002` Zabbix API error, `3001` Webhook push failed.

HTTP status codes map to error type (not business logic): 200 (success, even if Zabbix call failed), 400 (client error), 401 (auth), 403 (forbidden), 404 (not found), 500 (server error).

## Database

SQLite with these **required PRAGMAs** (set in `database.py` on startup):
```python
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = 10000;
PRAGMA foreign_keys = ON;
```

WAL mode is critical — it allows concurrent reads during writes, which is necessary since the scheduler writes while the API reads.

**Password storage**: Zabbix data source passwords → AES-128-CBC encrypted (key from `APP_SECRET_KEY`). User passwords → bcrypt.

## Key Design Decisions

- **SQLite over PostgreSQL/MySQL**: Single-node deployment, no external DB service needed. WAL mode handles the concurrency needs.
- **Single container over microservices**: The app's scale doesn't justify multi-container complexity. Supervisor manages the two processes.
- **Webhook-only alert output**: No built-in WeChat/DingTalk/Feishu integration. External systems consume the standardized JSON webhook. This keeps the core focused on visualization.
- **No AI built-in**: The webhook JSON schema includes `context` with recent metric data so external AI engines can analyze without calling back.
- **Multi-arch builds**: Target users run on ARM64 servers (Kunpeng/Phytium CPUs) as well as x86_64.
- **Zabbix version compatibility**: 5.x uses `user.login`, 7.x adds `user.checkAuthentication` — the client module must handle both.

## P1 Milestone Scope (current phase)

The P1 deliverable is a working minimal product:
1. Project scaffolding (Vue3+Vite, FastAPI, Docker multi-arch config)
2. Zabbix datasource CRUD + connection test (password encrypted)
3. Default monitoring dashboard (host status cards, stats, TOP N charts, auto-refresh 30s)
4. Host list + host detail + history trend charts (CPU/memory/disk/network, time ranges 1h–30d)
5. JWT login/refresh/password change + route guards
6. Alert rules + alert records + alert statistics
7. Webhook endpoint config + standardized push (with context data) + retry + push log
8. System settings page
9. Docker multi-arch image build + docker-compose production config

## Essential Zabbix Item Keys (P1)

| Metric | Item Key | Note |
|--------|----------|------|
| CPU usage | `system.cpu.util[,idle]` | Usage = 100 - idle value |
| Memory usage | `vm.memory.size[pused]` | Percentage used |
| Disk usage | `vfs.fs.size[{-mounted point},pused]` | Per-mountpoint |
| Network in | `net.if.in[{interface},bps]` | Auto-detect interface (prefer eth0) |
| Network out | `net.if.out[{interface},bps]` | Auto-detect interface (prefer eth0) |

Historical queries: use `zabbix.history.get()` for ≤1 day, `zabbix.trend.get()` for >1 day (Zabbix best practice).

## Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `APP_SECRET_KEY` | **Yes** | — | JWT signing + AES password encryption. Must be changed in production. |
| `DEFAULT_REFRESH_INTERVAL` | No | 30 | Dashboard polling interval (seconds) |
| `ALERT_CHECK_INTERVAL` | No | 60 | Alert detection interval (seconds) |
| `DATA_RETENTION_DAYS` | No | 30 | Auto-cleanup threshold for alert_records and webhook_logs |
| `DEFAULT_ADMIN_PASSWORD` | No | admin123 | Initial admin password (change after first login) |
| `TZ` | No | Asia/Shanghai | Timezone |
| `DEBUG` | No | false | FastAPI debug mode (use in development only) |

## Visual Theme

Dashboard colors (from design spec):
- Background: `#0d1b2e` (deep blue)
- Card background: `#1a2a4a`
- Primary/accent: `#00d4ff` (tech blue)
- Target resolution: 1920×1080, responsive with `vw/vh` + `calc()`

## Important Constraints

- **HTTP methods**: All API endpoints use only GET/POST. PUT/DELETE are intentionally avoided to bypass security device (WAF) blocking in customer environments. New endpoints must follow this convention — do not introduce PUT or DELETE.
- **APP_SECRET_KEY**: Changing `APP_SECRET_KEY` will invalidate all stored Zabbix datasource passwords (AES-128-CBC key is derived from it). Before changing the key, re-save all datasource credentials through the Web UI, or manually re-encrypt them using `utils/crypto.py` with the new key.
- **scheduler health**: The scheduler runs as an independent process. `/api/v1/scheduler-status` checks monitor_cache freshness; if cache is &gt;90s stale, the scheduler should be investigated even though `/api/v1/health` may still report healthy.
