# AI Growth Analyst — Backend (FastAPI)

Secure API that reuses the existing `analysis.py`, `connectors.py`, and
`demo_data.py` from the repo root while replacing Streamlit with a proper
auth'd, multi-account backend.

## Layout
```
backend/
  app/
    main.py            FastAPI entrypoint + middleware
    settings.py        env-based config (replaces Streamlit config.py)
    db.py              SQLAlchemy engine/session
    models.py          users, sessions, credentials, clients, reports, cache
    schemas.py         Pydantic request/response models
    analysis_bridge.py imports the root analysis modules (reused unchanged)
    security/
      crypto.py        Fernet encryption for creds at rest
      sessions.py      server-side sessions + auth dependencies
    services/
      credentials.py   decrypt a brand's Google creds at report time
      reports.py       Streamlit-free port of run_report (10-module pipeline)
    routers/
      health, auth, clients, reports, onpage
```

## Local setup
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                 # then fill in values

# generate the credential encryption key:
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# paste into CREDENTIAL_ENCRYPTION_KEY in .env

uvicorn app.main:app --reload --port 8000
# open http://localhost:8000/docs
```

You need a Postgres database. Fastest options: a local Docker postgres, or a free
Neon/Supabase instance — put its connection string in `DATABASE_URL`.

## Deployment
- **Backend** → Railway or Render (long-running; handles the ~60-90s report jobs).
- **Database** → Neon or Supabase (managed Postgres).
- **Secrets** → host env vars now; move `CREDENTIAL_ENCRYPTION_KEY` and OAuth
  secrets to a Secret Manager for production.
- Set `ENVIRONMENT=production` so cookies become `Secure` and tables are managed
  by Alembic migrations rather than auto-created.

## Migrations (production)
`Base.metadata.create_all` runs only in development. For production:
```bash
alembic init alembic          # one-time
alembic revision --autogenerate -m "init"
alembic upgrade head
```

## Known follow-ups (tracked in ../MIGRATION_PLAN.md)
- Per-client **user-OAuth** (refresh-token) support in connectors — currently
  service-account credentials flow end-to-end; user-OAuth still reads globals.
- Move `api_cache` from SQLite to the Postgres `ApiCache` table.
- Replace `BackgroundTasks` with Celery/RQ + Redis if you need retries/scale.
