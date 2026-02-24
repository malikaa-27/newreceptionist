import os
import base64
from cryptography.fernet import Fernet
from ..config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet:
    key = settings.encryption_key
    if not key:
        # Derive a stable key from SECRET_KEY for development convenience.
        # In production always supply ENCRYPTION_KEY directly.
        raw = settings.secret_key.encode("utf-8")
        padded = raw.ljust(32, b"0")[:32]
        key = base64.urlsafe_b64encode(padded)
    return Fernet(key)


def encrypt_token(plain: str) -> str:
    """Encrypt a plaintext token and return a base64-encoded ciphertext."""
    return _get_fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt_token(cipher: str) -> str:
    """Decrypt a ciphertext token back to plaintext."""
    return _get_fernet().decrypt(cipher.encode("utf-8")).decode("utf-8")
