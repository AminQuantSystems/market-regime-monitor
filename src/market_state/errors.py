"""Public errors for market-data validation, configuration, and calculations."""


class MarketDataError(ValueError):
    """Invalid market data or configuration.

    ``code`` is the stable machine-readable reason. The exception text is the
    human-readable message and does not include a traceback.
    """

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        super().__init__(message)
