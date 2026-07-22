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


def _host(url: str) -> str:
    """Bare host of a URL/site, lowercased, without a leading www."""
    from urllib.parse import urlparse
    h = (urlparse(url).netloc or url).lower().strip()
    return h[4:] if h.startswith("www.") else h


def _clarity_for_site(rows: list[dict], site: str) -> list[dict]:
    """
    Clarity uses a single global export token that belongs to ONE site. Keep
    only rows whose URL is on this client's own domain, so one brand's Clarity
    data never leaks into another brand's report. Rows without a host (path-only)
    are kept — they can't be disproved. If nothing matches, Clarity is treated
    as not connected for this client and the modules show their fallback state.
    """
    dom = _host(site)
    if not dom:
        return rows
    kept = []
    for r in rows or []:
        rh = _host(r.get("url", ""))
        if not rh or rh == dom or rh.endswith("." + dom) or dom.endswith("." + rh):
            kept.append(r)
    return kept


def _funnel_from_events(events: list[dict]) -> list[dict]:
    """Fallback flat funnel built from the already-fetched event totals, used
    when the device-segmented GA4 funnel query returns nothing."""
    by = {e.get("event_name"): e.get("event_count", 0) for e in (events or [])}
    steps = [{"step": label, "users": by[ev]}
             for label, ev in connectors.FUNNEL_STAGES if by.get(ev, 0)]
    return steps if len(steps) >= 2 else []


def load_data(client_cfg: dict, service_account_info: dict, days: int,
              end_date: str | None = None, prev_start: str | None = None,
              prev_end: str | None = None) -> dict:
    """Port of app.load_data — client_cfg is a plain dict (from the DB row)."""
    if client_cfg.get("use_demo_data"):
        return {
            "ga4": demo_data.ga4_page_metrics(),
            "ga4_totals": demo_data.ga4_totals(),
            "events": demo_data.ga4_event_counts(),
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
    events = _try(lambda: connectors.fetch_ga4_events(prop, sa, days, organic_only, end_date=end_date), [], "GA4 events error")
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
        raw_clarity = _try(lambda: connectors.fetch_clarity_insights(token), [], "Clarity error")
        # Scope the global Clarity token's data to THIS client's domain.
        clarity = _clarity_for_site(raw_clarity, site)
        if raw_clarity and not clarity:
            errors.append("Clarity: token belongs to a different site — not shown for this client")

    # Real device-segmented funnel from GA4 events; fall back to a flat funnel
    # derived from the event totals (never the demo numbers for a live client).
    funnel = _try(lambda: connectors.fetch_ga4_funnel(prop, sa, days, organic_only, end_date=end_date),
                  [], "GA4 funnel error")
    if not funnel:
        funnel = _funnel_from_events(events)

    return {
        "ga4": ga4, "ga4_totals": ga4_totals, "events": events, "gsc": gsc,
        "gsc_queries": gsc_queries, "gsc_queries_prev": gsc_queries_prev,
        "gsc_pairs": gsc_pairs, "clarity": clarity,
        "funnel": funnel,
        "indexation": indexation, "site": site, "is_demo": False, "errors": errors,
    }


def run_report(client_cfg: dict, credential: tuple[str, dict], days: int, model: str,
               analyst_name: str = "", end_date: str | None = None,
               start_date: str | None = None, prev_start: str | None = None,
               prev_end: str | None = None,
               on_progress=None) -> dict:
    """
    Port of app.run_report — returns the preserved 10-module results dict.
    `credential` is (kind, blob) from services.credentials.resolve_credential.
    `days` + optional `end_date` define a GA4-style custom range; the comparison
    period is the immediately preceding window of equal length.
    `on_progress(step_index, total_steps, label)` is called before each module
    so the API can report per-module progress to the polling frontend.
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

    # Live SERP checks (serper.dev, one batched request) — ONLY the middle-band
    # keywords worth uplifting; winners and no-hopers aren't worth credits.
    serper_credits = 0  # serper.dev bills ~1 credit per query in the batch
    if data.get("is_demo"):
        serp_data = demo_data.serper_positions()
    elif _settings.serper_api_key:
        middle_qs = analysis.top_striking_queries(data["gsc_queries"], n=10)
        serper_credits = len(middle_qs)
        serp_data = connectors.fetch_serper_positions(
            middle_qs, data["site"], _settings.serper_api_key, gl=_settings.serper_gl)
    else:
        serp_data = []

    steps = [
        ("organic", "Organic Performance", lambda: analysis.module_organic_performance(data["ga4"], data["gsc"], data["ga4_totals"], gk, model)),
        ("journey", "User Journey", lambda: analysis.module_user_journey(data["ga4"], data["clarity"], gk, model)),
        ("path_exploration", "Path Exploration", lambda: analysis.module_path_exploration(data["events"], gk, model)),
        ("funnel", "Funnel Drop-off", lambda: analysis.module_funnel(data["funnel"], gk, model)),
        ("heatmap", "Heatmap / Click", lambda: analysis.module_heatmap(data["clarity"], gk, model)),
        ("scroll", "Scroll Analysis", lambda: analysis.module_scroll(data["clarity"], data["ga4"], gk, model)),
        ("keywords", "Keyword Intelligence", lambda: analysis.module_keyword_intelligence(
            data["gsc_queries"], gk, model, prev_queries=data["gsc_queries_prev"], site_url=data["site"])),
        ("keyword_opportunities", "Top Keyword Opportunity", lambda: analysis.module_keyword_opportunities(
            data["gsc_queries"], gk, model, site_url=data["site"])),
        ("uplift", "Uplift Tracker", lambda: analysis.module_uplift_tracker(
            data["gsc_queries"], data["gsc"], data["ga4"], data["gsc_pairs"], serp_data,
            gk, model, site_url=data["site"])),
        ("cannibalization", "Cannibalization", lambda: analysis.module_cannibalization(data["gsc_pairs"], gk, model)),
        ("ux_audit", "UX & Speed Audit", lambda: analysis.module_ux_audit(
            data["ga4"], data["gsc"], data["clarity"], pagespeed_data, gk, model, crux_data=crux_data, grok_key=grok)),
        ("hidden_insights", "Hidden Insights", lambda: analysis.module_hidden_insights(data["ga4"], data["gsc"], data["clarity"], gk, model)),
        ("indexation", "Indexation Health", lambda: analysis.module_indexation_health(
            data["indexation"], gk, model, gsc_rows=data["gsc"])),
    ]
    total_steps = len(steps) + 1  # + executive summary

    for i, (key, label, fn) in enumerate(steps):
        if on_progress:
            on_progress(i, total_steps, label)
        results[key] = fn()
        if i < len(steps) - 1:
            time.sleep(_RATE_GAP_SECONDS)

    if on_progress:
        on_progress(len(steps), total_steps, "Executive Summary")
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
        "serper_credits": serper_credits,
    }
    results["_ga4_totals"] = data.get("ga4_totals", {})
    return results
