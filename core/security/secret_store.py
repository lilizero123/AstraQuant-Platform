"""
Lightweight encrypted secret storage.

The module keeps secrets in ``~/.quant_trader/secrets.json`` encrypted with a
Fernet key that is generated on first use.  This avoids writing clear-text
credentials such as broker passwords into ``settings.json`` while keeping the
implementation self-contained and cross-platform.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, Optional

from cryptography.fernet import Fernet

SECRET_DIR = Path.home() / ".quant_trader"
SECRET_DIR.mkdir(parents=True, exist_ok=True)
SECRET_KEY_PATH = SECRET_DIR / "secret.key"
SECRET_STORE_PATH = SECRET_DIR / "secrets.json"


def _load_key() -> bytes:
    if SECRET_KEY_PATH.exists():
        return SECRET_KEY_PATH.read_bytes()
    key = Fernet.generate_key()
    SECRET_KEY_PATH.write_bytes(key)
    return key


_FERNET = Fernet(_load_key())


def _load_store() -> Dict[str, str]:
    if SECRET_STORE_PATH.exists():
        try:
            return json.loads(SECRET_STORE_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return {}


def _write_store(data: Dict[str, str]):
    SECRET_STORE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def store_secret(key: str, value: Optional[str]):
    """Encrypt and persist ``value`` under ``key``."""
    data = _load_store()
    if not value:
        data.pop(key, None)
        _write_store(data)
        return
    token = _FERNET.encrypt(value.encode("utf-8")).decode("utf-8")
    data[key] = token
    _write_store(data)


def get_secret(key: str) -> Optional[str]:
    """Return the decrypted value for ``key`` or ``None`` if absent."""
    data = _load_store()
    token = data.get(key)
    if not token:
        return None
    try:
        decrypted = _FERNET.decrypt(token.encode("utf-8"))
        return decrypted.decode("utf-8")
    except Exception:
        return None


def delete_secret(key: str):
    """Remove ``key`` from the store."""
    data = _load_store()
    if key in data:
        data.pop(key)
        _write_store(data)
