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
    cache_key = f"ga4_page_metrics_v2_{property_id}_{days}_{organic_only}_{end_date}_{prev_start}_{prev_end}"
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


def fetch_ga4_events(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
) -> list[dict]:
    """
    Returns per-event totals (eventName × eventCount) for the current period,
    ranked by count. Feeds the Path Exploration module, which reconstructs the
    session_start → page_view → next-event flow from these counts.
    """
    cache_key = f"ga4_events_{property_id}_{days}_{organic_only}_{end_date}"
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange, FilterExpression, Filter
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        (cur_s, cur_e), _ = _period_dates(days, end_date, prev_start, prev_end)

        dim_filter = None
        if organic_only:
            dim_filter = FilterExpression(
                filter=Filter(
                    field_name="sessionDefaultChannelGroup",
                    string_filter=Filter.StringFilter(value="Organic Search")
                )
            )

        req = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="eventName")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[DateRange(start_date=cur_s.isoformat(), end_date=cur_e.isoformat())],
            dimension_filter=dim_filter,
            limit=100,
        )
        rows = []
        for row in client.run_report(req).rows:
            rows.append({
                "event_name": row.dimension_values[0].value,
                "event_count": int(float(row.metric_values[0].value or 0)),
            })
        rows.sort(key=lambda r: r["event_count"], reverse=True)
        set_cached_value(cache_key, rows)
        return rows
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


# Canonical conversion-funnel stages (label -> GA4 event). Only the stages a
# property actually records are kept, so shallow-tracking clients still get a
# real funnel instead of the old hard-coded demo numbers.
FUNNEL_STAGES = [
    ("Sessions", "session_start"),
    ("Viewed a page", "page_view"),
    ("Engaged", "user_engagement"),
    ("Started a form", "form_start"),
    ("Submitted a form", "form_submit"),
]


def fetch_ga4_funnel(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool = True,
    end_date: str | None = None,
) -> dict | list:
    """
    Builds a device-segmented conversion funnel from real GA4 event counts
    (eventName x deviceCategory). Returns {mobile:[...], desktop:[...], ...}
    when device data exists, otherwise a flat [{step, users}] list. Only the
    funnel stages the property records are included.
    """
    cache_key = f"ga4_funnel_{property_id}_{days}_{organic_only}_{end_date}"
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            RunReportRequest, Dimension, Metric, DateRange, FilterExpression, Filter
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        (cur_s, cur_e), _ = _period_dates(days, end_date, None, None)

        dim_filter = None
        if organic_only:
            dim_filter = FilterExpression(
                filter=Filter(
                    field_name="sessionDefaultChannelGroup",
                    string_filter=Filter.StringFilter(value="Organic Search")
                )
            )

        req = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="eventName"), Dimension(name="deviceCategory")],
            metrics=[Metric(name="eventCount")],
            date_ranges=[DateRange(start_date=cur_s.isoformat(), end_date=cur_e.isoformat())],
            dimension_filter=dim_filter,
            limit=250,
        )
        # counts[event][device] = eventCount
        counts: dict[str, dict[str, int]] = {}
        for row in client.run_report(req).rows:
            ev = row.dimension_values[0].value
            dev = row.dimension_values[1].value
            counts.setdefault(ev, {})[dev] = int(float(row.metric_values[0].value or 0))

        # Keep only funnel stages the property actually records.
        present = [(label, ev) for label, ev in FUNNEL_STAGES
                   if sum(counts.get(ev, {}).values()) > 0]
        if len(present) < 2:
            return []

        devices = ["mobile", "desktop", "tablet"]
        device_funnel: dict[str, list] = {}
        for dev in devices:
            steps = [{"step": label, "users": counts.get(ev, {}).get(dev, 0)} for label, ev in present]
            if sum(s["users"] for s in steps) > 0:
                device_funnel[dev] = steps

        # module_funnel detects device mode by the "mobile" key; if there's no
        # mobile data, hand back a flat aggregated funnel instead.
        if "mobile" in device_funnel:
            result: dict | list = device_funnel
        else:
            result = [{"step": label, "users": sum(counts.get(ev, {}).values())} for label, ev in present]

        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


# ---------------------------------------------------------------------------
# serper.dev — live Google SERP positions (middle-band keyword tracker)
# ---------------------------------------------------------------------------
def fetch_serper_positions(
    queries: list[str],
    site_url: str,
    api_key: str,
    gl: str = "in",
    hl: str = "en",
) -> list[dict]:
    """
    Live Google positions for a small set of queries via serper.dev.
    All queries are BATCHED into a single request (1 credit per query, one
    HTTP call) to conserve credits. For each query returns our live position
    plus the competitors ranking above us. Falls back to the cache, then [],
    on any failure — the Uplift Tracker renders fine without live data.
    """
    if not queries or not api_key:
        return []
    from urllib.parse import urlparse

    domain = (urlparse(site_url).netloc or site_url).lower()
    domain = domain[4:] if domain.startswith("www.") else domain
    cache_key = f"serper_{gl}_{domain}_" + "_".join(sorted(queries))[:160]

    def _host(link: str) -> str:
        h = urlparse(link).netloc.lower()
        return h[4:] if h.startswith("www.") else h

    def _ours(link: str) -> bool:
        h = _host(link)
        return h == domain or h.endswith("." + domain)

    try:
        import requests
        payload = [{"q": q, "gl": gl, "hl": hl, "num": 10} for q in queries]
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json=payload, timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        if isinstance(body, dict):
            body = [body]

        out = []
        for q, item in zip(queries, body):
            organic = item.get("organic") or []
            our_pos, our_url = None, None
            for r in organic:
                if _ours(r.get("link", "")):
                    our_pos, our_url = r.get("position"), r.get("link")
                    break
            above = [
                {"position": r.get("position"), "title": r.get("title", ""),
                 "domain": _host(r.get("link", ""))}
                for r in organic
                if not _ours(r.get("link", ""))
                and (our_pos is None or (r.get("position") or 99) < our_pos)
            ][:5]
            out.append({
                "query": q, "live_position": our_pos, "our_url": our_url,
                "competitors_above": above, "checked_gl": gl,
            })
        set_cached_value(cache_key, out)
        return out
    except Exception:
        cached = get_cached_value(cache_key)
        return cached if cached is not None else []


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
def fetch_gsc_indexation_summary(site_url: str, service_account_info: dict, days: int = 30) -> dict:
    """
    Indexation health from Search Console.

    Two reliable signals, since Google DEPRECATED the Sitemaps API "indexed"
    count (it returns 0):
      - submitted_urls: URLs across sitemaps, EXCLUDING sitemap-index files
        (their child sitemaps are listed separately, so summing everything
        double-counts). Image-only entries are excluded too.
      - pages_in_search: distinct pages that received Search impressions in the
        period — an uncapped (paginated) count of pages Google actually indexes
        and serves. This is the trustworthy "indexed" number.
    """
    cache_key = f"gsc_indexation_v2_{site_url}_{days}"
    try:
        from googleapiclient.discovery import build
        creds = _ga4_gsc_credentials(service_account_info, ["https://www.googleapis.com/auth/webmasters.readonly"])
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

        # --- Sitemaps: submitted URLs, de-duplicated ---
        resp = service.sitemaps().list(siteUrl=site_url).execute()
        sitemaps, total_submitted = [], 0
        for sm in resp.get("sitemap", []):
            is_index = bool(sm.get("isSitemapsIndex", False))
            # Count web URLs only (skip image/video sub-totals to avoid inflation).
            submitted = sum(int(c.get("submitted", 0)) for c in sm.get("contents", [])
                            if c.get("type") in (None, "web", "Web"))
            if not submitted:
                submitted = sum(int(c.get("submitted", 0)) for c in sm.get("contents", []))
            sitemaps.append({"path": sm.get("path", ""), "submitted": submitted, "indexed": 0, "is_index": is_index})
            if not is_index:  # a sitemap index re-counts its children — don't add it
                total_submitted += submitted

        # --- Pages actually in Search (uncapped, paginated) ---
        (cur_s, cur_e), _ = _period_dates(days, None)
        pages_in_search, start_row = 0, 0
        while True:
            body = {"startDate": cur_s.isoformat(), "endDate": cur_e.isoformat(),
                    "dimensions": ["page"], "rowLimit": 25000, "startRow": start_row}
            rows = service.searchanalytics().query(siteUrl=site_url, body=body).execute().get("rows", [])
            pages_in_search += sum(1 for r in rows if r.get("impressions", 0) > 0)
            if len(rows) < 25000:
                break
            start_row += len(rows)

        rate = round(pages_in_search / total_submitted * 100.0, 1) if total_submitted else 0.0
        result = {
            "submitted_urls": total_submitted,
            "indexed_urls": pages_in_search,
            "pages_in_search": pages_in_search,
            "indexation_rate": rate,
            "sitemaps": sitemaps,
            "sitemap_indexed_available": False,
            "crawled_not_indexed": 0,
            "discovered_not_indexed": 0,
        }
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


