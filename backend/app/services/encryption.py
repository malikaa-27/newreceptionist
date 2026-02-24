import base64
import os
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from app.config import get_settings

def _get_fernet() -> Fernet:
    settings = get_settings()
    # Derive a 32-byte key from SECRET_KEY using PBKDF2
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"ai_scheduling_salt_v1",
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(settings.secret_key.encode()))
    return Fernet(key)

def encrypt_token(token: str) -> str:
    """Encrypt a token string."""
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()

def decrypt_token(encrypted_token: str) -> str:
    """Decrypt an encrypted token string."""
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode()).decode()
