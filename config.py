"""
config.py — Central configuration loader for AI Growth Analyst.

Reads secrets from Streamlit's secrets.toml (local dev) or environment variables
(production / Cloud Run). All API keys and credentials are loaded here and NEVER
exposed to the browser or the end user.
"""

from __future__ import annotations
import os
import json

import streamlit as st


def _s(path: str, default=None):
    """
    Read a nested secret from st.secrets (e.g. 'anthropic.api_key').
    Falls back to an environment variable (path → uppercase, dots → underscores).
    Example: 'auth.google_client_id' → AUTH_GOOGLE_CLIENT_ID env var.
    """
    # Try st.secrets first (works locally and on Streamlit Cloud)
    try:
        node = st.secrets
        for part in path.split("."):
            node = node[part]
        return node
    except Exception:
        pass
    # Fall back to env var
    env_key = path.replace(".", "_").upper()
    return os.environ.get(env_key, default)


# ---------------------------------------------------------------------------
# AI narrative
# ---------------------------------------------------------------------------
GEMINI_KEY: str | None = _s("gemini.api_key")

# ---------------------------------------------------------------------------
# Google OAuth — employee login
# ---------------------------------------------------------------------------
ALLOWED_DOMAIN: str = _s("auth.allowed_domain", "schbang.com")
GOOGLE_CLIENT_ID: str | None = _s("auth.google_client_id")
GOOGLE_CLIENT_SECRET: str | None = _s("auth.google_client_secret")
# Local: http://localhost:8501  |  Production: https://analytics.schbang.com
REDIRECT_URI: str = _s("auth.redirect_uri", "http://localhost:8501")

# PageSpeed API key (optional, falls back to public quota if not provided)
PAGESPEED_API_KEY: str | None = _s("google_pagespeed.api_key")

# ---------------------------------------------------------------------------
# GCP service account — GA4 + Search Console (option A)
# ---------------------------------------------------------------------------
_sa_raw = _s("gcp_service_account")
GCP_SERVICE_ACCOUNT: dict = dict(_sa_raw) if _sa_raw else {}

# ---------------------------------------------------------------------------
# User OAuth — GA4 + Search Console (option B — uses analyst's own account)
# Use this when the service account hasn't been granted property access.
# Generate credentials once by running: python generate_ga4_gsc_token.py
# ---------------------------------------------------------------------------
USER_OAUTH_CLIENT_ID: str | None     = _s("user_oauth.client_id")
USER_OAUTH_CLIENT_SECRET: str | None = _s("user_oauth.client_secret")
USER_OAUTH_REFRESH_TOKEN: str | None = _s("user_oauth.refresh_token")

def user_oauth_configured() -> bool:
    """True when user OAuth credentials are present (option B)."""
    return bool(USER_OAUTH_CLIENT_ID and USER_OAUTH_CLIENT_SECRET and USER_OAUTH_REFRESH_TOKEN)


def auth_configured() -> bool:
    """True when OAuth client credentials are present."""
    return bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)


# ---------------------------------------------------------------------------
# Client registry
# ---------------------------------------------------------------------------
def load_clients() -> dict:
    """
    Load the multi-client registry from clients.json.
    Returns a dict of { display_name: client_config_dict }.
    """
    path = os.path.join(os.path.dirname(__file__), "clients.json")
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data.get("clients", {})
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        raise RuntimeError(f"clients.json is malformed: {e}") from e
