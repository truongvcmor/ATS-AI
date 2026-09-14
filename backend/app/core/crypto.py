"""Symmetric encryption for secrets stored at rest (currently: AI provider
API keys saved via the admin Settings UI — see app/models/system_settings.py).
Never log or return a decrypted value to a client; the API only ever returns
a masked preview (see app/services/settings/settings_service.py).
"""

import base64
import hashlib
import logging

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings

logger = logging.getLogger(__name__)


def _fernet() -> Fernet:
    key_material = settings.ENCRYPTION_KEY or settings.JWT_SECRET
    if not settings.ENCRYPTION_KEY:
        logger.warning(
            "ENCRYPTION_KEY is not set — deriving the secrets-at-rest encryption key from JWT_SECRET. "
            "Set a dedicated ENCRYPTION_KEY in production so rotating JWT_SECRET doesn't also break "
            "decryption of stored API keys."
        )
    # Fernet requires a 32-byte urlsafe-base64 key; derive one deterministically
    # from whatever secret material we have so any non-empty string works.
    digest = hashlib.sha256(key_material.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(plaintext: str) -> str:
    return _fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(token: str) -> str | None:
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        logger.error("Failed to decrypt a stored secret — was ENCRYPTION_KEY/JWT_SECRET changed?")
        return None


def mask_secret(plaintext: str) -> str:
    if len(plaintext) <= 4:
        return "****"
    return f"****{plaintext[-4:]}"
