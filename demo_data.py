"""
Demo data for AI Growth Analyst.

This lets the deployed app work immediately — before you wire up any GA4 / GSC /
Clarity / Anthropic credentials. Flip "Data source" to "Live" in the sidebar once
your keys are in .streamlit/secrets.toml.

The sample site mimics a construction / building-materials brand (roof leakage,
home loans, cement guides) so the analysis reads realistically.
"""

from datetime import date, timedelta

SITE_URL = "https://demo-buildmart.example.com"

# ---------------------------------------------------------------------------
# GA4-style page metrics: current period vs prior period
# ---------------------------------------------------------------------------
def ga4_page_metrics():
    """One row per page, with current-period and prior-period organic metrics."""
    return [
        # page_path, sessions, prev_sessions, engaged, bounce_rate, avg_session_duration, conversions, prev_conversions
        {"page_path": "/roof-leakage-solutions", "sessions": 9500, "prev_sessions": 11800,
         "engaged_sessions": 5100, "bounce_rate": 0.65, "avg_session_duration": 45.0,
         "conversions": 48, "prev_conversions": 70},
        {"page_path": "/home-loans", "sessions": 7200, "prev_sessions": 7000,
         "engaged_sessions": 4600, "bounce_rate": 0.52, "avg_session_duration": 88.0,
         "conversions": 90, "prev_conversions": 86},
        {"page_path": "/best-cement-guide", "sessions": 6100, "prev_sessions": 4200,
         "engaged_sessions": 4500, "bounce_rate": 0.41, "avg_session_duration": 132.0,
         "conversions": 61, "prev_conversions": 38},
        {"page_path": "/house-construction-guide", "sessions": 5400, "prev_sessions": 6800,
         "engaged_sessions": 2700, "bounce_rate": 0.71, "avg_session_duration": 38.0,
         "conversions": 12, "prev_conversions": 22},
        {"page_path": "/foundation-info", "sessions": 3100, "prev_sessions": 3050,
         "engaged_sessions": 1500, "bounce_rate": 0.68, "avg_session_duration": 52.0,
         "conversions": 9, "prev_conversions": 11},
        {"page_path": "/waterproofing-cost-calculator", "sessions": 4300, "prev_sessions": 2600,
         "engaged_sessions": 3400, "bounce_rate": 0.39, "avg_session_duration": 165.0,
         "conversions": 120, "prev_conversions": 78},
    ]


# ---------------------------------------------------------------------------
# GSC-style search performance, aggregated by page
# ---------------------------------------------------------------------------
def gsc_page_metrics():
    return [
        # page, clicks, prev_clicks, impressions, prev_impressions, ctr, prev_ctr, position, prev_position
        {"page": "/roof-leakage-solutions", "clicks": 2850, "prev_clicks": 3900,
         "impressions": 95000, "prev_impressions": 96000, "ctr": 0.030, "prev_ctr": 0.050,
         "position": 4.3, "prev_position": 4.1},
        {"page": "/home-loans", "clicks": 2100, "prev_clicks": 2050,
         "impressions": 41000, "prev_impressions": 40500, "ctr": 0.051, "prev_ctr": 0.050,
         "position": 6.2, "prev_position": 6.4},
        {"page": "/best-cement-guide", "clicks": 1800, "prev_clicks": 1200,
         "impressions": 30000, "prev_impressions": 26000, "ctr": 0.060, "prev_ctr": 0.046,
         "position": 5.1, "prev_position": 7.8},
        {"page": "/house-construction-guide", "clicks": 1500, "prev_clicks": 2300,
         "impressions": 60000, "prev_impressions": 61000, "ctr": 0.025, "prev_ctr": 0.038,
         "position": 8.9, "prev_position": 7.2},
        {"page": "/foundation-info", "clicks": 720, "prev_clicks": 700,
         "impressions": 22000, "prev_impressions": 21500, "ctr": 0.033, "prev_ctr": 0.033,
         "position": 9.4, "prev_position": 9.1},
        {"page": "/waterproofing-cost-calculator", "clicks": 1650, "prev_clicks": 980,
         "impressions": 24000, "prev_impressions": 18000, "ctr": 0.069, "prev_ctr": 0.054,
         "position": 3.8, "prev_position": 5.5},
    ]


