"""Public invitation exchange, logout, health, and contact configuration."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.access.settings import (
    COOKIE_NAME,
    access_required,
    analyse_limit_per_hour,
    contact_email,
    cookie_secure,
    key_is_strong,
    revoked_jtis,
    signing_key,
)
from app.api.access.tokens import InvitationError, current_unix_time, validate_invitation
from app.api.errors import APIError


class ExchangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


class RateLimitExceeded(Exception):
    def __init__(self, retry_after: int) -> None:
        self.retry_after = retry_after
        super().__init__("rate limit")


def enforce_analyse_limit(request: Request) -> None:
    if not access_required():
        return
    invitation = request.scope.get("state", {}).get("invitation")
    if not isinstance(invitation, dict) or not invitation.get("jti"):
        raise APIError(401, "DEMO_AUTH_REQUIRED", "Demonstration access is required.")
    retry_after = request.app.state.analyse_limiter.retry_after(
        str(invitation["jti"]),
        current_unix_time(),
        analyse_limit_per_hour(),
    )
    if retry_after is not None:
        raise RateLimitExceeded(retry_after)


def register_access_routes(app: FastAPI) -> None:
    @app.get("/healthz", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/public/demo-access")
    def demo_access() -> dict[str, str | None]:
        return {"contact_email": contact_email()}

    @app.post("/api/v1/auth/exchange")
    def exchange(body: ExchangeRequest) -> JSONResponse:
        key = signing_key()
        if access_required() and not key_is_strong(key):
            return JSONResponse(
                status_code=503,
                content={
                    "error": {
                        "code": "DEMO_ACCESS_MISCONFIGURED",
                        "message": "Demonstration access is not available.",
                        "category": "request",
                    }
                },
            )
        if not key_is_strong(key):
            return JSONResponse(
                status_code=401,
                content={
                    "error": {
                        "code": "DEMO_INVITE_INVALID",
                        "message": "This invitation is not valid.",
                        "category": "request",
                    }
                },
            )
        try:
            invitation = validate_invitation(body.token, key, revoked=revoked_jtis())
        except InvitationError as exc:
            return JSONResponse(
                status_code=401,
                content={"error": {"code": exc.code, "message": exc.message, "category": "request"}},
            )
        remaining = int(invitation["exp"]) - current_unix_time()
        response = JSONResponse({"status": "ok"})
        response.set_cookie(
            COOKIE_NAME,
            body.token,
            max_age=max(0, remaining),
            httponly=True,
            secure=cookie_secure(),
            samesite="lax",
            path="/",
        )
        return response

    @app.post("/api/v1/auth/logout")
    def logout() -> JSONResponse:
        response = JSONResponse({"status": "ended"})
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
            httponly=True,
            secure=cookie_secure(),
            samesite="lax",
        )
        return response

    @app.exception_handler(RateLimitExceeded)
    async def rate_limited(_request: Request, exc: RateLimitExceeded) -> JSONResponse:
        return JSONResponse(
            status_code=429,
            content={
                "error": {
                    "code": "DEMO_RATE_LIMIT_EXCEEDED",
                    "message": "This demonstration invitation has reached its hourly analysis limit.",
                    "category": "request",
                }
            },
            headers={"Retry-After": str(exc.retry_after)},
        )