# ===========================================================================
# Explorer primitives — ad-hoc, filtered GA4 / GSC queries
#
# Everything above answers a FIXED question ("top organic pages", "top
# queries"). The functions below take dimensions, metrics and filters as
# ARGUMENTS, so one function answers any question an analyst thinks to ask.
# Nothing above is modified — these are purely additive.
#
# Filter spec is plain JSON-serialisable dicts, so it can come straight from
# a UI query builder:
#
#   {"and": [
#       {"field": "landingPage",    "op": "regex", "value": "^/blog/"},
#       {"field": "deviceCategory", "op": "exact", "value": "mobile"},
#   ]}
#
# Groups: {"and": [...]}  {"or": [...]}  {"not": {...}}
# Leaf ops: exact contains begins_with ends_with regex partial_regex
#           in_list between eq gt gte lt lte
# ===========================================================================

_GA4_STRING_OPS = {
    "exact": "EXACT",
    "contains": "CONTAINS",
    "begins_with": "BEGINS_WITH",
    "ends_with": "ENDS_WITH",
    "regex": "FULL_REGEXP",
    "partial_regex": "PARTIAL_REGEXP",
}

_GA4_NUMERIC_OPS = {
    "eq": "EQUAL",
    "gt": "GREATER_THAN",
    "gte": "GREATER_THAN_OR_EQUAL",
    "lt": "LESS_THAN",
    "lte": "LESS_THAN_OR_EQUAL",
}

# GA4 splits organic across several channel groups. The fixed modules match
# "Organic Search" exactly; pass organic_only="all" to include Organic
# Shopping / Video / Social too.
_ORGANIC_ALL_REGEX = r"^Organic( |$)"


def _ga4_numeric_value(value):
    from google.analytics.data_v1beta.types import NumericValue
    if isinstance(value, bool):
        value = int(value)
    if isinstance(value, int):
        return NumericValue(int64_value=value)
    return NumericValue(double_value=float(value))


_GA4_ALL_OPS = set(_GA4_STRING_OPS) | set(_GA4_NUMERIC_OPS) | {"in_list", "between"}


def validate_ga4_filter(spec: dict | None) -> None:
    """
    Recursively check a filter spec's operators. Pure — no SDK needed — so a
    query builder can validate user input before spending an API call.
    Raises ValueError on an unknown op.
    """
    if not spec:
        return
    for key in ("and", "or"):
        if key in spec:
            for child in (spec.get(key) or []):
                validate_ga4_filter(child)
            return
    if "not" in spec:
        validate_ga4_filter(spec["not"])
        return
    if not (spec.get("field") or spec.get("dimension")):
        return
    op = str(spec.get("op") or "exact").lower()
    if op not in _GA4_ALL_OPS:
        # Never silently substitute: an unrecognised op falling through to
        # EXACT would quietly return a different dataset than asked for.
        raise ValueError(f"Unknown GA4 filter op {op!r}. Valid: {sorted(_GA4_ALL_OPS)}")


def _ga4_filter_expression(spec: dict | None):
    """Turn a plain-dict filter spec into a GA4 FilterExpression tree."""
    if not spec:
        return None
    validate_ga4_filter(spec)
    from google.analytics.data_v1beta.types import (
        Filter, FilterExpression, FilterExpressionList,
    )

    if "and" in spec or "or" in spec:
        key = "and" if "and" in spec else "or"
        kids = [_ga4_filter_expression(s) for s in (spec.get(key) or [])]
        kids = [k for k in kids if k is not None]
        if not kids:
            return None
        if len(kids) == 1:
            return kids[0]
        lst = FilterExpressionList(expressions=kids)
        return (FilterExpression(and_group=lst) if key == "and"
                else FilterExpression(or_group=lst))

    if "not" in spec:
        inner = _ga4_filter_expression(spec["not"])
        return FilterExpression(not_expression=inner) if inner else None

    field = spec.get("field") or spec.get("dimension")
    if not field:
        return None
    op = str(spec.get("op") or "exact").lower()
    value = spec.get("value")
    case_sensitive = bool(spec.get("case_sensitive", False))

    if op == "in_list":
        values = value if isinstance(value, (list, tuple)) else [value]
        return FilterExpression(filter=Filter(
            field_name=field,
            in_list_filter=Filter.InListFilter(
                values=[str(v) for v in values], case_sensitive=case_sensitive,
            ),
        ))

    if op == "between":
        lo, hi = value
        return FilterExpression(filter=Filter(
            field_name=field,
            between_filter=Filter.BetweenFilter(
                from_value=_ga4_numeric_value(lo), to_value=_ga4_numeric_value(hi),
            ),
        ))

    if op in _GA4_NUMERIC_OPS:
        return FilterExpression(filter=Filter(
            field_name=field,
            numeric_filter=Filter.NumericFilter(
                operation=_GA4_NUMERIC_OPS[op], value=_ga4_numeric_value(value),
            ),
        ))

    return FilterExpression(filter=Filter(
        field_name=field,
        string_filter=Filter.StringFilter(
            match_type=_GA4_STRING_OPS.get(op, "EXACT"),
            value=str(value), case_sensitive=case_sensitive,
        ),
    ))


def _organic_filter_spec(organic_only) -> dict | None:
    """Channel-group filter spec. True = "Organic Search"; "all" = every Organic *."""
    if not organic_only:
        return None
    if organic_only == "all":
        return {"field": "sessionDefaultChannelGroup", "op": "regex",
                "value": _ORGANIC_ALL_REGEX}
    return {"field": "sessionDefaultChannelGroup", "op": "exact",
            "value": "Organic Search"}


def merge_filters(*specs) -> dict | None:
    """AND together any number of filter specs, ignoring the empty ones."""
    live = [s for s in specs if s]
    if not live:
        return None
    return live[0] if len(live) == 1 else {"and": live}


def _resolve_window(days: int, end_date: str | None, start_date: str | None = None):
    """(start, end) dates — explicit start+end win, else `days` back from end_date."""
    if start_date and end_date:
        return date.fromisoformat(start_date), date.fromisoformat(end_date)
    (cur_s, cur_e), _ = _period_dates(days, end_date)
    return cur_s, cur_e


def _coerce_metric(v):
    """GA4/GSC return every metric as a string — make it a number."""
    try:
        f = float(v)
        return int(f) if f.is_integer() else round(f, 6)
    except (TypeError, ValueError):
        return v


def _ga4_quota(resp) -> dict:
    """Extract property quota consumption (only present with return_property_quota)."""
    pq = getattr(resp, "property_quota", None)
    if not pq:
        return {}
    out = {}
    for name in ("tokens_per_day", "tokens_per_hour", "concurrent_requests",
                 "server_errors_per_project_per_hour",
                 "potentially_thresholded_requests_per_hour",
                 "tokens_per_project_per_hour"):
        q = getattr(pq, name, None)
        if q is None:
            continue
        consumed, remaining = getattr(q, "consumed", 0), getattr(q, "remaining", 0)
        if consumed or remaining:
            out[name] = {"consumed": consumed, "remaining": remaining}
    return out


def _ga4_quality(resp) -> dict:
    """
    Sampling + cardinality warnings. GA4 silently estimates on large properties
    and collapses high-cardinality dimensions into an "(other)" row — both make
    numbers wrong in ways nobody notices. Surface them instead.
    """
    meta = getattr(resp, "metadata", None)
    samples = list(getattr(meta, "sampling_metadatas", None) or []) if meta else []
    sampled = any(
        getattr(s, "samples_read_count", 0) and getattr(s, "sampling_space_size", 0)
        and s.samples_read_count < s.sampling_space_size
        for s in samples
    )
    pct = None
    if sampled and samples:
        s = samples[0]
        if getattr(s, "sampling_space_size", 0):
            pct = round(s.samples_read_count / s.sampling_space_size * 100.0, 2)
    return {
        "sampled": sampled,
        "sample_percent": pct,
        "other_row_present": bool(getattr(meta, "data_loss_from_other_row", False)) if meta else False,
        "currency": getattr(meta, "currency_code", None) if meta else None,
        "timezone": getattr(meta, "time_zone", None) if meta else None,
    }


