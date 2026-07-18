"""
crypto.py — Symmetric encryption for credentials at rest (Tier-2 secrets).

Per-client Google credentials (client_id / client_secret / refresh_token /
service-account JSON) and property IDs are encrypted with Fernet before they
touch the database. The Fernet key itself is a Tier-1 secret pulled from the
environment / Secret Manager — never stored in the DB.

Result: a full database dump leaks NOTHING usable without the separate key.
"""
from __future__ import annotations

import json
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from ..settings import get_settings


@lru_cache
def _fernet() -> Fernet:
    key = get_settings().credential_encryption_key
    if not key:
        raise RuntimeError(
            "CREDENTIAL_ENCRYPTION_KEY is not set. Generate one with:\n"
            "  python -c \"from cryptography.fernet import Fernet; "
            "print(Fernet.generate_key().decode())\""
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_str(plaintext: str) -> str:
    """Encrypt a string → base64 token (safe to store in a text column)."""
    return _fernet().encrypt(plaintext.encode()).decode()


def decrypt_str(token: str) -> str:
    """Decrypt a token produced by encrypt_str. Raises on tamper/wrong key."""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken as exc:  # pragma: no cover
        raise ValueError("Credential decryption failed (bad key or tampered data).") from exc


def encrypt_json(obj: dict | list) -> str:
    """Encrypt a JSON-serializable object (e.g. a service-account dict)."""
    return encrypt_str(json.dumps(obj, separators=(",", ":")))


def decrypt_json(token: str) -> dict | list:
    return json.loads(decrypt_str(token))
