"""
credential_store.py — Encrypted local credential vault.
Uses Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256).
Credentials are never stored in plaintext.
"""

from __future__ import annotations
import json
import os
import base64
from pathlib import Path
from typing import Optional
from getpass import getpass

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


STORE_DIR = Path.home() / ".deploybot"
STORE_FILE = STORE_DIR / "vault.enc"
SALT_FILE = STORE_DIR / ".salt"


def _derive_key(master_password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=480_000,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode()))


def _get_or_create_salt() -> bytes:
    STORE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
    if SALT_FILE.exists():
        return SALT_FILE.read_bytes()
    salt = os.urandom(16)
    SALT_FILE.write_bytes(salt)
    SALT_FILE.chmod(0o600)
    return salt


class CredentialStore:
    """
    Encrypted key-value store for SSH credentials and deployment profiles.
    All data is encrypted with a master password before writing to disk.
    """

    def __init__(self, master_password: Optional[str] = None):
        self._salt = _get_or_create_salt()
        if master_password is None:
            master_password = os.environ.get("DEPLOYBOT_MASTER_PASSWORD") or getpass(
                "🔑 Master vault password: "
            )
        key = _derive_key(master_password, self._salt)
        self._fernet = Fernet(key)
        self._data: dict = self._load()

    # ------------------------------------------------------------------ #
    #  Public API                                                           #
    # ------------------------------------------------------------------ #

    def save_profile(self, name: str, profile: dict):
        """Store an encrypted deployment profile."""
        self._data.setdefault("profiles", {})[name] = profile
        self._persist()

    def get_profile(self, name: str) -> Optional[dict]:
        return self._data.get("profiles", {}).get(name)

    def list_profiles(self) -> list[str]:
        return list(self._data.get("profiles", {}).keys())

    def delete_profile(self, name: str):
        self._data.get("profiles", {}).pop(name, None)
        self._persist()

    def save_server(self, alias: str, creds: dict):
        """Store SSH credentials for a named server alias."""
        self._data.setdefault("servers", {})[alias] = creds
        self._persist()

    def get_server(self, alias: str) -> Optional[dict]:
        return self._data.get("servers", {}).get(alias)

    def list_servers(self) -> list[str]:
        return list(self._data.get("servers", {}).keys())

    # ------------------------------------------------------------------ #
    #  Persistence                                                          #
    # ------------------------------------------------------------------ #

    def _load(self) -> dict:
        if not STORE_FILE.exists():
            return {}
        try:
            encrypted = STORE_FILE.read_bytes()
            plaintext = self._fernet.decrypt(encrypted)
            return json.loads(plaintext)
        except InvalidToken:
            raise ValueError("❌ Incorrect master password or corrupted vault.")
        except Exception:
            return {}

    def _persist(self):
        STORE_DIR.mkdir(mode=0o700, parents=True, exist_ok=True)
        plaintext = json.dumps(self._data).encode()
        encrypted = self._fernet.encrypt(plaintext)
        STORE_FILE.write_bytes(encrypted)
        STORE_FILE.chmod(0o600)
