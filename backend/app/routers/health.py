"""health.py — liveness/readiness probe (no auth)."""
from fastapi import APIRouter

from ..settings import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "environment": s.environment,
        "auth_configured": s.auth_configured(),
    }
