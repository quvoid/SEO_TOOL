"""
admin.py — admin-only management (users, Gmail credentials, brands).

Gated by require_admin, so only admins (omkar.rakshe@schbang.com via the
ADMIN_EMAILS allowlist) can reach any of it. Regular members can use the
dashboard and see all brands, but never this panel.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..models import Client, Credential, CredentialKind, Role, User
from ..security.crypto import encrypt_json, encrypt_str
from ..security.sessions import require_admin

router = APIRouter(prefix="/admin", tags=["admin"])


# ---------- schemas ----------
class UserIn(BaseModel):
    email: str
    role: str = "analyst"  # "analyst" (member) or "admin"


class UserPatch(BaseModel):
    role: str | None = None
    is_active: bool | None = None


class CredentialIn(BaseModel):
    label: str
    client_id: str
    client_secret: str
    refresh_token: str


class BrandIn(BaseModel):
    display_name: str
    ga4_property_id: str = ""
    gsc_site_url: str = ""
    organic_only: bool = True
    use_demo_data: bool = False
    credential_id: str | None = None
    # Comma-separated brand variants. Empty = derive from the domain.
    brand_terms: str = ""


class BrandPatch(BaseModel):
    """Partial update — only the fields present are written."""
    display_name: str | None = None
    gsc_site_url: str | None = None
    organic_only: bool | None = None
    brand_terms: str | None = None


def _role(value: str) -> Role:
    try:
        return Role(value)
    except ValueError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"invalid role '{value}'")


# ---------- users ----------
@router.get("/users")
def list_users(_: User = Depends(require_admin), db: DbSession = Depends(get_db)):
    return [
        {"id": u.id, "email": u.email, "name": u.name, "role": u.role.value, "is_active": u.is_active}
        for u in db.query(User).order_by(User.created_at.asc())
    ]


@router.post("/users", status_code=status.HTTP_201_CREATED)
def add_user(body: UserIn, _: User = Depends(require_admin), db: DbSession = Depends(get_db)):
    email = body.email.strip().lower()
    if "@" not in email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "invalid email")
    existing = db.query(User).filter(User.email == email).one_or_none()
    if existing:
        existing.role = _role(body.role)
        existing.is_active = True
        db.commit()
        return {"id": existing.id, "email": existing.email, "role": existing.role.value}
    u = User(email=email, name=email.split("@")[0].replace(".", " ").title(),
             role=_role(body.role), is_active=True)
    db.add(u); db.commit(); db.refresh(u)
    return {"id": u.id, "email": u.email, "role": u.role.value}


@router.patch("/users/{user_id}")
def update_user(user_id: str, body: UserPatch, admin: User = Depends(require_admin),
                db: DbSession = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "user not found")
    if u.id == admin.id and (body.role == "analyst" or body.is_active is False):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "you can't demote or disable yourself")
    if body.role is not None:
        u.role = _role(body.role)
    if body.is_active is not None:
        u.is_active = body.is_active
    db.commit()
    return {"id": u.id, "role": u.role.value, "is_active": u.is_active}


# ---------- credentials (Gmail data-source accounts) ----------
@router.get("/credentials")
def list_credentials(_: User = Depends(require_admin), db: DbSession = Depends(get_db)):
    # Never return secret material — labels + counts only.
    out = []
    for c in db.query(Credential).order_by(Credential.created_at.asc()):
        n = db.query(Client).filter(Client.credential_id == c.id).count()
        out.append({"id": c.id, "label": c.label, "kind": c.kind.value, "brand_count": n})
    return out


@router.post("/credentials", status_code=status.HTTP_201_CREATED)
def add_credential(body: CredentialIn, admin: User = Depends(require_admin),
                   db: DbSession = Depends(get_db)):
    if not (body.client_id and body.client_secret and body.refresh_token):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "client_id, client_secret and refresh_token are required")
    cred = Credential(
        label=body.label or "gmail account",
        kind=CredentialKind.user_oauth,
        blob_enc=encrypt_json({
            "client_id": body.client_id,
            "client_secret": body.client_secret,
            "refresh_token": body.refresh_token,
        }),
        owner_user_id=admin.id,
    )
    db.add(cred); db.commit(); db.refresh(cred)
    return {"id": cred.id, "label": cred.label}


# ---------- brands (clients) ----------
@router.post("/clients", status_code=status.HTTP_201_CREATED)
def add_brand(body: BrandIn, admin: User = Depends(require_admin),
              db: DbSession = Depends(get_db)):
    client = Client(
        display_name=body.display_name,
        ga4_property_id_enc=encrypt_str(body.ga4_property_id) if body.ga4_property_id else "",
        gsc_site_url=body.gsc_site_url,
        organic_only=body.organic_only,
        brand_terms=body.brand_terms.strip(),
        use_demo_data=body.use_demo_data,
        credential_id=None if body.use_demo_data else body.credential_id,
        owner_user_id=admin.id,
    )
    db.add(client); db.commit(); db.refresh(client)
    return {"id": client.id, "display_name": client.display_name}


@router.patch("/clients/{client_id}")
def update_brand(client_id: str, body: BrandPatch, _: User = Depends(require_admin),
                 db: DbSession = Depends(get_db)):
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "brand not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(c, field, value.strip() if isinstance(value, str) else value)
    db.commit(); db.refresh(c)
    return {"id": c.id, "display_name": c.display_name, "brand_terms": c.brand_terms or ""}


@router.get("/clients/{client_id}/brand-suggestions")
def brand_suggestions(client_id: str, days: int = 30, _: User = Depends(require_admin),
                      db: DbSession = Depends(get_db)):
    """
    Mine Search Console for likely brand variants so an admin doesn't have to
    guess them. Navigational queries have a distinctive signature — people
    searching your name click through at rates ordinary queries never reach.
    """
    from ..analysis_bridge import connectors, configure_credential
    from ..services.credentials import resolve_credential

    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "brand not found")
    if not c.gsc_site_url:
        return {"suggestions": [], "current": c.brand_terms or "", "reason": "No GSC site URL set."}
    try:
        kind, blob = resolve_credential(c)
        sa = configure_credential(kind, blob)
        return {
            "current": c.brand_terms or "",
            "suggestions": connectors.suggest_brand_terms(c.gsc_site_url, sa, days=days),
        }
    except Exception as exc:  # noqa: BLE001
        return {"suggestions": [], "current": c.brand_terms or "", "reason": str(exc)}


@router.delete("/clients/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_brand(client_id: str, _: User = Depends(require_admin), db: DbSession = Depends(get_db)):
    c = db.get(Client, client_id)
    if not c:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "brand not found")
    db.delete(c); db.commit()
