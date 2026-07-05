"""
connectors.py — Live data connectors: GA4, Search Console, and Microsoft Clarity.

Each function returns the same dict shape as demo_data.py so analysis modules
never need to know whether they're running on demo or live data.

Auth:
  GA4 + GSC  → GCP Service Account JSON (Option A) or User OAuth Refresh Token (Option B)
"""

from datetime import date, timedelta


# ---------------------------------------------------------------------------
# Auth helpers — Option A: Service Account  |  Option B: User OAuth
# ---------------------------------------------------------------------------
def _google_credentials(service_account_info: dict, scopes: list):
    """Build credentials from a GCP service account JSON dict."""
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_info(
        service_account_info, scopes=scopes
    )


def _user_oauth_credentials(scopes: list):
    """
    Build credentials from a user OAuth refresh token.
    Used when the service account hasn't been granted property access
    but the analyst's own Google account has access.
    Run generate_ga4_gsc_token.py once to obtain the refresh token.
    """
    import config
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    creds = Credentials(
        token=None,
        refresh_token=config.USER_OAUTH_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=config.USER_OAUTH_CLIENT_ID,
        client_secret=config.USER_OAUTH_CLIENT_SECRET,
        scopes=scopes,
    )
    # Refresh to get a valid access token
    creds.refresh(Request())
    return creds


def _ga4_gsc_credentials(service_account_info: dict, scopes: list):
    """
    Auto-select auth method:
    - Uses user OAuth refresh token if configured (Option B - preferred).
    - Falls back to service account if user OAuth is not configured.
    Raises RuntimeError if neither is configured.
    """
    import config
    if config.user_oauth_configured():
        return _user_oauth_credentials(scopes)
    if service_account_info:
        return _google_credentials(service_account_info, scopes)
    raise RuntimeError(
        "No GA4/GSC credentials found. Add either [gcp_service_account] "
        "or [user_oauth] to secrets.toml."
    )


def _period_dates(days: int = 30):
    """Returns (current_period, prior_period) as (start, end) date tuples."""
    end = date.today() - timedelta(days=1)   # yesterday — today is partial in GA4
    cur_start = end - timedelta(days=days - 1)
    prev_end = cur_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=days - 1)
    return (cur_start, end), (prev_start, prev_end)


