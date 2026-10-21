"""Market Regime Monitor.

Phase 1D calculates Trend, short/medium-horizon Momentum, and realised
volatility, and validates local prices. Relative strength and directional
state are not included.
"""

from market_state.errors import MarketDataError
from market_state.momentum import MomentumResult, calculate_momentum, classify_momentum
from market_state.trend import TrendResult, calculate_trend, classify_trend
from market_state.validation import validate_configuration, validate_market_data
from market_state.volatility import (
    VolatilityClassification,
    VolatilityResult,
    calculate_rv21,
    calculate_volatility,
    classify_volatility,
)

__all__ = [
    "MarketDataError",
    "MomentumResult",
    "TrendResult",
    "VolatilityClassification",
    "VolatilityResult",
    "calculate_momentum",
    "calculate_rv21",
    "calculate_trend",
    "calculate_volatility",
    "classify_momentum",
    "classify_trend",
    "classify_volatility",
    "validate_configuration",
    "validate_market_data",
]