def run_ga4_report(
    property_id: str,
    service_account_info: dict,
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    days: int = 30,
    end_date: str | None = None,
    start_date: str | None = None,
    filters: dict | None = None,
    metric_filters: dict | None = None,
    organic_only: bool | str = False,
    order_by: str | None = None,
    order_desc: bool = True,
    limit: int = 250,
    max_rows: int | None = None,
    keep_empty_rows: bool = False,
    use_cache: bool = True,
) -> dict:
    """
    Generic GA4 runReport — the primitive every other GA4 helper below is built on.

    Unlike the fixed fetchers above this paginates (GA4 caps a single response
    at 250k rows but defaults to 10), reports sampling/cardinality quality, and
    returns quota consumption so callers can see what a query cost.

    Returns:
      {"rows": [{dim: val, metric: num}], "totals": {...}, "row_count": int,
       "quality": {sampled, other_row_present, ...}, "quota": {...},
       "dimensions": [...], "metrics": [...], "date_range": {...}}
    """
    dimensions = list(dimensions or [])
    metrics = list(metrics or ["sessions"])
    cur_s, cur_e = _resolve_window(days, end_date, start_date)
    filter_spec = merge_filters(_organic_filter_spec(organic_only), filters)
    cache_key = (
        f"ga4_run_{property_id}_{','.join(dimensions)}_{','.join(metrics)}"
        f"_{cur_s}_{cur_e}_{json.dumps(filter_spec, sort_keys=True)}"
        f"_{json.dumps(metric_filters, sort_keys=True)}_{order_by}_{order_desc}"
        f"_{limit}_{max_rows}_{keep_empty_rows}"
    )
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, OrderBy, RunReportRequest,
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)

        order_bys = []
        if order_by:
            if order_by in metrics:
                order_bys = [OrderBy(desc=order_desc,
                                     metric=OrderBy.MetricOrderBy(metric_name=order_by))]
            elif order_by in dimensions:
                order_bys = [OrderBy(desc=order_desc,
                                     dimension=OrderBy.DimensionOrderBy(dimension_name=order_by))]

        rows: list[dict] = []
        totals: dict = {}
        quality: dict = {}
        quota: dict = {}
        row_count = 0
        offset = 0
        page = max(1, min(int(limit or 250), 100000))

        while True:
            req = RunReportRequest(
                property=f"properties/{property_id}",
                dimensions=[Dimension(name=d) for d in dimensions],
                metrics=[Metric(name=m) for m in metrics],
                date_ranges=[DateRange(start_date=cur_s.isoformat(),
                                       end_date=cur_e.isoformat())],
                dimension_filter=_ga4_filter_expression(filter_spec),
                metric_filter=_ga4_filter_expression(metric_filters),
                order_bys=order_bys,
                limit=page,
                offset=offset,
                keep_empty_rows=keep_empty_rows,
                return_property_quota=True,
            )
            resp = client.run_report(req)

            dim_names = [h.name for h in resp.dimension_headers]
            met_names = [h.name for h in resp.metric_headers]
            for r in resp.rows:
                row = {dim_names[i]: dv.value for i, dv in enumerate(r.dimension_values)}
                row.update({met_names[i]: _coerce_metric(mv.value)
                            for i, mv in enumerate(r.metric_values)})
                rows.append(row)

            if not totals and resp.totals:
                totals = {met_names[i]: _coerce_metric(mv.value)
                          for i, mv in enumerate(resp.totals[0].metric_values)}
            quality = _ga4_quality(resp)
            quota = _ga4_quota(resp) or quota
            row_count = getattr(resp, "row_count", len(rows)) or len(rows)

            offset += len(resp.rows)
            if not resp.rows or offset >= row_count:
                break
            if max_rows and len(rows) >= max_rows:
                rows = rows[:max_rows]
                break

        result = {
            "rows": rows, "totals": totals, "row_count": row_count,
            "quality": quality, "quota": quota,
            "dimensions": dimensions, "metrics": metrics,
            "date_range": {"start": cur_s.isoformat(), "end": cur_e.isoformat()},
        }
        if use_cache:
            set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key) if use_cache else None
        if cached is not None:
            return cached
        raise exc


# ---------------------------------------------------------------------------
# GA4 — SEO-shaped wrappers over run_ga4_report
# ---------------------------------------------------------------------------

# Revenue metrics are valid on every GA4 property (they simply read 0 when
# there's no ecommerce), so they're safe to request unconditionally.
GA4_ECOMMERCE_METRICS = [
    "totalRevenue", "transactions", "ecommercePurchases",
    "addToCarts", "checkouts",
]

# Dimensions worth slicing organic traffic by. Exposed so the UI can offer a
# dropdown without hardcoding GA4 API names in the frontend.
GA4_BREAKDOWN_DIMENSIONS = {
    "country": "Country",
    "region": "Region / state",
    "city": "City",
    "deviceCategory": "Device",
    "browser": "Browser",
    "operatingSystem": "OS",
    "newVsReturning": "New vs returning",
    "sessionSourceMedium": "Source / medium",
    "sessionDefaultChannelGroup": "Channel group",
    "landingPagePlusQueryString": "Landing page",
    "pageTitle": "Page title",
}


def _ga4_compare(property_id, service_account_info, key_dim, metrics, days, end_date,
                 prev_start, prev_end, filters, organic_only, limit, order_by,
                 max_rows=None):
    """
    Run the same query over the current and prior window and join on key_dim.
    Returns (rows_with_prev_*, current_meta).
    """
    (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)
    cur = run_ga4_report(
        property_id, service_account_info, [key_dim], metrics,
        start_date=cur_s.isoformat(), end_date=cur_e.isoformat(),
        filters=filters, organic_only=organic_only, order_by=order_by,
        limit=limit, max_rows=max_rows,
    )
    prev = run_ga4_report(
        property_id, service_account_info, [key_dim], metrics,
        start_date=prev_s.isoformat(), end_date=prev_e.isoformat(),
        filters=filters, organic_only=organic_only, order_by=order_by,
        limit=limit, max_rows=max_rows,
    )
    prev_by_key = {r.get(key_dim): r for r in prev["rows"]}
    out = []
    for r in cur["rows"]:
        p = prev_by_key.get(r.get(key_dim), {})
        row = dict(r)
        for m in metrics:
            row[f"prev_{m}"] = p.get(m, 0)
        out.append(row)
    meta = {
        "quality": cur["quality"], "quota": cur["quota"],
        "date_range": cur["date_range"],
        "prev_date_range": {"start": prev_s.isoformat(), "end": prev_e.isoformat()},
    }
    return out, meta


def fetch_ga4_landing_pages(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool | str = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
    filters: dict | None = None,
    limit: int = 500,
    include_revenue: bool = True,
) -> dict:
    """
    Organic performance by LANDING PAGE (entry page), current vs prior period.

    This is the acquisition view `fetch_ga4_page_metrics` can't give you: that
    one groups by `pagePath`, which counts every page viewed in a session, so a
    session landing on /guide and then visiting /pricing credits both. For "which
    page earns the organic entrance" only the landing page is correct.

    Uses landingPagePlusQueryString so paginated / parameterised entries stay
    distinct; strip params downstream if you want them merged.
    """
    metrics = ["sessions", "engagedSessions", "engagementRate",
               "averageSessionDuration", "bounceRate", "conversions", "activeUsers"]
    if include_revenue:
        metrics += ["totalRevenue", "transactions"]

    rows, meta = _ga4_compare(
        property_id, service_account_info, "landingPagePlusQueryString", metrics,
        days, end_date, prev_start, prev_end, filters, organic_only,
        limit=limit, order_by="sessions", max_rows=limit,
    )
    for r in rows:
        r["landing_page"] = r.pop("landingPagePlusQueryString", "")
    rows.sort(key=lambda r: r.get("sessions", 0), reverse=True)
    return {"rows": rows, **meta}


def fetch_ga4_timeseries(
    property_id: str,
    service_account_info: dict,
    days: int = 90,
    organic_only: bool | str = True,
    end_date: str | None = None,
    filters: dict | None = None,
    metrics: list[str] | None = None,
    granularity: str = "date",
) -> dict:
    """
    Daily (or weekly/monthly) organic time series.

    Nothing else in this file requests the `date` dimension, which is why the
    report can only ever say "down 12% vs last period" — never *when* it moved.
    This is the input for trendlines, anomaly detection and update correlation.

    granularity: "date" | "week" | "month" | "yearMonth" | "dayOfWeek" | "hour"
    """
    metrics = metrics or ["sessions", "engagedSessions", "conversions",
                          "totalRevenue", "activeUsers"]
    dim = granularity if granularity in (
        "date", "week", "month", "yearMonth", "dayOfWeek", "hour", "nthDay") else "date"

    res = run_ga4_report(
        property_id, service_account_info, [dim], metrics,
        days=days, end_date=end_date, filters=filters, organic_only=organic_only,
        order_by=dim, order_desc=False, limit=100000,
    )
    for r in res["rows"]:
        raw = r.get(dim, "")
        # GA4 returns dates as YYYYMMDD — normalise to ISO for charting.
        if dim == "date" and len(raw) == 8 and raw.isdigit():
            r["date"] = f"{raw[0:4]}-{raw[4:6]}-{raw[6:8]}"
        else:
            r[dim] = raw
    res["rows"].sort(key=lambda r: str(r.get("date") or r.get(dim) or ""))
    res["granularity"] = dim
    return res


