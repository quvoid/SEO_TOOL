# AI Growth Analyst

Unifies **Google Analytics 4**, **Search Console**, and **Microsoft Clarity** into one
AI-written growth report. Computes the metrics deterministically, then uses Claude to
explain *why* and *what to do next* — per the Research & Implementation Guide.

This is the **MVP** (Modules 1, 2, 3, 4, 5, 10) built to deploy fast. It calls the
analytics APIs directly (no BigQuery warehouse needed to get started) and runs in a
**demo mode** with zero credentials so you can see and share it immediately.

```
demo_data.py    sample data — app works on deploy with no keys
connectors.py   live GA4 / GSC / Clarity API clients (service-account auth)
analysis.py     Modules 1–5 + 10 logic + Claude reasoning layer
app.py          Streamlit UI + orchestration + HTML report export
```

---

## 1. Run locally (5 min)

```bash
git clone <your-repo-url> && cd ai-growth-analyst
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

It opens at http://localhost:8501 in **Demo data** mode — no keys required. Click
**Run analysis** to see a full sample report.

---

## 2. Deploy online — free (10 min)

The fastest public deploy is **Streamlit Community Cloud**.

1. Push this folder to a **GitHub** repo (public or private).
2. Go to https://share.streamlit.io → **Create app** → pick your repo, branch, and
   `app.py`.
3. Click **Deploy**. In ~2 minutes you get a live URL like
   `https://your-app.streamlit.app`. It already works in demo mode.
4. To enable live data + AI narratives: in the app's **⋮ → Settings → Secrets**, paste
   the contents of `secrets.toml.example` with your real values (see below). Save —
   the app reboots automatically.

> Prefer your own infra? The same code runs on **Render**, **Railway**, or **Google
> Cloud Run** — start command `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`,
> and set the secrets as a mounted `secrets.toml` or env vars.

---

## 3. Get your credentials

**Anthropic (AI narratives)** — https://console.anthropic.com → API key. Needs API
credits; this is *separate* from a Claude.ai subscription. Without it the app still
runs and shows all computed tables/charts, just no written narrative.

**Google service account (GA4 + GSC, one account does both)**
1. Google Cloud Console → create a service account → create a **JSON key**.
2. Enable the **Google Analytics Data API** and **Search Console API** for the project.
3. GA4 → Admin → *Property Access Management* → add the service-account email as **Viewer**.
4. Search Console → Settings → *Users and permissions* → add it (Restricted is enough).
5. Paste the JSON fields into the `[gcp_service_account]` block of your secrets.

**Microsoft Clarity** — Clarity dashboard → Settings → **Data Export** → generate a
token. Note: Clarity's export API only returns the **last 1–3 days** of aggregated data.

**IDs to fill in**
- `ga4.property_id` — GA4 Admin → Property Settings → Property ID (digits only).
- `gsc.site_url` — exactly as listed in GSC, e.g. `sc-domain:example.com` or `https://example.com/`.

---

## 4. How it maps to the guide

| Guide module | Status | Inputs |
|---|---|---|
| 1 Organic Performance | ✅ | GA4 sessions + GSC clicks/CTR/position |
| 2 User Journey | ✅ | GA4 bounce/time + Clarity scroll/dead clicks |
| 3 Funnel Drop-off | ✅ | funnel step counts |
| 4 Heatmap/Click | ✅ | Clarity dead/rage/quickback clicks |
| 5 Scroll | ✅ | Clarity scroll depth |
| 10 Executive Summary | ✅ | synthesises the above |
| 6–9 (Click intel, Intent mismatch, Conv. scoring, Weekly finder) | roadmap | — |
| BigQuery warehouse / Dataflow ETL | deferred | direct-API is enough for MVP |

### Extending
- **Module 7 (Intent Mismatch):** `fetch_gsc_top_queries()` is already in `connectors.py`
  / `demo_data.py`. Add a module that embeds top queries vs page content and flags low
  similarity. Add it to `run_report()` and `show_results()` in `app.py`.
- **Scheduled/weekly runs:** wrap `run_report()` in a small script and trigger it with
  GitHub Actions or Cloud Scheduler, emailing the HTML report.
- **BigQuery:** when you outgrow direct API limits (100k+ pages), swap the connectors to
  read from BigQuery tables — the analysis modules don't change.

---

## Notes & caveats
- Demo mode uses invented data for a construction/building-materials brand so the
  narrative reads realistically; **none of it is real traffic.**
- GSC returns top rows only and Clarity is limited to a 1–3 day window — both are API
  limits, not bugs. For longer Clarity history, call it daily and store the results.
- Funnel input is currently static sample data; wire it to a GA4 funnel/events query for
  your real flow.
