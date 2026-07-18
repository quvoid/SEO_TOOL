"""
auth.py — Google OAuth 2.0 login with company-domain restriction.

Usage in app.py (must be the very first thing after st.set_page_config):
    import auth
    auth.require_login()      # blocks & shows login page if not authenticated
    user = auth.get_user()    # { email, name, picture }

Security guarantees:
- Only emails ending in @<ALLOWED_DOMAIN> can pass.
- All others see a clean "Access denied" page — no data leaks.
- Session tokens are stored in Streamlit's server-side session_state.
- OAuth state param prevents CSRF.
"""

from __future__ import annotations
import os
import streamlit as st
import config

# Allow HTTP redirect only for localhost dev. NEVER set in production.
if config.REDIRECT_URI.startswith("http://localhost"):
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")

_SCOPES = [
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

_LOGIN_CSS = """
<style>
/* Hide sidebar on login page */
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] { display: none !important; }

/* Dark gradient background */
[data-testid="stAppViewContainer"] > .main {
    background: linear-gradient(135deg, #0d0d1a 0%, #141428 50%, #0d0d1a 100%) !important;
    min-height: 100vh;
}
[data-testid="stHeader"] { background: transparent !important; }

/* Card */
.login-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 24px;
    padding: 48px 40px 40px;
    text-align: center;
    backdrop-filter: blur(12px);
    box-shadow: 0 24px 64px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.15);
    margin-top: 60px;
}
.login-badge {
    display: inline-block;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    border-radius: 50%;
    width: 72px; height: 72px; line-height: 72px;
    font-size: 36px;
    margin-bottom: 20px;
    box-shadow: 0 8px 24px rgba(99,102,241,0.4);
}
.login-title {
    font-size: 26px; font-weight: 800;
    color: #ffffff; margin: 0 0 6px;
    letter-spacing: -0.5px;
}
.login-company {
    font-size: 12px; font-weight: 600; letter-spacing: 2px;
    text-transform: uppercase;
    color: rgba(99,102,241,0.9); margin: 0 0 20px;
}
.login-divider {
    width: 48px; height: 2px;
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    margin: 0 auto 20px; border-radius: 2px;
}
.login-desc {
    color: rgba(255,255,255,0.55); font-size: 13.5px;
    line-height: 1.6; margin-bottom: 32px;
}
.login-desc strong { color: rgba(255,255,255,0.85); }
.login-lock {
    font-size: 11px; color: rgba(255,255,255,0.35);
    margin-top: 16px;
}
</style>
"""


def _make_flow():
    """Build the Google OAuth2 Flow object."""
    from google_auth_oauthlib.flow import Flow

    client_config = {
        "web": {
            "client_id": config.GOOGLE_CLIENT_ID,
            "client_secret": config.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [config.REDIRECT_URI],
        }
    }
    return Flow.from_client_config(
        client_config, scopes=_SCOPES, redirect_uri=config.REDIRECT_URI
    )


def _handle_callback(code: str) -> None:
    """Exchange OAuth code for user identity and verify domain."""
    from google.oauth2 import id_token
    from google.auth.transport import requests as google_requests

    try:
        flow = _make_flow()
        flow.fetch_token(code=code)
        credentials = flow.credentials

        info = id_token.verify_oauth2_token(
            credentials.id_token,
            google_requests.Request(),
            config.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=30,
        )
        email: str = info.get("email", "").lower()
        domain = email.split("@")[-1] if "@" in email else ""

        if domain != config.ALLOWED_DOMAIN.lower():
            st.query_params.clear()
            _show_access_denied(email)
            st.stop()

        st.session_state["user"] = {
            "email": email,
            "name": info.get("name", email.split("@")[0].title()),
            "picture": info.get("picture", ""),
        }
        st.query_params.clear()
        st.rerun()

    except Exception as exc:
        st.query_params.clear()
        st.error(f"⚠️ Authentication failed: {exc}. Please try signing in again.")
        if st.button("🔄 Try again", type="primary"):
            st.rerun()
        st.stop()


def _show_access_denied(email: str) -> None:
    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(f"""
        <div class="login-card">
            <div class="login-badge">🚫</div>
            <div class="login-title">Access Denied</div>
            <div class="login-company">Schbang Analytics</div>
            <div class="login-divider"></div>
            <div class="login-desc">
                <strong>{email}</strong> is not authorised.<br>
                Only <strong>@{config.ALLOWED_DOMAIN}</strong> accounts can access this platform.
            </div>
        </div>
        """, unsafe_allow_html=True)
    st.stop()


def _show_login_page() -> None:
    """Render the premium login page."""
    if not config.auth_configured():
        # Dev fallback when no OAuth creds are set — bypass auth
        st.session_state["user"] = {
            "email": "dev@schbang.com",
            "name": "Developer (no auth configured)",
            "picture": "",
        }
        st.rerun()
        return

    flow = _make_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        prompt="select_account",
        include_granted_scopes="true",
    )
    st.session_state["oauth_state"] = state

    st.markdown(_LOGIN_CSS, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.4, 1])
    with col2:
        st.markdown(f"""
        <div class="login-card">
            <div class="login-badge">📈</div>
            <div class="login-title">AI Growth Analyst</div>
            <div class="login-company">Schbang Analytics Platform</div>
            <div class="login-divider"></div>
            <div class="login-desc">
                Unified GA4 · Search Console · Keyword Intelligence<br>
                powered by Claude AI — for <strong>Schbang teams only</strong>.
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
        st.link_button(
            "  Sign in with Google",
            auth_url,
            use_container_width=True,
            type="primary",
        )
        st.markdown(
            f"<p class='login-lock'>🔒 Restricted to @{config.ALLOWED_DOMAIN} accounts</p>",
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def require_login() -> None:
    """
    Gate function — call this at the top of app.py before rendering anything.

    Real Google OAuth gate. A local dev bypass is available ONLY when the
    environment variable DEV_AUTH_BYPASS=1 is explicitly set — it is never
    on by default, so a deployed instance is always protected.
    """
    # Already authenticated this session.
    if "user" in st.session_state:
        return

    # Explicit, opt-in local dev bypass (never default-on).
    if os.environ.get("DEV_AUTH_BYPASS") == "1":
        st.session_state["user"] = {
            "email": f"dev@{config.ALLOWED_DOMAIN}",
            "name": "Developer (DEV_AUTH_BYPASS)",
            "picture": "",
        }
        return

    # Handle the OAuth redirect back from Google (?code=...).
    code = st.query_params.get("code")
    if code:
        _handle_callback(code)
        st.stop()

    # Not authenticated — render the login page and halt.
    _show_login_page()
    st.stop()


def get_user() -> dict:
    """Return the current authenticated user dict (email, name, picture)."""
    return st.session_state.get("user", {})


def logout() -> None:
    """Clear session and redirect to login."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
