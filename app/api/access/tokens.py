"""HMAC-SHA256 invitation tokens. Payloads contain no personal information."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

DEFAULT_INVITATION_DAYS = 14
MAX_INVITATION_DAYS = 30
_DAY_SECONDS = 24 * 60 * 60
_MAX_EXPIRY_SECONDS = MAX_INVITATION_DAYS * _DAY_SECONDS


class InvitationError(Exception):
    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


def current_unix_time() -> int:
    return int(time.time())


def canonical_payload(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def sign_payload(key: str, payload: dict[str, Any]) -> str:
    segment = _b64url(canonical_payload(payload))
    signature = hmac.new(key.encode("utf-8"), segment.encode("ascii"), hashlib.sha256).digest()
    return f"{segment}.{_b64url(signature)}"


def issue_invitation(
    key: str,
    *,
    days: int = DEFAULT_INVITATION_DAYS,
    now: int | None = None,
    jti: str | None = None,
    exp: int | None = None,
) -> tuple[str, str, int]:
    if not key:
        raise InvitationError("DEMO_INVITE_INVALID", "This invitation is not valid.")
    if days < 1 or days > MAX_INVITATION_DAYS:
        raise ValueError(f"Invitation duration must be from 1 to {MAX_INVITATION_DAYS} days.")
    issued_at = current_unix_time() if now is None else now
    invitation_id = jti or secrets.token_urlsafe(18)
    expires_at = exp if exp is not None else issued_at + days * _DAY_SECONDS
    payload = {"exp": expires_at, "jti": invitation_id, "v": 1}
    return sign_payload(key, payload), invitation_id, expires_at


def validate_invitation(
    token: str,
    key: str,
    *,
    now: int | None = None,
    revoked: set[str] | None = None,
) -> dict[str, Any]:
    if not key or not isinstance(token, str) or token.count(".") != 1:
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.")
    segment, signature_segment = token.split(".", 1)
    try:
        supplied_signature = _b64url_decode(signature_segment)
        expected_signature = hmac.new(key.encode("utf-8"), segment.encode("ascii"), hashlib.sha256).digest()
    except (ValueError, UnicodeEncodeError):
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.") from None
    if len(supplied_signature) != len(expected_signature) or not hmac.compare_digest(supplied_signature, expected_signature):
        raise InvitationError("DEMO_INVITE_INVALID", "This invitation is not valid.")
    try:
        payload = json.loads(_b64url_decode(segment))
    except (ValueError, json.JSONDecodeError):
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.") from None
    if not isinstance(payload, dict) or not {"v", "jti", "exp"} <= set(payload):
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.")
    if payload.get("v") != 1:
        raise InvitationError("DEMO_INVITE_UNSUPPORTED", "This invitation is not valid.")
    invitation_id = payload.get("jti")
    expires_at = payload.get("exp")
    if set(payload) != {"v", "jti", "exp"}:
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.")
    if not isinstance(invitation_id, str) or not invitation_id:
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.")
    if type(expires_at) is not int:
        raise InvitationError("DEMO_INVITE_MALFORMED", "This invitation is not valid.")
    expected_segment = _b64url(canonical_payload({"exp": expires_at, "jti": invitation_id, "v": 1}))
    if not hmac.compare_digest(expected_segment.encode("ascii"), segment.encode("ascii")):
        raise InvitationError("DEMO_INVITE_INVALID", "This invitation is not valid.")
    current = current_unix_time() if now is None else now
    if expires_at > current + _MAX_EXPIRY_SECONDS:
        raise InvitationError("DEMO_INVITE_INVALID", "This invitation is not valid.")
    if expires_at <= current:
        raise InvitationError("DEMO_INVITE_EXPIRED", "This invitation has expired.")
    if invitation_id in (revoked or set()):
        raise InvitationError("DEMO_INVITE_REVOKED", "This invitation is no longer valid.")
    return {"v": 1, "jti": invitation_id, "exp": expires_at}
