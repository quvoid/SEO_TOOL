"""
seed.py — production database seeder (env-driven, no secrets.toml / no .env writes).

Run ONCE after the backend is deployed and env vars are set, e.g. on Railway:
    python backend/seed.py

Reads everything from environment variables (already set on the host):
  Required:
    CREDENTIAL_ENCRYPTION_KEY   Fernet key (same one the app uses)
    DATABASE_URL                Postgres connection string
    USER_OAUTH_CLIENT_ID        Google OAuth client id  (the Gmail data source)
    USER_OAUTH_CLIENT_SECRET    Google OAuth client secret
    USER_OAUTH_REFRESH_TOKEN    Google OAuth refresh token
    CLIENTS_JSON                JSON string: {"clients": { "<name>": {..} }}
  Optional:
    OWNER_EMAIL                 admin/owner email (default omkar.rakshe@schbang.com)
    CREDENTIAL_LABEL            label for the credential (default "primary gmail")

Idempotent: replaces the owner's existing credentials/clients each run.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.db import Base, SessionLocal, engine  # noqa: E402
from app.models import Client, Credential, CredentialKind, Role, User  # noqa: E402
from app.security.crypto import encrypt_json, encrypt_str  # noqa: E402

OWNER = os.environ.get("OWNER_EMAIL", "omkar.rakshe@schbang.com").lower()


def _require(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"ERROR: env var {name} is required")
    return v


def _load_clients() -> dict:
    raw = os.environ.get("CLIENTS_JSON")
    if raw:
        return json.loads(raw).get("clients", {})
    # Fallback: clients.json in repo root (usually gitignored, so rarely present)
    f = BACKEND_DIR.parent / "clients.json"
    if f.exists():
        return json.loads(f.read_text(encoding="utf-8")).get("clients", {})
    print("WARN: no CLIENTS_JSON env and no clients.json — seeding zero clients")
    return {}


def main() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == OWNER).one_or_none()
        if user is None:
            user = User(email=OWNER, name=OWNER.split("@")[0].replace(".", " ").title(),
                        role=Role.admin, is_active=True)
            db.add(user); db.commit(); db.refresh(user)
        else:
            user.role = Role.admin; user.is_active = True; db.commit()

        # Clean prior seeded rows for a tidy re-run
        db.query(Client).filter(Client.owner_user_id == user.id).delete()
        db.query(Credential).filter(Credential.owner_user_id == user.id).delete()
        db.commit()

        cred = Credential(
            label=os.environ.get("CREDENTIAL_LABEL", "primary gmail"),
            kind=CredentialKind.user_oauth,
            blob_enc=encrypt_json({
                "client_id": _require("USER_OAUTH_CLIENT_ID"),
                "client_secret": _require("USER_OAUTH_CLIENT_SECRET"),
                "refresh_token": _require("USER_OAUTH_REFRESH_TOKEN"),
            }),
            owner_user_id=user.id,
        )
        db.add(cred); db.commit(); db.refresh(cred)

        n = 0
        for name, cfg in _load_clients().items():
            is_demo = bool(cfg.get("use_demo_data"))
            db.add(Client(
                display_name=name,
                ga4_property_id_enc=encrypt_str(cfg.get("ga4_property_id", "")) if cfg.get("ga4_property_id") else "",
                gsc_site_url=cfg.get("gsc_site_url", ""),
                organic_only=cfg.get("organic_only", True),
                use_demo_data=is_demo,
                credential_id=None if is_demo else cred.id,
                owner_user_id=user.id,
            ))
            n += 1
        db.commit()
        print(f"[ok] seeded owner={OWNER}, 1 credential, {n} clients")
    finally:
        db.close()


if __name__ == "__main__":
    main()
