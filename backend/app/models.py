"""
models.py — SQLAlchemy ORM models.

Replaces the file-based clients.json registry with a proper relational schema
supporting multiple Google (Gmail) data-source accounts, each owning a distinct
set of brands, plus users / sessions / report jobs.

Encrypted columns (suffix _enc) hold Fernet tokens — see security/crypto.py.
"""
from __future__ import annotations

import datetime as dt
import enum
import uuid

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Role(str, enum.Enum):
    admin = "admin"      # manage users + credentials (add new Gmail accounts)
    analyst = "analyst"  # run reports for assigned clients
    viewer = "viewer"    # read-only


class CredentialKind(str, enum.Enum):
    service_account = "service_account"
    user_oauth = "user_oauth"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    picture: Mapped[str] = mapped_column(String(1000), default="")
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.analyst)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Credential(Base):
    """
    One Google (Gmail) data-source account. Owns a set of brands (clients).
    All secret material lives in blob_enc (encrypted at rest).

    blob_enc decrypts to either:
      - service_account: the full SA JSON dict, or
      - user_oauth: {client_id, client_secret, refresh_token}
    """
    __tablename__ = "credentials"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    label: Mapped[str] = mapped_column(String(200))  # e.g. "analytics.schbang gmail"
    kind: Mapped[CredentialKind] = mapped_column(Enum(CredentialKind))
    blob_enc: Mapped[str] = mapped_column(Text)      # Fernet token (encrypted JSON)
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    clients: Mapped[list["Client"]] = relationship(back_populates="credential")


class Client(Base):
    """A brand/property. Belongs to one Credential (which Gmail can read it)."""
    __tablename__ = "clients"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(200))
    ga4_property_id_enc: Mapped[str] = mapped_column(Text, default="")  # encrypted
    gsc_site_url: Mapped[str] = mapped_column(String(500), default="")
    organic_only: Mapped[bool] = mapped_column(Boolean, default=True)
    use_demo_data: Mapped[bool] = mapped_column(Boolean, default=False)
    credential_id: Mapped[str | None] = mapped_column(
        ForeignKey("credentials.id"), nullable=True, index=True
    )
    owner_user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)

    credential: Mapped["Credential | None"] = relationship(back_populates="clients")


class ClientAccess(Base):
    """Which users may see which clients (row-level authorization)."""
    __tablename__ = "client_access"
    __table_args__ = (UniqueConstraint("user_id", "client_id", name="uq_user_client"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id", ondelete="CASCADE"), index=True)
    level: Mapped[str] = mapped_column(String(20), default="read")


class ReportStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"


class Report(Base):
    """An async analysis run. result_json holds the preserved 10-module dict."""
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    client_id: Mapped[str] = mapped_column(ForeignKey("clients.id"), index=True)
    requested_by: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.pending)
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    result_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)


class ApiCache(Base):
    """Migrated from the SQLite api_cache table in connectors.py."""
    __tablename__ = "api_cache"

    cache_key: Mapped[str] = mapped_column(String(500), primary_key=True)
    cache_value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_now)
