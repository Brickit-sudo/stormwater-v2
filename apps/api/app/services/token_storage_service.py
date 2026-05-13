from __future__ import annotations

import base64
import hashlib
import hmac
import os

from app.config import Settings, get_settings
from app.services.common import CRMValidationError


FERNET_PREFIX = "fernet:v1:"
LOCAL_KEY_PREFIX = "local-key:v1:"
LOCAL_DEV_PREFIX = "local-dev:v1:"


def _optional_secret(settings: Settings | None = None) -> str | None:
    value = getattr(settings or get_settings(), "token_encryption_key", None)
    if value is None:
        return None
    trimmed = value.strip()
    return trimmed or None


def _urlsafe_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii")


def _urlsafe_decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode("ascii"))


def _fernet_for_secret(secret: str):
    try:
        from cryptography.fernet import Fernet  # type: ignore[import-not-found]
    except ImportError:
        return None

    derived = hashlib.sha256(secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(derived))


def _derive_local_key(secret: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", secret.encode("utf-8"), salt, 100_000, dklen=32)


def _xor_stream(data: bytes, key: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        block = hmac.new(key, counter.to_bytes(8, "big"), hashlib.sha256).digest()
        output.extend(block)
        counter += 1
    return bytes(left ^ right for left, right in zip(data, output, strict=False))


def _protect_with_local_key(token: str, secret: str) -> str:
    salt = os.urandom(16)
    key = _derive_local_key(secret, salt)
    cipher_text = _xor_stream(token.encode("utf-8"), key)
    tag = hmac.new(key, salt + cipher_text, hashlib.sha256).digest()
    return f"{LOCAL_KEY_PREFIX}{_urlsafe_encode(salt + tag + cipher_text)}"


def _unprotect_with_local_key(payload: str, secret: str) -> str:
    raw = _urlsafe_decode(payload)
    if len(raw) < 48:
        raise CRMValidationError("Stored Outlook token payload is invalid.")

    salt = raw[:16]
    tag = raw[16:48]
    cipher_text = raw[48:]
    key = _derive_local_key(secret, salt)
    expected = hmac.new(key, salt + cipher_text, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, expected):
        raise CRMValidationError("Stored Outlook token payload could not be verified.")
    return _xor_stream(cipher_text, key).decode("utf-8")


def protect_token(token: str, settings: Settings | None = None) -> str:
    secret = _optional_secret(settings)
    if secret:
        fernet = _fernet_for_secret(secret)
        if fernet is not None:
            encrypted = fernet.encrypt(token.encode("utf-8")).decode("ascii")
            return f"{FERNET_PREFIX}{encrypted}"
        return _protect_with_local_key(token, secret)

    encoded = _urlsafe_encode(token.encode("utf-8"))
    return f"{LOCAL_DEV_PREFIX}{encoded}"


def unprotect_token(stored_value: str, settings: Settings | None = None) -> str:
    secret = _optional_secret(settings)
    if stored_value.startswith(FERNET_PREFIX):
        if not secret:
            raise CRMValidationError("TOKEN_ENCRYPTION_KEY is required to read the stored Outlook token.")
        fernet = _fernet_for_secret(secret)
        if fernet is None:
            raise CRMValidationError("Install cryptography or reconnect Outlook to read this encrypted token.")
        encrypted = stored_value.removeprefix(FERNET_PREFIX).encode("ascii")
        return fernet.decrypt(encrypted).decode("utf-8")

    if stored_value.startswith(LOCAL_KEY_PREFIX):
        if not secret:
            raise CRMValidationError("TOKEN_ENCRYPTION_KEY is required to read the stored Outlook token.")
        return _unprotect_with_local_key(stored_value.removeprefix(LOCAL_KEY_PREFIX), secret)

    if stored_value.startswith(LOCAL_DEV_PREFIX):
        payload = stored_value.removeprefix(LOCAL_DEV_PREFIX)
        return _urlsafe_decode(payload).decode("utf-8")

    raise CRMValidationError("Stored Outlook token uses an unknown protection format.")


def token_storage_mode(settings: Settings | None = None) -> str:
    secret = _optional_secret(settings)
    if not secret:
        return "local_dev_obfuscated"
    if _fernet_for_secret(secret) is not None:
        return "fernet_encrypted"
    return "local_key_protected"
