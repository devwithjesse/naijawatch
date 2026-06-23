NaijaWatch — Backend
====================

This directory contains the FastAPI backend, database models, services, and utility scripts.

Quick start (local)

1. Create a virtual environment and install dependencies

   python -m venv .venv
   source .venv/bin/activate   # Windows: .venv\Scripts\Activate.ps1 (PowerShell)
   pip install -r requirements.txt

2. Run the dev server

   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

3. Health check

   GET http://localhost:8000/api/health

Environment variables

- DATABASE_URL: SQLAlchemy database URL. Default in development: sqlite:///./naijawatch.db
- GROQ_API_KEY: LLM API key (optional for local testing)
- ORS_API_KEY: OpenRouteService API key (optional)
- SMTP_USER, SMTP_PASSWORD: SMTP credentials for mailer
- APP_BASE_URL: public base URL for confirmation links (default: http://localhost:8000)

Scripts

- utils/cloud_transfer.py
  - Migrate your development SQLite DB into a Postgres (Neon) database.
  - Usage: python backend/utils/cloud_transfer.py --sqlite backend/naijawatch.db --pg "$DATABASE_URL" [--commit]

Running cron wrappers manually

- Mailer: python -m app.cron.mailer
- Retrieve: python -m app.cron.retrieve
- Process: python -m app.cron.process --limit 100

Notes

- For production, use a managed Postgres. Set DATABASE_URL accordingly and do not use SQLite in production.
- The repository contains wrapper scripts in app/cron/; these are the entrypoints you should call from scheduled runners.