# ---------------------------------------------------------------------------
# GA4 Data API
# ---------------------------------------------------------------------------
def fetch_ga4_page_metrics(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool = True,
) -> list[dict]:
    """Returns page-level GA4 metrics for current vs prior period."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, Dimension, Metric, DateRange,
        FilterExpression, Filter,
    )

    creds = _ga4_gsc_credentials(
        service_account_info,
        ["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=creds)
    (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days)

    metrics = [
        Metric(name="sessions"),
        Metric(name="engagedSessions"),
        Metric(name="bounceRate"),
        Metric(name="averageSessionDuration"),
        Metric(name="conversions"),
    ]
    dim_filter = None
    if organic_only:
        dim_filter = FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        )

    def _run(start, end):
        req = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="pagePath")],
            metrics=metrics,
            date_ranges=[DateRange(
                start_date=start.isoformat(), end_date=end.isoformat()
            )],
            dimension_filter=dim_filter,
            limit=250,
        )
        out = {}
        for row in client.run_report(req).rows:
            page = row.dimension_values[0].value
            v = [m.value for m in row.metric_values]
            out[page] = {
                "sessions": int(float(v[0])),
                "engaged_sessions": int(float(v[1])),
                "bounce_rate": float(v[2]),
                "avg_session_duration": float(v[3]),
                "conversions": int(float(v[4])),
            }
        return out

    cur, prev = _run(cur_s, cur_e), _run(prev_s, prev_e)
    rows = []
    for page, c in cur.items():
        p = prev.get(page, {})
        rows.append({
            "page_path": page,
            "sessions": c["sessions"],
            "prev_sessions": p.get("sessions", 0),
            "engaged_sessions": c["engaged_sessions"],
            "bounce_rate": c["bounce_rate"],
            "avg_session_duration": c["avg_session_duration"],
            "conversions": c["conversions"],
            "prev_conversions": p.get("conversions", 0),
        })
    rows.sort(key=lambda r: r["sessions"], reverse=True)
    return rows


def fetch_ga4_totals(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool = True,
) -> dict:
    """Returns overall total organic sessions for current vs prior period (no page dimension limits)."""
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest, Metric, DateRange, FilterExpression, Filter
    )

    creds = _ga4_gsc_credentials(
        service_account_info,
        ["https://www.googleapis.com/auth/analytics.readonly"],
    )
    client = BetaAnalyticsDataClient(credentials=creds)
    (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days)

    metrics = [Metric(name="sessions")]
    dim_filter = None
    if organic_only:
        dim_filter = FilterExpression(
            filter=Filter(
                field_name="sessionDefaultChannelGroup",
                string_filter=Filter.StringFilter(value="Organic Search")
            )
        )

    def _run_totals(start, end):
        req = RunReportRequest(
            property=f"properties/{property_id}",
            metrics=metrics,
            date_ranges=[DateRange(
                start_date=start.isoformat(), end_date=end.isoformat()
            )],
            dimension_filter=dim_filter,
        )
        resp = client.run_report(req)
        if resp.rows:
            return int(float(resp.rows[0].metric_values[0].value))
        return 0

    cur_total = _run_totals(cur_s, cur_e)
    prev_total = _run_totals(prev_s, prev_e)
    return {"current_total": cur_total, "prev_total": prev_total}



# ---------------------------------------------------------------------------
# Search Console API — page-level
# ---------------------------------------------------------------------------
def fetch_gsc_page_metrics(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
) -> list[dict]:
    from googleapiclient.discovery import build

    creds = _ga4_gsc_credentials(
        service_account_info,
        ["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days)

    def _query(start, end):
        body = {
            "startDate": start.isoformat(),
            "endDate": end.isoformat(),
            "dimensions": ["page"],
            "rowLimit": 1000,
        }
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        out = {}
        for r in resp.get("rows", []):
            page = r["keys"][0]
            out[page] = {
                "clicks": r.get("clicks", 0),
                "impressions": r.get("impressions", 0),
                "ctr": r.get("ctr", 0.0),
                "position": r.get("position", 0.0),
            }
        return out

    cur, prev = _query(cur_s, cur_e), _query(prev_s, prev_e)
    rows = []
    for page, c in cur.items():
        p = prev.get(page, {})
        rows.append({
            "page": page,
            "clicks": c["clicks"], "prev_clicks": p.get("clicks", 0),
            "impressions": c["impressions"],
            "prev_impressions": p.get("impressions", 0),
            "ctr": c["ctr"], "prev_ctr": p.get("ctr", 0.0),
            "position": c["position"], "prev_position": p.get("position", 0.0),
        })
    rows.sort(key=lambda r: r["clicks"], reverse=True)
    return rows


# ---------------------------------------------------------------------------
# Search Console API — flat query list (for Module 6)
# ---------------------------------------------------------------------------
def fetch_gsc_queries_flat(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    top_n: int = 50,
) -> list[dict]:
    """
    Returns top queries sorted by clicks — flat list, no page grouping.
    Used as seed keywords in Module 6.
    """
    from googleapiclient.discovery import build

    creds = _ga4_gsc_credentials(
        service_account_info,
        ["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    (cur_s, cur_e), _ = _period_dates(days)

    body = {
        "startDate": cur_s.isoformat(),
        "endDate": cur_e.isoformat(),
        "dimensions": ["query"],
        "rowLimit": top_n,
        "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}],
    }
    resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    rows = []
    for r in resp.get("rows", []):
        rows.append({
            "query": r["keys"][0],
            "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "ctr": r.get("ctr", 0.0),
            "position": r.get("position", 0.0),
        })
    return rows


def fetch_gsc_top_queries(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    top_n: int = 5,
) -> dict:
    """Page → top N queries. Kept for compatibility / future Module 7."""
    from googleapiclient.discovery import build

    creds = _ga4_gsc_credentials(
        service_account_info,
        ["https://www.googleapis.com/auth/webmasters.readonly"],
    )
    service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    (cur_s, cur_e), _ = _period_dates(days)

    body = {
        "startDate": cur_s.isoformat(), "endDate": cur_e.isoformat(),
        "dimensions": ["page", "query"], "rowLimit": 5000,
    }
    resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
    by_page: dict = {}
    for r in resp.get("rows", []):
        page, query = r["keys"][0], r["keys"][1]
        by_page.setdefault(page, []).append({
            "query": query, "clicks": r.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "position": r.get("position", 0.0),
        })
    for page in by_page:
        by_page[page] = sorted(
            by_page[page], key=lambda q: q["clicks"], reverse=True
        )[:top_n]
    return by_page


# ---------------------------------------------------------------------------
# Microsoft Clarity Data Export API
# ---------------------------------------------------------------------------
def fetch_clarity_insights(api_token: str, num_days: int = 3) -> list[dict]:
    """
    Clarity returns aggregated metrics for the last 1-3 days only (API limit).
    We group URLs by base URL path (stripping query parameters) to prevent cluttering.
    """
    import requests

    url = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
    headers = {"Authorization": f"Bearer {api_token}"}
    params = {"numOfDays": num_days, "dimension1": "URL"}
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    temp_data: dict = {}

    metric_map = {
        "Traffic":         ("total_sessions",     "totalSessionCount"),
        "ScrollDepth":     ("avg_scroll_percent",  "averageScrollDepth"),
        "EngagementTime":  ("avg_engagement_time", "totalTime"),
        "DeadClickCount":  ("dead_clicks",         "subTotal"),
        "RageClickCount":  ("rage_clicks",         "subTotal"),
        "QuickbackClick":  ("quickback_clicks",    "subTotal"),
    }

    # Collect raw values for each metric for each normalized URL
    for metric in data if isinstance(data, list) else data.get("metrics", []):
        name = metric.get("metricName") or metric.get("metric")
        field, value_key = metric_map.get(name, (None, None))
        if not field:
            continue
        for info in metric.get("information", []):
            raw_url = info.get("Url") or info.get("URL") or info.get("url")
            if not raw_url:
                continue
            # Normalize: strip query parameters and trailing slash
            norm_url = raw_url.split("?")[0].rstrip("/") or "/"
            
            val = info.get(value_key) or info.get("subTotal") or 0
            try:
                numeric_val = float(val) if "percent" in field or "time" in field else int(float(val))
            except (TypeError, ValueError):
                numeric_val = 0
            
            record = temp_data.setdefault(norm_url, {
                "url": norm_url,
                "total_sessions": 0,
                "dead_clicks": 0,
                "rage_clicks": 0,
                "quickback_clicks": 0,
                "_scroll_sum": 0.0,
                "_scroll_count": 0,
                "_engage_sum": 0.0,
                "_engage_count": 0,
            })
            
            if field == "total_sessions":
                record["total_sessions"] += int(numeric_val)
            elif field == "dead_clicks":
                record["dead_clicks"] += int(numeric_val)
            elif field == "rage_clicks":
                record["rage_clicks"] += int(numeric_val)
            elif field == "quickback_clicks":
                record["quickback_clicks"] += int(numeric_val)
            elif field == "avg_scroll_percent":
                record["_scroll_sum"] += float(numeric_val)
                record["_scroll_count"] += 1
            elif field == "avg_engagement_time":
                record["_engage_sum"] += float(numeric_val)
                record["_engage_count"] += 1

    # Finalize aggregates
    result = []
    for norm_url, rec in temp_data.items():
        result.append({
            "url": norm_url,
            "total_sessions": rec["total_sessions"],
            "dead_clicks": rec["dead_clicks"],
            "rage_clicks": rec["rage_clicks"],
            "quickback_clicks": rec["quickback_clicks"],
            "avg_scroll_percent": round(rec["_scroll_sum"] / rec["_scroll_count"], 1) if rec["_scroll_count"] > 0 else 0.0,
            "avg_engagement_time": round(rec["_engage_sum"] / rec["_engage_count"], 1) if rec["_engage_count"] > 0 else 0.0,
        })
    return result


def fetch_pagespeed_metrics(url: str, api_key: str | None = None) -> dict:
    """
    Queries Google PageSpeed Insights API v5 for mobile performance scores and Core Web Vitals.
    Returns: {
        "url": url,
        "performance_score": int (0-100),
        "lcp": float (seconds),
        "cls": float,
        "inp": float (ms) or None
    }
    """
    import requests
    endpoint = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
    params = {
        "url": url,
        "strategy": "mobile",
        "category": "performance"
    }
    if api_key:
        params["key"] = api_key
    
    try:
        resp = requests.get(endpoint, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        
        lighthouse = data.get("lighthouseResult", {})
        categories = lighthouse.get("categories", {})
        performance = categories.get("performance", {})
        score = int(float(performance.get("score", 0)) * 100)
        
        audits = lighthouse.get("audits", {})
        lcp_val = audits.get("largest-contentful-paint", {}).get("numericValue", 0) / 1000.0
        cls_val = audits.get("cumulative-layout-shift", {}).get("numericValue", 0.0)
        
        inp_val = audits.get("interactive", {}).get("numericValue", 0.0)
        if "interaction-to-next-paint" in audits:
            inp_val = audits.get("interaction-to-next-paint", {}).get("numericValue", 0.0)
        
        return {
            "url": url,
            "performance_score": score,
            "lcp": round(lcp_val, 2),
            "cls": round(cls_val, 3),
            "inp": round(inp_val, 0)
        }
    except Exception as exc:
        return {
            "url": url,
            "performance_score": None,
            "lcp": None,
            "cls": None,
            "inp": None,
            "error": str(exc)
        }


def fetch_jina_markdown(url: str) -> str:
    """
    Calls the Jina Reader API to get clean markdown from a URL.
    Returns: markdown content or error string.
    """
    import requests
    jina_url = f"https://r.jina.ai/{url}"
    try:
        resp = requests.get(jina_url, timeout=20)
        resp.raise_for_status()
        return resp.text
    except Exception as exc:
        return f"Failed to fetch content from Jina Reader: {exc}"