def fetch_ga4_breakdown(
    property_id: str,
    service_account_info: dict,
    dimension: str = "deviceCategory",
    days: int = 30,
    organic_only: bool | str = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
    filters: dict | None = None,
    metrics: list[str] | None = None,
    limit: int = 100,
) -> dict:
    """
    Organic traffic split by any single dimension, current vs prior period.

    Covers the segmentation the fixed modules never touch — country / region /
    city, device, browser, new vs returning, source-medium (google vs bing vs
    the AI assistants now sending referrals). See GA4_BREAKDOWN_DIMENSIONS.
    """
    metrics = metrics or ["sessions", "engagedSessions", "engagementRate",
                          "conversions", "totalRevenue"]
    rows, meta = _ga4_compare(
        property_id, service_account_info, dimension, metrics, days, end_date,
        prev_start, prev_end, filters, organic_only, limit=limit,
        order_by="sessions", max_rows=limit,
    )
    for r in rows:
        r["label"] = r.get(dimension, "")
    rows.sort(key=lambda r: r.get("sessions", 0), reverse=True)
    return {"dimension": dimension, "rows": rows, **meta}


def fetch_ga4_key_events(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool | str = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
    filters: dict | None = None,
) -> dict:
    """
    Key events (conversions) broken out BY EVENT NAME, current vs prior.

    The existing pipeline pulls `conversions` as one blended integer, so a
    report can say conversions fell 20% but never which action fell — form
    submits, calls, or purchases. Rows are ordered by conversion volume, and
    events with zero conversions in both periods are dropped.

    Note: GA4 renamed "conversions" to "key events" in the UI only — the Data
    API metric is still `conversions`.
    """
    metrics = ["conversions", "eventCount", "eventValue"]
    rows, meta = _ga4_compare(
        property_id, service_account_info, "eventName", metrics, days, end_date,
        prev_start, prev_end, filters, organic_only, limit=200,
        order_by="conversions", max_rows=200,
    )
    out = []
    for r in rows:
        if not r.get("conversions") and not r.get("prev_conversions"):
            continue
        out.append({
            "event_name": r.get("eventName", ""),
            "conversions": r.get("conversions", 0),
            "prev_conversions": r.get("prev_conversions", 0),
            "event_count": r.get("eventCount", 0),
            "event_value": r.get("eventValue", 0),
        })
    out.sort(key=lambda r: r["conversions"], reverse=True)
    return {"rows": out, **meta}


def fetch_ga4_ecommerce_totals(
    property_id: str,
    service_account_info: dict,
    days: int = 30,
    organic_only: bool | str = True,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
    filters: dict | None = None,
) -> dict:
    """
    Organic revenue totals, current vs prior — the number a client actually asks
    about. Returns 0s (and revenue_tracked=False) on non-ecommerce properties.
    """
    metrics = ["totalRevenue", "purchaseRevenue", "transactions",
               "ecommercePurchases", "addToCarts", "checkouts", "sessions"]
    (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)

    def _totals(s, e):
        res = run_ga4_report(
            property_id, service_account_info, [], metrics,
            start_date=s.isoformat(), end_date=e.isoformat(),
            filters=filters, organic_only=organic_only,
        )
        t = res["totals"] or {m: 0 for m in metrics}
        txns = t.get("transactions", 0) or 0
        sessions = t.get("sessions", 0) or 0
        t["aov"] = round((t.get("totalRevenue", 0) or 0) / txns, 2) if txns else 0.0
        t["revenue_per_session"] = (
            round((t.get("totalRevenue", 0) or 0) / sessions, 2) if sessions else 0.0)
        t["conversion_rate"] = round(txns / sessions * 100.0, 2) if sessions else 0.0
        return t, res

    cur, cur_res = _totals(cur_s, cur_e)
    prev, _ = _totals(prev_s, prev_e)
    return {
        "current": cur,
        "previous": prev,
        "revenue_tracked": bool(cur.get("totalRevenue") or prev.get("totalRevenue")),
        "currency": (cur_res.get("quality") or {}).get("currency"),
        "quality": cur_res.get("quality", {}),
        "date_range": {"start": cur_s.isoformat(), "end": cur_e.isoformat()},
        "prev_date_range": {"start": prev_s.isoformat(), "end": prev_e.isoformat()},
    }


# ---------------------------------------------------------------------------
# GA4 — schema discovery & query validation
# ---------------------------------------------------------------------------
def fetch_ga4_metadata(property_id: str, service_account_info: dict) -> dict:
    """
    Every dimension and metric THIS property supports — including its custom
    ones (`customEvent:*`, `customUser:*`, calculated metrics).

    This is what lets the tool adapt to a client instead of forcing one fixed
    schema on all of them: discover that a property records
    `customEvent:lead_type`, let an admin map it, then feed it to any of the
    query functions above.
    """
    cache_key = f"ga4_metadata_{property_id}"
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        meta = client.get_metadata(name=f"properties/{property_id}/metadata")

        def _pack(items):
            out = []
            for it in items:
                out.append({
                    "api_name": it.api_name,
                    "ui_name": it.ui_name,
                    "description": getattr(it, "description", "") or "",
                    "custom": bool(getattr(it, "custom_definition", False)),
                    "category": getattr(it, "category", "") or "",
                })
            return out

        dims, mets = _pack(meta.dimensions), _pack(meta.metrics)
        result = {
            "dimensions": dims,
            "metrics": mets,
            "custom_dimensions": [d for d in dims if d["custom"]],
            "custom_metrics": [m for m in mets if m["custom"]],
        }
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


def check_ga4_compatibility(
    property_id: str,
    service_account_info: dict,
    dimensions: list[str],
    metrics: list[str],
) -> dict:
    """
    Ask GA4 whether a dimension/metric combination is even legal before running it.

    Essential once users build their own queries — GA4 rejects plenty of
    plausible-looking pairs (session-scoped metrics against item-scoped
    dimensions, etc.) and the raw error is not something you want to surface.
    Returns which fields are incompatible so the UI can grey them out.
    """
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            CheckCompatibilityRequest, Dimension, Metric,
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        resp = client.check_compatibility(CheckCompatibilityRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
        ))

        def _name(c, attr):
            f = getattr(c, attr, None)
            return getattr(f, "name", "") if f else ""

        incompatible = []
        for c in resp.dimension_compatibilities:
            if str(getattr(c, "compatibility", "")).endswith("INCOMPATIBLE"):
                incompatible.append({"field": _name(c, "dimension_metadata"), "type": "dimension"})
        for c in resp.metric_compatibilities:
            if str(getattr(c, "compatibility", "")).endswith("INCOMPATIBLE"):
                incompatible.append({"field": _name(c, "metric_metadata"), "type": "metric"})
        return {"compatible": not incompatible, "incompatible": incompatible}
    except Exception as exc:
        return {"compatible": True, "incompatible": [], "error": str(exc)}


# ---------------------------------------------------------------------------
# GA4 — pivot, cohort, realtime
# ---------------------------------------------------------------------------
def fetch_ga4_pivot(
    property_id: str,
    service_account_info: dict,
    row_dimension: str,
    pivot_dimension: str,
    metric: str = "sessions",
    days: int = 30,
    organic_only: bool | str = True,
    end_date: str | None = None,
    filters: dict | None = None,
    row_limit: int = 50,
    pivot_limit: int = 10,
) -> dict:
    """
    Two-dimensional cross-tab in one call — e.g. landing page × device, or
    country × channel. Building this from repeated runReport calls costs one
    request per column and blows the quota; runPivotReport does it in one.

    Returns {"columns": [...], "rows": [{"label":..., "cells": {col: value}}]}.
    """
    cur_s, cur_e = _resolve_window(days, end_date, None)
    filter_spec = merge_filters(_organic_filter_spec(organic_only), filters)
    cache_key = (f"ga4_pivot_{property_id}_{row_dimension}_{pivot_dimension}_{metric}"
                 f"_{cur_s}_{cur_e}_{json.dumps(filter_spec, sort_keys=True)}"
                 f"_{row_limit}_{pivot_limit}")
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange, Dimension, Metric, OrderBy, Pivot, RunPivotReportRequest,
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        resp = client.run_pivot_report(RunPivotReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=row_dimension), Dimension(name=pivot_dimension)],
            metrics=[Metric(name=metric)],
            date_ranges=[DateRange(start_date=cur_s.isoformat(), end_date=cur_e.isoformat())],
            dimension_filter=_ga4_filter_expression(filter_spec),
            pivots=[
                Pivot(field_names=[row_dimension], limit=row_limit,
                      order_bys=[OrderBy(desc=True,
                                         metric=OrderBy.MetricOrderBy(metric_name=metric))]),
                Pivot(field_names=[pivot_dimension], limit=pivot_limit),
            ],
        ))

        dim_names = [h.name for h in resp.dimension_headers]
        try:
            r_idx, p_idx = dim_names.index(row_dimension), dim_names.index(pivot_dimension)
        except ValueError:
            r_idx, p_idx = 0, 1

        table: dict[str, dict] = {}
        columns: list[str] = []
        for row in resp.rows:
            vals = [dv.value for dv in row.dimension_values]
            r_key = vals[r_idx] if r_idx < len(vals) else ""
            c_key = vals[p_idx] if p_idx < len(vals) else ""
            val = _coerce_metric(row.metric_values[0].value) if row.metric_values else 0
            table.setdefault(r_key, {})[c_key] = val
            if c_key not in columns:
                columns.append(c_key)

        rows = [{"label": k, "cells": v, "total": sum(x for x in v.values()
                                                      if isinstance(x, (int, float)))}
                for k, v in table.items()]
        rows.sort(key=lambda r: r["total"], reverse=True)
        result = {
            "row_dimension": row_dimension, "pivot_dimension": pivot_dimension,
            "metric": metric, "columns": columns, "rows": rows,
            "date_range": {"start": cur_s.isoformat(), "end": cur_e.isoformat()},
        }
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


