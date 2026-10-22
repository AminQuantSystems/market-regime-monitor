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
