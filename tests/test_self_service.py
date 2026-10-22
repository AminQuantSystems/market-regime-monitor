"""Self-service demonstration access. External services are fakes."""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient

from app.api.access.companies import company_identity
from app.api.access.tokens import issue_invitation, sign_payload
from app.api.access.verification import issue_verification, validate_verification
from app.api.main import create_app
from app.integrations.email.client import AzureEmailSender, EmailError, verification_text
from app.integrations.hubspot.client import HubSpotClient, HubSpotError

KEY = "pytest-demo-signing-key-0123456789abcdef-XYZ"
NOW = 1_800_000_000
LEAD = {
    "first_name": "Ada",
    "last_name": "North",
    "email": "ada@example.com",
    "organisation": "North Yard",
    "role": "Researcher",
    "interest": "Trend states",
    "website": "",
}
DEMO = {"data_source": "demo", "evaluation_date": "2026-03-06", "as_of_date": "2026-03-06"}


class Crm:
    def __init__(self) -> None:
        self.contacts: list[dict] = []
        self.companies: list[dict] = []
        self.associations: list[tuple[str, str]] = []
        self.fail_on: set[str] = set()
        self._next = 1

    def _guard(self, operation: str) -> None:
        if operation in self.fail_on:
            raise HubSpotError(operation, 503)

    def _new_id(self) -> str:
        value = str(self._next)
        self._next += 1
        return value

    def find_contact_by_email(self, email: str) -> dict | None:
        self._guard("find_contact")
        return next((contact for contact in self.contacts if contact["properties"].get("email") == email), None)

    def find_contact_by_request_id(self, request_id: str) -> dict | None:
        self._guard("find_request")
        return next(
            (contact for contact in self.contacts if contact["properties"].get("meem_demo_request_id") == request_id),
            None,
        )

    def create_contact(self, properties: dict[str, str]) -> dict:
        self._guard("create_contact")
        contact = {"id": self._new_id(), "properties": dict(properties)}
        self.contacts.append(contact)
        return contact

    def update_contact(self, contact_id: str, properties: dict[str, str]) -> None:
        self._guard("update_contact")
        contact = next(item for item in self.contacts if item["id"] == contact_id)
        contact["properties"].update(properties)

    def find_company_by_domain(self, domain: str) -> dict | None:
        self._guard("find_company")
        return next((company for company in self.companies if company["properties"].get("domain") == domain), None)

    def find_company_by_name(self, name: str) -> dict | None:
        self._guard("find_company")
        return next((company for company in self.companies if company["properties"].get("name") == name), None)

    def create_company(self, properties: dict[str, str]) -> dict:
        self._guard("create_company")
        company = {"id": self._new_id(), "properties": dict(properties)}
        self.companies.append(company)
        return company

    def associate_contact_company(self, contact_id: str, company_id: str) -> None:
        self._guard("associate")
        self.associations.append((contact_id, company_id))

    def company_name_for_contact(self, contact_id: str) -> str:
        self._guard("company_name")
        for linked_contact, company_id in self.associations:
            if linked_contact == contact_id:
                company = next(item for item in self.companies if item["id"] == company_id)
                return str(company["properties"].get("name") or "")
        return ""


class Mail:
    def __init__(self) -> None:
        self.configured_flag = True
        self.verification: list[tuple[str, str, str]] = []
        self.owner: list[tuple[str, dict]] = []
        self.fail_verification = False
        self.fail_owner = False

    def configured(self) -> bool:
        return self.configured_flag

    def send_verification(self, *, to: str, first_name: str, link: str) -> None:
        if self.fail_verification:
            raise EmailError
        self.verification.append((to, first_name, link))

    def send_owner_notification(self, *, to: str, summary: dict[str, str]) -> None:
        if self.fail_owner:
            raise RuntimeError("notification failed")
        self.owner.append((to, summary))


