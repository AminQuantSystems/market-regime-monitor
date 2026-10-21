"""Public errors for market-data validation, configuration, and calculations."""


class MarketStateError(ValueError):
    """Project error with a stable code and a human-readable message.

    The message is ``str(error)`` and does not include a traceback.
    ``MarketDataError`` stays a ``ValueError`` through this base.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)


class MarketDataError(MarketStateError):
    """Invalid market data, configuration, or a finance-input failure."""


class MarketRegimeError(MarketStateError):
    """An orchestration result contradicts the request.

    This covers a component identity that disagrees with the snapshot request,
    and a pair of snapshots that cannot be compared. It is not bad market data.
    """
