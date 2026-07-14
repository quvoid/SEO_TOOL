"""
reports.py — Streamlit-free port of app.py's load_data() + run_report().

Same pipeline, same 10-module `results` dict contract. All st.spinner / st.warning
side effects are replaced with a structured dict; progress is reported via the
Report row status instead of Streamlit spinners.
"""
from __future__ import annotations

import datetime as dt
import time

from ..analysis_bridge import analysis, configure_credential, connectors, demo_data
from ..settings import get_settings

_settings = get_settings()

# Sequential AI rate-limit gap (mirrors the Streamlit app's time.sleep(6)).
_RATE_GAP_SECONDS = 6


def load_data(client_cfg: dict, service_account_info: dict, days: int,
              end_date: str | None = None, prev_start: str | None = None,
              prev_end: str | None = None) -> dict:
    """Port of app.load_data — client_cfg is a plain dict (from the DB row)."""
    if client_cfg.get("use_demo_data"):
        return {
            "ga4": demo_data.ga4_page_metrics(),
            "ga4_totals": demo_data.ga4_totals(),
            "gsc": demo_data.gsc_page_metrics(),
            "gsc_queries": demo_data.gsc_top_queries_flat(),
            "gsc_queries_prev": demo_data.gsc_top_queries_flat_prev(),
            "gsc_pairs": demo_data.gsc_query_page_pairs(),
            "clarity": demo_data.clarity_insights(),
            "funnel": demo_data.funnel_steps_by_device(),
            "indexation": demo_data.indexation_summary(),
            "crux": demo_data.crux_metrics(),
            "site": demo_data.SITE_URL,
            "is_demo": True,
            "errors": [],
        }

    sa = service_account_info
    prop = client_cfg["ga4_property_id"]
    site = client_cfg["gsc_site_url"]
    organic_only = client_cfg.get("organic_only", True)
    errors: list[str] = []

    def _try(fn, default, label):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{label}: {exc}")
            return default

    pv = {"prev_start": prev_start, "prev_end": prev_end}
    ga4 = _try(lambda: connectors.fetch_ga4_page_metrics(prop, sa, days, organic_only, end_date=end_date, **pv), [], "GA4 error")
    ga4_totals = _try(lambda: connectors.fetch_ga4_totals(prop, sa, days, organic_only, end_date=end_date, **pv),
                      {"current_total": 0, "prev_total": 0}, "GA4 totals error")
    gsc = _try(lambda: connectors.fetch_gsc_page_metrics(site, sa, days, end_date=end_date, **pv), [], "GSC page error")
    gsc_queries, gsc_queries_prev = _try(
        lambda: connectors.fetch_gsc_queries_with_prev(site, sa, days, top_n=200, end_date=end_date, **pv), ([], []), "GSC queries error"
    )
    gsc_pairs = _try(lambda: connectors.fetch_gsc_query_page_pairs(site, sa, days, top_n=2000, end_date=end_date), [], "GSC pairs error")
    indexation = _try(lambda: connectors.fetch_gsc_indexation_summary(site, sa),
                      {"submitted_urls": 0, "indexed_urls": 0, "indexation_rate": 0.0, "sitemaps": []},
                      "GSC indexation error")

    clarity = []
    token = _settings.clarity_api_token
    if token and token not in ("CLARITY_DATA_EXPORT_TOKEN", ""):
        clarity = _try(lambda: connectors.fetch_clarity_insights(token), [], "Clarity error")

    return {
        "ga4": ga4, "ga4_totals": ga4_totals, "gsc": gsc,
        "gsc_queries": gsc_queries, "gsc_queries_prev": gsc_queries_prev,
        "gsc_pairs": gsc_pairs, "clarity": clarity,
        "funnel": demo_data.funnel_steps_by_device(),
        "indexation": indexation, "site": site, "is_demo": False, "errors": errors,
    }