# Top queries per page (for intent / mismatch context in Module 1 & later)
def gsc_top_queries():
    return {
        "/house-construction-guide": [
            {"query": "best cement", "clicks": 320, "impressions": 14000, "position": 9.1},
            {"query": "cement brands comparison", "clicks": 210, "impressions": 9000, "position": 8.5},
            {"query": "house construction process", "clicks": 140, "impressions": 12000, "position": 6.0},
        ],
        "/roof-leakage-solutions": [
            {"query": "roof leakage solution", "clicks": 900, "impressions": 30000, "position": 4.0},
            {"query": "how to stop roof leakage", "clicks": 640, "impressions": 28000, "position": 4.5},
        ],
    }


# ---------------------------------------------------------------------------
# Clarity-style behaviour metrics per URL
# ---------------------------------------------------------------------------
def clarity_insights():
    return [
        # url, total_sessions, avg_scroll_percent, avg_engagement_time, dead_clicks, rage_clicks, quickback_clicks
        {"url": "/roof-leakage-solutions", "total_sessions": 2000, "avg_scroll_percent": 28,
         "avg_engagement_time": 41, "dead_clicks": 300, "rage_clicks": 45, "quickback_clicks": 120},
        {"url": "/home-loans", "total_sessions": 1600, "avg_scroll_percent": 62,
         "avg_engagement_time": 88, "dead_clicks": 40, "rage_clicks": 8, "quickback_clicks": 30},
        {"url": "/best-cement-guide", "total_sessions": 1400, "avg_scroll_percent": 74,
         "avg_engagement_time": 130, "dead_clicks": 22, "rage_clicks": 4, "quickback_clicks": 15},
        {"url": "/house-construction-guide", "total_sessions": 1200, "avg_scroll_percent": 31,
         "avg_engagement_time": 36, "dead_clicks": 180, "rage_clicks": 30, "quickback_clicks": 95},
        {"url": "/foundation-info", "total_sessions": 800, "avg_scroll_percent": 44,
         "avg_engagement_time": 50, "dead_clicks": 60, "rage_clicks": 12, "quickback_clicks": 40},
        {"url": "/waterproofing-cost-calculator", "total_sessions": 1100, "avg_scroll_percent": 81,
         "avg_engagement_time": 160, "dead_clicks": 18, "rage_clicks": 3, "quickback_clicks": 10},
    ]


# ---------------------------------------------------------------------------
# A simple funnel (Module 3)
# ---------------------------------------------------------------------------
def funnel_steps():
    return [
        {"step": "Landing page", "users": 1000},
        {"step": "Used cost calculator", "users": 480},
        {"step": "Reached lead form", "users": 190},
        {"step": "Submitted form", "users": 38},
    ]


def date_range():
    end = date(2026, 6, 24)
    start = end - timedelta(days=29)
    return start.isoformat(), end.isoformat()


# ---------------------------------------------------------------------------
# Flat GSC query list (for Module 6 — Keyword Intelligence)
# ---------------------------------------------------------------------------
def gsc_top_queries_flat():
    """Top queries ranked by clicks — mirrors what fetch_gsc_queries_flat() returns live."""
    return [
        {"query": "roof leakage solution", "clicks": 900, "impressions": 30000, "ctr": 0.030, "position": 4.0},
        {"query": "how to stop roof leakage", "clicks": 640, "impressions": 28000, "ctr": 0.023, "position": 4.5},
        {"query": "best cement brand india", "clicks": 480, "impressions": 40000, "ctr": 0.012, "position": 9.1},
        {"query": "house construction guide", "clicks": 320, "impressions": 22000, "ctr": 0.015, "position": 8.2},
        {"query": "waterproofing cost india", "clicks": 290, "impressions": 12000, "ctr": 0.024, "position": 3.8},
        {"query": "foundation repair cost", "clicks": 180, "impressions": 9000, "ctr": 0.020, "position": 9.4},
        {"query": "concrete mix ratio guide", "clicks": 150, "impressions": 15000, "ctr": 0.010, "position": 12.5},
        {"query": "home construction loan india", "clicks": 210, "impressions": 8000, "ctr": 0.026, "position": 6.2},
        {"query": "waterproofing solution for terrace", "clicks": 130, "impressions": 11000, "ctr": 0.012, "position": 14.3},
        {"query": "roof waterproofing cost per sqft", "clicks": 110, "impressions": 7500, "ctr": 0.015, "position": 11.8},
    ]


