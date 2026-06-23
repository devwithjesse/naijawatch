NaijaWatch — Intelligence System
================================
Visit at https://naijawatch-frontend.onrender.com

NaijaWatch converts security-focused news articles into structured event intelligence for visualization and travel risk summaries across Nigeria.

This README covers repository layout, local development, production readiness, database migration, cron jobs, caching, and deployment notes for the chosen stack (Cloud Run, Netlify, Neon, GitHub Actions).

Table of contents
- Project overview
- Repo layout
- Quick start (dev)
- Environment variables (backend)
- Database migration (SQLite → Neon)
- Cron jobs & GitHub Actions
- Caching strategy
- Deployment summary (Cloud Run + Netlify + Neon)
- Testing mailer & preview
- Troubleshooting & runbook

Project overview
----------------
- Backend: FastAPI, SQLAlchemy; collects RSS, runs LLM extraction, geocoding, travel risk engine.
- Frontend: React (Vite + TanStack) — SPA that consumes the backend API.
- Dev DB: SQLite (local); Prod DB: Neon (Postgres)
- Cron: GitHub Actions scheduled workflows run the retrieval, processing, and mailer wrappers.
- Cache: Redis (Upstash or Google Memorystore) used for travel routes, map payloads, and risk ranking caches.

Repo layout (important files)
- NaijaWatch/
  - backend/
    - app/ (FastAPI project)
      - main.py (FastAPI entrypoint)
      - core/ (config, scheduler)
      - routers/ (events, news, stats, travel, digest)
      - services/ (pipeline, extractor, travel_engine, risk_engine, geocoder, llm)
      - cron/ (wrappers: retrieve.py, process.py, mailer.py)
      - templates/ (email templates)
    - scripts/
      - sqlite_to_neon.py  -- migration helper (dry-run by default)
      - render_digest_preview.py -- render email preview locally
    - requirements.txt
  - frontend/
    - src/ (React app)
    - public/ (static assets, logo, favicons)
  - .github/workflows/ (CI + scheduled cron workflows)

Quick start (local)
-------------------
Prereqs
- Python 3.11+ (backend)
- Node 18+ and npm (frontend)
- Redis (optional local) if you want to test caching (or set REDIS_URL to Upstash)

Backend (dev)
1. cd NaijaWatch/backend
2. python -m venv .venv
3. source .venv/bin/activate  # Windows: .venv\Scripts\Activate.ps1
4. pip install -r requirements.txt
5. Set env (example):
   export DATABASE_URL="sqlite:///./naijawatch.db"
   export APP_BASE_URL="http://localhost:5173"
   # optional: REDIS_URL, SMTP_USER, SMTP_PASSWORD, GROQ_API_KEY, ORS_API_KEY
6. Run:
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
7. Health:
   curl http://localhost:8000/api/health

Frontend (dev)
1. cd NaijaWatch/frontend
2. bun install
3. Set VITE_API_BASE to your backend (local dev):
   export VITE_API_BASE="http://localhost:8000"  # for Linux/macOS
4. Run dev server:
   bun run dev
5. Open the URL printed by Vite (usually http://localhost:5173)

Environment variables (backend)
-------------------------------
- DATABASE_URL: SQLAlchemy DB URL (sqlite:///./naijawatch.db or Postgres URL)
- REDIS_URL: redis/redis+tls URL (Upstash or Memorystore)
- GROQ_API_KEY: LLM API key
- ORS_API_KEY: OpenRouteService API key
- SMTP_USER, SMTP_PASSWORD: SMTP credentials (or set EMAIL_API_KEY for HTTP mail provider)
- APP_BASE_URL: Public frontend base URL (used in email links)
- FROM_EMAIL: Sender address for digest

Database migration: SQLite → Neon (safe flow)
--------------------------------------------
We provide a migration helper script: backend/utils/cloud_transfer.py
- Dry-run (no writes):
  python backend/utils/cloud_transfer.py --sqlite backend/naijawatch.db --pg "$DATABASE_URL"
- Commit (write to Postgres):
  python backend/utils/cloud_transfer.py --sqlite backend/naijawatch.db --pg "$DATABASE_URL" --commit

Recommended steps before commit
1. Take test snapshot / create a staging DB.
2. Run dry-run and inspect counts.
3. Fix any orphaned references in SQLite.
4. Run commit on a test DB; verify row counts and sequences.
5. Run commit on production only after backup.

Cron jobs & GitHub Actions
--------------------------
Wrappers in app/cron/ and scheduled GitHub workflows:
- retrieve.yml: runs daily (collector + import)
- process.yml: runs every 12 hours (LLM extraction worker)
- mailer.yml: runs weekly (snapshot + send digest)

Secrets to add in GitHub (Settings → Secrets → Actions)
- DATABASE_URL
- REDIS_URL
- GROQ_API_KEY
- ORS_API_KEY
- SMTP_USER
- SMTP_PASSWORD
- APP_BASE_URL
- FROM_EMAIL

Caching strategy (what’s cached)
- Travel route states (route_states:<coords>) — TTL 24h
- Events / map payload (events_map:days=...:state=...) — TTL 5m
- State rankings (state_rankings:days=...) — TTL 1h
- National risk (national_risk:days=...) — TTL 15m (configurable)

Hosting & deployment summary
----------------------------
- Frontend: Netlify — build & deploy the static Vite app. Set VITE_API_BASE in Netlify site envs.
- Backend: Google Cloud Run — containerized FastAPI. Use Cloud Run env vars for DATABASE_URL, REDIS_URL, and API keys.
- DB: Neon Postgres — production DB. Use migration script to import dev data.
- Cache: Upstash (or Google Memorystore) — set REDIS_URL.
- Cron: GitHub Actions scheduled workflows to run wrappers and perform jobs.

Mailer & testing
----------------
- Template: backend/app/templates/digest_weekly.html (Jinja). Preview locally:
  python backend/utils/render_digest_preview.py --out /tmp/digest_preview.html
- Send test mail via mailer wrapper:
  python -m app.cron.mailer
- Use Mailtrap or a test SMTP provider while testing GitHub Actions

Troubleshooting notes & runbook
------------------------------
- If health shows DB error: ensure DATABASE_URL is set and reachable. Test with psql or the sqlite_to_neon tools.
- If Upstash keys aren’t populating: check REDIS_URL, try redis-cli to test PING.
- If migration fails due to FK errors: fix orphans in SQLite and re-run dry-run.


