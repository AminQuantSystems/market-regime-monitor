"""Market State Flight Deck.

Phase 1B calculates the Trend instrument and validates local prices.
Momentum, volatility, relative strength, and directional state are not included.
"""

from market_state.errors import MarketDataError
from market_state.trend import TrendResult, calculate_trend, classify_trend
from market_state.validation import validate_configuration, validate_market_data

__all__ = [
    "MarketDataError",
    "TrendResult",
    "calculate_trend",
    "classify_trend",
    "validate_configuration",
    "validate_market_data",
]