def fetch_ga4_cohort_retention(
    property_id: str,
    service_account_info: dict,
    weeks: int = 6,
    organic_only: bool | str = True,
    end_date: str | None = None,
    granularity: str = "WEEKLY",
) -> dict:
    """
    Do the users we acquire from organic actually come back?

    Cohorts users by first-session week and tracks active users in each
    following week. Almost no SEO tool answers this, and for content sites it
    separates traffic that compounds from traffic that churns.

    Returns {"cohorts": [{"cohort":..., "size":N, "periods":[{n, users, pct}]}]}.
    """
    gran = granularity if granularity in ("DAILY", "WEEKLY", "MONTHLY") else "WEEKLY"
    span = {"DAILY": 1, "WEEKLY": 7, "MONTHLY": 30}[gran]
    end = (date.fromisoformat(end_date) if end_date else date.today() - timedelta(days=1))
    start = end - timedelta(days=span * weeks - 1)
    cache_key = f"ga4_cohort_{property_id}_{gran}_{weeks}_{start}_{end}_{organic_only}"
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            Cohort, CohortSpec, CohortsRange, DateRange, Dimension, Metric,
            RunReportRequest,
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        nth = {"DAILY": "cohortNthDay", "WEEKLY": "cohortNthWeek",
               "MONTHLY": "cohortNthMonth"}[gran]

        cohorts = []
        for i in range(weeks):
            c_start = start + timedelta(days=span * i)
            c_end = min(c_start + timedelta(days=span - 1), end)
            if c_start > end:
                break
            cohorts.append(Cohort(
                name=f"cohort_{i}", dimension="firstSessionDate",
                date_range=DateRange(start_date=c_start.isoformat(),
                                     end_date=c_end.isoformat()),
            ))

        resp = client.run_report(RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="cohort"), Dimension(name=nth)],
            metrics=[Metric(name="cohortActiveUsers")],
            dimension_filter=_ga4_filter_expression(_organic_filter_spec(organic_only)),
            cohort_spec=CohortSpec(
                cohorts=cohorts,
                cohorts_range=CohortsRange(granularity=gran, start_offset=0,
                                           end_offset=max(0, len(cohorts) - 1)),
            ),
        ))

        grid: dict[str, dict[int, int]] = {}
        for row in resp.rows:
            name = row.dimension_values[0].value
            try:
                n = int(row.dimension_values[1].value)
            except (TypeError, ValueError):
                continue
            grid.setdefault(name, {})[n] = _coerce_metric(row.metric_values[0].value)

        labels = {c.name: c.date_range.start_date for c in cohorts}
        out = []
        for name in sorted(grid, key=lambda k: labels.get(k, k)):
            periods = grid[name]
            size = periods.get(0, 0) or 0
            out.append({
                "cohort": name,
                "starts": labels.get(name, ""),
                "size": size,
                "periods": [
                    {"n": n, "users": periods[n],
                     "pct": round(periods[n] / size * 100.0, 1) if size else 0.0}
                    for n in sorted(periods)
                ],
            })
        result = {"granularity": gran, "cohorts": out,
                  "date_range": {"start": start.isoformat(), "end": end.isoformat()}}
        set_cached_value(cache_key, result)
        return result
    except Exception as exc:
        cached = get_cached_value(cache_key)
        if cached is not None:
            return cached
        raise exc


def fetch_ga4_realtime(
    property_id: str,
    service_account_info: dict,
    dimensions: list[str] | None = None,
    metrics: list[str] | None = None,
    minutes: int = 30,
    limit: int = 50,
) -> dict:
    """
    Live traffic in the last N minutes (max 29 minutes ago → now).

    Deliberately uncached — "realtime" from cache is a lie. Realtime supports a
    reduced dimension set: unifiedScreenName, country, city, deviceCategory,
    audienceName, eventName, streamName, platform.
    """
    dimensions = dimensions or ["unifiedScreenName"]
    metrics = metrics or ["activeUsers", "screenPageViews"]
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            Dimension, Metric, MinuteRange, RunRealtimeReportRequest,
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = BetaAnalyticsDataClient(credentials=creds)
        resp = client.run_realtime_report(RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name=d) for d in dimensions],
            metrics=[Metric(name=m) for m in metrics],
            minute_ranges=[MinuteRange(
                name="recent", start_minutes_ago=min(max(minutes, 1), 29),
                end_minutes_ago=0,
            )],
            limit=limit,
        ))
        dim_names = [h.name for h in resp.dimension_headers]
        met_names = [h.name for h in resp.metric_headers]
        rows = []
        for r in resp.rows:
            row = {dim_names[i]: dv.value for i, dv in enumerate(r.dimension_values)}
            row.update({met_names[i]: _coerce_metric(mv.value)
                        for i, mv in enumerate(r.metric_values)})
            rows.append(row)
        totals = {}
        if resp.totals:
            totals = {met_names[i]: _coerce_metric(mv.value)
                      for i, mv in enumerate(resp.totals[0].metric_values)}
        return {"rows": rows, "totals": totals, "minutes": minutes}
    except Exception as exc:
        return {"rows": [], "totals": {}, "minutes": minutes, "error": str(exc)}


def fetch_ga4_funnel_report(
    property_id: str,
    service_account_info: dict,
    steps: list[dict] | None = None,
    days: int = 30,
    organic_only: bool | str = True,
    end_date: str | None = None,
    breakdown: str | None = "deviceCategory",
    open_funnel: bool = False,
    breakdown_limit: int = 5,
) -> dict:
    """
    A REAL funnel via runFunnelReport (Data API v1alpha).

    `fetch_ga4_funnel` above reconstructs a funnel from raw eventCount totals,
    which isn't one: event counts aren't sequential and aren't user-scoped, so a
    visitor firing form_start twice inflates that stage and stages can appear to
    grow as you go down. This asks GA4 for the actual sequential, user-scoped
    funnel with proper drop-off.

    steps: [{"name": "Viewed product", "event": "view_item"}, ...] — defaults to
    FUNNEL_STAGES so it's a drop-in comparison. Per-client step definitions are
    the point though; pass them in.

    runFunnelReport is in early preview. Returns {} (never raises) if the alpha
    client isn't available or the property rejects it, so callers can fall back
    to fetch_ga4_funnel.
    """
    steps = steps or [{"name": label, "event": ev} for label, ev in FUNNEL_STAGES]
    cur_s, cur_e = _resolve_window(days, end_date, None)
    cache_key = (f"ga4_funnel_real_{property_id}_{cur_s}_{cur_e}_{organic_only}"
                 f"_{breakdown}_{open_funnel}_{json.dumps(steps, sort_keys=True)}")
    try:
        from google.analytics.data_v1alpha import AlphaAnalyticsDataClient
        from google.analytics.data_v1alpha.types import (
            DateRange, Dimension, Funnel, FunnelBreakdown, FunnelEventFilter,
            FunnelFilterExpression, FunnelStep, RunFunnelReportRequest,
        )

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/analytics.readonly"],
        )
        client = AlphaAnalyticsDataClient(credentials=creds)

        funnel_steps = [
            FunnelStep(
                name=s.get("name") or s.get("event", f"step_{i}"),
                filter_expression=FunnelFilterExpression(
                    funnel_event_filter=FunnelEventFilter(event_name=s["event"])
                ),
            )
            for i, s in enumerate(steps) if s.get("event")
        ]
        if len(funnel_steps) < 2:
            return {}

        req = RunFunnelReportRequest(
            property=f"properties/{property_id}",
            date_ranges=[DateRange(start_date=cur_s.isoformat(),
                                   end_date=cur_e.isoformat())],
            funnel=Funnel(is_open_funnel=open_funnel, steps=funnel_steps),
        )
        if breakdown:
            req.funnel_breakdown = FunnelBreakdown(
                breakdown_dimension=Dimension(name=breakdown),
                limit=breakdown_limit,
            )
        resp = client.run_funnel_report(req)

        table = getattr(resp, "funnel_table", None)
        if table is None:
            return {}
        dim_names = [h.name for h in table.dimension_headers]
        met_names = [h.name for h in table.metric_headers]
        rows = []
        for r in table.rows:
            row = {dim_names[i]: dv.value for i, dv in enumerate(r.dimension_values)}
            row.update({met_names[i]: _coerce_metric(mv.value)
                        for i, mv in enumerate(r.metric_values)})
            rows.append(row)

        result = {
            "rows": rows,
            "steps": [s.get("name") or s.get("event") for s in steps if s.get("event")],
            "breakdown": breakdown,
            "date_range": {"start": cur_s.isoformat(), "end": cur_e.isoformat()},
        }
        set_cached_value(cache_key, result)
        return result
    except Exception:
        cached = get_cached_value(cache_key)
        return cached if cached is not None else {}


