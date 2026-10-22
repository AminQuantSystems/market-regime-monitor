"""Public demonstration request and email verification routes."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from app.api.access.leads import clean_request, request_demonstration, verify_demonstration
from app.api.access.routes import attach_session
from app.api.access.settings import (
    azure_email_connection,
    azure_email_sender,
    email_daily_limit,
    hubspot_service_key,
    owner_email,
    public_base_url,
    request_limit_per_hour,
    revoked_jtis,
    signing_key,
    verification_cooldown_seconds,
)
from app.api.access.tokens import current_unix_time
from app.api.errors import APIError
from app.integrations.email.client import AzureEmailSender, UnconfiguredMailer
from app.integrations.hubspot.client import HubSpotClient

logger = logging.getLogger(__name__)


class AccessRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    organisation: str = ""
    role: str = ""
    interest: str = ""
    website: str = ""


class VerifyBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    token: str


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    parts = [part.strip() for part in forwarded.split(",") if part.strip()]
    if parts:
        return parts[-1]
    if request.client is not None and request.client.host:
        return request.client.host
    return "unknown"


def _hubspot(request: Request) -> HubSpotClient:
    configured = request.app.state.hubspot
    if configured is not None:
        return configured
    key = hubspot_service_key()
    if not key:
        raise APIError(503, "DEMO_CRM_UNAVAILABLE", "Demonstration requests are temporarily unavailable.")
    return HubSpotClient(key)


def _mailer(request: Request) -> AzureEmailSender | UnconfiguredMailer:
    configured = request.app.state.mailer
    if configured is not None:
        return configured
    connection = azure_email_connection()
    sender = azure_email_sender()
    if not connection or not sender:
        return UnconfiguredMailer()
    return AzureEmailSender(connection, sender)


def register_self_service_routes(app: FastAPI) -> None:
    @app.post("/api/v1/demo-access/request")
    def request_access(body: AccessRequest, request: Request) -> dict[str, str]:
        now = current_unix_time()
        gate = request.app.state.request_gate
        if gate.ip_retry_after(client_ip(request), now, request_limit_per_hour()) is not None:
            raise APIError(429, "DEMO_REQUEST_RATE_LIMIT", "Please wait before requesting demonstration access again.")
        if body.website.strip():
            return {"status": "verification_required"}
        lead = clean_request(body.model_dump())
        request_demonstration(
            hubspot=_hubspot(request),
            mailer=_mailer(request),
            lead=lead,
            now=now,
            public_base=public_base_url() or str(request.base_url).rstrip("/"),
            signing_key=signing_key(),
            gate=gate,
            cooldown_seconds=verification_cooldown_seconds(),
            daily_limit=email_daily_limit(),
        )
        return {"status": "verification_required"}

    @app.post("/api/v1/demo-access/verify")
    def verify_access(body: VerifyBody, request: Request) -> JSONResponse:
        _token, expires_at, summary = verify_demonstration(
            hubspot=_hubspot(request),
            token=body.token,
            signing_key=signing_key(),
            now=current_unix_time(),
            revoked=revoked_jtis(),
        )
        response = JSONResponse({"status": "ok"})
        attach_session(response, _token, expires_at)
        _notify_owner(_mailer(request), summary)
        return response


def _notify_owner(mailer: AzureEmailSender | UnconfiguredMailer, summary: dict[str, str]) -> None:
    address = owner_email()
    if not address or not mailer.configured():
        return
    try:
        mailer.send_owner_notification(to=address, summary=summary)
    except Exception:
        logger.warning("Owner notification was not sent.")
