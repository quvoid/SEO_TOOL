# Deployment — Frontend on Vercel, Backend on Railway

Goal: a live URL where you sign in with **Google (omkar.rakshe@schbang.com)** and see
**live** GA4/GSC data. omkar is auto-granted admin via the allowlist.

Architecture: the browser only ever talks to the Vercel domain. Vercel proxies
`/api/*` to the Railway backend, so the auth cookie is same-origin and "just works".

```
Browser ──HTTPS──> Vercel (React)  ──/api/* rewrite──>  Railway (FastAPI) ──> Postgres
                                                              │
                                                     Google OAuth + GA4/GSC/Gemini
```

---

## Prerequisites
- Code pushed to a GitHub repo (this project).
- Accounts: Vercel, Railway, and access to your **Google Cloud OAuth** client
  (the `[auth]` web client already in your `secrets.toml`).
- Generate a production Fernet key (keep it secret, you'll paste it into Railway):
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```

---

## STEP 1 — Backend on Railway

1. **New Project → Deploy from GitHub repo** → pick this repo.
   Railway reads `railway.json` and builds `backend/Dockerfile`.
2. **Add Postgres**: in the project, **New → Database → PostgreSQL**. Railway exposes
   `DATABASE_URL` automatically.
3. **Set environment variables** (Service → Variables). Reference the DB with
   `${{Postgres.DATABASE_URL}}`:

   | Variable | Value |
   |---|---|
   | `ENVIRONMENT` | `production` |
   | `DATABASE_URL` | `${{Postgres.DATABASE_URL}}` |
   | `SESSION_SECRET` | a long random string |
   | `CREDENTIAL_ENCRYPTION_KEY` | the Fernet key you generated |
   | `AUTH_ALLOWED_DOMAIN` | `schbang.com` |
   | `ADMIN_EMAILS` | `omkar.rakshe@schbang.com` |
   | `AUTH_GOOGLE_CLIENT_ID` | your `[auth]` web client id |
   | `AUTH_GOOGLE_CLIENT_SECRET` | your `[auth]` web client secret |
   | `GEMINI_API_KEY` | your Gemini key |
   | `XAI_API_KEY` | your Grok key |
   | `GOOGLE_PAGESPEED_API_KEY` | your PageSpeed key |
   | `CLARITY_API_TOKEN` | your Clarity token (optional) |
   | `USER_OAUTH_CLIENT_ID` | data-source `[user_oauth]` client id |
   | `USER_OAUTH_CLIENT_SECRET` | data-source `[user_oauth]` client secret |
   | `USER_OAUTH_REFRESH_TOKEN` | data-source `[user_oauth]` refresh token |
   | `CLIENTS_JSON` | see below |
   | `AUTH_REDIRECT_URI` | fill in AFTER Step 3 (Vercel URL) |
   | `FRONTEND_ORIGIN` | fill in AFTER Step 3 (Vercel URL) |

   `CLIENTS_JSON` (one line) — your brands:
   ```json
   {"clients":{"Ultratech Cement":{"use_demo_data":false,"ga4_property_id":"342904846","gsc_site_url":"https://www.ultratechcement.com/","organic_only":true}}}
   ```

   > Do **not** set `DEV_AUTH_BYPASS` in production — it is ignored when
   > `ENVIRONMENT=production`, so the site always requires real Google login.

4. **Deploy.** When it's up, copy the public URL (e.g. `https://seo-backend.up.railway.app`).
   Check `https://<railway-url>/health` returns `{"status":"ok"}`.

5. **Seed the database** (one-off). In Railway: Service → **⋮ → Run a command** (or the CLI):
   ```
   python backend/seed.py
   ```
   It creates the omkar admin user, your encrypted Gmail credential, and your clients.
   Expected: `[ok] seeded owner=omkar.rakshe@schbang.com, 1 credential, 1 clients`.

---

## STEP 2 — Point the frontend at the backend

Edit **`frontend/vercel.json`** — replace the placeholder with your Railway URL:
```json
{ "source": "/api/:path*", "destination": "https://seo-backend.up.railway.app/:path*" }
```
Commit & push.

---

## STEP 3 — Frontend on Vercel

1. **New Project → import this GitHub repo.**
2. **Root Directory: `frontend`** (important — the app lives in a subfolder).
3. Framework preset: **Vite**. Build/output are already set by `vercel.json`
   (`npm run build` → `dist`). No env vars needed (the app is live by default).
4. **Deploy.** Copy the URL (e.g. `https://schbang-seo.vercel.app`).

---

## STEP 4 — Close the loop (auth URLs)

1. **Railway → Variables**, now set:
   - `FRONTEND_ORIGIN` = `https://schbang-seo.vercel.app`
   - `AUTH_REDIRECT_URI` = `https://schbang-seo.vercel.app/api/auth/callback`

   Railway redeploys automatically.

2. **Google Cloud Console → APIs & Services → Credentials →** open your `[auth]`
   OAuth **Web** client → **Authorized redirect URIs → Add**:
   ```
   https://schbang-seo.vercel.app/api/auth/callback
   ```
   Save.

---

## STEP 5 — Log in

Open `https://schbang-seo.vercel.app` → **Sign in with Google** →
choose **omkar.rakshe@schbang.com** → you land on the dashboard as **admin**,
pick a client, **Run Report** → live GA4/GSC data.

---

## Notes & gotchas
- **AI quota**: if Gemini shows `429 ... limit: 0`, the charts still render (they use
  GA4/GSC data); only the "AI Analysis" text is affected. Use a key with quota.
- **Adding a second Gmail / more brands later**: re-run `seed.py` with updated
  `CLIENTS_JSON` (and add another credential row) — or we build the admin UI for it.
- **Report speed**: a full run is ~1–3 min (10 sequential AI calls + rate-limit gaps).
  Railway keeps the process alive for the background job; the UI polls until done.
- **Schema changes**: tables auto-create on boot. Once stable, switch to Alembic.
- **Secrets**: never commit `backend/.env` or `secrets.toml` (both gitignored). All
  production secrets live in Railway's Variables.
