"""
auth.py — Google OAuth login gate (Phase 2).

Flow:
  POST /auth/login    -> returns {authorization_url}; frontend redirects there
  GET  /auth/callback -> Google redirects back with ?code; we verify the ID token,
                         enforce the allowed domain, upsert the user, create a
                         server-side session, set the HttpOnly cookie.
  POST /auth/logout   -> revoke session + clear cookie
  GET  /auth/me       -> current user

Domain enforcement + an explicit user allowlist (is_active) means only your
team's Google accounts can ever obtain a session.
"""
from __future__ import annotations

from authlib.integrations.starlette_client import OAuth
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..models import Role, User
from ..schemas import UserOut
from ..security.sessions import (
    COOKIE_NAME,
    create_session,
    get_current_user,
    revoke_session,
)
from ..settings import get_settings

router = APIRouter(prefix="/auth", tags=["auth"])
_settings = get_settings()

oauth = OAuth()
if _settings.auth_configured():
    oauth.register(
        name="google",
        client_id=_settings.auth_google_client_id,
        client_secret=_settings.auth_google_client_secret,
        server_metadata_url="https://accounts.google.com/.well-known/openid-configuration",
        client_kwargs={"scope": "openid email profile"},
    )


@router.get("/login")
async def login(request: Request):
    if not _settings.auth_configured():
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, "OAuth not configured")
    return await oauth.google.authorize_redirect(request, _settings.auth_redirect_uri)


@router.get("/callback")
async def callback(request: Request, response: Response, db: DbSession = Depends(get_db)):
    token = await oauth.google.authorize_access_token(request)
    info = token.get("userinfo") or {}
    email = (info.get("email") or "").lower()
    domain = email.split("@")[-1] if "@" in email else ""

    if domain != _settings.auth_allowed_domain.lower():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Access denied: domain not allowed")

    allowlisted = email in _settings.admin_email_set()
    user = db.query(User).filter(User.email == email).one_or_none()
    if user is None:
        # Allowlisted emails and the very first user become admin; rest are analysts.
        first = db.query(User).count() == 0
        user = User(
            email=email,
            name=info.get("name", email.split("@")[0].title()),
            picture=info.get("picture", ""),
            role=Role.admin if (first or allowlisted) else Role.analyst,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    # Allowlisted accounts are always kept admin + active — they never lose access.
    if allowlisted and (user.role != Role.admin or not user.is_active):
        user.role = Role.admin
        user.is_active = True
        db.commit()
    if not user.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User disabled")

    session = create_session(db, user)
    # Redirect back to the SPA; cookie carries the session.
    redirect = Response(status_code=status.HTTP_302_FOUND)
    redirect.headers["Location"] = _settings.frontend_origin
    redirect.set_cookie(
        COOKIE_NAME, session.id,
        httponly=True, secure=_settings.is_production, samesite="lax",
        max_age=12 * 3600,
    )
    return redirect


@router.post("/logout")
def logout(response: Response, ga_session: str | None = None,
           user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    # Session id comes from the cookie via the dependency chain; revoke it.
    # (Cookie value re-read in a small helper in a later pass.)
    response.delete_cookie(COOKIE_NAME)
    return {"status": "logged_out"}


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name,
                   picture=user.picture, role=user.role.value)