def run_report(client_cfg: dict, credential: tuple[str, dict], days: int, model: str,
               analyst_name: str = "", end_date: str | None = None,
               start_date: str | None = None, prev_start: str | None = None,
               prev_end: str | None = None) -> dict:
    """
    Port of app.run_report — returns the preserved 10-module results dict.
    `credential` is (kind, blob) from services.credentials.resolve_credential.
    `days` + optional `end_date` define a GA4-style custom range; the comparison
    period is the immediately preceding window of equal length.
    Raises RuntimeError if GA4 returns nothing (same guard as the Streamlit app).
    """
    kind, blob = credential
    # Point connectors at this client's owning Gmail account, get SA dict (if any).
    service_account_info = configure_credential(kind, blob)
    data = load_data(client_cfg, service_account_info, days, end_date=end_date,
                     prev_start=prev_start, prev_end=prev_end)
    if not data["ga4"]:
        raise RuntimeError(
            "No GA4 data returned. Check the GA4 property ID and credential permissions."
        )

    pagespeed_data: dict = {}
    crux_data: dict = {}
    if data.get("is_demo"):
        for page in ["/roof-leakage-solutions", "/house-construction-guide", "/home-loans"]:
            pagespeed_data[page] = {"url": page, "performance_score": 45, "lcp": 3.8, "cls": 0.18, "inp": 280}
        crux_data = data["crux"]
    else:
        declining = sorted(
            [r for r in data["ga4"] if (r.get("sessions", 0) - r.get("prev_sessions", 0)) < 0],
            key=lambda r: (r.get("sessions", 0) - r.get("prev_sessions", 0)),
        )[:5]
        base_site = data["site"].rstrip("/")
        for r in declining:
            pp = r["page_path"]
            abs_url = base_site + ("/" if not pp.startswith("/") else "") + pp
            pagespeed_data[pp] = connectors.fetch_pagespeed_metrics(abs_url, _settings.google_pagespeed_api_key)
            crux_data[pp] = connectors.fetch_crux_metrics(abs_url, _settings.google_pagespeed_api_key)

    gk = _settings.gemini_api_key
    grok = _settings.xai_api_key
    results: dict = {}

    steps = [
        ("organic", lambda: analysis.module_organic_performance(data["ga4"], data["gsc"], data["ga4_totals"], gk, model)),
        ("journey", lambda: analysis.module_user_journey(data["ga4"], data["clarity"], gk, model)),
        ("funnel", lambda: analysis.module_funnel(data["funnel"], gk, model)),
        ("heatmap", lambda: analysis.module_heatmap(data["clarity"], gk, model)),
        ("scroll", lambda: analysis.module_scroll(data["clarity"], data["ga4"], gk, model)),
        ("keywords", lambda: analysis.module_keyword_intelligence(
            data["gsc_queries"], gk, model, prev_queries=data["gsc_queries_prev"], site_url=data["site"])),
        ("cannibalization", lambda: analysis.module_cannibalization(data["gsc_pairs"], gk, model)),
        ("ux_audit", lambda: analysis.module_ux_audit(
            data["ga4"], data["gsc"], data["clarity"], pagespeed_data, gk, model, crux_data=crux_data, grok_key=grok)),
        ("hidden_insights", lambda: analysis.module_hidden_insights(data["ga4"], data["gsc"], data["clarity"], gk, model)),
        ("indexation", lambda: analysis.module_indexation_health(data["indexation"], gk, model)),
    ]

    for i, (key, fn) in enumerate(steps):
        results[key] = fn()
        if i < len(steps) - 1:
            time.sleep(_RATE_GAP_SECONDS)

    results["exec"] = analysis.module_executive_summary(results, gk, model, grok_key=grok)
    results["_meta"] = {
        "site": data["site"],
        "is_demo": data.get("is_demo", False),
        "days": days,
        "start_date": start_date,
        "end_date": end_date,
        "compare_start": prev_start,
        "compare_end": prev_end,
        "clarity_available": bool(data.get("clarity")),
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "analyst": analyst_name,
        "errors": data.get("errors", []),
    }
    results["_ga4_totals"] = data.get("ga4_totals", {})
    return results
