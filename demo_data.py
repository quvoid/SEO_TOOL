"""
Demo data for AI Growth Analyst.

This lets the deployed app work immediately — before you wire up any GA4 / GSC /
Clarity / Anthropic credentials. Flip "Data source" to "Live" in the sidebar once
your keys are in .streamlit/secrets.toml.

The sample site mimics a construction / building-materials brand (roof leakage,
home loans, cement guides) so the analysis reads realistically.
"""

from datetime import date, timedelta

SITE_URL = "https://www.ultratechcement.com"


def ga4_totals():
    """GA4 overview totals for the selected period."""
    return {
        "current_total": 467279,
        "prev_total": 442860,
        "engagement_rate": 0.5075,
        "total_users": 450126,
        "returning_users": 17057,
        "new_users": 621194,
        "avg_session_duration": 121.0,
        "active_users": 436908,
        "sessions_per_user": 1.07,
        "bounce_rate": 0.4925,
    }

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
        {"query": "cement plaster wall guide", "clicks": 95, "impressions": 6200, "ctr": 0.015, "position": 18.4},
        {"query": "ultratech cement price list", "clicks": 870, "impressions": 21000, "ctr": 0.041, "position": 2.1},
        {"query": "ultratech cement dealers", "clicks": 520, "impressions": 14000, "ctr": 0.037, "position": 2.8},
        {"query": "ultratech premium cement", "clicks": 310, "impressions": 9500, "ctr": 0.033, "position": 3.2},
        {"query": "\u0905\u0932\u094d\u091f\u094d\u0930\u093e\u091f\u0947\u0915 cement", "clicks": 260, "impressions": 6800, "ctr": 0.038, "position": 2.9},
        {"query": "\u0b85\u0bb2\u0bcd\u0b9f\u0bcd\u0bb0\u0bbe cement", "clicks": 180, "impressions": 5200, "ctr": 0.035, "position": 3.4},
        {"query": "\u0c05\u0c32\u0c4d\u0c1f\u0c4d\u0c30\u0c3e cement", "clicks": 145, "impressions": 4300, "ctr": 0.034, "position": 3.8},
        {"query": "load bearing wall construction", "clicks": 88, "impressions": 5400, "ctr": 0.016, "position": 22.3},
        {"query": "earthquake resistant house design", "clicks": 72, "impressions": 4800, "ctr": 0.015, "position": 31.5},
    ]


# ---------------------------------------------------------------------------
# Previous period flat queries (for new/lost query WoW diff — Module 6)
# ---------------------------------------------------------------------------
def gsc_top_queries_flat_prev():
    """Previous period queries — some match current, some are lost, some are new in current."""
    return [
        {"query": "roof leakage solution", "clicks": 980, "impressions": 32000, "ctr": 0.031, "position": 3.8},
        {"query": "how to stop roof leakage", "clicks": 700, "impressions": 30000, "ctr": 0.023, "position": 4.2},
        {"query": "best cement brand india", "clicks": 550, "impressions": 42000, "ctr": 0.013, "position": 8.8},
        {"query": "house construction guide", "clicks": 370, "impressions": 24000, "ctr": 0.015, "position": 7.9},
        {"query": "cement plaster mix ratio", "clicks": 250, "impressions": 18000, "ctr": 0.014, "position": 6.5},
        {"query": "terrace waterproofing tips", "clicks": 180, "impressions": 9500, "ctr": 0.019, "position": 7.2},
        {"query": "home construction loan india", "clicks": 200, "impressions": 8000, "ctr": 0.025, "position": 6.5},
        {"query": "foundation repair cost", "clicks": 190, "impressions": 9500, "ctr": 0.020, "position": 9.1},
        {"query": "ultratech cement price list", "clicks": 790, "impressions": 19000, "ctr": 0.042, "position": 2.4},
        {"query": "ultratech cement dealers", "clicks": 460, "impressions": 12500, "ctr": 0.037, "position": 3.1},
        {"query": "\u0905\u0932\u094d\u091f\u094d\u0930\u093e\u091f\u0947\u0915 cement", "clicks": 230, "impressions": 6400, "ctr": 0.036, "position": 3.0},
        {"query": "building construction steps india", "clicks": 140, "impressions": 7200, "ctr": 0.019, "position": 11.3},
        {"query": "site leveling cost per sqft", "clicks": 95, "impressions": 4100, "ctr": 0.023, "position": 16.8},
    ]