# ---------------------------------------------------------------------------
# Search Console — generic filtered query
#
# Nothing above this point sends a single GSC filter: every GSC fetcher takes
# the top N by clicks and filters afterwards in Python. That's the wrong order.
# On most sites brand queries dominate the top 200, so filtering client-side
# means the non-brand long tail never entered the dataset at all. Pushing an
# excludingRegex to the API returns the top 200 *actual non-brand* queries for
# the same quota.
# ---------------------------------------------------------------------------

# GSC only supports groupType "and" today; every filter in a request is ANDed.
_GSC_OPS = {
    "contains": "contains",
    "not_contains": "notContains",
    "equals": "equals",
    "not_equals": "notEquals",
    "regex": "includingRegex",
    "not_regex": "excludingRegex",
    # pass-throughs for callers using the raw API names
    "notContains": "notContains",
    "notEquals": "notEquals",
    "includingRegex": "includingRegex",
    "excludingRegex": "excludingRegex",
}

# GSC search types. `discover` is often the largest traffic source for content
# and publisher clients and is completely invisible to a web-only pipeline.
GSC_SEARCH_TYPES = ("web", "image", "video", "news", "discover", "googleNews")

GSC_DIMENSIONS = ("query", "page", "country", "device", "searchAppearance", "date")


def _gsc_filter_groups(filters: list[dict] | None) -> list[dict]:
    """
    Build dimensionFilterGroups from
    [{"dimension":"query","op":"not_regex","expression":"brand|brnd"}, ...].
    """
    if not filters:
        return []
    built = []
    for f in filters:
        dim = f.get("dimension") or f.get("field")
        expr = f.get("expression", f.get("value"))
        raw_op = str(f.get("op") or f.get("operator") or "contains")
        if raw_op not in _GSC_OPS:
            # Never silently substitute: a typo'd "not_regex" degrading to
            # "contains" would invert a brand filter and quietly return the
            # opposite dataset.
            raise ValueError(
                f"Unknown GSC filter op {raw_op!r}. Valid: {sorted(_GSC_OPS)}"
            )
        if not dim or expr in (None, ""):
            continue
        built.append({"dimension": dim, "operator": _GSC_OPS[raw_op],
                      "expression": str(expr)})
    return [{"groupType": "and", "filters": built}] if built else []


def _brand_regex(site_url: str | None, brand_terms: list[str] | None = None,
                 max_len: int = 1200) -> str:
    """
    RE2-safe alternation of brand tokens for GSC's regex filters.

    GSC uses RE2 — no lookaheads, no backreferences — so this stays a plain
    `a|b|c`. Two things make it match how people actually type brand names:

      - multi-word terms tolerate spaces/hyphens ("my brand" also matches
        "my-brand"),
      - the DOMAIN ROOT is also matched split, because domains are written
        concatenated but searched with spaces. `bodycraft.co.in` must catch
        "body craft"; `ultratechcement.com` must catch "ultratech cement" —
        which is how essentially everyone types them. A variant with an optional
        separator between every character covers every possible split point at
        once. It still requires the exact letter sequence in order, so false
        positives are negligible.

    Only the auto-derived root gets that treatment: terms passed in (or from
    BRAND_KEYWORD_OVERRIDES) are human-curated and already carry their own
    spacing variants, and interleaving them all would bloat the pattern.

    When brand_terms isn't supplied this defers to analysis._detect_brand_terms,
    which owns BRAND_KEYWORD_OVERRIDES (including non-Latin transliterations).
    Keeping one brand list means the API-side filter and the in-Python
    is_branded() can't disagree about what counts as brand.
    """
    import re as _re
    from urllib.parse import urlparse

    terms = [t for t in (brand_terms or []) if t and str(t).strip()]
    if not terms and site_url:
        try:
            import analysis as _analysis
            terms = list(_analysis._detect_brand_terms(site_url) or [])
        except Exception:
            terms = []

    host = (urlparse(site_url or "").netloc or site_url or "").lower()
    host = host[4:] if host.startswith("www.") else host
    root = host.split(":")[0].split("/")[0].split(".")[0]
    if root in ("com", "www", "co", "in", "org", "net"):
        root = ""

    parts, seen = [], set()

    def _add(pattern: str) -> None:
        if pattern and pattern not in seen:
            seen.add(pattern)
            parts.append(pattern)

    for t in list(terms) + ([root] if root else []):
        t = str(t).strip().lower()
        if not t:
            continue
        words = [w for w in _re.split(r"[\s\-_]+", t) if w]
        if not words:
            continue
        # de-dupe on the BUILT pattern: "Acme Corp" and "acme-corp" collapse
        # to the same alternative.
        _add(r"[\s\-]*".join(_re.escape(w) for w in words))

    # Split-tolerant variant of the domain root. 5+ chars only — shorter roots
    # are rarely concatenations and interleaving them buys nothing.
    if root and len(root) >= 5 and " " not in root:
        _add(r"[\s\-]*".join(_re.escape(ch) for ch in root))

    pattern = "|".join(parts)
    if len(pattern) > max_len:
        # Very long alternations risk a GSC rejection; keep the longest (most
        # specific) alternatives that fit rather than sending something invalid.
        kept, total = [], 0
        for p in sorted(parts, key=len, reverse=True):
            if total + len(p) + 1 > max_len:
                break
            kept.append(p)
            total += len(p) + 1
        pattern = "|".join(kept)
    return pattern


def suggest_brand_terms(site_url: str, service_account_info: dict, days: int = 30,
                        top_n: int = 1000, limit: int = 12) -> list[dict]:
    """
    Propose brand variants by mining Search Console, for a human to approve.

    Domain-derived guessing has a hard ceiling: nothing in `hdfcbank.com` reveals
    that the brand is also searched as plain "hdfc".

    The tempting signal — high CTR at a strong position — does NOT work. Tested
    against real data it surfaced "prenatal massage gurgaon" and "bikini wax in
    bangalore": hyper-specific long-tail queries earn high CTR at rank 1-2 for
    exactly the same reasons brand queries do. Using it would misclassify real
    non-brand demand as brand.

    What actually identifies a brand variant is LEXICAL relation to the domain
    root. A term is a candidate when, ignoring spacing and punctuation, it
    contains the root or the root contains it:

        "hdfc"            ⊂ "hdfcbank"     → the missing standalone brand
        "bodycraft salon" ⊃ "bodycraft"    → a brand-plus-modifier
        "prenatal massage"                 → unrelated, correctly rejected

    Candidates already covered by the current pattern are dropped, so what comes
    back is only what the automatic derivation genuinely misses. Suggestions
    only — never auto-applied, since a false positive silently reclassifies
    traffic in a way nobody would notice.
    """
    import re as _re
    from urllib.parse import urlparse

    host = (urlparse(site_url or "").netloc or site_url or "").lower()
    host = host[4:] if host.startswith("www.") else host
    root = _re.sub(r"[^a-z0-9]", "", host.split(":")[0].split("/")[0].split(".")[0])
    if len(root) < 4:
        return []

    rows = run_gsc_query(site_url, service_account_info, ["query"], days=days,
                         max_rows=top_n)
    if not rows:
        return []

    existing = _brand_regex(site_url)
    known = _re.compile(existing, _re.I) if existing else None
    norm = lambda s: _re.sub(r"[^a-z0-9]", "", s.lower())

    # Aggregate candidate n-grams across every query they appear in, so a term
    # like "hdfc" accumulates the weight of all the queries containing it.
    agg: dict[str, dict] = {}
    for r in rows:
        q = (r.get("query") or "").strip().lower()
        if not q:
            continue
        tokens = [t for t in _re.split(r"\s+", q) if t]
        for size in (1, 2, 3):
            for i in range(len(tokens) - size + 1):
                ngram = " ".join(tokens[i:i + size])
                ng = norm(ngram)
                # Lexically tied to the root, and substantial enough that the
                # overlap isn't coincidental (a 2-letter substring is noise).
                if len(ng) < 4 or len(ng) < 0.4 * len(root):
                    continue
                if ng not in root and root not in ng:
                    continue
                if known and known.search(ngram):
                    # Already matched by the derived pattern — "bodycraft salon"
                    # adds nothing over "bodycraft". Only genuine gaps are useful.
                    continue
                a = agg.setdefault(ngram, {
                    "term": ngram, "clicks": 0, "queries": 0,
                    # A term SHORTER than the root ("hdfc" from "hdfcbank") is the
                    # valuable case the derivation can't reach — and also the risky
                    # one, because a short fragment can be an ordinary word ("body"
                    # from "bodycraft" would swallow "body massage"). Flag it so the
                    # UI can warn instead of pretending the choice is free.
                    "partial": ng in root and ng != root,
                })
                a["clicks"] += r.get("clicks", 0) or 0
                a["queries"] += 1

    out = [a for a in agg.values() if a["clicks"] > 0]
    out.sort(key=lambda x: (-x["clicks"], len(x["term"])))
    for a in out:
        a["clicks"] = round(a["clicks"])
    return out[:limit]


