"""
settings.py — Central configuration for the FastAPI backend.

Replaces the Streamlit-coupled config.py. All secrets are read from environment
variables (local: backend/.env; production: host env / Secret Manager). No secret
is ever hardcoded, committed, or sent to the browser.
"""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # Core
    environment: str = "development"
    frontend_origin: str = "http://localhost:5173"
    session_secret: str = "change-me"

    # Local dev only: when true, skip Google OAuth and act as a seeded dev admin.
    # Never enable in production (guarded in sessions.get_current_user).
    dev_auth_bypass: bool = False
    # Identity assumed when dev_auth_bypass is on.
    dev_user_email: str = "omkar.rakshe@schbang.com"

    # Comma-separated allowlist of emails that are ALWAYS admin + active, in both
    # dev-bypass and real OAuth login. Guarantees these accounts never lose access.
    admin_emails: str = "omkar.rakshe@schbang.com"

    # Encryption (Tier-1)
    credential_encryption_key: str = ""

    # Database — local dev defaults to SQLite (no external DB needed).
    # Production overrides with a Postgres URL.
    database_url: str = "sqlite:///./growth_analyst_dev.db"

    # Google OAuth login gate
    auth_allowed_domain: str = "schbang.com"
    auth_google_client_id: str | None = None
    auth_google_client_secret: str | None = None
    auth_redirect_uri: str = "http://localhost:8000/auth/callback"

    # AI engines
    gemini_api_key: str | None = None
    xai_api_key: str | None = None

    # Optional data sources
    google_pagespeed_api_key: str | None = None
    clarity_api_token: str | None = None

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    def auth_configured(self) -> bool:
        return bool(self.auth_google_client_id and self.auth_google_client_secret)

    def admin_email_set(self) -> set[str]:
        return {e.strip().lower() for e in self.admin_emails.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()