# ---------------------------------------------------------------------------
# GSC Query + Page pairs (for Keyword Cannibalization — Module 6b)
# ---------------------------------------------------------------------------
def gsc_query_page_pairs():
    """GSC query+page dimension pairs — includes deliberate cannibalization examples."""
    return [
        {"query": "best cement brand india", "page": "/best-cement-guide", "clicks": 320, "impressions": 14000, "position": 5.2},
        {"query": "best cement brand india", "page": "/house-construction-guide", "clicks": 180, "impressions": 9000, "position": 8.7},
        {"query": "best cement brand india", "page": "/foundation-info", "clicks": 60, "impressions": 4000, "position": 14.2},
        {"query": "roof leakage solution", "page": "/roof-leakage-solutions", "clicks": 900, "impressions": 30000, "position": 4.0},
        {"query": "waterproofing cost india", "page": "/waterproofing-cost-calculator", "clicks": 290, "impressions": 12000, "position": 3.8},
        {"query": "waterproofing cost india", "page": "/roof-leakage-solutions", "clicks": 95, "impressions": 5000, "position": 9.1},
        {"query": "house construction guide", "page": "/house-construction-guide", "clicks": 210, "impressions": 12000, "position": 6.0},
        {"query": "house construction guide", "page": "/best-cement-guide", "clicks": 70, "impressions": 6000, "position": 11.3},
        {"query": "home loans india", "page": "/home-loans", "clicks": 420, "impressions": 15000, "position": 5.5},
        {"query": "foundation cost calculator", "page": "/waterproofing-cost-calculator", "clicks": 110, "impressions": 4500, "position": 8.9},
        {"query": "foundation cost calculator", "page": "/foundation-info", "clicks": 55, "impressions": 3200, "position": 12.4},
        {"query": "ultratech cement price list", "page": "/best-cement-guide", "clicks": 870, "impressions": 21000, "position": 2.1},
    ]


# ---------------------------------------------------------------------------
# Indexation Health (Module 9)
# ---------------------------------------------------------------------------
def indexation_summary():
    """Demo indexation health data from GSC Sitemaps API."""
    return {
        "submitted_urls": 1240,
        "indexed_urls": 980,
        "crawled_not_indexed": 142,
        "discovered_not_indexed": 88,
        "indexation_rate": 79.0,
        "sitemaps": [
            {"path": "/sitemap.xml", "submitted": 850, "indexed": 720},
            {"path": "/sitemap-blog.xml", "submitted": 390, "indexed": 260},
        ],
    }


# ---------------------------------------------------------------------------
# CrUX Field Data (for Module 7 — Real-user Core Web Vitals)
# ---------------------------------------------------------------------------
def crux_metrics():
    """Demo CrUX (Chrome User Experience Report) p75 field data per URL path."""
    return {
        "/roof-leakage-solutions": {
            "lcp_p75": 5.2, "cls_p75": 0.28, "inp_p75": 420, "fcp_p75": 3.1, "rating": "poor",
        },
        "/home-loans": {
            "lcp_p75": 2.8, "cls_p75": 0.05, "inp_p75": 180, "fcp_p75": 1.8, "rating": "needs_improvement",
        },
        "/best-cement-guide": {
            "lcp_p75": 2.1, "cls_p75": 0.02, "inp_p75": 140, "fcp_p75": 1.4, "rating": "good",
        },
        "/house-construction-guide": {
            "lcp_p75": 4.8, "cls_p75": 0.22, "inp_p75": 380, "fcp_p75": 2.9, "rating": "poor",
        },
        "/foundation-info": {
            "lcp_p75": 3.2, "cls_p75": 0.09, "inp_p75": 220, "fcp_p75": 2.1, "rating": "needs_improvement",
        },
        "/waterproofing-cost-calculator": {
            "lcp_p75": 1.9, "cls_p75": 0.01, "inp_p75": 120, "fcp_p75": 1.2, "rating": "good",
        },
    }


# ---------------------------------------------------------------------------
# Device-segmented funnel (for Module 3)
# ---------------------------------------------------------------------------
def funnel_steps_by_device():
    """Device-segmented funnel — mobile vs desktop vs tablet."""
    return {
        "mobile": [
            {"step": "Landing page", "users": 580},
            {"step": "Used cost calculator", "users": 194},
            {"step": "Reached lead form", "users": 62},
            {"step": "Submitted form", "users": 8},
        ],
        "desktop": [
            {"step": "Landing page", "users": 340},
            {"step": "Used cost calculator", "users": 242},
            {"step": "Reached lead form", "users": 116},
            {"step": "Submitted form", "users": 27},
        ],
        "tablet": [
            {"step": "Landing page", "users": 80},
            {"step": "Used cost calculator", "users": 44},
            {"step": "Reached lead form", "users": 12},
            {"step": "Submitted form", "users": 3},
        ],
    }
