"""Decide whether a demonstration request creates a domain company or a named company."""

from __future__ import annotations

FREE_EMAIL_DOMAINS = frozenset(
    {
        "gmail.com",
        "googlemail.com",
        "outlook.com",
        "hotmail.com",
        "yahoo.com",
        "icloud.com",
        "me.com",
        "live.com",
    }
)


def company_identity(email: str, organisation: str) -> tuple[str, str]:
    """Return ('domain', domain) or ('name', organisation).

    Free-mail domains are not created as companies. googlemail.com, icloud.com,
    me.com and live.com follow the same rule as the named consumer domains.
    """
    domain = email.rsplit("@", 1)[1].lower()
    if domain in FREE_EMAIL_DOMAINS:
        return ("name", organisation)
    return ("domain", domain)
