"""onpage.py — On-Page SEO Optimizer (mirrors app.py's second top-level tab)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from ..analysis_bridge import analysis, connectors
from ..models import User
from ..schemas import OnPageRequest
from ..security.sessions import get_current_user
from ..settings import get_settings

router = APIRouter(prefix="/onpage", tags=["onpage"])
_settings = get_settings()


@router.post("")
def optimize(body: OnPageRequest, user: User = Depends(get_current_user)):
    if not body.url:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "url is required")
    jina_md = connectors.fetch_jina_markdown(body.url)
    ps_stats = connectors.fetch_pagespeed_metrics(body.url, _settings.google_pagespeed_api_key)
    blueprint = analysis.module_onpage_seo(
        jina_md, [], ps_stats, _settings.gemini_api_key,
        "gemini-2.0-flash", grok_key=_settings.xai_api_key,
    )
    return {"url": body.url, "blueprint": blueprint, "pagespeed": ps_stats}
