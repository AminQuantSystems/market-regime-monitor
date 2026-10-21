"""Market Regime Monitor.

Phase 1I compares categorical What Changed transitions between two snapshots.
The comparison adds no finance of its own. There is no composite directional
regime. The interface is not included.
"""

from market_state.change import (
    ComponentStateTransition,
    MarketRegimeChange,
    calculate_market_regime_change,
    compare_market_regime_snapshots,
)
from market_state.errors import MarketDataError, MarketRegimeError, MarketStateError
from market_state.momentum import MomentumResult, calculate_momentum, classify_momentum
from market_state.regime import MarketRegimeSnapshot, calculate_market_regime_snapshot
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
    "ComponentStateTransition",
    "MarketDataError",
    "MarketRegimeChange",
    "MarketRegimeError",
    "MarketRegimeSnapshot",
    "MarketStateError",
    "MomentumResult",
    "RelativePerformanceResult",
    "TrendResult",
    "VolatilityClassification",
    "VolatilityResult",
    "calculate_market_regime_change",
    "calculate_market_regime_snapshot",
    "compare_market_regime_snapshots",
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
