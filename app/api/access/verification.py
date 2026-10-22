"""HMAC-SHA256 email verification tokens. The payload contains no personal information."""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from typing import Any

from app.api.access.tokens import (
    InvitationError,
    _b64url,
    _b64url_decode,
    canonical_payload,
    current_unix_time,
    sign_payload,
)

VERIFICATION_SECONDS = 30 * 60
MAX_VERIFICATION_SECONDS = 60 * 60
PURPOSE = "email_verify"


def issue_verification(
    key: str,
    request_id: str,
    *,
    now: int | None = None,
    lifetime: int = VERIFICATION_SECONDS,
    jti: str | None = None,
    exp: int | None = None,
) -> tuple[str, str, int]:
    if not key or not request_id:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    if lifetime < 1 or lifetime > MAX_VERIFICATION_SECONDS:
        raise ValueError(f"Verification lifetime must be from 1 to {MAX_VERIFICATION_SECONDS} seconds.")
    issued_at = current_unix_time() if now is None else now
    verification_id = jti or secrets.token_urlsafe(18)
    expires_at = exp if exp is not None else issued_at + lifetime
    payload = {
        "exp": expires_at,
        "jti": verification_id,
        "purpose": PURPOSE,
        "request_id": request_id,
        "v": 1,
    }
    return sign_payload(key, payload), verification_id, expires_at


def validate_verification(token: str, key: str, *, now: int | None = None) -> dict[str, Any]:
    if not key or not isinstance(token, str) or token.count(".") != 1:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    segment, signature_segment = token.split(".", 1)
    try:
        supplied = _b64url_decode(signature_segment)
        expected = hmac.new(key.encode("utf-8"), segment.encode("ascii"), hashlib.sha256).digest()
    except (ValueError, UnicodeEncodeError):
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.") from None
    if len(supplied) != len(expected) or not hmac.compare_digest(supplied, expected):
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    try:
        payload = json.loads(_b64url_decode(segment))
    except (ValueError, json.JSONDecodeError):
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.") from None
    required = {"v", "purpose", "request_id", "jti", "exp"}
    if not isinstance(payload, dict) or set(payload) != required or payload.get("v") != 1:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    if payload.get("purpose") != PURPOSE:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    request_id = payload.get("request_id")
    verification_id = payload.get("jti")
    expires_at = payload.get("exp")
    if not isinstance(request_id, str) or not request_id or not isinstance(verification_id, str) or not verification_id:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    if type(expires_at) is not int:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    canonical = canonical_payload(
        {"exp": expires_at, "jti": verification_id, "purpose": PURPOSE, "request_id": request_id, "v": 1}
    )
    if not hmac.compare_digest(_b64url(canonical).encode("ascii"), segment.encode("ascii")):
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    current = current_unix_time() if now is None else now
    if expires_at > current + MAX_VERIFICATION_SECONDS:
        raise InvitationError("DEMO_VERIFY_INVALID", "This verification link is not valid.")
    if expires_at <= current:
        raise InvitationError("DEMO_VERIFY_EXPIRED", "This verification link has expired.")
    return {"v": 1, "purpose": PURPOSE, "request_id": request_id, "jti": verification_id, "exp": expires_at}
