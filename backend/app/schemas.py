"""schemas.py — Pydantic request/response models (the browser-facing contract)."""
from __future__ import annotations

from pydantic import BaseModel


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    picture: str
    role: str


class ClientOut(BaseModel):
    """Safe client view. Property ID is intentionally masked for non-owners."""
    id: str
    display_name: str
    gsc_site_url: str
    organic_only: bool
    use_demo_data: bool
    credential_label: str | None = None
    ga4_property_id_masked: str | None = None  # e.g. "•••4846"


class ClientCreate(BaseModel):
    display_name: str
    ga4_property_id: str = ""
    gsc_site_url: str = ""
    organic_only: bool = True
    use_demo_data: bool = False
    credential_id: str | None = None


class ReportCreate(BaseModel):
    client_id: str
    days: int = 30
    # Optional GA4-style custom range (ISO 'YYYY-MM-DD'). When both are given they
    # take precedence over `days`. If compare_start/compare_end are also given,
    # they define a custom comparison window; otherwise it's the preceding period.
    start_date: str | None = None
    end_date: str | None = None
    compare_start: str | None = None
    compare_end: str | None = None
    model: str = "gemini-2.0-flash"


class ReportOut(BaseModel):
    id: str
    client_id: str
    status: str
    error: str | None = None


class OnPageRequest(BaseModel):
    url: str
    client_id: str | None = None
