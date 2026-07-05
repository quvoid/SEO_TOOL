"""
app.py — AI Growth Analyst | Schbang Analytics Platform

Architecture:
  1. Google OAuth gate (domain-locked to @schbang.com)
  2. Multi-client selector (clients.json registry)
  3. Live GA4 + GSC + Ads data — no demo toggle in the sidebar
  4. Modules 1–6 + 10 rendered with Plotly charts
  5. HTML report export

Run locally:  python -m streamlit run app.py
Deploy:       Cloud Run / Streamlit Community Cloud (see Dockerfile + README)
"""

from __future__ import annotations
import datetime as dt
import time
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import streamlit as st

import auth
import config
import demo_data
import analysis
import connectors

# ---------------------------------------------------------------------------
# Page config — must be first Streamlit call
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="AI Growth Analyst | Schbang",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Auth gate — blocks everything below if not authenticated
# ---------------------------------------------------------------------------
auth.require_login()
user = auth.get_user()

# ---------------------------------------------------------------------------
# Global CSS — premium dark-accent UI
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=DM+Sans:wght@400;500;600;700&display=swap');

/* ===== GLOBAL RESET & BASE ===== */
html, body, [class*="css"] {
    font-family: 'Inter', 'DM Sans', sans-serif;
}

/* ===== MAIN BACKGROUND ===== */
[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(135deg, #f8f7ff 0%, #f0effe 50%, #f8f7ff 100%) !important;
    min-height: 100vh;
}
[data-testid="stHeader"] {
    background: rgba(255,255,255,0.8) !important;
    backdrop-filter: blur(12px);
    border-bottom: 1px solid rgba(99,102,241,0.15);
}

/* ===== SIDEBAR ===== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0d0d1f 0%, #12122a 50%, #0d0d1f 100%) !important;
    border-right: 1px solid rgba(99,102,241,0.2);
    box-shadow: 4px 0 24px rgba(0,0,0,0.25);
}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] li { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] input { color: #1a1a1a !important; background: #ffffff !important; }
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #1a1a1a !important;
    background-color: #ffffff !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { color: #1a1a1a !important; }

/* ===== METRIC CARDS ===== */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, rgba(99,102,241,0.08) 0%, rgba(139,92,246,0.05) 100%);
    border: 1px solid rgba(99,102,241,0.25);
    border-left: 4px solid #6366f1 !important;
    border-radius: 14px;
    padding: 18px 20px !important;
    box-shadow: 0 2px 12px rgba(99,102,241,0.08), 0 1px 3px rgba(0,0,0,0.06);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stMetric"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99,102,241,0.15);
}
[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 800 !important;
    color: #1e1b4b !important;
}
[data-testid="stMetricLabel"] {
    font-size: 12px !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #6b7280 !important;
}
[data-testid="stMetricDelta"] {
    font-size: 13px !important;
    font-weight: 600 !important;
}

/* ===== SECTION HEADERS ===== */
h2 {
    font-size: 20px !important;
    font-weight: 800 !important;
    color: #1e1b4b !important;
    border-bottom: none !important;
    padding-bottom: 0 !important;
}

/* ===== DATAFRAME / TABLES ===== */
[data-testid="stDataFrame"] {
    border-radius: 14px;
    overflow: hidden;
    border: 1px solid rgba(99,102,241,0.15);
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
}

/* ===== PLOTLY CHARTS ===== */
.js-plotly-plot {
    border-radius: 14px;
    overflow: hidden;
}

/* ===== DOWNLOAD BUTTON ===== */
.stDownloadButton button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px;
    box-shadow: 0 4px 14px rgba(99,102,241,0.4) !important;
    transition: all 0.2s ease !important;
}
.stDownloadButton button:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 20px rgba(99,102,241,0.5) !important;
}

/* ===== PRIMARY BUTTON ===== */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 14px !important;
    letter-spacing: 0.3px;
    box-shadow: 0 4px 14px rgba(99,102,241,0.35) !important;
    transition: all 0.2s ease !important;
    color: white !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 8px 24px rgba(99,102,241,0.5) !important;
}

/* ===== CAPTION TEXT ===== */
.stCaption {
    color: #6b7280 !important;
    font-size: 12.5px !important;
}

/* ===== INFO/SUCCESS/WARNING/ERROR ALERTS ===== */
[data-testid="stAlert"] {
    border-radius: 12px !important;
}

/* ===== PAGE TITLE ===== */
h1 {
    font-size: 32px !important;
    font-weight: 900 !important;
    background: linear-gradient(135deg, #1e1b4b 0%, #4c1d95 50%, #6366f1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    letter-spacing: -0.5px;
}

/* ===== TABS ===== */
[data-testid="stTabs"] [role="tablist"] {
    background: rgba(99,102,241,0.06);
    border-radius: 12px;
    padding: 4px;
    gap: 4px;
    border-bottom: none !important;
}
[data-testid="stTabs"] [role="tab"] {
    border-radius: 9px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 8px 18px !important;
    transition: all 0.2s ease !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    background: white !important;
    color: #6366f1 !important;
    box-shadow: 0 2px 8px rgba(99,102,241,0.2) !important;
}

/* ===== DIVIDER ===== */
hr {
    border: none !important;
    border-top: 1px solid rgba(99,102,241,0.15) !important;
    margin: 28px 0 !important;
}

/* ===== ANIMATIONS ===== */
@keyframes fadeInUp {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}
@keyframes shimmer {
    0% { background-position: -200% center; }
    100% { background-position: 200% center; }
}
.module-card-animate {
    animation: fadeInUp 0.5s ease forwards;
}
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    st.markdown("## 📈 AI Growth Analyst")
    st.caption("**Schbang Analytics Platform**")
    st.divider()

    # User info + logout
    pic = user.get("picture", "")
    name = user.get("name", "User")
    email = user.get("email", "")
    if pic:
        col_pic, col_info = st.columns([1, 3])
        with col_pic:
            st.image(pic, width=36)
        with col_info:
            st.markdown(f"**{name}**")
            st.caption(email)
    else:
        st.markdown(f"👤 **{name}**")
        st.caption(email)

    if st.button("Logout", width='stretch'):
        auth.logout()

    st.divider()

    # Client selector
    clients = config.load_clients()
    if not clients:
        st.error("clients.json is empty or missing. Add at least one client.")
        st.stop()

    client_name = st.selectbox(
        "Client",
        list(clients.keys()),
        help="Add more clients in clients.json",
    )
    client_cfg = clients[client_name]
    is_demo = client_cfg.get("use_demo_data", False)

    if is_demo:
        st.info("📊 Demo data mode", icon="ℹ️")
    else:
        st.success("🔴 Live data", icon="✅")

    st.divider()

    # Report settings
    days = st.selectbox(
        "Comparison window",
        [7, 28, 30, 90],
        index=2,
        format_func=lambda d: f"Last {d} days vs prior {d}",
    )

    model = st.selectbox(
        "AI model",
        ["gemini-2.5-flash", "gemini-2.5-pro"],
        index=0,
        help="Flash = fast/efficient  ·  Pro = deepest reasoning",
    )

    run = st.button("▶  Run Analysis", type="primary", width='stretch')

    st.divider()

    # Integration status
    st.caption("**Integration status**")
    st.markdown(
        f"- GA4 / GSC:   {'✅ service account' if config.GCP_SERVICE_ACCOUNT else ('✅ user OAuth' if config.user_oauth_configured() else '⚠️ not configured')}\n"
        f"- AI narratives:   {'✅ Gemini' if config.GEMINI_KEY else '⚠️ no key'}"
    )


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)   # 5-min cache per client+window
def load_data(client_name: str, client_cfg_frozen: str, days: int) -> dict:
    """
    Load all data for a given client. Results are cached for 30 minutes to
    prevent quota exhaustion when multiple analysts run reports concurrently.
    client_cfg_frozen is a JSON string of the client config (for cache key).
    """
    import json
    cfg = json.loads(client_cfg_frozen)

    if cfg.get("use_demo_data"):
        demo_ga4 = demo_data.ga4_page_metrics()
        demo_sum = sum(r["sessions"] for r in demo_ga4)
        demo_prev = sum(r["prev_sessions"] for r in demo_ga4)
        return {
            "ga4": demo_ga4,
            "ga4_totals": {"current_total": demo_sum, "prev_total": demo_prev},
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
        }

    # --- Live data ---
    sa = config.GCP_SERVICE_ACCOUNT
    prop = cfg["ga4_property_id"]
    site = cfg["gsc_site_url"]
    organic_only = cfg.get("organic_only", True)

    errors: list[str] = []

    ga4 = []
    try:
        ga4 = connectors.fetch_ga4_page_metrics(prop, sa, days, organic_only)
    except Exception as exc:
        errors.append(f"GA4 error: {exc}")

    ga4_totals = {"current_total": 0, "prev_total": 0}
    try:
        ga4_totals = connectors.fetch_ga4_totals(prop, sa, days, organic_only)
    except Exception as exc:
        errors.append(f"GA4 totals error: {exc}")

    gsc = []
    try:
        gsc = connectors.fetch_gsc_page_metrics(site, sa, days)
    except Exception as exc:
        errors.append(f"GSC page error: {exc}")

    gsc_queries = []
    gsc_queries_prev = []
    try:
        gsc_queries, gsc_queries_prev = connectors.fetch_gsc_queries_with_prev(site, sa, days, top_n=200)
    except Exception as exc:
        errors.append(f"GSC queries error: {exc}")

    gsc_pairs = []
    try:
        gsc_pairs = connectors.fetch_gsc_query_page_pairs(site, sa, days, top_n=2000)
    except Exception as exc:
        errors.append(f"GSC query-page pairs error: {exc}")

    indexation = {"submitted_urls": 0, "indexed_urls": 0, "indexation_rate": 0.0, "sitemaps": []}
    try:
        indexation = connectors.fetch_gsc_indexation_summary(site, sa)
    except Exception as exc:
        errors.append(f"GSC Indexation summary error: {exc}")

    clarity = []  # Clarity is optional; no error if not configured
    clarity_token = config._s("clarity.api_token")
    if clarity_token and clarity_token not in ["CLARITY_DATA_EXPORT_TOKEN", ""]:
        try:
            clarity = connectors.fetch_clarity_insights(clarity_token)
        except Exception as exc:
            errors.append(f"Clarity error: {exc}")

    return {
        "ga4": ga4,
        "ga4_totals": ga4_totals,
        "gsc": gsc,
        "gsc_queries": gsc_queries,
        "gsc_queries_prev": gsc_queries_prev,
        "gsc_pairs": gsc_pairs,
        "clarity": clarity,
        "funnel": demo_data.funnel_steps_by_device(),   # Replace with live device funnel queries when ready
        "indexation": indexation,
        "site": site,
        "is_demo": False,
        "errors": errors,
    }


