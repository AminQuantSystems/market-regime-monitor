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
    """A calculated component result contradicts the snapshot request.

    This is an orchestration integrity failure. It is not bad market data.
    """
