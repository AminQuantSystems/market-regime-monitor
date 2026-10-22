"""Gated demonstration access. Finance behaviour is compared, not redefined."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api.access.settings import key_is_strong
from app.api.access.tokens import issue_invitation, sign_payload, validate_invitation
from app.api.main import create_app

ROOT = Path(__file__).resolve().parents[1]
KEY = "pytest-demo-signing-key-0123456789abcdef-XYZ"
NOW = 1_800_000_000
DEMO = {"data_source": "demo", "evaluation_date": "2026-03-06", "as_of_date": "2026-03-06"}


def _env(monkeypatch: pytest.MonkeyPatch, **values: str) -> None:
    for name in (
        "MEEM_DEMO_ACCESS_REQUIRED",
        "MEEM_DEMO_SIGNING_KEY",
        "MEEM_DEMO_REVOKED_JTIS",
        "MEEM_DEMO_CONTACT_EMAIL",
        "MEEM_DEMO_COOKIE_SECURE",
        "MEEM_DEMO_ANALYSE_LIMIT_PER_HOUR",
        "MEEM_SERVE_FRONTEND",
    ):
        monkeypatch.delenv(name, raising=False)
    for name, value in values.items():
        monkeypatch.setenv(name, value)


def _gated(monkeypatch: pytest.MonkeyPatch, **values: str) -> TestClient:
    _env(monkeypatch, MEEM_DEMO_ACCESS_REQUIRED="1", MEEM_DEMO_SIGNING_KEY=KEY, **values)
    return TestClient(create_app(), raise_server_exceptions=False)


def _live_invite(**kwargs: object) -> tuple[str, str, int]:
    return issue_invitation(KEY, **kwargs)  # type: ignore[arg-type]


def test_valid_invitation_round_trip() -> None:
    token, invitation_id, expires_at = issue_invitation(KEY, now=NOW, days=14)
    claims = validate_invitation(token, KEY, now=NOW)
    assert claims == {"v": 1, "jti": invitation_id, "exp": expires_at}
    assert "email" not in token


def test_invalid_signature_is_rejected() -> None:
    token, _invitation_id, _expires_at = _live_invite()
    broken = token[:-1] + ("A" if token[-1] != "A" else "B")
    with pytest.raises(Exception) as caught:
        validate_invitation(broken, KEY, now=NOW)
    assert caught.value.code == "DEMO_INVITE_INVALID"


def test_expired_invitation_is_rejected() -> None:
    token, _invitation_id, expires_at = issue_invitation(KEY, now=NOW, days=1)
    with pytest.raises(Exception) as caught:
        validate_invitation(token, KEY, now=expires_at)
    assert caught.value.code == "DEMO_INVITE_EXPIRED"


def test_malformed_and_incomplete_invitations_are_rejected() -> None:
    with pytest.raises(Exception) as malformed:
        validate_invitation("not-a-token", KEY, now=NOW)
    assert malformed.value.code == "DEMO_INVITE_MALFORMED"
    incomplete = sign_payload(KEY, {"v": 1, "jti": "missing-expiry"})
    with pytest.raises(Exception) as missing:
        validate_invitation(incomplete, KEY, now=NOW)
    assert missing.value.code == "DEMO_INVITE_MALFORMED"


def test_unsupported_version_is_rejected() -> None:
    token = sign_payload(KEY, {"v": 2, "jti": "future-format", "exp": NOW + 60})
    with pytest.raises(Exception) as caught:
        validate_invitation(token, KEY, now=NOW)
    assert caught.value.code == "DEMO_INVITE_UNSUPPORTED"


def test_revoked_jti_is_rejected() -> None:
    token, invitation_id, _expires_at = issue_invitation(KEY, now=NOW)
    with pytest.raises(Exception) as caught:
        validate_invitation(token, KEY, now=NOW, revoked={invitation_id})
    assert caught.value.code == "DEMO_INVITE_REVOKED"


def test_unreasonable_future_expiry_is_rejected() -> None:
    token, _invitation_id, _expires_at = issue_invitation(KEY, now=NOW, exp=NOW + 31 * 24 * 60 * 60)
    with pytest.raises(Exception) as caught:
        validate_invitation(token, KEY, now=NOW)
    assert caught.value.code == "DEMO_INVITE_INVALID"


def test_missing_or_weak_signing_key_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    _env(monkeypatch, MEEM_DEMO_ACCESS_REQUIRED="1")
    with pytest.raises(RuntimeError, match="too weak"):
        create_app()
    _env(monkeypatch, MEEM_DEMO_ACCESS_REQUIRED="1", MEEM_DEMO_SIGNING_KEY="a" * 50)
    assert key_is_strong("a" * 50) is False
    with pytest.raises(RuntimeError, match="too weak"):
        create_app()


def test_exchange_sets_cookie_and_logout_clears_it(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _gated(monkeypatch, MEEM_DEMO_COOKIE_SECURE="1")
    token, _invitation_id, _expires_at = _live_invite(days=14)
    response = client.post("/api/v1/auth/exchange", json={"token": token})
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert "meem_demo_session=" in cookie
    assert "HttpOnly" in cookie
    assert "Secure" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    assert token not in response.text
    logout = client.post("/api/v1/auth/logout")
    assert logout.status_code == 200
    cleared = logout.headers["set-cookie"].lower()
    assert "meem_demo_session=" in cleared
    assert "max-age=0" in cleared


def test_cookie_can_be_insecure_for_local_http(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _gated(monkeypatch, MEEM_DEMO_COOKIE_SECURE="0")
    token, _invitation_id, _expires_at = _live_invite()
    response = client.post("/api/v1/auth/exchange", json={"token": token})
    assert "Secure" not in response.headers["set-cookie"]
    assert "HttpOnly" in response.headers["set-cookie"]


def test_protected_api_requires_a_session_and_accepts_a_valid_one(monkeypatch: pytest.MonkeyPatch) -> None:
    open_client = TestClient(create_app(), raise_server_exceptions=False)
    expected = open_client.post("/api/v1/market-regime/analyse", data=DEMO)
    assert expected.status_code == 200
    gated = _gated(monkeypatch)
    denied = gated.post("/api/v1/market-regime/analyse", data=DEMO)
    assert denied.status_code == 401
    assert denied.json()["error"]["code"] == "DEMO_AUTH_REQUIRED"
    assert "traceback" not in denied.text.lower()
    token, _invitation_id, _expires_at = _live_invite()
    assert gated.post("/api/v1/auth/exchange", json={"token": token}).status_code == 200
    allowed = gated.post("/api/v1/market-regime/analyse", data=DEMO)
    assert allowed.status_code == 200
    assert allowed.json() == expected.json()


def test_browser_entry_redirects_and_health_stays_public(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _gated(monkeypatch)
    page = client.get("/", follow_redirects=False)
    assert page.status_code == 302
    assert page.headers["location"] == "/access"
    access = client.get("/access", follow_redirects=False)
    assert access.status_code != 302
    health = client.get("/healthz")
    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    asset = client.get("/assets/app.js", follow_redirects=False)
    assert asset.status_code != 302
    assert asset.status_code != 401


def test_public_contact_configuration(monkeypatch: pytest.MonkeyPatch) -> None:
    hidden = _gated(monkeypatch)
    assert hidden.get("/api/v1/public/demo-access").json() == {"contact_email": None}
    shown = _gated(monkeypatch, MEEM_DEMO_CONTACT_EMAIL="reviews@example.com")
    assert shown.get("/api/v1/public/demo-access").json() == {"contact_email": "reviews@example.com"}


def test_analyse_rate_limit_returns_429(monkeypatch: pytest.MonkeyPatch) -> None:
    client = _gated(monkeypatch, MEEM_DEMO_ANALYSE_LIMIT_PER_HOUR="1")
    token, _invitation_id, _expires_at = _live_invite()
    assert client.post("/api/v1/auth/exchange", json={"token": token}).status_code == 200
    assert client.post("/api/v1/market-regime/analyse", data=DEMO).status_code == 200
    limited = client.post("/api/v1/market-regime/analyse", data=DEMO)
    assert limited.status_code == 429
    assert limited.json()["error"]["code"] == "DEMO_RATE_LIMIT_EXCEEDED"
    assert int(limited.headers["retry-after"]) >= 1


def test_revoked_environment_value_denies_exchange(monkeypatch: pytest.MonkeyPatch) -> None:
    token, invitation_id, _expires_at = _live_invite()
    client = _gated(monkeypatch, MEEM_DEMO_REVOKED_JTIS=f"other,{invitation_id}")
    response = client.post("/api/v1/auth/exchange", json={"token": token})
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "DEMO_INVITE_REVOKED"
    assert token not in response.text


def test_invite_script_prints_fragment_link_without_the_key() -> None:
    env = os.environ.copy()
    env["MEEM_DEMO_SIGNING_KEY"] = KEY
    result = subprocess.run(
        [sys.executable, "scripts/create_demo_invite.py", "--base-url", "https://demo.example", "--days", "14"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "Invite ID:" in result.stdout
    assert "Expires:" in result.stdout
    assert "Link: https://demo.example/access#token=" in result.stdout
    assert "?token=" not in result.stdout
    assert KEY not in result.stdout
    assert KEY not in result.stderr
    refused = subprocess.run(
        [sys.executable, "scripts/create_demo_invite.py", "--base-url", "https://demo.example", "--days", "31"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert refused.returncode == 2
    assert KEY not in refused.stderr
