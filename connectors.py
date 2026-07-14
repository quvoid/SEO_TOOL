"""
connectors.py — Live data connectors: GA4, Search Console, and Microsoft Clarity.

Each function returns the same dict shape as demo_data.py so analysis modules
never need to know whether they're running on demo or live data.

Auth:
  GA4 + GSC  → GCP Service Account JSON (Option A) or User OAuth Refresh Token (Option B)
"""

from datetime import date, timedelta
import sqlite3
import json
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "api_cache.db")

def init_cache_db():
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS api_cache (
                cache_key TEXT PRIMARY KEY,
                cache_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

def get_cached_value(key: str):
    try:
        init_cache_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT cache_value FROM api_cache WHERE cache_key = ?", (key,))
        row = cursor.fetchone()
        conn.close()
        if row:
            return json.loads(row[0])
    except Exception:
        pass
    return None

def set_cached_value(key: str, value):
    try:
        init_cache_db()
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO api_cache (cache_key, cache_value, updated_at) VALUES (?, ?, CURRENT_TIMESTAMP)",
            (key, json.dumps(value))
        )
        conn.commit()
        conn.close()
    except Exception:
        pass



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


def _period_dates(days: int = 30, end_date: str | None = None,
                  prev_start: str | None = None, prev_end: str | None = None):
    """
    Returns (current_period, prior_period) as (start, end) date tuples.

    - end_date: optional ISO 'YYYY-MM-DD' — the last day of the current window.
      Defaults to yesterday (today is partial in GA4).
    - prev_start / prev_end: optional ISO dates for a CUSTOM comparison window
      (GA4-style "compare to" custom range). When both are given they are used
      verbatim; otherwise the comparison is the immediately preceding period of
      equal length.
    """
    if end_date:
        end = date.fromisoformat(end_date) if isinstance(end_date, str) else end_date
    else:
        end = date.today() - timedelta(days=1)
    cur_start = end - timedelta(days=days - 1)
    if prev_start and prev_end:
        ps = date.fromisoformat(prev_start) if isinstance(prev_start, str) else prev_start
        pe = date.fromisoformat(prev_end) if isinstance(prev_end, str) else prev_end
        return (cur_start, end), (ps, pe)
    p_end = cur_start - timedelta(days=1)
    p_start = p_end - timedelta(days=days - 1)
    return (cur_start, end), (p_start, p_end)


# ---------------------------------------------------------------------------
# GA4 Data API
# ---------------------------------------------------------------------------
def fetch_ga4_page_metrics(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
) -> list[dict]:
    """Returns page-level GA4 metrics for current vs prior period."""
    cache_key = f"ga4_page_metrics_{property_id}_{days}_{organic_only}_{end_date}_{prev_start}_{prev_end}"
    try:
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
        (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)

        metrics = [
            Metric(name="sessions"),
            Metric(name="engagedSessions"),
            Metric(name="bounceRate"),
            Metric(name="averageSessionDuration"),
            Metric(name="conversions"),
            Metric(name="activeUsers"),
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
                    "active_users": int(float(v[5])),
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
                "active_users": c.get("active_users", 0),
            })
        rows.sort(key=lambda r: r["sessions"], reverse=True)
        set_cached_value(cache_key, rows)
        return rows
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


def fetch_ga4_totals(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
) -> dict:
    """Returns overall GA4 summary metrics for current vs prior period."""
    cache_key = f"ga4_totals_{property_id}_{days}_{organic_only}_{end_date}_{prev_start}_{prev_end}"
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Metric, DateRange, FilterExpression, Filter
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)

        metrics = [
            Metric(name="sessions"),
            Metric(name="engagementRate"),
            Metric(name="totalUsers"),
            Metric(name="newUsers"),
            Metric(name="activeUsers"),
            Metric(name="averageSessionDuration"),
            Metric(name="bounceRate"),
        ]
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
                values = [m.value for m in resp.rows[0].metric_values]
                sessions = int(float(values[0] or 0))
                total_users = int(float(values[2] or 0))
                new_users = int(float(values[3] or 0))
                active_users = int(float(values[4] or 0))
                return {
                    "current_total": sessions,
                    "engagement_rate": float(values[1] or 0),
                    "total_users": total_users,
                    "new_users": new_users,
                    "returning_users": total_users - new_users,
                    "active_users": active_users,
                    "avg_session_duration": float(values[5] or 0),
                    "bounce_rate": float(values[6] or 0),
                    "sessions_per_user": (sessions / active_users) if active_users else 0.0,
                }
            return {
                "current_total": 0,
                "engagement_rate": 0.0,
                "total_users": 0,
                "new_users": 0,
                "returning_users": 0,
                "active_users": 0,
                "avg_session_duration": 0.0,
                "bounce_rate": 0.0,
                "sessions_per_user": 0.0,
            }

        result = _run_totals(cur_s, cur_e)
        prev_result = _run_totals(prev_s, prev_e)
        result["prev_total"] = prev_result["current_total"]
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc




