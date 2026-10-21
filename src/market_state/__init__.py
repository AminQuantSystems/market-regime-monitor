"""Market Regime Monitor.

Phase 1F calculates Trend, short/medium-horizon Momentum, realised volatility,
and Benchmark Relative Performance, and validates local prices. There is no
composite directional regime. The Market Regime Snapshot is not included.
"""

from market_state.errors import MarketDataError
from market_state.momentum import MomentumResult, calculate_momentum, classify_momentum
from market_state.relative_performance import (
    RelativePerformanceResult,
    calculate_relative_performance,
    classify_relative_performance,
)
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
    "RelativePerformanceResult",
    "TrendResult",
    "VolatilityClassification",
    "VolatilityResult",
    "calculate_momentum",
    "calculate_relative_performance",
    "calculate_rv21",
    "calculate_trend",
    "calculate_volatility",
    "classify_momentum",
    "classify_relative_performance",
    "classify_trend",
    "classify_volatility",
    "validate_configuration",
    "validate_market_data",
]
