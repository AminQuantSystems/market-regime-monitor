"""Reject unauthenticated demonstration traffic without reading request bodies."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

from app.api.access.settings import COOKIE_NAME, access_required, key_is_strong, revoked_jtis, signing_key
from app.api.access.tokens import InvitationError, validate_invitation

Scope = dict
Receive = Callable[[], Awaitable[dict]]
Send = Callable[[dict], Awaitable[None]]

_PUBLIC = {
    ("GET", "/access"),
    ("HEAD", "/access"),
    ("GET", "/healthz"),
    ("HEAD", "/healthz"),
    ("GET", "/api/v1/public/demo-access"),
    ("POST", "/api/v1/auth/exchange"),
    ("POST", "/api/v1/auth/logout"),
}


def _is_public(method: str, path: str) -> bool:
    if method == "OPTIONS":
        return True
    if (method, path) in _PUBLIC:
        return True
    return method in {"GET", "HEAD"} and (path.startswith("/assets/") or path.startswith("/brand/"))


def _cookie(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name.lower() != b"cookie":
            continue
        for part in value.decode("latin-1").split(";"):
            key, separator, rest = part.strip().partition("=")
            if separator and key == COOKIE_NAME:
                return rest
    return None


async def _json(send: Send, status: int, code: str, message: str) -> None:
    body = json.dumps({"error": {"code": code, "message": message, "category": "request"}}).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})


async def _redirect(send: Send, location: str) -> None:
    await send(
        {
            "type": "http.response.start",
            "status": 302,
            "headers": [(b"location", location.encode("ascii"))],
        }
    )
    await send({"type": "http.response.body", "body": b""})


class DemoAccessMiddleware:
    def __init__(self, app: Callable) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not access_required():
            await self.app(scope, receive, send)
            return
        method = scope.get("method", "GET").upper()
        path = scope.get("path", "")
        if _is_public(method, path):
            await self.app(scope, receive, send)
            return
        key = signing_key()
        if not key_is_strong(key):
            await _json(send, 503, "DEMO_ACCESS_MISCONFIGURED", "Demonstration access is not available.")
            return
        token = _cookie(scope)
        invitation = None
        error_code = "DEMO_AUTH_REQUIRED"
        error_message = "Demonstration access is required."
        if token:
            try:
                invitation = validate_invitation(token, key, revoked=revoked_jtis())
            except InvitationError as exc:
                error_code = exc.code
                error_message = exc.message
        if invitation is None:
            if path.startswith("/api/"):
                await _json(send, 401, error_code, error_message)
            else:
                await _redirect(send, "/access")
            return
        state = scope.setdefault("state", {})
        state["invitation"] = invitation
        await self.app(scope, receive, send)
