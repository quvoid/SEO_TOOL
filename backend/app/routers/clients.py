"""
clients.py — CRUD for brands, with encryption + row-level authorization.

Property IDs are encrypted at rest and masked in responses to non-owners.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from ..db import get_db
from ..models import Client, ClientAccess, Role, User
from ..schemas import ClientCreate, ClientOut
from ..security.crypto import encrypt_str
from ..security.sessions import get_current_user

router = APIRouter(prefix="/clients", tags=["clients"])


def _mask_property_id(client: Client, viewer: User) -> str | None:
    """Only the owner / admins see the real property id; others get a mask."""
    if not client.ga4_property_id_enc:
        return None
    from ..security.crypto import decrypt_str
    pid = decrypt_str(client.ga4_property_id_enc)
    if viewer.role == Role.admin or client.owner_user_id == viewer.id:
        return pid
    return "•••" + pid[-4:] if len(pid) >= 4 else "••••"


def _to_out(client: Client, viewer: User) -> ClientOut:
    return ClientOut(
        id=client.id,
        display_name=client.display_name,
        gsc_site_url=client.gsc_site_url,
        organic_only=client.organic_only,
        use_demo_data=client.use_demo_data,
        credential_label=client.credential.label if client.credential else None,
        ga4_property_id_masked=_mask_property_id(client, viewer),
    )


def _accessible_client_ids(db: DbSession, user: User) -> set[str]:
    owned = {c.id for c in db.query(Client).filter(Client.owner_user_id == user.id)}
    granted = {a.client_id for a in db.query(ClientAccess).filter(ClientAccess.user_id == user.id)}
    return owned | granted


@router.get("", response_model=list[ClientOut])
def list_clients(user: User = Depends(get_current_user), db: DbSession = Depends(get_db)):
    # Internal team tool: every authenticated member sees all brands.
    clients = db.query(Client).order_by(Client.display_name.asc()).all()
    return [_to_out(c, user) for c in clients]


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(body: ClientCreate, user: User = Depends(get_current_user),
                  db: DbSession = Depends(get_db)):
    client = Client(
        display_name=body.display_name,
        ga4_property_id_enc=encrypt_str(body.ga4_property_id) if body.ga4_property_id else "",
        gsc_site_url=body.gsc_site_url,
        organic_only=body.organic_only,
        use_demo_data=body.use_demo_data,
        credential_id=body.credential_id,
        owner_user_id=user.id,
    )
    db.add(client)
    db.commit()
    db.refresh(client)
    return _to_out(client, user)


@router.delete("/{client_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_client(client_id: str, user: User = Depends(get_current_user),
                  db: DbSession = Depends(get_db)):
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
    if client.owner_user_id != user.id and user.role != Role.admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your client")
    db.delete(client)
    db.commit()
