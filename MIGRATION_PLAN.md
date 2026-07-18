# Migration Plan — Streamlit → FastAPI + React (Secure Multi-Account Platform)

Status legend: ✅ done · 🔨 in progress · ⬜ todo

## Goal
Move the AI Growth Analyst off Streamlit to a proper **FastAPI backend + React (Vite/TS) frontend**
with real authentication, encrypted credential storage, and multi-Gmail / multi-brand support —
while preserving the exact 10-module analysis output structure.

## Decisions (locked)
- **Frontend:** React + Vite + TypeScript.
- **Backend:** FastAPI (Python), reuses `analysis.py`, `connectors.py`, `demo_data.py` unchanged.
- **"Another Gmail" = multiple data-source Google accounts.** Each Gmail is a `credential` that owns
  a distinct set of brands (`clients`). Gmail #1 has its brands, Gmail #2 has different brands.
  New Gmail client_id/secret/refresh_token supplied later.
- **Deploy:** Frontend → **Vercel**. Backend → **Railway/Render** (long-running; Vercel serverless
  cannot handle the ~60–90s report jobs or persistent cache). DB → **Neon/Supabase Postgres**.

## Credential security model
- **Tier 1 — platform secrets** (Gemini, Grok, Google OAuth client secret, master encryption key):
  host env vars now → Secret Manager/Vault later. Never in repo, never sent to browser.
- **Tier 2 — per-credential data creds** (GA4 property IDs, GSC URLs, SA JSON, refresh tokens):
  stored in Postgres **encrypted at rest** (Fernet/envelope). Encryption key from Tier 1.
- **Tier 3 — browser:** receives analysis results only. No keys, no unauthorized property IDs.
- **Access control:** every clients/reports endpoint checks authn + per-user authorization for that client.

## Data model
```
users          (id, email, name, picture, role, is_active, created_at)
sessions       (id, user_id, expires_at, revoked)
credentials    (id, label, kind[SA|user_oauth], enc_blob, owner_user_id, created_at)  # a Gmail account
clients        (id, display_name, ga4_property_id[enc], gsc_site_url,
                credential_id -> credentials.id, use_demo_data, organic_only, owner_user_id)
client_access  (user_id, client_id, level)
reports        (id, client_id, requested_by, status, params_json, result_json, created_at)
api_cache      (cache_key, cache_value, updated_at)   # migrated from SQLite
```

## Backend API surface
```
POST /auth/login       -> Google auth URL
GET  /auth/callback    -> verify domain+allowlist, set HttpOnly cookie
POST /auth/logout
GET  /auth/me
GET/POST/PUT/DELETE /clients
POST /reports          -> start run_report as a background job
GET  /reports/{id}     -> poll status + results (10-module dict)
POST /onpage           -> on-page SEO optimizer
POST /credentials      -> add a new Gmail data-source account (admin)
GET/POST /admin/users  -> team management (admin)
```

## Preserved analysis contract
`results` dict keys stay identical: `organic, journey, funnel, heatmap, scroll, keywords,
cannibalization, ux_audit, hidden_insights, indexation, exec, _meta, _ga4_totals`.
Frontend renders one component per key → module structure after analysis is unchanged.

## Phases
- ✅ **Phase 0 — Secure now:** untrack `clients.json`, re-enable real login (`DEV_AUTH_BYPASS` opt-in), commit this plan.
- 🔨 **Phase 1 — Backend skeleton:** FastAPI app, Postgres schema + migrations, config off `st.secrets`,
  encryption helpers, port `run_report` to a service.
- ⬜ **Phase 2 — Auth:** Google OAuth (Authlib), session cookies, users/allowlist, roles.
- ⬜ **Phase 3 — Reports API:** `/clients`, `/reports`, `/onpage`, background jobs, cache in Postgres.
- ⬜ **Phase 4 — Frontend:** React/Vite login → client picker → 10-module dashboard + on-page tab.
- ⬜ **Phase 5 — Cutover:** deploy (Vercel + Railway + Neon), point domain, retire Streamlit.
- ⬜ **Phase 6 — Hardening:** rate limits, audit log, verify encryption, review auth.

## Deployment topology
| Piece | Host |
|---|---|
| Frontend (React/Vite) | Vercel |
| Backend (FastAPI) | Railway or Render |
| Database | Neon or Supabase (Postgres) |
| Secrets | host env vars → Secret Manager later |
