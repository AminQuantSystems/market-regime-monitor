"""Environment configuration for the gated demonstration."""

from __future__ import annotations

import os

COOKIE_NAME = "meem_demo_session"
MIN_SIGNING_KEY_CHARACTERS = 43
MIN_DISTINCT_CHARACTERS = 10
DEFAULT_ANALYSE_LIMIT = 30


def flag(name: str, default: str = "0") -> bool:
    return os.environ.get(name, default).strip() == "1"


def access_required() -> bool:
    return flag("MEEM_DEMO_ACCESS_REQUIRED")


def serve_frontend() -> bool:
    return flag("MEEM_SERVE_FRONTEND")


def cookie_secure() -> bool:
    return flag("MEEM_DEMO_COOKIE_SECURE")


def signing_key() -> str:
    return os.environ.get("MEEM_DEMO_SIGNING_KEY", "")


def key_is_strong(key: str) -> bool:
    """A strong key is at least token_urlsafe(32) long and not a repeated pattern."""
    if len(key.encode("utf-8")) < MIN_SIGNING_KEY_CHARACTERS:
        return False
    if len(set(key)) < MIN_DISTINCT_CHARACTERS:
        return False
    return True


def require_strong_signing_key() -> None:
    if access_required() and not key_is_strong(signing_key()):
        raise RuntimeError(
            "MEEM_DEMO_ACCESS_REQUIRED is enabled but MEEM_DEMO_SIGNING_KEY is absent or too weak. "
            "Refusing to start an unprotected demonstration."
        )


def revoked_jtis() -> set[str]:
    raw = os.environ.get("MEEM_DEMO_REVOKED_JTIS", "")
    return {item.strip() for item in raw.split(",") if item.strip()}


def contact_email() -> str | None:
    value = os.environ.get("MEEM_DEMO_CONTACT_EMAIL", "").strip()
    return value or None


def analyse_limit_per_hour() -> int:
    raw = os.environ.get("MEEM_DEMO_ANALYSE_LIMIT_PER_HOUR", str(DEFAULT_ANALYSE_LIMIT)).strip()
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_ANALYSE_LIMIT
    if value < 1:
        return DEFAULT_ANALYSE_LIMIT
    return value