def run_gsc_query(
    site_url: str,
    service_account_info: dict,
    dimensions: list[str] | None = None,
    days: int = 30,
    end_date: str | None = None,
    start_date: str | None = None,
    filters: list[dict] | None = None,
    search_type: str = "web",
    data_state: str | None = None,
    row_limit: int = 25000,
    max_rows: int = 25000,
    aggregation_type: str | None = None,
    use_cache: bool = True,
) -> list[dict]:
    """
    Generic Search Analytics query with filters, pagination and search types.

    The fixed fetchers above cap out at 200–2000 rows with no filters and no
    pagination; GSC allows 25,000 rows per request with `startRow` paging, so
    they've been seeing a fraction of the data.

    data_state: None/"final" (default, 2-3 day lag) | "all" (fresh but partial)
    search_type: see GSC_SEARCH_TYPES — "discover" is the notable one.
    """
    dimensions = list(dimensions or ["query"])
    cur_s, cur_e = _resolve_window(days, end_date, start_date)
    groups = _gsc_filter_groups(filters)
    cache_key = (f"gsc_run_{site_url}_{','.join(dimensions)}_{cur_s}_{cur_e}"
                 f"_{search_type}_{data_state}_{aggregation_type}_{max_rows}"
                 f"_{json.dumps(groups, sort_keys=True)}")
    try:
        from googleapiclient.discovery import build

        creds = _ga4_gsc_credentials(
            service_account_info,
            ["https://www.googleapis.com/auth/webmasters.readonly"],
        )
        service = build("searchconsole", "v1", credentials=creds, cache_discovery=False)

        rows: list[dict] = []
        start_row = 0
        page = max(1, min(int(row_limit or 25000), 25000))
        while True:
            body: dict = {
                "startDate": cur_s.isoformat(),
                "endDate": cur_e.isoformat(),
                "dimensions": dimensions,
                "rowLimit": page,
                "startRow": start_row,
                "type": search_type if search_type in GSC_SEARCH_TYPES else "web",
            }
            if groups:
                body["dimensionFilterGroups"] = groups
            if data_state:
                body["dataState"] = str(data_state).upper()
            if aggregation_type:
                body["aggregationType"] = aggregation_type

            resp = service.searchanalytics().query(siteUrl=site_url, body=body).execute()
            batch = resp.get("rows", [])
            for r in batch:
                keys = r.get("keys", [])
                row = {dimensions[i]: keys[i] for i in range(min(len(dimensions), len(keys)))}
                row.update({
                    "clicks": r.get("clicks", 0),
                    "impressions": r.get("impressions", 0),
                    "ctr": r.get("ctr", 0.0),
                    "position": r.get("position", 0.0),
                })
                rows.append(row)

            start_row += len(batch)
            if len(batch) < page or start_row >= max_rows:
                break

        rows = rows[:max_rows]
        if use_cache:
            set_cached_value(cache_key, rows)
        return rows
    except Exception as exc:
        cached = get_cached_value(cache_key) if use_cache else None
        if cached is not None:
            return cached
        raise exc


def fetch_gsc_brand_split(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    end_date: str | None = None,
    brand_terms: list[str] | None = None,
    top_n: int = 250,
    extra_filters: list[dict] | None = None,
) -> dict:
    """
    Branded vs non-branded, split API-side so each bucket gets its own top N.

    Two requests: one includingRegex the brand pattern, one excludingRegex it.
    The non-brand list this returns is the one worth acting on — it's the top
    non-brand queries on the whole site, not whatever non-brand terms happened
    to survive a brand-dominated top 200.
    """
    pattern = _brand_regex(site_url, brand_terms)
    extra = list(extra_filters or [])
    if not pattern:
        # No brand pattern derivable — return everything as non-brand rather
        # than silently mislabelling it.
        rows = run_gsc_query(site_url, service_account_info, ["query"], days,
                             end_date, filters=extra, max_rows=top_n)
        return {"brand_pattern": "", "branded": [], "non_branded": rows,
                "totals": {"branded": {}, "non_branded": _gsc_totals(rows)}}

    branded = run_gsc_query(
        site_url, service_account_info, ["query"], days, end_date,
        filters=extra + [{"dimension": "query", "op": "regex", "expression": pattern}],
        max_rows=top_n,
    )
    non_branded = run_gsc_query(
        site_url, service_account_info, ["query"], days, end_date,
        filters=extra + [{"dimension": "query", "op": "not_regex", "expression": pattern}],
        max_rows=top_n,
    )
    branded.sort(key=lambda r: r["clicks"], reverse=True)
    non_branded.sort(key=lambda r: r["clicks"], reverse=True)
    return {
        "brand_pattern": pattern,
        "branded": branded,
        "non_branded": non_branded,
        "totals": {"branded": _gsc_totals(branded),
                   "non_branded": _gsc_totals(non_branded)},
    }


def _gsc_totals(rows: list[dict]) -> dict:
    """Clicks/impressions totals + impression-weighted CTR and position."""
    clicks = sum(r.get("clicks", 0) for r in rows)
    impr = sum(r.get("impressions", 0) for r in rows)
    wpos = sum(r.get("position", 0) * r.get("impressions", 0) for r in rows)
    return {
        "clicks": round(clicks, 1),
        "impressions": round(impr, 1),
        "ctr": round(clicks / impr, 4) if impr else 0.0,
        "position": round(wpos / impr, 2) if impr else 0.0,
        "queries": len(rows),
    }


# Intent patterns are RE2-safe (no lookarounds). Tuned for the query shapes
# that actually show up in GSC rather than textbook taxonomy.
GSC_INTENT_PATTERNS = {
    "informational": r"^(how|what|why|when|where|who|which)\b|\b(guide|tutorial|tips|examples?|meaning|definition|ideas)\b",
    "commercial": r"\b(best|top|review|reviews|compare|comparison|vs|versus|alternatives?)\b",
    "transactional": r"\b(buy|price|pricing|cost|cheap|discount|deal|deals|coupon|order|quote|hire|book|near me)\b",
}


def fetch_gsc_intent_breakdown(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    end_date: str | None = None,
    brand_terms: list[str] | None = None,
    top_n: int = 100,
    patterns: dict | None = None,
) -> dict:
    """
    Queries bucketed by search intent, each bucket filtered API-side.

    One request per bucket, so each returns its OWN top N — you get the top
    transactional queries even when informational traffic swamps the site. Brand
    terms are excluded from every bucket so intent reflects demand, not
    navigation.
    """
    patterns = patterns or GSC_INTENT_PATTERNS
    brand = _brand_regex(site_url, brand_terms)
    base = [{"dimension": "query", "op": "not_regex", "expression": brand}] if brand else []

    buckets = {}
    for name, pattern in patterns.items():
        rows = run_gsc_query(
            site_url, service_account_info, ["query"], days, end_date,
            filters=base + [{"dimension": "query", "op": "regex", "expression": pattern}],
            max_rows=top_n,
        )
        rows.sort(key=lambda r: r["clicks"], reverse=True)
        buckets[name] = {"pattern": pattern, "rows": rows, "totals": _gsc_totals(rows)}
    return {"brand_pattern": brand, "buckets": buckets}


# ---------------------------------------------------------------------------
# Search Console — time series, hourly, and dimension breakdowns
# ---------------------------------------------------------------------------
def fetch_gsc_timeseries(
    site_url: str,
    service_account_info: dict,
    days: int = 90,
    end_date: str | None = None,
    filters: list[dict] | None = None,
    search_type: str = "web",
    data_state: str | None = None,
) -> list[dict]:
    """
    Daily clicks / impressions / CTR / position.

    Combine with a brand filter to get the two lines that actually matter
    separately — brand traffic moving is a marketing event, non-brand moving is
    an SEO event, and a blended line hides both.
    """
    rows = run_gsc_query(site_url, service_account_info, ["date"], days, end_date,
                         filters=filters, search_type=search_type,
                         data_state=data_state, max_rows=2000)
    rows.sort(key=lambda r: r.get("date", ""))
    return rows


