"""
credentials.py — resolve and decrypt a brand's Google data-source credentials.

Each Client belongs to a Credential (a Gmail account). At report time we decrypt
that credential in-memory only, hand it to the connectors, and never persist or
log the plaintext.
"""
from __future__ import annotations

from ..models import Client, Credential, CredentialKind
from ..security.crypto import decrypt_json, decrypt_str


def resolve_credential(client: Client) -> tuple[str, dict]:
    """
    Decrypt a client's owning credential in memory.
    Returns (kind, blob) where kind is 'user_oauth' | 'service_account' | 'none'.
    Handles BOTH auth types end-to-end (see analysis_bridge.configure_credential).
    """
    cred = client.credential
    if cred is None:
        return ("none", {})
    return (cred.kind.value, decrypt_json(cred.blob_enc))  # type: ignore[return-value]


def resolve_service_account_info(client: Client) -> dict:
    """Back-compat helper: SA dict only (empty for user-OAuth credentials)."""
    cred = client.credential
    if cred is None or cred.kind != CredentialKind.service_account:
        return {}
    return decrypt_json(cred.blob_enc)  # type: ignore[return-value]


def resolve_user_oauth(cred: Credential) -> dict:
    """Decrypt a user-OAuth credential → {client_id, client_secret, refresh_token}."""
    if cred.kind != CredentialKind.user_oauth:
        raise ValueError("Credential is not user_oauth kind.")
    return decrypt_json(cred.blob_enc)  # type: ignore[return-value]


def client_ga4_property_id(client: Client) -> str:
    return decrypt_str(client.ga4_property_id_enc) if client.ga4_property_id_enc else ""
