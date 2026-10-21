"""Market State Flight Deck.

Phase 1C calculates Trend and short/medium-horizon Momentum, and validates
local prices. Volatility, relative strength, and directional state are not included.
"""

from market_state.errors import MarketDataError
from market_state.momentum import MomentumResult, calculate_momentum, classify_momentum
from market_state.trend import TrendResult, calculate_trend, classify_trend
from market_state.validation import validate_configuration, validate_market_data

__all__ = [
    "MarketDataError",
    "MomentumResult",
    "TrendResult",
    "calculate_momentum",
    "calculate_trend",
    "classify_momentum",
    "classify_trend",
    "validate_configuration",
    "validate_market_data",
]
