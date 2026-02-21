import os
import base64
from cryptography.fernet import Fernet

def get_encryption_key() -> bytes:
    """Get encryption key for storing sensitive data."""
    key = os.getenv("ENCRYPTION_KEY")
    if not key:
        raise ValueError(
            "ENCRYPTION_KEY environment variable is required. "
            "Generate one with: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
    return key.encode() if isinstance(key, str) else key


_fernet = Fernet(get_encryption_key())


def encrypt(plain_text: str) -> str:
    """Encrypt a string value."""
    if not plain_text:
        return ""
    return _fernet.encrypt(plain_text.encode()).decode()


def decrypt(encrypted_text: str) -> str:
    """Decrypt an encrypted string value."""
    if not encrypted_text:
        return ""
    try:
        return _fernet.decrypt(encrypted_text.encode()).decode()
    except Exception:
        return ""