def _client(monkeypatch: pytest.MonkeyPatch, **env: str) -> tuple[TestClient, Crm, Mail]:
    for name in (
        "MEEM_DEMO_ACCESS_REQUIRED",
        "MEEM_DEMO_SIGNING_KEY",
        "MEEM_DEMO_REVOKED_JTIS",
        "MEEM_DEMO_COOKIE_SECURE",
        "MEEM_DEMO_PUBLIC_BASE_URL",
        "MEEM_DEMO_REQUEST_LIMIT_PER_HOUR",
        "MEEM_DEMO_VERIFICATION_COOLDOWN_MINUTES",
        "MEEM_DEMO_EMAIL_DAILY_LIMIT",
        "MEEM_DEMO_OWNER_EMAIL",
        "HUBSPOT_SERVICE_KEY",
        "AZURE_COMMUNICATION_CONNECTION_STRING",
        "AZURE_EMAIL_SENDER",
        "MEEM_SERVE_FRONTEND",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("MEEM_DEMO_ACCESS_REQUIRED", "1")
    monkeypatch.setenv("MEEM_DEMO_SIGNING_KEY", KEY)
    monkeypatch.setenv("MEEM_DEMO_PUBLIC_BASE_URL", "https://demo.example")
    monkeypatch.setenv("MEEM_DEMO_COOKIE_SECURE", "0")
    for name, value in env.items():
        monkeypatch.setenv(name, value)
    app = create_app()
    crm = Crm()
    mail = Mail()
    app.state.hubspot = crm
    app.state.mailer = mail
    return TestClient(app, raise_server_exceptions=False), crm, mail


def _token(mail: Mail) -> str:
    return mail.verification[0][2].split("#verify=", 1)[1]


def test_company_identity_uses_domain_or_submitted_name() -> None:
    assert company_identity("ada@example.com", "North Yard") == ("domain", "example.com")
    assert company_identity("ada@gmail.com", "Independent Office") == ("name", "Independent Office")
    assert company_identity("ada@icloud.com", "Family Office") == ("name", "Family Office")


def test_verification_token_rejects_expiry_signature_purpose_and_future_cap() -> None:
    token, verification_id, expires_at = issue_verification(KEY, "request-1", now=NOW)
    assert validate_verification(token, KEY, now=NOW)["jti"] == verification_id
    expired, _, expired_at = issue_verification(KEY, "request-1", now=NOW, exp=NOW - 1)
    with pytest.raises(Exception) as caught:
        validate_verification(expired, KEY, now=NOW)
    assert caught.value.code == "DEMO_VERIFY_EXPIRED"
    assert expired_at == NOW - 1
    segment, signature = token.split(".", 1)
    broken_signature = ("A" if not signature.startswith("A") else "B") + signature[1:]
    with pytest.raises(Exception) as bad_signature:
        validate_verification(f"{segment}.{broken_signature}", KEY, now=NOW)
    assert bad_signature.value.code == "DEMO_VERIFY_INVALID"
    wrong_purpose = sign_payload(KEY, {"exp": NOW + 60, "jti": "j", "purpose": "other", "request_id": "request-1", "v": 1})
    with pytest.raises(Exception) as purpose:
        validate_verification(wrong_purpose, KEY, now=NOW)
    assert purpose.value.code == "DEMO_VERIFY_INVALID"
    too_long, _, _ = issue_verification(KEY, "request-1", now=NOW, exp=NOW + 61 * 60)
    with pytest.raises(Exception) as future:
        validate_verification(too_long, KEY, now=NOW)
    assert future.value.code == "DEMO_VERIFY_INVALID"


def test_hubspot_client_uses_exact_email_company_lookup_and_default_association() -> None:
    calls: list[tuple[str, str]] = []

    def transport(method: str, url: str, payload: dict | None) -> tuple[int, dict | None]:
        calls.append((method, url))
        if method == "GET" and "idProperty=email" in url:
            return 404, {}
        if method == "POST" and url.endswith("/contacts"):
            return 201, {"id": "10", "properties": payload["properties"] if payload else {}}
        if method == "POST" and url.endswith("/companies/search"):
            return 200, {"results": []}
        if method == "POST" and url.endswith("/companies"):
            return 201, {"id": "20"}
        if method == "PUT" and "/associations/default/" in url:
            return 200, {}
        return 500, {}

    client = HubSpotClient("service-key", transport=transport)
    assert client.find_contact_by_email("ada@example.com") is None
    created = client.create_contact({"email": "ada@example.com"})
    company = client.find_company_by_domain("example.com")
    assert company is None
    client.associate_contact_company(created["id"], client.create_company({"name": "North Yard", "domain": "example.com"})["id"])
    assert calls[0][0] == "GET"
    assert "/crm/objects/2026-09/contacts/" in calls[0][1]
    assert calls[2][1].endswith("/crm/objects/2026-09/companies/search")
    assert "/contact/10/associations/default/company/20" in calls[4][1]


def test_email_sender_builds_verification_without_calling_azure_when_injected() -> None:
    sent: list[tuple[str, str, str]] = []
    sender = AzureEmailSender("endpoint=unit;", "donotreply@example.com", deliver=lambda to, subject, plain: sent.append((to, subject, plain)))
    sender.send_verification(to="ada@example.com", first_name="Ada", link="https://demo.example/access#verify=abc")
    assert sent[0][1] == "Market Regime Monitor — Verify Demo Access"
    assert sent[0][2] == verification_text("Ada", "https://demo.example/access#verify=abc")
    assert "investment recommendations" in sent[0][2]


def test_request_validation_honeypot_and_crm_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    client, crm, mail = _client(monkeypatch)
    invalid = client.post("/api/v1/demo-access/request", json={**LEAD, "email": "not-an-email"})
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "DEMO_REQUEST_INVALID"
    injected = client.post("/api/v1/demo-access/request", json={**LEAD, "first_name": "Ada\r\nBcc: x"})
    assert injected.status_code == 422
    honeypot = client.post("/api/v1/demo-access/request", json={**LEAD, "website": "https://spam.example", "email": "bad"})
    assert honeypot.status_code == 200
    assert honeypot.json() == {"status": "verification_required"}
    assert crm.contacts == []
    assert mail.verification == []
    crm.fail_on.add("find_contact")
    failed = client.post("/api/v1/demo-access/request", json=LEAD)
    assert failed.status_code == 503
    assert failed.json()["error"]["code"] == "DEMO_CRM_UNAVAILABLE"
    assert mail.verification == []


def test_request_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    client, crm, _mail = _client(monkeypatch, MEEM_DEMO_REQUEST_LIMIT_PER_HOUR="1", MEEM_DEMO_EMAIL_DAILY_LIMIT="1")
    first = client.post("/api/v1/demo-access/request", json=LEAD)
    assert first.status_code == 200
    limited = client.post("/api/v1/demo-access/request", json={**LEAD, "email": "other@example.com"})
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "DEMO_REQUEST_RATE_LIMIT"
    cooled, _, _ = _client(monkeypatch, MEEM_DEMO_VERIFICATION_COOLDOWN_MINUTES="10")
    assert cooled.post("/api/v1/demo-access/request", json=LEAD).status_code == 200
    again = cooled.post("/api/v1/demo-access/request", json=LEAD)
    assert again.status_code == 429
    assert again.json()["error"]["code"] == "DEMO_REQUEST_COOLDOWN"
    persisted, persisted_crm, _persisted_mail = _client(monkeypatch)
    persisted_crm.contacts.append(
        {
            "id": "3",
            "properties": {"email": "ada@example.com", "meem_demo_requested_at": str(int(time.time()) * 1000)},
        }
    )
    persisted_again = persisted.post("/api/v1/demo-access/request", json=LEAD)
    assert persisted_again.status_code == 429
    assert persisted_again.json()["error"]["code"] == "DEMO_REQUEST_COOLDOWN"
    daily, _, mail = _client(monkeypatch, MEEM_DEMO_EMAIL_DAILY_LIMIT="1", MEEM_DEMO_REQUEST_LIMIT_PER_HOUR="5")
    assert daily.post("/api/v1/demo-access/request", json=LEAD).status_code == 200
    second = daily.post("/api/v1/demo-access/request", json={**LEAD, "email": "bea@example.com"})
    assert second.status_code == 429
    assert second.json()["error"]["code"] == "DEMO_EMAIL_DAILY_LIMIT"
    assert len(mail.verification) == 1
    assert len(crm.contacts) == 1


def test_contact_deduplication_company_and_free_email(monkeypatch: pytest.MonkeyPatch) -> None:
    client, crm, mail = _client(monkeypatch, MEEM_DEMO_VERIFICATION_COOLDOWN_MINUTES="10")
    crm.contacts.append({"id": "9", "properties": {"email": "ada@example.com", "meem_demo_requested_at": "1"}})
    crm.companies.append({"id": "4", "properties": {"name": "Existing", "domain": "example.com"}})
    response = client.post("/api/v1/demo-access/request", json=LEAD)
    assert response.status_code == 200
    assert len(crm.contacts) == 1
    assert crm.contacts[0]["id"] == "9"
    assert crm.contacts[0]["properties"]["firstname"] == "Ada"
    assert crm.contacts[0]["properties"]["jobtitle"] == "Researcher"
    assert crm.contacts[0]["properties"]["meem_demo_status"] == "EMAIL_VERIFICATION_SENT"
    assert crm.associations == [("9", "4")]
    assert len(crm.companies) == 1
    assert "#verify=" in mail.verification[0][2]
    assert "?verify=" not in mail.verification[0][2]
    free, free_crm, _free_mail = _client(monkeypatch)
    created = free.post("/api/v1/demo-access/request", json={**LEAD, "email": "ada@gmail.com", "organisation": "Independent Office"})
    assert created.status_code == 200
    assert free_crm.companies[0]["properties"] == {"name": "Independent Office"}
    assert free_crm.associations


def test_email_failure_does_not_grant_access(monkeypatch: pytest.MonkeyPatch) -> None:
    client, crm, mail = _client(monkeypatch)
    mail.fail_verification = True
    response = client.post("/api/v1/demo-access/request", json=LEAD)
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "DEMO_EMAIL_UNAVAILABLE"
    assert crm.contacts[0]["properties"]["meem_demo_status"] == "EMAIL_FAILED"
    assert crm.contacts[0]["properties"]["meem_demo_verification_jti"] == "consumed"


def test_verification_grants_one_session_and_blocks_replay(monkeypatch: pytest.MonkeyPatch) -> None:
    client, crm, mail = _client(
        monkeypatch,
        MEEM_DEMO_COOKIE_SECURE="1",
        MEEM_DEMO_OWNER_EMAIL="owner@example.com",
    )
    mail.fail_owner = True
    assert client.post("/api/v1/demo-access/request", json=LEAD).status_code == 200
    granted = client.post("/api/v1/demo-access/verify", json={"token": _token(mail)})
    assert granted.status_code == 200
    cookie = granted.headers["set-cookie"]
    assert "meem_demo_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert crm.contacts[0]["properties"]["meem_demo_status"] == "ACCESS_GRANTED"
    assert crm.contacts[0]["properties"]["meem_demo_verification_jti"] == "consumed"
    assert crm.contacts[0]["properties"]["meem_demo_access_jti"]
    assert "notification failed" not in granted.text
    assert mail.owner == []
    replay = client.post("/api/v1/demo-access/verify", json={"token": _token(mail)})
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "DEMO_VERIFY_USED"
    demo_token, _, _ = issue_invitation(KEY, now=NOW, days=14)
    wrong = client.post("/api/v1/demo-access/verify", json={"token": demo_token})
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "DEMO_VERIFY_INVALID"
    mismatched, mismatched_crm, _mismatched_mail = _client(monkeypatch)
    token, _verification_id, _expires = issue_verification(KEY, "req-9")
    mismatched_crm.contacts.append(
        {
            "id": "8",
            "properties": {
                "meem_demo_request_id": "req-9",
                "meem_demo_verification_jti": "different-jti",
                "meem_demo_status": "EMAIL_VERIFICATION_SENT",
            },
        }
    )
    mismatch = mismatched.post("/api/v1/demo-access/verify", json={"token": token})
    assert mismatch.status_code == 401
    assert mismatch.json()["error"]["code"] == "DEMO_VERIFY_INVALID"


def test_manual_invite_logout_and_analysis_gate_remain(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _crm, mail = _client(monkeypatch, MEEM_DEMO_COOKIE_SECURE="0")
    denied = client.post("/api/v1/market-regime/analyse", data=DEMO)
    assert denied.status_code == 401
    invitation, _, _ = issue_invitation(KEY, days=14)
    exchanged = client.post("/api/v1/auth/exchange", json={"token": invitation})
    assert exchanged.status_code == 200
    verification, _, _ = issue_verification(KEY, "request-x", now=NOW)
    rejected = client.post("/api/v1/auth/exchange", json={"token": verification})
    assert rejected.status_code == 401
    assert client.post("/api/v1/auth/logout").status_code == 200
    assert client.post("/api/v1/demo-access/request", json=LEAD).status_code == 200
    session = client.post("/api/v1/demo-access/verify", json={"token": _token(mail)})
    assert session.status_code == 200
    allowed = client.post("/api/v1/market-regime/analyse", data=DEMO)
    assert allowed.status_code == 200
    assert allowed.json()["markets"][0]["current"]["trend"]["trend_state"] == "Strong Up"
    ended = client.post("/api/v1/auth/logout")
    assert ended.status_code == 200
    assert "Max-Age=0" in ended.headers["set-cookie"]
    assert client.post("/api/v1/market-regime/analyse", data=DEMO).status_code == 401
