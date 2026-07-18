"""
analysis_bridge.py — imports the EXISTING analysis modules from the repo root.

analysis.py, connectors.py and demo_data.py are reused unchanged. Only `config`
(which imports streamlit) is NOT imported here — the backend uses settings.py
instead and passes keys/creds explicitly.

connectors.py imports `config` lazily inside functions that use the global
service account / user-OAuth path. The backend avoids those globals by passing
per-client `service_account_info` explicitly (see services/reports.py). A thin
shim module named `config` is registered so any lazy `import config` inside
connectors resolves to backend settings rather than the Streamlit config.
"""
from __future__ import annotations

import os
import sys
import types

# --- Make the repo root importable (analysis.py etc. live one level up) ---
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from .settings import get_settings

_settings = get_settings()


def _install_config_shim() -> None:
    """
    Register a lightweight `config` module so connectors.py's lazy
    `import config` picks up backend settings (no Streamlit) instead of the
    Streamlit-coupled root config.py.
    """
    if "config" in sys.modules:
        return
    shim = types.ModuleType("config")
    shim.USER_OAUTH_CLIENT_ID = None
    shim.USER_OAUTH_CLIENT_SECRET = None
    shim.USER_OAUTH_REFRESH_TOKEN = None
    shim.GEMINI_KEY = _settings.gemini_api_key
    shim.GROK_KEY = _settings.xai_api_key
    shim.PAGESPEED_API_KEY = _settings.google_pagespeed_api_key
    shim.GCP_SERVICE_ACCOUNT = {}

    def user_oauth_configured() -> bool:
        return bool(
            shim.USER_OAUTH_CLIENT_ID
            and shim.USER_OAUTH_CLIENT_SECRET
            and shim.USER_OAUTH_REFRESH_TOKEN
        )

    def _s(path: str, default=None):
        # Minimal shim for connectors' clarity token lookup etc.
        mapping = {"clarity.api_token": _settings.clarity_api_token}
        return mapping.get(path, default)

    shim.user_oauth_configured = user_oauth_configured
    shim._s = _s
    sys.modules["config"] = shim


_install_config_shim()

import analysis  # noqa: E402  (existing module, reused unchanged)
import connectors  # noqa: E402
import demo_data  # noqa: E402


def configure_credential(kind: str, blob: dict) -> dict:
    """
    Point the connectors' lazily-imported `config` at the credential for the
    report about to run, and return the `service_account_info` dict to pass
    into the fetch_* functions.

    - user_oauth:      set USER_OAUTH_* globals (connectors prefer these), sa={}
    - service_account: clear user-OAuth globals, pass the SA dict through

    This is what makes multiple Gmail accounts work: each report reconfigures
    the credential for its own client's owning account.
    """
    shim = sys.modules["config"]
    if kind == "user_oauth":
        shim.USER_OAUTH_CLIENT_ID = blob.get("client_id")
        shim.USER_OAUTH_CLIENT_SECRET = blob.get("client_secret")
        shim.USER_OAUTH_REFRESH_TOKEN = blob.get("refresh_token")
        shim.GCP_SERVICE_ACCOUNT = {}
        return {}
    # service_account (or none)
    shim.USER_OAUTH_CLIENT_ID = None
    shim.USER_OAUTH_CLIENT_SECRET = None
    shim.USER_OAUTH_REFRESH_TOKEN = None
    sa = blob if kind == "service_account" else {}
    shim.GCP_SERVICE_ACCOUNT = sa
    return sa


__all__ = ["analysis", "connectors", "demo_data", "configure_credential"]
