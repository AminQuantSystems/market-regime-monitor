"""Self-service demonstration requests. HubSpot is the record. Email verifies the address."""

from __future__ import annotations

import hmac
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from app.api.access.companies import company_identity
from app.api.access.settings import key_is_strong
from app.api.access.tokens import InvitationError, issue_invitation
from app.api.access.verification import issue_verification, validate_verification
from app.api.errors import APIError
from app.integrations.email.client import EmailError, format_utc
from app.integrations.hubspot.client import HubSpotError

logger = logging.getLogger(__name__)

LAWFUL_BASIS = "Legitimate interest \u2013 prospect/lead"
UNAVAILABLE = "Demonstration requests are temporarily unavailable."
WAIT = "Please wait before requesting demonstration access again."
INVALID_REQUEST = "This request could not be accepted."
VERIFY_INVALID = "This verification link is not valid."
VERIFY_EXPIRED = "This verification link has expired."
VERIFY_USED = "This verification link has already been used."


def clean_request(payload: dict[str, str]) -> dict[str, str]:
    cleaned = {
        "first_name": _field(payload.get("first_name", ""), 100, required=True),
        "last_name": _field(payload.get("last_name", ""), 100, required=True),
        "email": _field(payload.get("email", ""), 254, required=True).lower(),
        "organisation": _field(payload.get("organisation", ""), 200, required=True),
        "role": _field(payload.get("role", ""), 200, required=True),
        "interest": _field(payload.get("interest", ""), 1000, required=False),
    }
    if not _email_ok(cleaned["email"]):
        raise APIError(422, "DEMO_REQUEST_INVALID", INVALID_REQUEST)
    return cleaned


def _field(value: str, limit: int, *, required: bool) -> str:
    if not isinstance(value, str) or any(character in value for character in "\r\n\x00"):
        raise APIError(422, "DEMO_REQUEST_INVALID", INVALID_REQUEST)
    text = value.strip()
    if required and not text:
        raise APIError(422, "DEMO_REQUEST_INVALID", INVALID_REQUEST)
    if len(text) > limit:
        raise APIError(422, "DEMO_REQUEST_INVALID", INVALID_REQUEST)
    return text


def _email_ok(value: str) -> bool:
    if any(character.isspace() for character in value):
        return False
    local, separator, domain = value.partition("@")
    if not separator or "@" in domain or not local or "." not in domain:
        return False
    return not domain.startswith(".") and not domain.endswith(".")


def _same(left: str, right: str) -> bool:
    left_bytes = left.encode("utf-8")
    right_bytes = right.encode("utf-8")
    if len(left_bytes) != len(right_bytes):
        return False
    return hmac.compare_digest(left_bytes, right_bytes)