def fetch_gsc_hourly(
    site_url: str,
    service_account_info: dict,
    days: int = 7,
    end_date: str | None = None,
    filters: list[dict] | None = None,
    dimensions: list[str] | None = None,
) -> list[dict]:
    """
    Hourly performance — the earliest possible warning that something broke.

    Standard GSC data lags 2-3 days, so a Monday drop surfaces on Wednesday.
    The HOUR dimension (added April 2025) returns up to 10 days of hourly data
    via the API even though the UI only shows the last 24 hours, which means you
    can compare today hour-by-hour against the same day last week.

    Requires dataState HOURLY_ALL, and the data is explicitly partial — the most
    recent hours will keep filling in. Timestamps come back in Pacific Time
    (`YYYY-MM-DDThh:mm:ss-07:00`); `hour_iso` preserves the raw value.
    """
    dims = list(dimensions or []) + ["HOUR"]
    rows = run_gsc_query(
        site_url, service_account_info, dims, min(days, 10), end_date,
        filters=filters, data_state="HOURLY_ALL", max_rows=25000,
    )
    for r in rows:
        r["hour_iso"] = r.pop("HOUR", "")
    rows.sort(key=lambda r: r.get("hour_iso", ""))
    return rows


def fetch_gsc_by_dimension(
    site_url: str,
    service_account_info: dict,
    dimension: str = "device",
    days: int = 30,
    end_date: str | None = None,
    prev_start: str | None = None,
    prev_end: str | None = None,
    filters: list[dict] | None = None,
    search_type: str = "web",
    top_n: int = 500,
) -> dict:
    """
    GSC performance by country / device / searchAppearance, current vs prior.

    Two blind spots this closes:
      - device: mobile and desktop positions diverge sharply, and under
        mobile-first indexing the mobile position is the real one.
      - country: the pipeline compares GSC's GLOBAL average position against
        serper.dev positions checked with gl=in. Filtering GSC to the same
        country makes those two numbers comparable for the first time.

    searchAppearance shows which SERP features you hold and lose. Note it can't
    be combined with other dimensions in one request — GSC returns an error.
    """
    (cur_s, cur_e), (prev_s, prev_e) = _period_dates(days, end_date, prev_start, prev_end)

    def _run(s, e):
        return run_gsc_query(site_url, service_account_info, [dimension],
                             start_date=s.isoformat(), end_date=e.isoformat(),
                             filters=filters, search_type=search_type, max_rows=top_n)

    cur, prev = _run(cur_s, cur_e), _run(prev_s, prev_e)
    prev_by_key = {r.get(dimension): r for r in prev}
    rows = []
    for r in cur:
        p = prev_by_key.get(r.get(dimension), {})
        rows.append({
            "label": r.get(dimension, ""),
            "clicks": r.get("clicks", 0), "prev_clicks": p.get("clicks", 0),
            "impressions": r.get("impressions", 0),
            "prev_impressions": p.get("impressions", 0),
            "ctr": r.get("ctr", 0.0), "prev_ctr": p.get("ctr", 0.0),
            "position": r.get("position", 0.0), "prev_position": p.get("position", 0.0),
        })
    rows.sort(key=lambda r: r["clicks"], reverse=True)
    return {
        "dimension": dimension, "rows": rows, "totals": _gsc_totals(cur),
        "date_range": {"start": cur_s.isoformat(), "end": cur_e.isoformat()},
        "prev_date_range": {"start": prev_s.isoformat(), "end": prev_e.isoformat()},
    }


def fetch_gsc_discover(
    site_url: str,
    service_account_info: dict,
    days: int = 30,
    end_date: str | None = None,
    top_n: int = 250,
) -> dict:
    """
    Google Discover performance — pages and daily trend.

    Entirely invisible to a web-only pipeline, and for content and publisher
    clients it's frequently the largest single traffic source. Discover has no
    query dimension (there's no query), so it's pages and dates only. Returns
    empty rows when the property has no Discover eligibility.
    """
    pages = run_gsc_query(site_url, service_account_info, ["page"], days, end_date,
                          search_type="discover", max_rows=top_n)
    trend = run_gsc_query(site_url, service_account_info, ["date"], days, end_date,
                          search_type="discover", max_rows=500)
    pages.sort(key=lambda r: r["clicks"], reverse=True)
    trend.sort(key=lambda r: r.get("date", ""))
    return {"pages": pages, "trend": trend, "totals": _gsc_totals(pages),
            "has_discover_data": bool(pages)}


# ---------------------------------------------------------------------------
# Search Console — URL Inspection API
# ---------------------------------------------------------------------------
def fetch_gsc_url_inspection(
    site_url: str,
    service_account_info: dict,
    urls: list[str],
    max_urls: int = 100,
    pause: float = 0.12,
    refresh: bool = False,
) -> dict:
    """
    Per-URL index status, straight from Google.

    `fetch_gsc_indexation_summary` infers indexation from sitemap counts and
    impression proxies because the Sitemaps API's "indexed" number is dead. This
    is the real thing: for each URL, whether Google indexed it, what state it's
    in, when it last crawled, and — the one that catches real bugs — which
    canonical Google chose versus the one you declared.

    That turns "indexation rate: 62%" into "these 47 URLs are Crawled - currently
    not indexed, and Google overrode your canonical on 12 of them."

    Quota is 2,000/day and 600/min per property on a rolling 24h window, so
    results are cached PER URL and only uncached ones cost quota. `max_urls`
    caps a single call; pass a prioritised list (top landing pages, new
    publishes) rather than a whole sitemap.
    """
    import time

    urls = [u for u in (urls or []) if u][:max_urls]
    if not urls:
        return {"rows": [], "summary": {}, "inspected": 0, "from_cache": 0}

    results: list[dict] = []
    to_fetch: list[str] = []
    for u in urls:
        cached = None if refresh else get_cached_value(f"gsc_inspect_{site_url}_{u}")
        if cached is not None:
            results.append(cached)
        else:
            to_fetch.append(u)

    from_cache = len(results)
    errors = 0
    if to_fetch:
        try:
            from googleapiclient.discovery import build

            creds = _ga4_gsc_credentials(
                service_account_info,
                ["https://www.googleapis.com/auth/webmasters.readonly"],
            )
            service = build("searchconsole", "v1", credentials=creds,
                            cache_discovery=False)
            for u in to_fetch:
                try:
                    resp = service.urlInspection().index().inspect(body={
                        "inspectionUrl": u, "siteUrl": site_url,
                        "languageCode": "en-US",
                    }).execute()
                    idx = (resp.get("inspectionResult") or {}).get("indexStatusResult") or {}
                    mob = (resp.get("inspectionResult") or {}).get("mobileUsabilityResult") or {}
                    rich = (resp.get("inspectionResult") or {}).get("richResultsResult") or {}
                    google_canonical = idx.get("googleCanonical", "")
                    user_canonical = idx.get("userCanonical", "")
                    row = {
                        "url": u,
                        "verdict": idx.get("verdict", "VERDICT_UNSPECIFIED"),
                        "coverage_state": idx.get("coverageState", ""),
                        "indexing_state": idx.get("indexingState", ""),
                        "robots_txt_state": idx.get("robotsTxtState", ""),
                        "page_fetch_state": idx.get("pageFetchState", ""),
                        "last_crawl_time": idx.get("lastCrawlTime", ""),
                        "crawled_as": idx.get("crawledAs", ""),
                        "google_canonical": google_canonical,
                        "user_canonical": user_canonical,
                        # The high-value signal: Google picked a different
                        # canonical than the page declared.
                        "canonical_mismatch": bool(
                            google_canonical and user_canonical
                            and google_canonical.rstrip("/") != user_canonical.rstrip("/")
                        ),
                        "indexed": idx.get("coverageState", "").lower().startswith("submitted and indexed")
                                   or idx.get("verdict") == "PASS",
                        "sitemaps": idx.get("sitemap", []),
                        "referring_urls": len(idx.get("referringUrls", []) or []),
                        "mobile_usable": mob.get("verdict", ""),
                        "rich_results": rich.get("verdict", ""),
                    }
                    set_cached_value(f"gsc_inspect_{site_url}_{u}", row)
                    results.append(row)
                except Exception as exc:  # one bad URL shouldn't kill the batch
                    errors += 1
                    results.append({"url": u, "verdict": "ERROR", "error": str(exc),
                                    "coverage_state": "", "indexed": False,
                                    "canonical_mismatch": False})
                if pause:
                    time.sleep(pause)
        except Exception as exc:
            return {"rows": results, "summary": {}, "inspected": 0,
                    "from_cache": from_cache, "error": str(exc)}

    by_state: dict[str, int] = {}
    for r in results:
        state = r.get("coverage_state") or r.get("verdict") or "Unknown"
        by_state[state] = by_state.get(state, 0) + 1

    indexed = sum(1 for r in results if r.get("indexed"))
    summary = {
        "total": len(results),
        "indexed": indexed,
        "not_indexed": len(results) - indexed,
        "indexation_rate": round(indexed / len(results) * 100.0, 1) if results else 0.0,
        "canonical_mismatches": sum(1 for r in results if r.get("canonical_mismatch")),
        "errors": errors,
        "by_coverage_state": dict(sorted(by_state.items(), key=lambda kv: -kv[1])),
    }
    return {"rows": results, "summary": summary,
            "inspected": len(to_fetch) - errors, "from_cache": from_cache}
