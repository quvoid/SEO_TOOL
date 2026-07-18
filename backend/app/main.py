"""
main.py — FastAPI application entrypoint.

Run locally:
    cd backend
    uvicorn app.main:app --reload --port 8000

Production (Railway/Render):
    gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 0.0.0.0:$PORT
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from .db import Base, engine
from .routers import admin, auth, clients, health, onpage, reports
from .settings import get_settings

_settings = get_settings()

app = FastAPI(title="AI Growth Analyst API", version="0.1.0")

# Starlette session middleware — required by Authlib's OAuth state handling.
app.add_middleware(SessionMiddleware, secret_key=_settings.session_secret, same_site="lax",
                   https_only=_settings.is_production)

# CORS — only the known frontend origin, with credentials (cookies) allowed.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[_settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(auth.router)
app.include_router(clients.router)
app.include_router(reports.router)
app.include_router(onpage.router)
app.include_router(admin.router)


@app.on_event("startup")
def _startup() -> None:
    # Create tables if they don't exist. Idempotent and safe to run every boot.
    # (Once the schema stabilises, switch to Alembic migrations — see README.)
    Base.metadata.create_all(bind=engine)

    # Optional one-time boot seeding for hosts without a shell (Render free tier).
    if _settings.seed_on_startup:
        try:
            import seed  # backend/seed.py is on sys.path (app runs from backend/)
            print("[startup] seed_on_startup:", seed.seed_database(only_if_empty=True))
        except Exception as exc:  # noqa: BLE001 — never let seeding crash boot
            print(f"[startup] seed skipped: {exc}")
