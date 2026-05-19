from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone


_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:\+90|0)?\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}")
_IBAN_RE = re.compile(r"TR\d{2}\s?(?:\d{4}\s?){5}\d{2}", re.IGNORECASE)


def generate_api_key(prefix: str = "nkr") -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def hash_secret(secret: str, salt: str | None = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", secret.encode(), salt.encode(), 120_000)
    return digest.hex(), salt


def verify_secret(secret: str, expected_hash: str, salt: str) -> bool:
    digest, _ = hash_secret(secret, salt)
    return hmac.compare_digest(digest, expected_hash)


def mask_sensitive_text(text: str) -> str:
    text = _EMAIL_RE.sub("[email-masked]", text)
    text = _PHONE_RE.sub("[phone-masked]", text)
    text = _IBAN_RE.sub("[iban-masked]", text)
    return text


@dataclass(frozen=True)
class AuditEvent:
    actor: str
    action: str
    resource: str
    created_at: datetime
    metadata: dict[str, str]

    @classmethod
    def create(cls, actor: str, action: str, resource: str, **metadata: str) -> "AuditEvent":
        masked = {k: mask_sensitive_text(v) for k, v in metadata.items()}
        return cls(actor=actor, action=action, resource=resource, created_at=datetime.now(timezone.utc), metadata=masked)
