"""Assemble one market's four instrument results at one exact date.

``MarketRegimeSnapshot`` is an orchestration and audit record. It is not a
fifth finance model. It does not calculate a moving average, a return, a
realised volatility, a percentile, or an active return, and it does not
combine the four readings into a score, a vote, or another label.

Direction is ``trend.trend_state``. The snapshot does not calculate a second
direction. A snapshot is one market at one as-of date. It does not contain
the previous session.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from market_state.momentum import MomentumResult, calculate_momentum
from market_state.relative_performance import RelativePerformanceResult, calculate_relative_performance
from market_state.trend import TrendResult, calculate_trend
from market_state.volatility import VolatilityResult, calculate_volatility


@dataclass(frozen=True)
class MarketRegimeSnapshot:
    """The four instrument results for one market on one observation date."""

    market_id: str
    as_of_date: str
    trend: TrendResult
    momentum: MomentumResult
    volatility: VolatilityResult
    relative_performance: RelativePerformanceResult


def calculate_market_regime_snapshot(
    prices: pd.DataFrame,
    market_id: str,
    benchmark_id: str,
    as_of_date: str,
) -> MarketRegimeSnapshot:
    """Assemble Trend, Momentum, Volatility, and Benchmark Relative Performance.

    All four calculations receive this prices frame, this market, and this
    exact as-of date. Relative performance also receives ``benchmark_id``.
    V1 accepts only ACWI there, and that check stays in the relative-performance
    instrument. If any calculation raises ``MarketDataError``, that error
    propagates and no snapshot is returned.

    The binding history length is whatever the longest component requires.
    That component is the volatility regime. This function does not repeat
    the minimum and does not call ``validate_market_data``.
    """
    trend = calculate_trend(prices, market_id, as_of_date)
    momentum = calculate_momentum(prices, market_id, as_of_date)
    volatility = calculate_volatility(prices, market_id, as_of_date)
    relative_performance = calculate_relative_performance(prices, market_id, benchmark_id, as_of_date)
    return MarketRegimeSnapshot(
        market_id=market_id,
        as_of_date=as_of_date,
        trend=trend,
        momentum=momentum,
        volatility=volatility,
        relative_performance=relative_performance,
    )