# ---------------------------------------------------------------------------
# Report runner
# ---------------------------------------------------------------------------
def run_report(client_name: str, client_cfg: dict, days: int, model: str) -> dict | None:
    import json
    data = load_data(client_name, json.dumps(client_cfg, sort_keys=True), days)

    # Show any non-fatal API errors as warnings
    for err in data.get("errors", []):
        st.warning(err)

    if not data["ga4"]:
        st.error(
            "No GA4 data returned. Check the GA4 property ID and service account "
            "permissions, then re-run."
        )
        return None

    # Fetch PageSpeed & CrUX metrics for top declining pages
    pagespeed_data = {}
    crux_data = {}
    if data.get("is_demo"):
        for page in ["/roof-leakage-solutions", "/house-construction-guide", "/home-loans"]:
            pagespeed_data[page] = {
                "url": page,
                "performance_score": 45,
                "lcp": 3.8,
                "cls": 0.18,
                "inp": 280
            }
        crux_data = data["crux"]
    else:
        declining = sorted(
            [r for r in data["ga4"] if (r.get("sessions", 0) - r.get("prev_sessions", 0)) < 0],
            key=lambda r: (r.get("sessions", 0) - r.get("prev_sessions", 0))
        )[:5]
        for r in declining:
            page_path = r["page_path"]
            # Construct absolute URL using GSC site URL prefix
            base_site = data["site"].rstrip("/")
            abs_url = base_site + ("/" if not page_path.startswith("/") else "") + page_path
            with st.spinner(f"Fetching PageSpeed Insights & CrUX field data for {page_path}…"):
                stats = connectors.fetch_pagespeed_metrics(abs_url, config.PAGESPEED_API_KEY)
                pagespeed_data[page_path] = stats
                crux_stats = connectors.fetch_crux_metrics(abs_url, config.PAGESPEED_API_KEY)
                crux_data[page_path] = crux_stats

    results: dict = {}
    gk = config.GEMINI_KEY

    with st.spinner("Module 1 — Organic Performance…"):
        results["organic"] = analysis.module_organic_performance(
            data["ga4"], data["gsc"], data["ga4_totals"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 2 — User Journey…"):
        results["journey"] = analysis.module_user_journey(
            data["ga4"], data["clarity"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 3 — Funnel Drop-off…"):
        results["funnel"] = analysis.module_funnel(data["funnel"], gk, model)
    time.sleep(6)

    with st.spinner("Module 4 — Heatmap / Click…"):
        results["heatmap"] = analysis.module_heatmap(data["clarity"], gk, model)
    time.sleep(6)

    with st.spinner("Module 5 — Scroll Analysis…"):
        results["scroll"] = analysis.module_scroll(data["clarity"], gk, model)
    time.sleep(6)

    with st.spinner("Module 6 — Keyword Intelligence…"):
        results["keywords"] = analysis.module_keyword_intelligence(
            data["gsc_queries"], gk, model, prev_queries=data["gsc_queries_prev"], site_url=data["site"]
        )
    time.sleep(6)

    with st.spinner("Module 6b — Keyword Cannibalization…"):
        results["cannibalization"] = analysis.module_cannibalization(
            data["gsc_pairs"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 7 — Declining Pages UX & Speed Audit…"):
        results["ux_audit"] = analysis.module_ux_audit(
            data["ga4"], data["gsc"], data["clarity"], pagespeed_data, gk, model, crux_data=crux_data, grok_key=config.GROK_KEY
        )
    time.sleep(6)

    with st.spinner("Module 8 — Hidden Growth Insights…"):
        results["hidden_insights"] = analysis.module_hidden_insights(
            data["ga4"], data["gsc"], data["clarity"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 9 — Indexation Health…"):
        results["indexation"] = analysis.module_indexation_health(
            data["indexation"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 10 — Executive Summary…"):
        results["exec"] = analysis.module_executive_summary(results, gk, model, grok_key=config.GROK_KEY)

    results["_meta"] = {
        "client": client_name,
        "site": data["site"],
        "is_demo": data.get("is_demo", False),
        "days": days,
        "generated": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "analyst": user.get("name", ""),
    }
    return results


# ---------------------------------------------------------------------------
# Rendering helpers
# ---------------------------------------------------------------------------
def _narrative(text: str):
    st.markdown(text)


def _plotly_bar(series: pd.Series, color: str = "#6366f1", title: str = "") -> go.Figure:
    fig = px.bar(
        x=series.index, y=series.values,
        labels={"x": "", "y": ""},
        color_discrete_sequence=[color],
    )
    fig.update_layout(
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=28 if title else 4, b=0),
        title=dict(text=title, font=dict(size=13)),
        xaxis=dict(showgrid=False),
        yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.06)"),
        font=dict(family="Inter"),
    )
    return fig


# ---------------------------------------------------------------------------
# Results renderer
# ---------------------------------------------------------------------------
def show_results(results: dict):
    meta = results["_meta"]
    demo_badge = " 〔demo data〕" if meta["is_demo"] else ""
    st.caption(
        f"**{meta['site'] or meta['client']}**{demo_badge}  ·  "
        f"Last {meta['days']} days  ·  Generated {meta['generated']}"
        + (f"  ·  by {meta['analyst']}" if meta.get("analyst") else "")
    )


    # ── Executive Summary (Module 10) ──────────────────────────────────────
    ex = results["exec"]
    m1_ref = results.get("organic", {})
    delta_pct = m1_ref.get("overall_delta_pct", 0) or 0

    # ── Health Verdict Banner ───────────────────────────────────────────────
    if delta_pct >= 5:
        verdict_bg = "linear-gradient(135deg, #064e3b, #065f46)"
        verdict_border = "rgba(16,185,129,0.4)"
        verdict_icon = "📈"
        verdict_text = "Growth on Track"
        verdict_sub = f"Organic sessions are up {delta_pct:+.1f}% vs. prior period. Maintain momentum."
        kpi_accent = "#10b981"
    elif delta_pct >= 0:
        verdict_bg = "linear-gradient(135deg, #1e3a5f, #1e40af)"
        verdict_border = "rgba(99,102,241,0.4)"
        verdict_icon = "➡️"
        verdict_text = "Stable — Optimization Needed"
        verdict_sub = f"Organic sessions flat at {delta_pct:+.1f}% vs. prior period. SEO quick-wins available."
        kpi_accent = "#6366f1"
    elif delta_pct >= -10:
        verdict_bg = "linear-gradient(135deg, #78350f, #92400e)"
        verdict_border = "rgba(245,158,11,0.4)"
        verdict_icon = "⚠️"
        verdict_text = "Caution — Sessions Declining"
        verdict_sub = f"Organic sessions down {delta_pct:.1f}% vs. prior period. Prioritize fixes immediately."
        kpi_accent = "#f59e0b"
    else:
        verdict_bg = "linear-gradient(135deg, #7f1d1d, #991b1b)"
        verdict_border = "rgba(239,68,68,0.4)"
        verdict_icon = "🚨"
        verdict_text = "Critical — Significant Traffic Drop"
        verdict_sub = f"Organic sessions down {delta_pct:.1f}% vs. prior period. Immediate action required."
        kpi_accent = "#ef4444"

    meta_site = results["_meta"].get("site", "") or results["_meta"].get("client", "")
    meta_days = results["_meta"].get("days", 30)
    meta_gen = results["_meta"].get("generated", "")

    verdict_html = f"""
    <div style="background:{verdict_bg};border:1px solid {verdict_border};border-radius:18px;
                padding:28px 32px;margin-bottom:24px;
                box-shadow:0 8px 32px rgba(0,0,0,0.2);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:12px;">
            <div>
                <div style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.6);text-transform:uppercase;
                            letter-spacing:1.5px;margin-bottom:8px;">📋 Module 10 — Executive Summary</div>
                <div style="font-size:28px;font-weight:900;color:white;margin-bottom:6px;letter-spacing:-0.5px;">
                    {verdict_icon} {verdict_text}
                </div>
                <div style="font-size:14px;color:rgba(255,255,255,0.75);max-width:500px;line-height:1.5;">{verdict_sub}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:42px;font-weight:900;color:white;letter-spacing:-1px;">{delta_pct:+.1f}%</div>
                <div style="font-size:12px;color:rgba(255,255,255,0.6);">Sessions vs prior {meta_days} days</div>
                <div style="font-size:11px;color:rgba(255,255,255,0.4);margin-top:4px;">{meta_site}</div>
            </div>
        </div>
        <div style="margin-top:16px;padding-top:16px;border-top:1px solid rgba(255,255,255,0.1);
                    font-size:11px;color:rgba(255,255,255,0.4);">
            Generated {meta_gen} · AI Growth Analyst by Schbang Analytics
        </div>
    </div>
    """
    st.html(verdict_html)

    # ── KPI Strip ──────────────────────────────────────────────────────────
    m8_ref = results.get("hidden_insights", {})
    n_losers = len(m1_ref.get("losers", []))
    n_gainers = len(m1_ref.get("gainers", []))
    n_zombies_ex = len(m8_ref.get("zombies", []))

    kpi_strip = f"""
    <div style="display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap;">
        <div style="flex:1;min-width:130px;background:white;border:1px solid rgba(99,102,241,0.2);
                    border-top:3px solid #6366f1;border-radius:14px;padding:16px 18px;text-align:center;
                    box-shadow:0 2px 10px rgba(99,102,241,0.08);">
            <div style="font-size:26px;font-weight:900;color:#1e1b4b;">{m1_ref.get('total_sessions', 0):,}</div>
            <div style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Organic Sessions</div>
            <div style="font-size:13px;font-weight:700;color:{'#10b981' if delta_pct >= 0 else '#ef4444'};margin-top:2px;">{delta_pct:+.1f}%</div>
        </div>
        <div style="flex:1;min-width:130px;background:white;border:1px solid rgba(239,68,68,0.2);
                    border-top:3px solid #ef4444;border-radius:14px;padding:16px 18px;text-align:center;
                    box-shadow:0 2px 10px rgba(239,68,68,0.06);">
            <div style="font-size:26px;font-weight:900;color:#1e1b4b;">{n_losers}</div>
            <div style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Declining Pages</div>
            <div style="font-size:13px;font-weight:700;color:#ef4444;margin-top:2px;">Needs attention</div>
        </div>
        <div style="flex:1;min-width:130px;background:white;border:1px solid rgba(16,185,129,0.2);
                    border-top:3px solid #10b981;border-radius:14px;padding:16px 18px;text-align:center;
                    box-shadow:0 2px 10px rgba(16,185,129,0.06);">
            <div style="font-size:26px;font-weight:900;color:#1e1b4b;">{n_gainers}</div>
            <div style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Growing Pages</div>
            <div style="font-size:13px;font-weight:700;color:#10b981;margin-top:2px;">Scale these up</div>
        </div>
        <div style="flex:1;min-width:130px;background:white;border:1px solid rgba(245,158,11,0.2);
                    border-top:3px solid #f59e0b;border-radius:14px;padding:16px 18px;text-align:center;
                    box-shadow:0 2px 10px rgba(245,158,11,0.06);">
            <div style="font-size:26px;font-weight:900;color:#1e1b4b;">{n_zombies_ex}</div>
            <div style="font-size:11px;font-weight:700;color:#6b7280;text-transform:uppercase;letter-spacing:0.5px;">Zombie Pages</div>
            <div style="font-size:13px;font-weight:700;color:#f59e0b;margin-top:2px;">CTR opportunity</div>
        </div>
    </div>
    """
    st.html(kpi_strip)

    # ── Key Findings as styled chips ───────────────────────────────────────
    if ex.get("key_points"):
        st.markdown("##### 📌 Key Findings")
        chips_html = '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:20px;">'
        icons = ["📊", "🛑", "🖱️", "⚡", "🧟", "🐮", "💎"]
        for i, pt in enumerate(ex["key_points"]):
            ico = icons[i % len(icons)]
            chips_html += (
                f'<div style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2);'
                f'border-radius:10px;padding:10px 14px;font-size:13px;color:#1e1b4b;'
                f'line-height:1.4;max-width:340px;">'
                f'<span style="margin-right:6px;">{ico}</span>{pt}</div>'
            )
        chips_html += "</div>"
        st.html(chips_html)

    # ── AI Narrative in styled blockquote ──────────────────────────────────
    if ex.get("narrative"):
        st.html("""<div style="background:linear-gradient(135deg,rgba(99,102,241,0.07),rgba(139,92,246,0.04));
                           border:1px solid rgba(99,102,241,0.2);border-left:4px solid #6366f1;
                           border-radius:4px 16px 16px 4px;padding:20px 24px;margin:4px 0 20px;">
                    <div style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;
                                letter-spacing:1.5px;margin-bottom:10px;">🤖 AI Executive Briefing</div>""")
        _narrative(ex["narrative"])
        st.html("</div>")

    # ── 3-Month Growth Calendar ─────────────────────────────────────────────
    st.markdown("##### 🗓️ 3-Month Growth Action Calendar")

    # Extract action items per month from narrative if available, or use standard ones
    m7_ref = results.get("ux_audit", {})
    worst_page = ""
    if m7_ref.get("audit_rows"):
        worst_speed = sorted(
            [r for r in m7_ref["audit_rows"] if r.get("pagespeed_score") is not None],
            key=lambda r: r["pagespeed_score"]
        )
        if worst_speed:
            worst_page = worst_speed[0]["page"]

    zombie_page = ""
    if m8_ref.get("zombies"):
        zombie_page = m8_ref["zombies"][0]["page"]

    gem_page = ""
    if m8_ref.get("gems"):
        gem_page = m8_ref["gems"][0]["page"]

    calendar_html = f"""
    <div style="display:flex;gap:14px;flex-wrap:wrap;margin-bottom:24px;">
        <!-- Month 1 -->
        <div style="flex:1;min-width:220px;background:linear-gradient(160deg,#fff7ed,#fef3c7);
                    border:1px solid rgba(245,158,11,0.3);border-radius:16px;padding:20px;
                    box-shadow:0 2px 12px rgba(245,158,11,0.08);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:#f59e0b;color:white;font-size:12px;font-weight:800;
                             padding:4px 10px;border-radius:20px;">Month 1</span>
                <span style="font-size:13px;font-weight:700;color:#78350f;">Speed &amp; CRO Fixes</span>
            </div>
            <ul style="margin:0;padding-left:16px;font-size:12.5px;color:#92400e;line-height:1.8;">
                <li>Fix Core Web Vitals on top declining pages{f' (esp. {worst_page[:35]})' if worst_page else ''}</li>
                <li>Remove dead click targets — make images/elements clearly non-clickable</li>
                <li>Resolve rage click hotspots — test broken buttons and CTAs</li>
                <li>Compress images &amp; enable lazy loading for LCP improvements</li>
                <li>A/B test above-fold CTAs on high-traffic pages</li>
            </ul>
        </div>
        <!-- Month 2 -->
        <div style="flex:1;min-width:220px;background:linear-gradient(160deg,#eef2ff,#e0e7ff);
                    border:1px solid rgba(99,102,241,0.3);border-radius:16px;padding:20px;
                    box-shadow:0 2px 12px rgba(99,102,241,0.08);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:#6366f1;color:white;font-size:12px;font-weight:800;
                             padding:4px 10px;border-radius:20px;">Month 2</span>
                <span style="font-size:13px;font-weight:700;color:#1e1b4b;">SEO Quick Wins</span>
            </div>
            <ul style="margin:0;padding-left:16px;font-size:12.5px;color:#3730a3;line-height:1.8;">
                <li>Rewrite title tags &amp; meta descriptions for zombie pages{f' (start: {zombie_page[:30]})' if zombie_page else ''}</li>
                <li>Target position 4–20 keywords — push to top 3 with on-page updates</li>
                <li>Optimize H1/H2 hierarchy for top GSC opportunity queries</li>
                <li>Add schema markup (FAQ, How-To) to high-impression pages</li>
                <li>Build internal links pointing to top keyword opportunity pages</li>
            </ul>
        </div>
        <!-- Month 3 -->
        <div style="flex:1;min-width:220px;background:linear-gradient(160deg,#f0fdf4,#dcfce7);
                    border:1px solid rgba(16,185,129,0.3);border-radius:16px;padding:20px;
                    box-shadow:0 2px 12px rgba(16,185,129,0.08);">
            <div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;">
                <span style="background:#10b981;color:white;font-size:12px;font-weight:800;
                             padding:4px 10px;border-radius:20px;">Month 3</span>
                <span style="font-size:13px;font-weight:700;color:#065f46;">Content Expansion</span>
            </div>
            <ul style="margin:0;padding-left:16px;font-size:12.5px;color:#065f46;line-height:1.8;">
                <li>Expand unexplored gem pages with deeper content{f' (esp. {gem_page[:30]})' if gem_page else ''}</li>
                <li>Create supporting cluster content for top-performing topics</li>
                <li>Identify and fix keyword cannibalization conflicts</li>
                <li>Launch link-building campaign for highest-potential pages</li>
                <li>Run full audit of scroll depth — restructure low-scroll content</li>
            </ul>
        </div>
    </div>
    """
    st.html(calendar_html)
    st.divider()

    # ── Module 1 — Organic Performance ────────────────────────────────────
    m1 = results["organic"]
    st.subheader("📊 " + m1["title"])
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric(
        "Organic sessions",
        f"{m1['total_sessions']:,}",
        f"{m1['overall_delta_pct']:+.1f}%",
    )
    mc2.metric("Declining pages", len(m1["losers"]))
    mc3.metric("Growing pages", len(m1["gainers"]))

    pages_list = m1.get("all_pages", m1.get("losers", []))
    if pages_list:
        df = pd.DataFrame(pages_list)
        # Sort by sessions descending and limit to top 15
        df = df.sort_values(by="sessions", ascending=False).head(15)
        
        # Add Status column
        def _get_status(val):
            if val is None or val == 0:
                return "➖ Flat"
            return "📈 Growing" if val > 0 else "🛑 Declining"
        df["Status"] = df["session_delta_pct"].apply(_get_status)
        
        df = df[[
            "page", "Status", "sessions", "session_delta_pct",
            "ctr", "ctr_delta_pct", "position", "position_delta"
        ]]
        df.columns = ["Page Path", "Status", "Sessions", "Sessions Δ%", "CTR", "CTR Δ%", "Avg pos", "Pos Δ"]
        st.dataframe(df, width='stretch', hide_index=True)
    _narrative(m1["narrative"])
    st.divider()

    # ── Module 2 — User Journey ────────────────────────────────────────────
    m2 = results["journey"]
    st.subheader("🧭 " + m2["title"])
    if m2["flagged"]:
        df = pd.DataFrame(m2["flagged"]).rename(columns={
            "page": "Page", "bounce_rate": "Bounce",
            "scroll_percent": "Scroll %", "dead_clicks": "Dead clicks",
            "rage_clicks": "Rage clicks", "avg_session_duration": "Avg time (s)",
        })
        st.dataframe(df, width='stretch', hide_index=True)
    else:
        st.info("No high-bounce + low-scroll pages flagged. UX looks healthy.")
    _narrative(m2["narrative"])
    st.divider()

    # ── Module 3 — Funnel ─────────────────────────────────────────────────
    m3 = results["funnel"]
    st.subheader("🔽 " + m3["title"])
    fdf = pd.DataFrame(m3["steps"]).set_index("step")["users"]
    st.plotly_chart(_plotly_bar(fdf, "#8b5cf6"), width='stretch')
    st.caption(
        f"Overall completion: **{m3['overall_completion_pct']:.1f}%**  ·  "
        f"Biggest drop: **{m3['biggest_drop']['step']}** "
        f"({m3['biggest_drop']['drop_pct']:.0f}%)"
    )
    _narrative(m3["narrative"])
    st.divider()

    # ── Module 4 — Heatmap ────────────────────────────────────────────────
    m4 = results["heatmap"]
    st.subheader("🖱️ " + m4["title"])

    # ── Legend strip ──────────────────────────────────────────────────────
    legend_html = """
    <div style="display:flex;gap:20px;flex-wrap:wrap;margin-bottom:20px;padding:14px 18px;
                background:linear-gradient(135deg,rgba(99,102,241,0.06),rgba(139,92,246,0.04));
                border-radius:12px;border:1px solid rgba(99,102,241,0.15);">
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:20px;">💀</span>
            <div>
                <div style="font-weight:700;font-size:13px;color:#1e1b4b;">Dead Clicks</div>
                <div style="font-size:11px;color:#6b7280;max-width:160px;">User clicks on non-interactive elements (images, text that looks like a button)</div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:20px;">😡</span>
            <div>
                <div style="font-weight:700;font-size:13px;color:#1e1b4b;">Rage Clicks</div>
                <div style="font-size:11px;color:#6b7280;max-width:160px;">Frustrated repeated clicks — user expected something to happen but it didn't</div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:20px;">⚡</span>
            <div>
                <div style="font-weight:700;font-size:13px;color:#1e1b4b;">Quickbacks</div>
                <div style="font-size:11px;color:#6b7280;max-width:160px;">User landed, immediately left — content didn't match their expectation</div>
            </div>
        </div>
        <div style="display:flex;align-items:center;gap:8px;">
            <span style="font-size:20px;">🌡️</span>
            <div>
                <div style="font-weight:700;font-size:13px;color:#1e1b4b;">Frustration Score</div>
                <div style="font-size:11px;color:#6b7280;max-width:160px;">Weighted score: Dead×1 + Rage×3 + Quickbacks×2 (higher = more urgent fix)</div>
            </div>
        </div>
    </div>
    """
    st.html(legend_html)

    all_clarity = results.get("heatmap", {}).get("flagged", [])
    # Fallback: if flagged is empty but we have clarity data, show top 5 by score
    if not all_clarity:
        import json as _json
        raw_clarity = st.session_state.get("_clarity_raw", [])
        all_clarity = sorted(
            raw_clarity,
            key=lambda c: c.get("dead_clicks", 0) + c.get("rage_clicks", 0) * 2,
            reverse=True
        )[:5]

    if m4["flagged"] or all_clarity:
        display_rows = m4["flagged"] if m4["flagged"] else all_clarity

        # ── Per-page frustration cards ─────────────────────────────────────
        max_score = max(
            (r.get("dead_clicks", 0) + r.get("rage_clicks", 0) * 3 + r.get("quickback_clicks", 0) * 2)
            for r in display_rows
        ) or 1

        for i, row in enumerate(display_rows):
            url = row.get("url", "Unknown")
            dead = row.get("dead_clicks", 0)
            rage = row.get("rage_clicks", 0)
            quick = row.get("quickback_clicks", 0)
            sessions = row.get("total_sessions", 0)
            score = dead + rage * 3 + quick * 2
            score_pct = min(100, int(score / max_score * 100))

            # Risk classification
            if rage >= 10 or score > 150:
                risk_color = "#ef4444"
                risk_bg = "rgba(239,68,68,0.08)"
                risk_border = "rgba(239,68,68,0.3)"
                risk_label = "🔴 Critical"
                bar_color = "#ef4444"
            elif rage >= 5 or dead >= 50 or score > 70:
                risk_color = "#f59e0b"
                risk_bg = "rgba(245,158,11,0.08)"
                risk_border = "rgba(245,158,11,0.3)"
                risk_label = "🟡 Moderate"
                bar_color = "#f59e0b"
            else:
                risk_color = "#10b981"
                risk_bg = "rgba(16,185,129,0.08)"
                risk_border = "rgba(16,185,129,0.3)"
                risk_label = "🟢 Healthy"
                bar_color = "#10b981"

            # Truncate long URL for display
            url_display = url
            if "://" in url_display:
                url_display = "/" + url_display.split("/", 3)[-1]
            if len(url_display) > 60:
                url_display = url_display[:57] + "…"

            card_html = f"""
            <div style="background:{risk_bg};border:1px solid {risk_border};border-left:4px solid {risk_color};
                        border-radius:14px;padding:18px 22px;margin-bottom:14px;
                        animation:fadeInUp 0.4s ease {i*0.08:.2f}s both;">
                <div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:14px;">
                    <div>
                        <div style="font-weight:700;font-size:14px;color:#1e1b4b;margin-bottom:2px;"
                             title="{url}">{url_display}</div>
                        <div style="font-size:11px;color:#9ca3af;">{sessions:,} sessions analysed</div>
                    </div>
                    <span style="background:{risk_color};color:white;font-size:11px;font-weight:700;
                                 padding:4px 10px;border-radius:20px;white-space:nowrap;">{risk_label}</span>
                </div>
                <div style="display:flex;gap:24px;margin-bottom:14px;flex-wrap:wrap;">
                    <div style="text-align:center;min-width:60px;">
                        <div style="font-size:11px;color:#6b7280;font-weight:600;margin-bottom:2px;">💀 DEAD</div>
                        <div style="font-size:22px;font-weight:800;color:#1e1b4b;">{dead:,}</div>
                    </div>
                    <div style="text-align:center;min-width:60px;">
                        <div style="font-size:11px;color:#6b7280;font-weight:600;margin-bottom:2px;">😡 RAGE</div>
                        <div style="font-size:22px;font-weight:800;color:{risk_color};">{rage:,}</div>
                    </div>
                    <div style="text-align:center;min-width:60px;">
                        <div style="font-size:11px;color:#6b7280;font-weight:600;margin-bottom:2px;">⚡ QUICK</div>
                        <div style="font-size:22px;font-weight:800;color:#6366f1;">{quick:,}</div>
                    </div>
                    <div style="flex:1;min-width:140px;display:flex;flex-direction:column;justify-content:center;">
                        <div style="display:flex;justify-content:space-between;margin-bottom:5px;">
                            <span style="font-size:11px;color:#6b7280;font-weight:600;">🌡️ FRUSTRATION SCORE</span>
                            <span style="font-size:12px;font-weight:800;color:{bar_color};">{score_pct}%</span>
                        </div>
                        <div style="background:rgba(0,0,0,0.08);border-radius:8px;height:10px;overflow:hidden;">
                            <div style="width:{score_pct}%;background:linear-gradient(90deg,{bar_color}cc,{bar_color});
                                        height:100%;border-radius:8px;transition:width 0.8s ease;"></div>
                        </div>
                    </div>
                </div>
            </div>
            """
            st.html(card_html)

        # ── Plotly frustration bar chart ────────────────────────────────────
        st.markdown("#### 📊 Frustration Score by Page")
        st.caption("Weighted score: Dead clicks ×1 + Rage clicks ×3 + Quickbacks ×2. Color = severity level.")

        import plotly.graph_objects as _go
        page_labels = []
        score_vals = []
        bar_colors = []
        for row in display_rows:
            url = row.get("url", "")
            if "://" in url:
                label = "/" + url.split("/", 3)[-1]
            else:
                label = url
            if len(label) > 45:
                label = label[:42] + "…"
            sc = row.get("dead_clicks", 0) + row.get("rage_clicks", 0) * 3 + row.get("quickback_clicks", 0) * 2
            page_labels.append(label)
            score_vals.append(sc)
            # Color by rage severity
            rage_c = row.get("rage_clicks", 0)
            if rage_c >= 10 or sc > 150:
                bar_colors.append("#ef4444")
            elif rage_c >= 5 or sc > 70:
                bar_colors.append("#f59e0b")
            else:
                bar_colors.append("#10b981")

        fig_heat = _go.Figure(_go.Bar(
            x=score_vals,
            y=page_labels,
            orientation="h",
            marker=dict(color=bar_colors, line=dict(width=0)),
            text=[f"Score: {v}" for v in score_vals],
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Frustration Score: %{x}<extra></extra>",
        ))
        fig_heat.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=60, t=10, b=10),
            xaxis=dict(
                title="Frustration Score",
                showgrid=True,
                gridcolor="rgba(99,102,241,0.1)",
                title_font=dict(size=12, color="#6b7280"),
            ),
            yaxis=dict(
                showgrid=False,
                automargin=True,
                tickfont=dict(size=12, family="Inter"),
            ),
            font=dict(family="Inter", color="#374151"),
            height=max(220, len(display_rows) * 52),
            bargap=0.3,
        )
        # Add reference line at score=70 (moderate threshold)
        fig_heat.add_vline(x=70, line_dash="dot", line_color="#f59e0b",
                           annotation_text="Moderate threshold",
                           annotation_position="top right",
                           annotation_font_size=11)
        st.plotly_chart(fig_heat, use_container_width=True)

    else:
        st.html("""
        <div style="background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);
                    border-radius:14px;padding:20px 24px;text-align:center;">
            <div style="font-size:28px;margin-bottom:8px;">✅</div>
            <div style="font-weight:700;font-size:15px;color:#065f46;">No significant click frustration detected</div>
            <div style="font-size:13px;color:#6b7280;margin-top:4px;">All pages are within acceptable dead/rage click thresholds</div>
        </div>
        """)

    # AI narrative in styled card
    if m4.get("narrative"):
        st.html("""<div style="background:rgba(99,102,241,0.05);border-left:3px solid #6366f1;
                           border-radius:0 12px 12px 0;padding:14px 18px;margin:12px 0;">
                    <span style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;letter-spacing:1px;">
                        🤖 AI Analysis</span></div>""")
        _narrative(m4["narrative"])
    st.divider()

    # ── Module 5 — Scroll ─────────────────────────────────────────────────
    m5 = results["scroll"]
    st.subheader("📜 " + m5["title"])
    st.caption("Average scroll depth per page. Below 40% (red) means most visitors never see below-the-fold content.")
    
    pages = m5.get("all_pages", m5.get("low_scroll_pages", []))
    if pages:
        df_data = []
        for p in pages:
            url_val = p.get("url") or p.get("page") or ""
            url_display = url_val
            if "://" in url_display:
                url_display = "/" + url_display.split("/", 3)[-1]
            
            scroll_val = float(p.get("avg_scroll_percent", 0.0))
            sessions_val = int(p.get("total_sessions", 0))
            
            df_data.append({
                "Page Path": url_display,
                "Average Scroll Depth": scroll_val,
                "Sessions": sessions_val,
            })
            
        df_scroll = pd.DataFrame(df_data)
        
        # Search and sort controls
        col_filter, col_sort = st.columns([2, 1])
        with col_filter:
            search_query = st.text_input("🔍 Search Page Path", placeholder="Filter by URL path...", key="scroll_search_input")
        with col_sort:
            sort_order = st.selectbox(
                "↕️ Default Sort Order",
                ["Worst First (Ascending)", "Best First (Descending)"],
                index=0,
                key="scroll_sort_select"
            )
            
        # Apply filtering
        if search_query:
            df_scroll = df_scroll[df_scroll["Page Path"].str.contains(search_query, case=False, na=False)]
            
        # Apply default sorting
        ascending_bool = (sort_order == "Worst First (Ascending)")
        df_scroll = df_scroll.sort_values(by="Average Scroll Depth", ascending=ascending_bool)
        
        # Render sortable/filterable dataframe
        st.dataframe(
            df_scroll,
            column_config={
                "Page Path": st.column_config.TextColumn(
                    "Page Path",
                    help="Cleaned URL path of the page",
                    width="medium"
                ),
                "Average Scroll Depth": st.column_config.ProgressColumn(
                    "Average Scroll Depth",
                    help="Average scroll percentage of page height",
                    format="%.1f%%",
                    min_value=0.0,
                    max_value=100.0
                ),
                "Sessions": st.column_config.NumberColumn(
                    "Sessions",
                    help="Total sessions analyzed",
                    format="%d"
                ),
            },
            hide_index=True,
            use_container_width=True
        )
        
        st.html("""
        <div style="font-size:12.5px;color:#ef4444;font-weight:600;margin-top:8px;margin-bottom:16px;">
            ⚠️ 40% threshold – pages below this require placing call-to-action buttons (CTAs) and important value propositions higher up.
        </div>
        """)
    else:
        st.info("No scroll depth data available.")
    _narrative(m5["narrative"])
    st.divider()


    # ── Module 6 — Keyword Intelligence ───────────────────────────────────
    m6 = results["keywords"]
    st.subheader("🔍 " + m6["title"])
    st.caption(
        f"Analysed **{m6['total_queries_analysed']}** GSC queries to identify "
        "low-hanging organic search optimization opportunities."
    )

    # 1. Branded vs Non-Branded Split
    st.markdown("### 🏷️ Branded vs Non-Branded Query Split")
    total_clicks = m6["brand_clicks"] + m6["non_brand_clicks"]
    brand_pct = m6["brand_click_pct"]
    non_brand_pct = 100.0 - brand_pct if total_clicks else 100.0

    col_brand1, col_brand2 = st.columns(2)
    with col_brand1:
        st.metric("Branded Clicks", f"{m6['brand_clicks']:,}", f"{brand_pct:.1f}% of total")
        if m6.get("brand_terms"):
            st.caption(f"Brand terms detected: `{', '.join(m6['brand_terms'])}`")
        else:
            st.caption("No brand terms configured.")
    with col_brand2:
        st.metric("Non-Branded Clicks", f"{m6['non_brand_clicks']:,}", f"{non_brand_pct:.1f}% of total")
        st.caption("Discovery search visibility")

    st.progress(brand_pct / 100.0 if total_clicks else 0.0, text=f"Branded Clicks ({brand_pct:.1f}%) vs Non-Branded Clicks ({non_brand_pct:.1f}%)")

    # 2. Striking Distance Opportunities & Position Distribution
    st.markdown("### 🎯 Position Distribution & Striking Distance Buckets")
    st.caption("Segmented queries by their average ranking position band on Google.")

    tab_1_3, tab_4_10, tab_11_20, tab_21_50 = st.tabs([
        f"🥇 Rank 1-3 ({len(m6['bands']['1-3'])})",
        f"🎯 Rank 4-10 ({len(m6['bands']['4-10'])}) - Striking Distance",
        f"📈 Rank 11-20 ({len(m6['bands']['11-20'])})",
        f"🔍 Rank 21-50 ({len(m6['bands']['21-50'])})"
    ])

    def _render_band_df(queries_list):
        if not queries_list:
            st.info("No queries found in this position band.")
            return
        band_df = pd.DataFrame(queries_list)[["query", "clicks", "impressions", "ctr", "position"]]
        band_df = band_df.rename(columns={
            "query": "Query", "clicks": "Clicks", "impressions": "Impressions",
            "ctr": "CTR", "position": "Position"
        })
        band_df["CTR"] = band_df["CTR"].apply(lambda val: f"{val * 100:.2f}%")
        band_df["Position"] = band_df["Position"].round(1)
        st.dataframe(band_df, width='stretch', hide_index=True)

    with tab_1_3:
        _render_band_df(m6['bands']['1-3'])
    with tab_4_10:
        st.caption("Keywords ranking on page 1 but not in top 3. High opportunity, responsive to on-page & link edits.")
        _render_band_df(m6['bands']['4-10'])
    with tab_11_20:
        _render_band_df(m6['bands']['11-20'])
    with tab_21_50:
        _render_band_df(m6['bands']['21-50'])

    # 3. New vs Lost Queries
    st.markdown("### 🔄 New vs Lost Queries (Week-over-Week Diff)")
    col_queries1, col_queries2 = st.columns(2)

    with col_queries1:
        st.subheader("🆕 New Queries")
        st.caption("Keywords the site ranked for this period, but not in the prior period.")
        if m6.get("new_queries"):
            new_df = pd.DataFrame(m6["new_queries"])[["query", "clicks", "impressions", "position"]]
            new_df = new_df.rename(columns={"query": "Query", "clicks": "Clicks", "impressions": "Impressions", "position": "Position"})
            new_df["Position"] = new_df["Position"].round(1)
            st.dataframe(new_df, width='stretch', hide_index=True)
        else:
            st.info("No new queries detected.")

    with col_queries2:
        st.subheader("⚠️ Lost Queries")
        st.caption("Keywords the site ranked for in the prior period, but not in this period.")
        if m6.get("lost_queries"):
            lost_df = pd.DataFrame(m6["lost_queries"])[["query", "clicks", "impressions", "position"]]
            lost_df = lost_df.rename(columns={"query": "Query", "clicks": "Clicks", "impressions": "Impressions", "position": "Position"})
            lost_df["Position"] = lost_df["Position"].round(1)
            st.dataframe(lost_df, width='stretch', hide_index=True)
        else:
            st.info("No lost queries detected.")

    st.markdown("### 🚀 SEO Click Uplift Opportunities (Top 10)")
    if m6["opportunities"]:
        df = pd.DataFrame(m6["opportunities"])
        df = df.rename(columns={
            "query": "Query",
            "position": "Position",
            "impressions": "Impressions (proxy for volume)",
            "current_clicks": "Current clicks",
            "potential_clicks": "Potential clicks (top 3)",
            "click_uplift": "Click uplift",
        })
        st.dataframe(df, width='stretch', hide_index=True)

        # Opportunity bar chart — click uplift by keyword
        uplift_df = (
            pd.DataFrame(m6["opportunities"])
            .set_index("query")["click_uplift"]
            .head(8)
        )
        st.plotly_chart(
            _plotly_bar(uplift_df, "#22c55e", "Click uplift potential by keyword"),
            width='stretch',
        )
    _narrative(m6["narrative"])
    st.divider()

    # ── Module 6b — Keyword Cannibalization ────────────────────────────────
    m6b = results.get("cannibalization")
    if m6b:
        st.subheader("⚔️ " + m6b["title"])
        st.caption("Detects when multiple pages rank for the same search query, diluting your organic authority.")

        if m6b.get("conflicts"):
            conflicts_data = []
            for c in m6b["conflicts"]:
                conflicts_data.append({
                    "Query": c["query"],
                    "Competitors": c["num_pages"],
                    "Total Clicks": c["total_clicks"],
                    "Total Impressions": c["total_impressions"],
                    "Preferred Owner": c["winner"],
                    "Owner Click Share": f"{c['winner_click_share']:.1f}%",
                    "Severity": c["severity"]
                })
            st.dataframe(pd.DataFrame(conflicts_data), width='stretch', hide_index=True)

            with st.expander("🔍 View Competing URLs Breakdown"):
                for c in m6b["conflicts"][:5]:
                    st.write(f"**Query:** `{c['query']}` (Impressions: {c['total_impressions']:,} · Severity: {c['severity']})")
                    comp_df = pd.DataFrame(c["competing_pages"])[["page", "clicks", "impressions", "ctr", "position"]]
                    comp_df = comp_df.rename(columns={"page": "URL Path", "clicks": "Clicks", "impressions": "Impressions", "ctr": "CTR", "position": "Position"})
                    comp_df["CTR"] = comp_df["CTR"].apply(lambda v: f"{v*100:.2f}%")
                    comp_df["Position"] = comp_df["Position"].round(1)
                    st.dataframe(comp_df, width='stretch', hide_index=True)
        else:
            st.success("No keyword cannibalization conflicts detected.")

        _narrative(m6b["narrative"])
        st.divider()

    # ── Module 7 — Declining Pages UX & Speed Audit ────────────────────────
    m7 = results.get("ux_audit")
    if m7:
        st.subheader("🏥 " + m7["title"])
        st.caption("Correlating search session losses with user frustration signals (dead/rage clicks) and mobile PageSpeed performance (Lab vs CrUX Field data).")
        if m7.get("audit_rows"):
            df7 = pd.DataFrame(m7["audit_rows"])[[
                "page", "sessions", "session_change_pct", "avg_position",
                "pagespeed_score", "lcp", "crux_lcp", "crux_cls", "crux_inp", "crux_rating",
                "dead_clicks", "rage_clicks", "risk_level"
            ]]
            df7.columns = [
                "Page Path", "Sessions", "Change %", "Avg Rank", 
                "Lab PageSpeed %", "Lab LCP (s)", "CrUX LCP (s)", "CrUX CLS", "CrUX INP (ms)", "CrUX Rating",
                "Dead Clicks", "Rage Clicks", "UX Risk Level"
            ]
            df7["CrUX LCP (s)"] = df7["CrUX LCP (s)"].apply(lambda x: f"{x:.2f}s" if pd.notnull(x) and x != "" else "n/a")
            df7["CrUX CLS"] = df7["CrUX CLS"].apply(lambda x: f"{x:.3f}" if pd.notnull(x) and x != "" else "n/a")
            df7["CrUX INP (ms)"] = df7["CrUX INP (ms)"].apply(lambda x: f"{int(x)}ms" if pd.notnull(x) and x != "" else "n/a")
            df7["CrUX Rating"] = df7["CrUX Rating"].apply(lambda x: str(x).upper().replace('_', ' ') if pd.notnull(x) and x != "" else "N/A")
            st.dataframe(df7, width='stretch', hide_index=True)
        _narrative(m7["narrative"])
        st.divider()

    # ── Module 8 — Hidden Growth Insights ─────────────────────────────────
    m8 = results.get("hidden_insights")
    if m8:
        st.subheader("💡 " + m8["title"])
        st.caption("AI-detected hidden patterns: pages leaking clicks, undervalued pages needing SEO push, and high-value pages where UX friction is costing conversions.")

        # ── KPI summary strip ───────────────────────────────────────────────
        n_zombies = len(m8.get("zombies", []))
        n_gems = len(m8.get("gems", []))
        n_cows = len(m8.get("cows", []))

        kpi_html = f"""
        <div style="display:flex;gap:14px;margin-bottom:28px;flex-wrap:wrap;">
            <div style="flex:1;min-width:140px;background:linear-gradient(135deg,rgba(245,158,11,0.12),rgba(245,158,11,0.06));
                        border:1px solid rgba(245,158,11,0.3);border-top:3px solid #f59e0b;border-radius:14px;padding:18px 20px;text-align:center;">
                <div style="font-size:32px;font-weight:900;color:#92400e;">{n_zombies}</div>
                <div style="font-size:12px;font-weight:700;color:#b45309;text-transform:uppercase;letter-spacing:0.5px;">🧟 Zombie Pages</div>
                <div style="font-size:11px;color:#9ca3af;margin-top:3px;">High impressions, low CTR</div>
            </div>
            <div style="flex:1;min-width:140px;background:linear-gradient(135deg,rgba(99,102,241,0.10),rgba(99,102,241,0.05));
                        border:1px solid rgba(99,102,241,0.25);border-top:3px solid #6366f1;border-radius:14px;padding:18px 20px;text-align:center;">
                <div style="font-size:32px;font-weight:900;color:#3730a3;">{n_gems}</div>
                <div style="font-size:12px;font-weight:700;color:#4338ca;text-transform:uppercase;letter-spacing:0.5px;">💎 Unexplored Gems</div>
                <div style="font-size:11px;color:#9ca3af;margin-top:3px;">High engagement, low SEO visibility</div>
            </div>
            <div style="flex:1;min-width:140px;background:linear-gradient(135deg,rgba(239,68,68,0.10),rgba(239,68,68,0.05));
                        border:1px solid rgba(239,68,68,0.25);border-top:3px solid #ef4444;border-radius:14px;padding:18px 20px;text-align:center;">
                <div style="font-size:32px;font-weight:900;color:#991b1b;">{n_cows}</div>
                <div style="font-size:12px;font-weight:700;color:#dc2626;text-transform:uppercase;letter-spacing:0.5px;">🐮 Friction Cash Cows</div>
                <div style="font-size:11px;color:#9ca3af;margin-top:3px;">High traffic, high UX friction</div>
            </div>
        </div>
        """
        st.html(kpi_html)

        # ── 🧟 Zombie Pages Card ───────────────────────────────────────────
        zombie_header = """
        <div style="background:linear-gradient(135deg,#fffbeb,#fef3c7);border:1px solid rgba(245,158,11,0.35);
                    border-left:5px solid #f59e0b;border-radius:14px;padding:18px 22px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                    <div style="font-size:17px;font-weight:800;color:#78350f;">🧟 Zombie Pages</div>
                    <div style="font-size:12px;color:#92400e;margin-top:2px;">High impressions, low CTR, ranking position &lt; 20 — title &amp; snippet need a rewrite</div>
                </div>
                <span style="background:#f59e0b;color:white;font-size:11px;font-weight:700;
                             padding:5px 12px;border-radius:20px;">High Priority</span>
            </div>
        """
        st.html(zombie_header)

        if m8.get("zombies"):
            for i, z in enumerate(m8["zombies"][:5]):
                page = z.get("page", "")
                imps = z.get("impressions", 0)
                ctr = z.get("ctr", 0)
                pos = z.get("position", 0)
                # CTR gap vs 3% avg
                ctr_gap = max(0, min(100, int((3.0 - ctr) / 3.0 * 100))) if ctr < 3 else 0

                page_display = page
                if "://" in page_display:
                    page_display = "/" + page_display.split("/", 3)[-1]
                if len(page_display) > 65:
                    page_display = page_display[:62] + "…"

                z_card = f"""
                <div style="background:white;border:1px solid rgba(245,158,11,0.2);border-radius:10px;
                            padding:14px 16px;margin-bottom:10px;margin-left:4px;">
                    <div style="font-weight:700;font-size:13px;color:#1e1b4b;margin-bottom:10px;" title="{page}">{page_display}</div>
                    <div style="display:flex;gap:16px;margin-bottom:10px;flex-wrap:wrap;">
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">IMPRESSIONS</div>
                            <div style="font-size:18px;font-weight:800;color:#1e1b4b;">{imps:,}</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">CTR</div>
                            <div style="font-size:18px;font-weight:800;color:#ef4444;">{ctr:.2f}%</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">POSITION</div>
                            <div style="font-size:18px;font-weight:800;color:#f59e0b;">{pos:.1f}</div>
                        </div>
                        <div style="flex:1;min-width:120px;display:flex;flex-direction:column;justify-content:center;">
                            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                                <span style="font-size:11px;color:#6b7280;font-weight:600;">CTR GAP vs 3% avg</span>
                                <span style="font-size:11px;font-weight:700;color:#ef4444;">-{ctr_gap}%</span>
                            </div>
                            <div style="background:#fee2e2;border-radius:6px;height:8px;overflow:hidden;">
                                <div style="width:{ctr_gap}%;background:linear-gradient(90deg,#fca5a5,#ef4444);height:100%;border-radius:6px;"></div>
                            </div>
                        </div>
                    </div>
                </div>
                """
                st.html(z_card)
            st.html("</div>")
        else:
            st.html("""<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px;">✅ No zombie pages detected — CTR is healthy across all high-impression pages</div></div>""")

        # ── 💎 Unexplored Gems Card ────────────────────────────────────────
        gem_header = """
        <div style="background:linear-gradient(135deg,#eef2ff,#e0e7ff);border:1px solid rgba(99,102,241,0.3);
                    border-left:5px solid #6366f1;border-radius:14px;padding:18px 22px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                    <div style="font-size:17px;font-weight:800;color:#1e1b4b;">💎 Unexplored Gems</div>
                    <div style="font-size:12px;color:#4338ca;margin-top:2px;">High user engagement but low Google Search visibility — push with SEO &amp; internal linking</div>
                </div>
                <span style="background:#6366f1;color:white;font-size:11px;font-weight:700;
                             padding:5px 12px;border-radius:20px;">Optimize Now</span>
            </div>
        """
        st.html(gem_header)

        if m8.get("gems"):
            for i, g in enumerate(m8["gems"][:5]):
                page = g.get("page", "")
                scroll = g.get("avg_scroll_percent", 0)
                duration = g.get("avg_duration", 0)
                sessions = g.get("sessions", 0)
                gsc_imps = g.get("impressions", 0)

                page_display = page
                if len(page_display) > 65:
                    page_display = page_display[:62] + "…"

                # Scroll color
                scroll_color = "#10b981" if scroll >= 60 else "#6366f1" if scroll >= 40 else "#f59e0b"

                g_card = f"""
                <div style="background:white;border:1px solid rgba(99,102,241,0.2);border-radius:10px;
                            padding:14px 16px;margin-bottom:10px;margin-left:4px;">
                    <div style="font-weight:700;font-size:13px;color:#1e1b4b;margin-bottom:10px;" title="{page}">{page_display}</div>
                    <div style="display:flex;gap:16px;margin-bottom:10px;flex-wrap:wrap;">
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">SCROLL DEPTH</div>
                            <div style="font-size:18px;font-weight:800;color:{scroll_color};">{scroll:.0f}%</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">AVG DURATION</div>
                            <div style="font-size:18px;font-weight:800;color:#6366f1;">{duration:.0f}s</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">SESSIONS</div>
                            <div style="font-size:18px;font-weight:800;color:#1e1b4b;">{sessions:,}</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">GSC IMPS</div>
                            <div style="font-size:18px;font-weight:800;color:#9ca3af;">{gsc_imps:,}</div>
                        </div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <span style="font-size:11px;color:#6b7280;font-weight:600;">SCROLL DEPTH</span>
                        <span style="font-size:11px;font-weight:700;color:{scroll_color};">{scroll:.0f}%</span>
                    </div>
                    <div style="background:#e0e7ff;border-radius:6px;height:8px;overflow:hidden;">
                        <div style="width:{min(100,int(scroll))}%;background:linear-gradient(90deg,#a5b4fc,#6366f1);height:100%;border-radius:6px;"></div>
                    </div>
                </div>
                """
                st.html(g_card)
            st.html("</div>")
        else:
            st.html("""<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px;">✅ No undervalued pages found — all high-engagement pages have solid GSC visibility</div></div>""")

        # ── 🐮 Friction Cash Cows Card ─────────────────────────────────────
        cow_header = """
        <div style="background:linear-gradient(135deg,#fef2f2,#fee2e2);border:1px solid rgba(239,68,68,0.3);
                    border-left:5px solid #ef4444;border-radius:14px;padding:18px 22px;margin-bottom:14px;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:14px;">
                <div>
                    <div style="font-size:17px;font-weight:800;color:#7f1d1d;">🐮 Friction Cash Cows</div>
                    <div style="font-size:12px;color:#dc2626;margin-top:2px;">High-traffic or converting pages where UX friction (dead/rage clicks) is losing conversions</div>
                </div>
                <span style="background:#ef4444;color:white;font-size:11px;font-weight:700;
                             padding:5px 12px;border-radius:20px;">Fix Urgently</span>
            </div>
        """
        st.html(cow_header)

        if m8.get("cows"):
            for i, c in enumerate(m8["cows"][:5]):
                page = c.get("page", "")
                dead = c.get("dead_clicks", 0)
                rage = c.get("rage_clicks", 0)
                sessions = c.get("sessions", 0)
                convs = c.get("conversions", 0)

                page_display = page
                if len(page_display) > 65:
                    page_display = page_display[:62] + "…"

                friction_score = dead + rage * 3
                friction_pct = min(100, int(friction_score / max(1, friction_score + 50) * 100))

                c_card = f"""
                <div style="background:white;border:1px solid rgba(239,68,68,0.2);border-radius:10px;
                            padding:14px 16px;margin-bottom:10px;margin-left:4px;">
                    <div style="font-weight:700;font-size:13px;color:#1e1b4b;margin-bottom:10px;" title="{page}">{page_display}</div>
                    <div style="display:flex;gap:16px;margin-bottom:10px;flex-wrap:wrap;">
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">💀 DEAD CLICKS</div>
                            <div style="font-size:18px;font-weight:800;color:#1e1b4b;">{dead:,}</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">😡 RAGE CLICKS</div>
                            <div style="font-size:18px;font-weight:800;color:#ef4444;">{rage:,}</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">SESSIONS</div>
                            <div style="font-size:18px;font-weight:800;color:#6366f1;">{sessions:,}</div>
                        </div>
                        <div style="text-align:center;min-width:70px;">
                            <div style="font-size:11px;color:#6b7280;font-weight:600;">CONVERSIONS</div>
                            <div style="font-size:18px;font-weight:800;color:#10b981;">{convs:,}</div>
                        </div>
                    </div>
                    <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                        <span style="font-size:11px;color:#6b7280;font-weight:600;">FRICTION LEVEL</span>
                        <span style="font-size:11px;font-weight:700;color:#ef4444;">{friction_pct}%</span>
                    </div>
                    <div style="background:#fee2e2;border-radius:6px;height:8px;overflow:hidden;">
                        <div style="width:{friction_pct}%;background:linear-gradient(90deg,#fca5a5,#ef4444);height:100%;border-radius:6px;"></div>
                    </div>
                </div>
                """
                st.html(c_card)
            st.html("</div>")
        else:
            st.html("""<div style="text-align:center;padding:16px;color:#9ca3af;font-size:13px;">✅ No friction-heavy high-value pages found</div></div>""")

        # AI narrative
        if m8.get("narrative"):
            st.html("""<div style="background:rgba(99,102,241,0.05);border-left:3px solid #6366f1;
                               border-radius:0 12px 12px 0;padding:14px 18px;margin:16px 0 8px;">
                        <span style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;letter-spacing:1px;">
                            🤖 AI Strategic Analysis</span></div>""")
            _narrative(m8["narrative"])
        st.divider()

    # ── Module 9 — Indexation Health ──────────────────────────────────────
    m9 = results.get("indexation")
    if m9:
        st.subheader("🌐 " + m9["title"])
        st.caption("Sitemap and coverage health data directly from Search Console sitemaps endpoints.")

        col_idx1, col_idx2, col_idx3 = st.columns(3)
        with col_idx1:
            st.metric("Indexation Rate", f"{m9['indexation_rate']:.1f}%", f"{m9['indexed_urls']:,} / {m9['submitted_urls']:,} URLs")
        with col_idx2:
            st.metric("Crawled, Not Indexed", f"{m9['crawled_not_indexed']:,}")
        with col_idx3:
            st.metric("Discovered, Not Indexed", f"{m9['discovered_not_indexed']:,}")

        if m9.get("sitemaps"):
            sm_df = pd.DataFrame(m9["sitemaps"])[["path", "submitted", "indexed"]]
            sm_df = sm_df.rename(columns={"path": "Sitemap Path", "submitted": "Submitted URLs", "indexed": "Indexed URLs"})
            sm_df["Index Rate"] = sm_df.apply(lambda r: f"{(r['Indexed URLs'] / r['Submitted URLs'] * 100):.1f}%" if r['Submitted URLs'] else "0.0%", axis=1)
            st.dataframe(sm_df, width='stretch', hide_index=True)

        _narrative(m9["narrative"])
        st.divider()

    # ── Download ──────────────────────────────────────────────────────────
    st.divider()
    html = _build_html_report(results)
    st.download_button(
        "⬇  Download report (HTML → PDF)",
        html,
        file_name=f"growth-report-{meta['client'].replace(' ', '-')}-{dt.date.today()}.html",
        mime="text/html",
        width='stretch',
    )
    st.caption(
        "Open the HTML file in your browser → Print → Save as PDF for a client-ready report."
    )


# ---------------------------------------------------------------------------
# HTML report builder
# ---------------------------------------------------------------------------
def _build_html_report(results: dict) -> str:
    meta = results["_meta"]
    css = """
    <style>
    body{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:860px;
         margin:40px auto;line-height:1.6;color:#1a1a1a;padding:0 24px}
    h1{font-size:28px;font-weight:800;border-bottom:3px solid #6366f1;padding-bottom:8px}
    h2{font-size:20px;font-weight:700;margin-top:36px;border-bottom:1px solid #e5e7eb;
       padding-bottom:6px;color:#1e1b4b}
    .meta{color:#6b7280;font-size:13px;margin:4px 0 28px}
    table{border-collapse:collapse;width:100%;margin:12px 0;font-size:13px}
    th{background:#f5f3ff;color:#4c1d95;font-weight:600;padding:8px 12px;text-align:left}
    td{padding:7px 12px;border-bottom:1px solid #f3f4f6}
    tr:hover td{background:#fafafa}
    blockquote{border-left:3px solid #6366f1;margin:12px 0;padding:4px 16px;
               color:#374151;background:#f5f3ff20}
    .badge-low{color:#15803d} .badge-med{color:#b45309} .badge-high{color:#dc2626}
    </style>
    """
    header = (
        f"<h1>AI Growth Analyst Report</h1>"
        f"<p class='meta'><b>Client:</b> {meta['client']}  ·  "
        f"<b>Site:</b> {meta['site'] or 'Demo'}  ·  "
        f"<b>Window:</b> last {meta['days']} days  ·  "
        f"<b>Generated:</b> {meta['generated']}"
        + (f"  ·  <b>Analyst:</b> {meta['analyst']}" if meta.get("analyst") else "")
        + ("  ·  <i>[demo data]</i>" if meta.get("is_demo") else "")
        + "</p><hr>"
    )

    parts = [header]
    order = ["exec", "organic", "journey", "funnel", "heatmap", "scroll", "keywords", "cannibalization", "ux_audit", "hidden_insights", "indexation"]
    for key in order:
        r = results.get(key)
        if not r:
            continue
        parts.append(f"<h2>{r['title']}</h2>")
        nar = r["narrative"].replace("\n", "<br>")
        parts.append(f"<div>{nar}</div>")

        # Keyword opportunities table
        if key == "keywords":
            # Branded vs Non-branded split & Striking distance buckets
            brand_note = (
                f"<div style='background:#f9fafb;padding:12px;border-radius:6px;margin:12px 0;border:1px solid #e5e7eb;font-size:13px;'>"
                f"<b>Brand Dependency:</b> {r['brand_click_pct']:.1f}% branded clicks vs {100.0 - r['brand_click_pct']:.1f}% non-branded discovery clicks.<br>"
                f"<b>Rank Position Distribution:</b> "
                f"Rank 1-3 ({len(r['bands']['1-3'])} queries) · "
                f"Rank 4-10 ({len(r['bands']['4-10'])} queries) · "
                f"Rank 11-20 ({len(r['bands']['11-20'])} queries) · "
                f"Rank 21-50 ({len(r['bands']['21-50'])} queries)"
                f"</div>"
            )
            parts.append(brand_note)

            # New vs Lost queries
            if r.get("new_queries") or r.get("lost_queries"):
                parts.append("<div style='display:flex;gap:15px;margin:15px 0;'>")
                if r.get("new_queries"):
                    parts.append(
                        "<div style='flex:1;'><h4>🆕 Top New Queries</h4>"
                        "<table><tr><th>Query</th><th>Impressions</th><th>Position</th></tr>"
                    )
                    for q in r["new_queries"][:5]:
                        parts.append(f"<tr><td>{q['query']}</td><td>{q['impressions']:,}</td><td>{q['position']:.1f}</td></tr>")
                    parts.append("</table></div>")
                if r.get("lost_queries"):
                    parts.append(
                        "<div style='flex:1;'><h4>⚠️ Top Lost Queries</h4>"
                        "<table><tr><th>Query</th><th>Impressions</th><th>Position</th></tr>"
                    )
                    for q in r["lost_queries"][:5]:
                        parts.append(f"<tr><td>{q['query']}</td><td>{q['impressions']:,}</td><td>{q['position']:.1f}</td></tr>")
                    parts.append("</table></div>")
                parts.append("</div>")

            # Flat opportunities table
            if r.get("opportunities"):
                parts.append("<h4>🚀 High-Uplift SEO Opportunities</h4>")
                parts.append(
                    "<table><tr>"
                    "<th>Query</th><th>Position</th><th>Impressions</th>"
                    "<th>Current Clicks</th><th>Click Uplift</th>"
                    "</tr>"
                )
                for o in r["opportunities"]:
                    parts.append(
                        f"<tr><td>{o['query']}</td><td>{o['position']}</td>"
                        f"<td>{o['impressions']:,}</td><td>{o['current_clicks']}</td>"
                        f"<td><b>{o['click_uplift']:,}</b></td></tr>"
                    )
                parts.append("</table>")

        # Cannibalization conflicts table
        if key == "cannibalization" and r.get("conflicts"):
            parts.append(
                "<table><tr>"
                "<th>Competing Query</th><th>Competitors</th><th>Total Clicks</th><th>Total Impressions</th><th>Preferred Owner</th><th>Severity</th>"
                "</tr>"
            )
            for c in r["conflicts"]:
                parts.append(
                    f"<tr><td>{c['query']}</td><td>{c['num_pages']}</td>"
                    f"<td>{c['total_clicks']:,}</td><td>{c['total_impressions']:,}</td>"
                    f"<td>{c['winner']}</td><td>{c['severity']}</td></tr>"
                )
            parts.append("</table>")

        # UX Audit table with CrUX
        if key == "ux_audit" and r.get("audit_rows"):
            parts.append(
                "<table><tr>"
                "<th>Page Path</th><th>Sessions</th><th>Change %</th><th>Rank</th>"
                "<th>Lab LCP</th><th>CrUX LCP</th><th>CrUX CLS</th><th>CrUX INP</th><th>CrUX Rating</th>"
                "<th>Dead Clicks</th><th>Rage Clicks</th><th>UX Risk</th>"
                "</tr>"
            )
            for o in r["audit_rows"]:
                pos_val = o.get("avg_position")
                pos_display = f"{pos_val:.1f}" if pos_val is not None else "n/a"
                lcp_val = o.get("lcp")
                lcp_display = f"{lcp_val}s" if lcp_val is not None else "n/a"

                clcp = o.get("crux_lcp")
                clcp_disp = f"{clcp:.2f}s" if clcp is not None else "n/a"
                ccls = o.get("crux_cls")
                ccls_disp = f"{ccls:.3f}" if ccls is not None else "n/a"
                cinp = o.get("crux_inp")
                cinp_disp = f"{cinp}ms" if cinp is not None else "n/a"
                crat = o.get("crux_rating")
                crat_disp = str(crat).upper().replace('_', ' ') if crat else "N/A"

                parts.append(
                    f"<tr><td>{o['page']}</td><td>{o['sessions']}</td>"
                    f"<td>{o['session_change_pct']:+.1f}%</td>"
                    f"<td>{pos_display}</td>"
                    f"<td>{lcp_display}</td>"
                    f"<td>{clcp_disp}</td><td>{ccls_disp}</td><td>{cinp_disp}</td><td>{crat_disp}</td>"
                    f"<td>{o['dead_clicks']}</td><td>{o['rage_clicks']}</td>"
                    f"<td>{o['risk_level']}</td></tr>"
                )
            parts.append("</table>")

        # Indexation health
        if key == "indexation":
            idx_summary = (
                f"<div style='background:#f9fafb;padding:12px;border-radius:6px;margin:12px 0;border:1px solid #e5e7eb;font-size:13px;'>"
                f"<b>Indexation Rate:</b> {r['indexation_rate']:.1f}% ({r['indexed_urls']:,} indexed / {r['submitted_urls']:,} submitted)<br>"
                f"<b>Crawled but not indexed:</b> {r['crawled_not_indexed']:,}<br>"
                f"<b>Discovered but not indexed:</b> {r['discovered_not_indexed']:,}"
                f"</div>"
            )
            parts.append(idx_summary)
            if r.get("sitemaps"):
                parts.append(
                    "<table><tr><th>Sitemap Path</th><th>Submitted URLs</th><th>Indexed URLs</th><th>Index Rate</th></tr>"
                )
                for s in r["sitemaps"]:
                    rate_val = (s['indexed'] / s['submitted'] * 100) if s['submitted'] else 0.0
                    parts.append(
                        f"<tr><td>{s['path']}</td><td>{s['submitted']:,}</td><td>{s['indexed']:,}</td><td>{rate_val:.1f}%</td></tr>"
                    )
                parts.append("</table>")

    return (
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<title>Growth Report — {meta['client']}</title>"
        f"{css}</head><body>{''.join(parts)}</body></html>"
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
st.title("🚀 Schbang Growth Platform")

tab_dashboard, tab_onpage = st.tabs(["📊 Growth Dashboard", "🔍 On-Page SEO Optimizer"])

with tab_dashboard:
    if run:
        st.session_state["results"] = run_report(client_name, client_cfg, days, model)
        st.session_state["active_client"] = client_name

    # Clear results when client changes mid-session
    if st.session_state.get("active_client") != client_name:
        st.session_state.pop("results", None)

    if st.session_state.get("results"):
        show_results(st.session_state["results"])
    else:
        st.markdown("### Select a client and click **▶ Run Analysis**")
        st.info(
            "**What you'll get:**\n"
            "- 📊 Module 1 — Organic Performance (GA4 + GSC)\n"
            "- 🧭 Module 2 — User Journey (GA4 + Clarity)\n"
            "- 🔽 Module 3 — Funnel Drop-off Analysis\n"
            "- 🖱️ Module 4 — Heatmap & Click Frustration Audits\n"
            "- 📜 Module 5 — Scroll Depth Analytics\n"
            "- 🔍 Module 6 — GSC & Keyword Intelligence\n"
            "- 🏥 Module 7 — Declining Pages UX & Core Web Vitals Audit\n"
            "- 💡 Module 8 — Hidden Growth Insights Dashboard\n"
            "- 📋 Module 10 — Executive Summary & 3-Month Action Plan\n\n"
            "All tables + charts are always shown. AI narratives require a Gemini API key."
        )
        if not config.auth_configured():
            st.warning(
                "**Auth not configured:** Google OAuth credentials are missing. "
                "The app is running without login enforcement.",
                icon="⚠️",
            )

with tab_onpage:
    st.subheader("📝 On-Page SEO & Content Optimizer")
    st.caption("Scrapes live text content using Jina Reader, analyzes it against Search Console keyword rankings, checks mobile PageSpeed, and utilizes Gemini to write meta tags, heading structures, and body copy improvements.")

    base_site_url = client_cfg.get("gsc_site_url", "https://www.ultratechcement.com").rstrip("/")
    path_input = st.text_input("Landing page path", value="/for-homebuilders/home-building-explained-single/descriptive-articles/types-of-houses")

    if st.button("▶ Optimize Content", key="btn_onpage_opt"):
        abs_url = base_site_url + ("/" if not path_input.startswith("/") else "") + path_input

        with st.status(f"Optimizing {path_input}…") as status:
            status.update(label="1. Scrape live content via Jina Reader…")
            jina_md = connectors.fetch_jina_markdown(abs_url)

            status.update(label="2. Retrieve ranking GSC queries for page…")
            # Pull flat queries for seed keyword mapping
            sa = config.GCP_SERVICE_ACCOUNT
            gsc_queries = []
            if client_cfg.get("use_demo_data"):
                gsc_queries = [
                    {"query": "types of houses", "clicks": 450, "impressions": 8500, "position": 4.2},
                    {"query": "different types of houses", "clicks": 210, "impressions": 4800, "position": 6.8},
                    {"query": "house types list", "clicks": 95, "impressions": 3000, "position": 8.1}
                ]
            else:
                try:
                    # Fetch top keywords to check intent gaps
                    gsc_queries = connectors.fetch_gsc_queries_flat(base_site_url, sa, days, top_n=20)
                except Exception as exc:
                    st.warning(f"GSC keyword pull failed: {exc}")

            status.update(label="3. Audit mobile PageSpeed & Core Web Vitals…")
            ps_stats = connectors.fetch_pagespeed_metrics(abs_url, config.PAGESPEED_API_KEY)

            status.update(label="4. Generating optimization copywriting blueprint…")
            gk = config.GEMINI_KEY
            blueprint = analysis.module_onpage_seo(jina_md, gsc_queries, ps_stats, gk, model, grok_key=config.GROK_KEY)

            status.update(label="Optimization complete!", state="complete")

        st.success(f"Generated optimization roadmap for: {abs_url}")
        st.markdown(blueprint)

