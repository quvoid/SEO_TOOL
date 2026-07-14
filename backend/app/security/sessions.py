"""
sessions.py — server-side sessions + FastAPI auth dependencies.

Session id is stored in a signed, HttpOnly, Secure, SameSite=Lax cookie. The
browser never sees a bearer token or any credential. The session row lives in
Postgres so it can be revoked server-side (logout / admin kill).
"""
from __future__ import annotations

import datetime as dt

from fastapi import Cookie, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..models import Role, Session as SessionModel, User
from ..settings import get_settings

COOKIE_NAME = "ga_session"
SESSION_TTL = dt.timedelta(hours=12)
_settings = get_settings()

DEV_USER_EMAIL = _settings.dev_user_email


def _get_or_create_dev_user(db: DbSession) -> User:
    """Local-dev identity used only when DEV_AUTH_BYPASS is on."""
    email = DEV_USER_EMAIL.lower()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        name = email.split("@")[0].replace(".", " ").title()
        user = User(email=email, name=name, role=Role.admin, is_active=True)
        db.add(user)
        db.commit()
        db.refresh(user)
    # Always keep allowlisted accounts admin + active.
    if email in _settings.admin_email_set() and (user.role != Role.admin or not user.is_active):
        user.role = Role.admin
        user.is_active = True
        db.commit()
    return user


def create_session(db: DbSession, user: User) -> SessionModel:
    row = SessionModel(
        user_id=user.id,
        expires_at=dt.datetime.now(dt.timezone.utc) + SESSION_TTL,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def revoke_session(db: DbSession, session_id: str) -> None:
    row = db.get(SessionModel, session_id)
    if row:
        row.revoked = True
        db.commit()


def get_current_user(
    ga_session: str | None = Cookie(default=None),
    db: DbSession = Depends(get_db),
) -> User:
    # Local dev only — never honoured in production.
    if _settings.dev_auth_bypass and not _settings.is_production:
        return _get_or_create_dev_user(db)
    if not ga_session:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    row = db.get(SessionModel, ga_session)
    now = dt.datetime.now(dt.timezone.utc)
    if not row or row.revoked or row.expires_at < now:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    user = db.get(User, row.user_id)
    if not user or not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User disabled")
    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Admin only")
    return user
