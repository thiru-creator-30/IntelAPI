from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import get_settings

_fernet: Optional[Fernet] = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = get_settings().encryption_key
        if not key:
            # Dev-only ephemeral key. Persists only for the process lifetime, which means
            # encrypted values become unreadable after restart in dev if no key is configured.
            key = base64.urlsafe_b64encode(os.urandom(32)).decode()
        # Ensure urlsafe base64 and 32 bytes.
        if len(key) != 44:
            # Treat as raw passphrase and derive a key
            key = base64.urlsafe_b64encode(hashlib.sha256(key.encode()).digest()).decode()
        _fernet = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet


def encrypt_value(plaintext: str) -> bytes:
    return _get_fernet().encrypt(plaintext.encode("utf-8"))


def decrypt_value(ct: bytes) -> str:
    try:
        return _get_fernet().decrypt(ct).decode("utf-8")
    except InvalidToken:
        return ""


def hash_token(token: str) -> str:
    salt = get_settings().session_secret_key
    return hashlib.sha256((salt + "|" + token).encode("utf-8")).hexdigest()


def generate_token(nbytes: int = 32) -> str:
    return secrets.token_urlsafe(nbytes)


def constant_time_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def hash_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
