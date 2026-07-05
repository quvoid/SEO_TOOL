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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f0f1e 0%, #141428 100%) !important;
    border-right: 1px solid rgba(255,255,255,0.07);
}
/* Sidebar text — labels, captions, markdown */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] li { color: rgba(255,255,255,0.85) !important; }

/* Keep select/input text DARK so it stays readable on white background */
[data-testid="stSidebar"] select,
[data-testid="stSidebar"] input { color: #1a1a1a !important; background: #ffffff !important; }

/* Selectbox + widget containers — style the Streamlit custom dropdowns */
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #1a1a1a !important;
    background-color: #ffffff !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg { color: #1a1a1a !important; }

/* Metrics */
[data-testid="stMetric"] {
    background: rgba(99,102,241,0.07);
    border: 1px solid rgba(99,102,241,0.2);
    border-radius: 12px;
    padding: 16px !important;
}
[data-testid="stMetricValue"] { font-weight: 700 !important; }

/* Section headers */
h2 { border-bottom: 2px solid rgba(99,102,241,0.3); padding-bottom: 6px; }

/* Tables */
[data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }

/* Positive/negative delta colours */
.pos { color: #22c55e; font-weight: 600; }
.neg { color: #ef4444; font-weight: 600; }

/* Download button */
.stDownloadButton button {
    background: linear-gradient(135deg, #6366f1, #8b5cf6) !important;
    color: white !important; border: none !important;
    border-radius: 8px !important;
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
@st.cache_data(ttl=1800, show_spinner=False)   # 30-min cache per client+window
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
            "clarity": demo_data.clarity_insights(),
            "funnel": demo_data.funnel_steps(),
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
    try:
        gsc_queries = connectors.fetch_gsc_queries_flat(site, sa, days, top_n=50)
    except Exception as exc:
        errors.append(f"GSC queries error: {exc}")

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
        "clarity": clarity,
        "funnel": demo_data.funnel_steps(),   # replace with live funnel query when ready
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

    # Fetch PageSpeed metrics for top declining pages
    pagespeed_data = {}
    if data.get("is_demo"):
        for page in ["/for-homebuilders/home-building-explained-single/descriptive-articles/types-of-houses", "/house-construction-guide", "/home-loans"]:
            pagespeed_data[page] = {
                "url": page,
                "performance_score": 45,
                "lcp": 3.8,
                "cls": 0.18,
                "inp": 280
            }
    else:
        declining = sorted(
            [r for r in data["ga4"] if (r.get("sessions", 0) - r.get("prev_sessions", 0)) < 0],
            key=lambda r: (r.get("sessions", 0) - r.get("prev_sessions", 0))
        )[:3]
        for r in declining:
            page_path = r["page_path"]
            # Construct absolute URL using GSC site URL prefix
            base_site = data["site"].rstrip("/")
            abs_url = base_site + ("/" if not page_path.startswith("/") else "") + page_path
            with st.spinner(f"Fetching PageSpeed Insights for {page_path}…"):
                stats = connectors.fetch_pagespeed_metrics(abs_url, config.PAGESPEED_API_KEY)
                pagespeed_data[page_path] = stats

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
            data["gsc_queries"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 7 — Declining Pages UX & Speed Audit…"):
        results["ux_audit"] = analysis.module_ux_audit(
            data["ga4"], data["gsc"], data["clarity"], pagespeed_data, gk, model
        )
    time.sleep(6)

    with st.spinner("Module 8 — Hidden Growth Insights…"):
        results["hidden_insights"] = analysis.module_hidden_insights(
            data["ga4"], data["gsc"], data["clarity"], gk, model
        )
    time.sleep(6)

    with st.spinner("Module 10 — Executive Summary…"):
        results["exec"] = analysis.module_executive_summary(results, gk, model)

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

    # ── Executive Summary ──────────────────────────────────────────────────
    ex = results["exec"]
    st.subheader("📋 " + ex["title"])
    col_pts, col_nar = st.columns([1, 2])
    with col_pts:
        for b in ex["key_points"]:
            st.markdown(f"• {b}")
    with col_nar:
        _narrative(ex["narrative"])
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
    if m4["flagged"]:
        df = pd.DataFrame(m4["flagged"])[[
            "url", "dead_clicks", "rage_clicks", "quickback_clicks", "total_sessions"
        ]]
        df.columns = ["URL", "Dead clicks", "Rage clicks", "Quickbacks", "Sessions"]
        st.dataframe(df, width='stretch', hide_index=True)
    _narrative(m4["narrative"])
    st.divider()

    # ── Module 5 — Scroll ─────────────────────────────────────────────────
    m5 = results["scroll"]
    st.subheader("📜 " + m5["title"])
    st.caption("Average scroll depth per page. Below 40% (red) means most visitors never see below-the-fold content.")
    
    pages = m5.get("all_pages", m5.get("low_scroll_pages", []))
    if pages:
        bar_html = []
        for p in pages:
            url_display = p["url"]
            if "://" in url_display:
                url_display = url_display.split("://", 1)[1]
            if "/" in url_display:
                url_display = "/" + url_display.split("/", 1)[1]
            else:
                url_display = "/"
            
            scroll_val = p["avg_scroll_percent"]
            color = "#ef4444" if scroll_val < 40 else "#22c55e"
            
            bar_html.append(
                f'<div style="display:flex;align-items:center;margin-bottom:14px;font-family:\'Inter\',sans-serif;">'
                f'<div style="width:250px;font-size:13px;text-overflow:ellipsis;overflow:hidden;white-space:nowrap;color:#1e1b4b;" title="{p["url"]}">{url_display}</div>'
                f'<div style="flex-grow:1;background-color:#f3f4f6;height:16px;border-radius:8px;margin:0 16px;overflow:hidden;position:relative;">'
                f'<div style="width:{scroll_val}%;background-color:{color};height:100%;border-radius:8px;"></div>'
                f'</div>'
                f'<div style="width:45px;text-align:right;font-size:13px;font-weight:700;color:{color};">{int(scroll_val)}%</div>'
                f'</div>'
            )
        
        container_html = (
            f'<div style="max-height:380px;overflow-y:auto;padding:16px;border:1px solid rgba(0,0,0,0.06);border-radius:12px;background-color:#ffffff;margin-bottom:16px;box-shadow:inset 0 2px 4px rgba(0,0,0,0.02);">'
            f'{"".join(bar_html)}'
            f'</div>'
            f'<div style="font-size:12px;color:#ef4444;font-weight:600;margin-bottom:16px;">'
            f'--- 40% threshold – pages below this need content re-ordering'
            f'</div>'
        )
        st.html(container_html)
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

    # ── Module 7 — Declining Pages UX & Speed Audit ────────────────────────
    m7 = results.get("ux_audit")
    if m7:
        st.subheader("🏥 " + m7["title"])
        st.caption("Correlating search session losses with user frustration signals (dead/rage clicks) and mobile PageSpeed performance.")
        if m7.get("audit_rows"):
            df7 = pd.DataFrame(m7["audit_rows"])[[
                "page", "sessions", "session_change_pct", "avg_position",
                "pagespeed_score", "lcp", "dead_clicks", "rage_clicks", "risk_level"
            ]]
            df7.columns = ["Page Path", "Sessions", "Change %", "Avg Rank", "PageSpeed %", "LCP (s)", "Dead Clicks", "Rage Clicks", "UX Risk Level"]
            st.dataframe(df7, width='stretch', hide_index=True)
        _narrative(m7["narrative"])
        st.divider()

    # ── Module 8 — Hidden Growth Insights ─────────────────────────────────
    m8 = results.get("hidden_insights")
    if m8:
        st.subheader("💡 " + m8["title"])
        
        col_z, col_g, col_c = st.columns(3)
        with col_z:
            st.warning("🧟 **Zombie Pages**")
            if m8.get("zombies"):
                for z in m8["zombies"][:2]:
                    st.caption(f"**{z['page']}** (CTR: {z['ctr']:.1f}%, Imps: {z['impressions']:,})")
            else:
                st.caption("None flagged.")
        with col_g:
            st.info("💎 **Unexplored Gems**")
            if m8.get("gems"):
                for g in m8["gems"][:2]:
                    st.caption(f"**{g['page']}** (Scroll: {g['avg_scroll_percent']:.0f}%, Duration: {g['avg_duration']:.0f}s)")
            else:
                st.caption("None flagged.")
        with col_c:
            st.error("🐮 **Friction Cash Cows**")
            if m8.get("cows"):
                for c in m8["cows"][:2]:
                    st.caption(f"**{c['page']}** (Dead: {c['dead_clicks']}, Conversions: {c['conversions']})")
            else:
                st.caption("None flagged.")
                
        _narrative(m8["narrative"])
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
    order = ["exec", "organic", "journey", "funnel", "heatmap", "scroll", "keywords", "ux_audit", "hidden_insights"]
    for key in order:
        r = results.get(key)
        if not r:
            continue
        parts.append(f"<h2>{r['title']}</h2>")
        nar = r["narrative"].replace("\n", "<br>")
        parts.append(f"<div>{nar}</div>")

        # Keyword opportunities table
        if key == "keywords" and r.get("opportunities"):
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

        # UX Audit table
        if key == "ux_audit" and r.get("audit_rows"):
            parts.append(
                "<table><tr>"
                "<th>Page Path</th><th>Sessions</th><th>Change %</th><th>Avg Rank</th>"
                "<th>PageSpeed</th><th>Dead Clicks</th><th>Rage Clicks</th><th>Risk Level</th>"
                "</tr>"
            )
            for o in r["audit_rows"]:
                pos_val = o.get("avg_position")
                pos_display = f"{pos_val:.1f}" if pos_val is not None else "n/a"
                score_val = o.get("pagespeed_score")
                score_display = f"{score_val}%" if score_val is not None else "n/a"
                parts.append(
                    f"<tr><td>{o['page']}</td><td>{o['sessions']}</td>"
                    f"<td>{o['session_change_pct']:+.1f}%</td>"
                    f"<td>{pos_display}</td>"
                    f"<td>{score_display}</td>"
                    f"<td>{o['dead_clicks']}</td><td>{o['rage_clicks']}</td>"
                    f"<td>{o['risk_level']}</td></tr>"
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
            blueprint = analysis.module_onpage_seo(jina_md, gsc_queries, ps_stats, gk, model)

            status.update(label="Optimization complete!", state="complete")

        st.success(f"Generated optimization roadmap for: {abs_url}")
        st.markdown(blueprint)