def _millis(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if text.isdigit():
        return int(text)
    if text.endswith(("Z", "z")):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    try:
        delta = parsed.astimezone(timezone.utc) - datetime(1970, 1, 1, tzinfo=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None
    return delta.days * 86_400_000 + delta.seconds * 1000 + delta.microseconds // 1000


def _properties(contact: dict[str, Any]) -> dict[str, Any]:
    properties = contact.get("properties")
    return properties if isinstance(properties, dict) else {}


def _contact_properties(lead: dict[str, str], request_id: str, verification_id: str, requested_ms: int) -> dict[str, str]:
    properties = {
        "email": lead["email"],
        "firstname": lead["first_name"],
        "lastname": lead["last_name"],
        "jobtitle": lead["role"],
        "meem_demo_status": "REQUESTED",
        "meem_demo_requested_at": str(requested_ms),
        "meem_demo_request_id": request_id,
        "meem_demo_verification_jti": verification_id,
    }
    if lead["interest"]:
        properties["meem_demo_interest"] = lead["interest"]
    return properties


def request_demonstration(
    *,
    hubspot: Any,
    mailer: Any,
    lead: dict[str, str],
    now: int,
    public_base: str,
    signing_key: str,
    gate: Any,
    cooldown_seconds: int,
    daily_limit: int,
) -> None:
    if not key_is_strong(signing_key):
        raise APIError(503, "DEMO_ACCESS_MISCONFIGURED", "Demonstration access is not available.")
    try:
        existing = hubspot.find_contact_by_email(lead["email"])
    except HubSpotError:
        raise APIError(503, "DEMO_CRM_UNAVAILABLE", UNAVAILABLE) from None
    if _within_cooldown(existing, now, cooldown_seconds) or gate.email_retry_after(lead["email"], now, cooldown_seconds):
        raise APIError(429, "DEMO_REQUEST_COOLDOWN", WAIT)
    if gate.daily_retry_after(now, daily_limit) is not None:
        raise APIError(429, "DEMO_EMAIL_DAILY_LIMIT", WAIT)

    request_id = secrets.token_urlsafe(18)
    try:
        verification_token, verification_id, _expires = issue_verification(signing_key, request_id, now=now)
    except InvitationError as exc:
        raise APIError(503, "DEMO_ACCESS_MISCONFIGURED", "Demonstration access is not available.") from exc
    requested_ms = now * 1000
    properties = _contact_properties(lead, request_id, verification_id, requested_ms)
    try:
        if existing is None:
            properties["hs_legal_basis"] = LAWFUL_BASIS
            created = hubspot.create_contact(properties)
            contact_id = str(created.get("id") or "")
        else:
            contact_id = str(existing.get("id") or "")
            _update_contact(hubspot, contact_id, properties, existing)
        if not contact_id:
            raise HubSpotError("contact_id", 0)
        _associate_company(hubspot, contact_id, lead["email"], lead["organisation"])
    except HubSpotError:
        raise APIError(503, "DEMO_CRM_UNAVAILABLE", UNAVAILABLE) from None

    link = f"{public_base}/access#verify={verification_token}" if public_base else ""
    gate.remember_email(lead["email"], now)
    if not link or not mailer.configured():
        _mark_email_failed(hubspot, contact_id, existing)
        raise APIError(503, "DEMO_EMAIL_UNAVAILABLE", UNAVAILABLE)
    try:
        _update_contact(hubspot, contact_id, {"meem_demo_status": "EMAIL_VERIFICATION_SENT"}, existing)
    except HubSpotError:
        raise APIError(503, "DEMO_CRM_UNAVAILABLE", UNAVAILABLE) from None
    gate.remember_send(now)
    try:
        mailer.send_verification(to=lead["email"], first_name=lead["first_name"], link=link)
    except EmailError:
        _mark_email_failed(hubspot, contact_id, existing)
        raise APIError(503, "DEMO_EMAIL_UNAVAILABLE", UNAVAILABLE) from None


def _update_contact(hubspot: Any, contact_id: str, properties: dict[str, str], contact: dict[str, Any] | None) -> None:
    try:
        hubspot.update_contact(contact_id, properties)
    except HubSpotError as exc:
        if _basis_refused(contact, exc):
            logger.error(
                "HubSpot refused the update because the existing contact has no hs_legal_basis and the portal requires one. No basis was written."
            )
        raise


def _basis_refused(contact: dict[str, Any] | None, exc: HubSpotError) -> bool:
    if contact is None or exc.operation != "update_contact" or "hs_legal_basis" not in exc.missing_properties:
        return False
    return not str(_properties(contact).get("hs_legal_basis") or "").strip()


def _within_cooldown(contact: dict[str, Any] | None, now: int, cooldown_seconds: int) -> bool:
    if contact is None:
        return False
    requested = _millis(_properties(contact).get("meem_demo_requested_at"))
    if requested is None:
        return False
    return now * 1000 - requested < cooldown_seconds * 1000


def _mark_email_failed(hubspot: Any, contact_id: str, contact: dict[str, Any] | None) -> None:
    try:
        _update_contact(
            hubspot,
            contact_id,
            {"meem_demo_status": "EMAIL_FAILED", "meem_demo_verification_jti": "consumed"},
            contact,
        )
    except HubSpotError:
        logger.warning("Demonstration request status could not be marked failed.")


def _associate_company(hubspot: Any, contact_id: str, email: str, organisation: str) -> None:
    kind, value = company_identity(email, organisation)
    if kind == "domain":
        company = hubspot.find_company_by_domain(value)
        properties = {"name": organisation, "domain": value}
    else:
        company = hubspot.find_company_by_name(value)
        properties = {"name": organisation}
    if company is None:
        company = hubspot.create_company(properties)
    company_id = str(company.get("id") or "")
    if not company_id:
        raise HubSpotError("company_id", 0)
    hubspot.associate_contact_company(contact_id, company_id)


def verify_demonstration(
    *,
    hubspot: Any,
    token: str,
    signing_key: str,
    now: int,
    revoked: set[str],
) -> tuple[str, int, dict[str, str]]:
    try:
        claims = validate_verification(token, signing_key, now=now)
    except InvitationError as exc:
        raise APIError(401, exc.code, exc.message) from None
    try:
        contact = hubspot.find_contact_by_request_id(str(claims["request_id"]))
    except HubSpotError:
        raise APIError(503, "DEMO_CRM_UNAVAILABLE", UNAVAILABLE) from None
    if contact is None:
        raise APIError(401, "DEMO_VERIFY_INVALID", VERIFY_INVALID)
    properties = _properties(contact)
    status = str(properties.get("meem_demo_status") or "")
    stored_jti = str(properties.get("meem_demo_verification_jti") or "")
    if status == "ACCESS_GRANTED" or stored_jti in {"", "consumed"}:
        raise APIError(401, "DEMO_VERIFY_USED", VERIFY_USED)
    if status != "EMAIL_VERIFICATION_SENT" or not _same(stored_jti, str(claims["jti"])):
        raise APIError(401, "DEMO_VERIFY_INVALID", VERIFY_INVALID)
    try:
        access_token, access_id, access_exp = issue_invitation(signing_key, days=14, now=now)
    except (InvitationError, ValueError):
        raise APIError(503, "DEMO_ACCESS_MISCONFIGURED", "Demonstration access is not available.") from None
    if access_id in revoked:
        raise APIError(401, "DEMO_INVITE_REVOKED", "This invitation is no longer valid.")
    contact_id = str(contact.get("id") or "")
    try:
        _update_contact(
            hubspot,
            contact_id,
            {
                "meem_demo_verified_at": str(now * 1000),
                "meem_demo_access_jti": access_id,
                "meem_demo_access_expires_at": str(access_exp * 1000),
                "meem_demo_status": "ACCESS_GRANTED",
                "meem_demo_verification_jti": "consumed",
            },
            contact,
        )
    except HubSpotError:
        raise APIError(503, "DEMO_CRM_UNAVAILABLE", UNAVAILABLE) from None
    try:
        organisation = hubspot.company_name_for_contact(contact_id)
    except HubSpotError:
        organisation = ""
    requested = _millis(properties.get("meem_demo_requested_at"))
    summary = {
        "name": f"{properties.get('firstname', '')} {properties.get('lastname', '')}".strip(),
        "email": str(properties.get("email") or ""),
        "organisation": organisation,
        "role": str(properties.get("jobtitle") or ""),
        "interest": str(properties.get("meem_demo_interest") or ""),
        "requested": format_utc(requested // 1000) if requested else "",
        "verified": format_utc(now),
        "access_expires": format_utc(access_exp),
    }
    return access_token, access_exp, summary
