from __future__ import annotations

import re
from typing import Any

from app.core.security import decrypt_value, encrypt_value

_VAR_RE = re.compile(r"\{\{\s*([A-Za-z0-9_\-\.]+)\s*\}\}")

REDACTED_PLACEHOLDER = "••••••••"


def encrypt_var_value(plaintext: str) -> bytes:
    return encrypt_value(plaintext)


def decrypt_var_value(ct: bytes) -> str:
    return decrypt_value(ct)


def resolve_variables(template: str, vars_by_name: dict[str, dict[str, Any]]) -> tuple[str, set[str]]:
    """Substitute {{VAR_NAME}} with decrypted values. Returns (resolved, secret_names_used)."""
    used: set[str] = set()

    def repl(m: re.Match[str]) -> str:
        name = m.group(1)
        v = vars_by_name.get(name)
        if v is None:
            return m.group(0)
        used.add(name)
        if v.get("is_secret"):
            return decrypt_var_value(v["value_enc"])
        return decrypt_var_value(v["value_enc"])

    return _VAR_RE.sub(repl, template), used