# ---------------------------------------------------------------------------
# Search Console API — page-level
# ---------------------------------------------------------------------------
def fetch_gsc_page_metrics(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
) -> list[dict]:
    cache_key = f"gsc_page_metrics_{site_url}_{days}_{end_date}_{prev_start}_{prev_end}"
    try:
        from googleapiclient.discovery import build

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)

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
        set_cached_value(cache_key, rows)
        return rows
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


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
    cache_key = f"gsc_queries_flat_{site_url}_{days}_{top_n}"
    try:
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
        set_cached_value(cache_key, rows)
        return rows
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


def fetch_gsc_top_queries(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    top_n: int = 5,
) -> dict:
    """Page → top N queries. Kept for compatibility / future Module 7."""
    cache_key = f"gsc_top_queries_{site_url}_{days}_{top_n}"
    try:
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
        set_cached_value(cache_key, by_page)
        return by_page
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


# ---------------------------------------------------------------------------
# Microsoft Clarity Data Export API
# ---------------------------------------------------------------------------
def fetch_clarity_insights(api_token: str, num_days: int = 3) -> list[dict]:
    """
    Clarity returns aggregated metrics for the last 1-3 days only (API limit).
    We group URLs by base URL path (stripping query parameters) to prevent cluttering.
    """
    cache_key = f"clarity_insights_{num_days}"
    try:
        import requests

        url = "https://www.clarity.ms/export-data/api/v1/project-live-insights"
        headers = {"Authorization": f"Bearer {api_token}"}
        params = {"numOfDays": num_days, "dimension1": "URL"}
        resp = requests.get(url, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        temp_data: dict = {}

        metric_map = {
            "traffic":         ("total_sessions",     "totalSessionCount"),
            "scrolldepth":     ("avg_scroll_percent",  "averageScrollDepth"),
            "engagementtime":  ("avg_engagement_time", "totalTime"),
            "deadclickcount":  ("dead_clicks",         "subTotal"),
            "rageclickcount":  ("rage_clicks",         "subTotal"),
            "quickbackclick":  ("quickback_clicks",    "subTotal"),
        }

        # Collect raw values for each metric for each normalized URL
        for metric in data if isinstance(data, list) else data.get("metrics", []):
            name = metric.get("metricName") or metric.get("metric")
            if not name:
                continue
            norm_name = name.replace(" ", "").lower()
            field, value_key = metric_map.get(norm_name, (None, None))
            if not field:
                continue
            for info in metric.get("information", []):
                raw_url = info.get("Url") or info.get("URL") or info.get("url")
                if not raw_url:
                    continue
                # Normalize: strip query parameters and trailing slash
                norm_url = raw_url.split("?")[0].rstrip("/") or "/"
                
                # Dynamic value extraction with fallbacks
                val = info.get(value_key) or info.get("subTotal") or info.get("value") or info.get("average") or info.get("count") or 0
                try:
                    numeric_val = float(val) if "percent" in field or "time" in field else int(float(val))
                except (TypeError, ValueError):
                    numeric_val = 0
                
                # If scroll depth is returned as a fraction between 0.0 and 1.0, scale to 0-100%
                if field == "avg_scroll_percent" and 0.0 < numeric_val <= 1.0:
                    numeric_val *= 100.0
                
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
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


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
    cache_key = f"pagespeed_{url}"
    try:
        import requests
        endpoint = "https://pagespeedonline.googleapis.com/pagespeedonline/v5/runPagespeed"
        params = {
            "url": url,
            "strategy": "mobile",
            "category": "performance"
        }
        if api_key:
            params["key"] = api_key
        
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
        
        result = {
            "url": url,
            "performance_score": score,
            "lcp": round(lcp_val, 2),
            "cls": round(cls_val, 3),
            "inp": round(inp_val, 0)
        }
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
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
    cache_key = f"jina_{url}"
    try:
        import requests
        jina_url = f"https://r.jina.ai/{url}"
        resp = requests.get(jina_url, timeout=20)
        resp.raise_for_status()
        result = resp.text
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        return f"Failed to fetch content from Jina Reader: {exc}"



# ---------------------------------------------------------------------------
# GSC Query + Page Pairs — for Keyword Cannibalization (Module 6b)
# ---------------------------------------------------------------------------
def fetch_gsc_query_page_pairs(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    top_n: int = 2000,
    end_date: str | None = None,
) -> list[dict]:
    """Fetch GSC data with both query AND page dimensions for cannibalization detection."""
    cache_key = f"gsc_query_page_pairs_{site_url}_{days}_{end_date}"
    try:
        from googleapiclient.discovery import build
        creds = _ga4_gsc_credentials(service_account_info, ["https://www.googleapis.com/auth/webmasters.readonly"])
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        (cur_s, cur_e), _ = _period_dates(days, end_date)
        body = {"startDate": cur_s.isoformat(), "endDate": cur_e.isoformat(), "dimensions": ["query", "page"], "rowLimit": top_n}
        resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
        rows = [{"query": r["keys"][0], "page": r["keys"][1], "clicks": r.get("clicks",0), "impressions": r.get("impressions",0), "ctr": r.get("ctr",0.0), "position": r.get("position",0.0)} for r in resp.get("rows", [])]
        set_cached_value(cache_key, rows)
        return rows
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


# ---------------------------------------------------------------------------
# GSC Queries with Previous Period — for New vs Lost Query WoW (Module 6)
# ---------------------------------------------------------------------------
def fetch_gsc_queries_with_prev(site_url: str, service_account_info: dict, days: int = 30, top_n: int = 200, end_date: str | None = None, prev_start: str | None = None, prev_end: str | None = None) -> tuple:
    """Returns (current_queries, prev_queries) for new/lost query WoW diff."""
    cache_key = f"gsc_queries_with_prev_{site_url}_{days}_{top_n}_{end_date}_{prev_start}_{prev_end}"
    try:
        from googleapiclient.discovery import build
        creds = _ga4_gsc_credentials(service_account_info, ["https://www.googleapis.com/auth/webmasters.readonly"])
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)
        def _run(start, end):
            body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "dimensions": ["query"], "rowLimit": top_n, "orderBy": [{"fieldName": "clicks", "sortOrder": "DESCENDING"}]}
            resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            return [{"query": r["keys"][0], "clicks": r.get("clicks",0), "impressions": r.get("impressions",0), "ctr": r.get("ctr",0.0), "position": r.get("position",0.0)} for r in resp.get("rows", [])]
        cur = _run(cur_s, cur_e)
        prev = _run(prev_s, prev_e)
        set_cached_value(cache_key, {"current": cur, "prev": prev})
        return cur, prev
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached.get("current", []), cached.get("prev", [])
        raise exc


