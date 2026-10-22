"""Process-local analysis limit for one container replica."""

from __future__ import annotations

WINDOW_SECONDS = 60 * 60


class AnalyseRateLimiter:
    """Counts analysis attempts per invitation inside this process.

    The limit resets when the process restarts, including a scale-to-zero
    shutdown. It is abuse protection, not contractual metering.
    """

    def __init__(self) -> None:
        self._attempts: dict[str, list[int]] = {}

    def retry_after(self, jti: str, now: int, limit: int, window: int = WINDOW_SECONDS) -> int | None:
        threshold = now - window
        recent = [stamp for stamp in self._attempts.get(jti, []) if stamp > threshold]
        if len(recent) >= limit:
            self._attempts[jti] = recent
            return max(1, recent[0] + window - now)
        recent.append(now)
        self._attempts[jti] = recent
        return None


class RequestGate:
    """Process-local request and email ceilings.

    These counters reset when the container process restarts, including a
    scale-to-zero shutdown. Per-email cooldown is also checked against the
    timestamp stored in HubSpot, which survives a restart. This is abuse
    protection, not contractual metering.
    """

    def __init__(self) -> None:
        self._ips: dict[str, list[int]] = {}
        self._emails: dict[str, int] = {}
        self._sends: list[int] = []

    def ip_retry_after(self, ip: str, now: int, limit: int, window: int = WINDOW_SECONDS) -> int | None:
        threshold = now - window
        recent = [stamp for stamp in self._ips.get(ip, []) if stamp > threshold]
        if len(recent) >= limit:
            self._ips[ip] = recent
            return max(1, recent[0] + window - now)
        recent.append(now)
        self._ips[ip] = recent
        return None

    def email_retry_after(self, email: str, now: int, cooldown: int) -> int | None:
        stamp = self._emails.get(email)
        if stamp is not None and now - stamp < cooldown:
            return max(1, stamp + cooldown - now)
        return None

    def remember_email(self, email: str, now: int) -> None:
        self._emails[email] = now

    def daily_retry_after(self, now: int, limit: int, window: int = 24 * WINDOW_SECONDS) -> int | None:
        threshold = now - window
        recent = [stamp for stamp in self._sends if stamp > threshold]
        self._sends = recent
        if len(recent) >= limit:
            return max(1, recent[0] + window - now)
        return None

    def remember_send(self, now: int) -> None:
        self._sends.append(now)
