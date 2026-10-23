"""Azure Communication Services email. One attempt, then a structured failure."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

Delivery = Callable[[str, str, str], None]


class EmailError(Exception):
    def __init__(self) -> None:
        super().__init__("email send failed")


def verification_text(first_name: str, link: str) -> str:
    return (
        f"Hello {first_name},\n\n"
        "Please verify your email address to access the Market Regime Monitor institutional demonstration.\n\n"
        "Verify and Access Demo\n"
        f"{link}\n\n"
        "This verification link expires in 30 minutes.\n\n"
        "For your security, please use ‘End Demo Session’ when you have finished, particularly on a shared device.\n\n"
        "Market Regime Monitor is analytical research software. It does not provide investment recommendations, "
        "trade signals or price predictions.\n\n"
        "MEEM Technologies\n"
    )


def owner_text(summary: dict[str, str]) -> str:
    return (
        "NEW MEEM DEMO LEAD\n\n"
        f"Name: {summary.get('name', '')}\n"
        f"Email: {summary.get('email', '')}\n"
        f"Organisation: {summary.get('organisation', '')}\n"
        f"Role: {summary.get('role', '')}\n"
        f"Interest: {summary.get('interest', '')}\n"
        f"Requested: {summary.get('requested', '')}\n"
        f"Verified: {summary.get('verified', '')}\n"
        f"Access expires: {summary.get('access_expires', '')}\n"
    )


def format_utc(unix_seconds: int) -> str:
    return datetime.fromtimestamp(unix_seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class UnconfiguredMailer:
    def configured(self) -> bool:
        return False

    def send_verification(self, *, to: str, first_name: str, link: str) -> None:
        raise EmailError

    def send_owner_notification(self, *, to: str, summary: dict[str, str]) -> None:
        raise EmailError


class AzureEmailSender:
    def __init__(self, connection_string: str, sender: str, deliver: Delivery | None = None) -> None:
        self._connection_string = connection_string
        self._sender = sender
        self._deliver = deliver

    def configured(self) -> bool:
        return bool(self._connection_string and self._sender)

    def send_verification(self, *, to: str, first_name: str, link: str) -> None:
        self._send(to, "Market Regime Monitor — Verify Demo Access", verification_text(first_name, link))

    def send_owner_notification(self, *, to: str, summary: dict[str, str]) -> None:
        self._send(to, "NEW MEEM DEMO LEAD", owner_text(summary))

    def _send(self, to: str, subject: str, plain: str) -> None:
        if not self.configured():
            raise EmailError
        try:
            if self._deliver is not None:
                self._deliver(to, subject, plain)
                return
            self._azure(to, subject, plain)
        except EmailError:
            raise
        except Exception:
            raise EmailError from None

    def _azure(self, to: str, subject: str, plain: str) -> None:
        from azure.communication.email import EmailClient

        client = EmailClient.from_connection_string(self._connection_string)
        poller = client.begin_send(
            {
                "senderAddress": self._sender,
                "recipients": {"to": [{"address": to}]},
                "content": {"subject": subject, "plainText": plain},
            }
        )
        poller.result(timeout=30)