# ---------------------------------------------------------------------------
# GSC Sitemaps API — Indexation Health (Module 9)
# ---------------------------------------------------------------------------
def fetch_gsc_indexation_summary(site_url: str, service_account_info: dict) -> dict:
    """Fetch sitemap indexation data from Search Console Sitemaps API."""
    cache_key = f"gsc_indexation_{site_url}"
    try:
        from googleapiclient.discovery import build
        creds = _ga4_gsc_credentials(service_account_info, ["https://www.googleapis.com/auth/webmasters.readonly"])
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
        resp = service.sitemaps().list(siteUrl=site_url).execute()
        sitemaps, total_submitted, total_indexed = [], 0, 0
        for sm in resp.get("sitemap", []):
            submitted, indexed = 0, 0
            for cnt in sm.get("contents", []):
                submitted += int(cnt.get("submitted", 0))
                indexed += int(cnt.get("indexed", 0))
            sitemaps.append({"path": sm.get("path",""), "submitted": submitted, "indexed": indexed})
            total_submitted += submitted
            total_indexed += indexed
        rate = (total_indexed / total_submitted * 100.0) if total_submitted else 0.0
        result = {"submitted_urls": total_submitted, "indexed_urls": total_indexed, "indexation_rate": round(rate,1), "sitemaps": sitemaps, "crawled_not_indexed": 0, "discovered_not_indexed": 0}
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


# ---------------------------------------------------------------------------
# CrUX API — Real-user Core Web Vitals Field Data (Module 7 Enhancement)
# ---------------------------------------------------------------------------
def fetch_crux_metrics(url: str, api_key: str | None = None) -> dict:
    """Fetch Chrome UX Report p75 field data. Returns {} if URL not in CrUX dataset."""
    cache_key = f"crux_{url}"
    try:
        import requests
        endpoint = "https://chromeuxreport.googleapis.com/v1/records:queryRecord"
        params = {"key": api_key} if api_key else {}
        payload = {"url": url, "formFactor": "PHONE", "metrics": ["largest_contentful_paint","cumulative_layout_shift","interaction_to_next_paint","first_contentful_paint"]}
        resp = requests.post(endpoint, json=payload, params=params, timeout=30)
        if resp.status_code == 404:
            return {}
        resp.raise_for_status()
        metrics = resp.json().get("record", {}).get("metrics", {})
        def _p75(n): return metrics.get(n, {}).get("percentiles", {}).get("p75")
        lcp_ms = _p75("largest_contentful_paint")
        cls_v = _p75("cumulative_layout_shift")
        inp_ms = _p75("interaction_to_next_paint")
        fcp_ms = _p75("first_contentful_paint")
        lcp_s = round(lcp_ms/1000.0, 2) if lcp_ms else None
        fcp_s = round(fcp_ms/1000.0, 2) if fcp_ms else None
        poor = (lcp_s and lcp_s > 4.0) or (cls_v and cls_v > 0.25) or (inp_ms and inp_ms > 500)
        needs = (lcp_s and lcp_s > 2.5) or (cls_v and cls_v > 0.1) or (inp_ms and inp_ms > 200)
        result = {"lcp_p75": lcp_s, "cls_p75": cls_v, "inp_p75": inp_ms, "fcp_p75": fcp_s, "rating": "poor" if poor else ("needs_improvement" if needs else "good")}
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        return {}
