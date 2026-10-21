"""Benchmark-relative performance against the common ACWI comparison benchmark.

The instrument answers how this market performed over the previous 63 trading
observations relative to ACWI. The value is conventional active return: the
asset simple return minus the benchmark simple return. ACWI is the common V1
comparison benchmark used so every enabled market shares one scale. It is not
claimed to be the mandate-specific performance benchmark for each regional
market. This is cross-market comparison, not performance reporting.

The module does not use Trend, Momentum, Volatility, or directional state.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import pandas as pd

from market_state.errors import MarketDataError

COMMON_BENCHMARK = "ACWI"
RETURN_LOOKBACK = 63
MINIMUM_OBSERVATIONS = RETURN_LOOKBACK + 1
STRONG_OUTPERFORM_MIN = 0.05
OUTPERFORM_MIN = 0.02
UNDERPERFORM_MAX = -0.02
STRONG_UNDERPERFORM_MAX = -0.05


@dataclass(frozen=True)
class RelativePerformanceResult:
    """Full-precision benchmark-relative measurement for one observation."""

    market_id: str
    benchmark_id: str
    as_of_date: str
    adjusted_close: float
    benchmark_adjusted_close: float
    asset_return_63: float
    benchmark_return_63: float
    active_return_63: float
    relative_performance_state: str
    reason_code: str


def classify_relative_performance(active_return_63) -> tuple[str, str]:
    """Classify one computed active return.

    This is a predicate on a single finite number. It does not rebuild the
    return from prices. Comparisons are exact. There is no tolerance and no
    rounding. The five bands cover every finite real value and do not overlap.
    """
    active = _finite_active_return(active_return_63)
    if active >= STRONG_OUTPERFORM_MIN:
        return "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM"
    if active >= OUTPERFORM_MIN:
        return "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"
    if active > UNDERPERFORM_MAX:
        return "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL"
    if active > STRONG_UNDERPERFORM_MAX:
        return "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"
    return "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"


def calculate_relative_performance(
    prices: pd.DataFrame,
    market_id: str,
    benchmark_id: str,
    as_of_date: str,
) -> RelativePerformanceResult:
    """Calculate Benchmark Relative Performance for one asset at an exact date.

    V1 accepts only ``benchmark_id == ACWI``. ACWI is the common comparison
    benchmark. A request for ACWI itself, or any request where the market and
    the benchmark identifier are the same, fails with ``DATA_BENCHMARK_EXCLUDED``
    and does not return a zero active return. Any other benchmark identifier
    fails with ``CONFIG_WRONG_BENCHMARK``.

    The asset and ACWI are then taken separately. Each must contain the exact
    as-of date. Only rows on or before that date are used. Each history needs
    at least 64 observations. The latest 64 date labels must match exactly.
    The simple returns use the observation at ``t`` and the observation 63
    places earlier. Later rows cannot complete a short history.
    """
    _require_frame(prices)
    if market_id == benchmark_id or market_id == COMMON_BENCHMARK:
        raise MarketDataError(
            "DATA_BENCHMARK_EXCLUDED",
            f"{market_id} is the common comparison benchmark and is not classified against itself",
        )
    if benchmark_id != COMMON_BENCHMARK:
        raise MarketDataError(
            "CONFIG_WRONG_BENCHMARK",
            f"V1 benchmark_id must be {COMMON_BENCHMARK}",
        )

    asset = _history_through(prices, market_id, as_of_date)
    benchmark = _history_through(prices, benchmark_id, as_of_date)
    asset_window = asset.iloc[-MINIMUM_OBSERVATIONS:]
    benchmark_window = benchmark.iloc[-MINIMUM_OBSERVATIONS:]
    if asset_window["date"].tolist() != benchmark_window["date"].tolist():
        raise MarketDataError(
            "DATA_DATE_INDEX_MISMATCH",
            "asset and ACWI dates differ across the latest 64 observations",
        )

    asset_t = _positive_price(asset_window["adjusted_close"].iloc[-1], "adjusted_close")
    asset_lag = _positive_price(asset_window["adjusted_close"].iloc[0], "adjusted_close")
    benchmark_t = _positive_price(benchmark_window["adjusted_close"].iloc[-1], "benchmark adjusted_close")
    benchmark_lag = _positive_price(benchmark_window["adjusted_close"].iloc[0], "benchmark adjusted_close")
    asset_return = _simple_return(asset_t, asset_lag)
    benchmark_return = _simple_return(benchmark_t, benchmark_lag)
    active = asset_return - benchmark_return
    if not math.isfinite(active):
        raise MarketDataError("DATA_INVALID_ACTIVE_RETURN", "active return is not finite")
    state, reason = classify_relative_performance(active)
    return RelativePerformanceResult(
        market_id=market_id,
        benchmark_id=benchmark_id,
        as_of_date=as_of_date,
        adjusted_close=asset_t,
        benchmark_adjusted_close=benchmark_t,
        asset_return_63=asset_return,
        benchmark_return_63=benchmark_return,
        active_return_63=active,
        relative_performance_state=state,
        reason_code=reason,
    )


def _require_frame(prices: pd.DataFrame) -> None:
    if not isinstance(prices, pd.DataFrame):
        raise MarketDataError("DATA_INVALID_COLUMNS", "expected a pandas DataFrame")
    missing = [column for column in ("date", "market_id", "adjusted_close") if column not in prices.columns]
    if missing:
        raise MarketDataError("DATA_INVALID_COLUMNS", f"missing columns {missing}")


def _history_through(prices: pd.DataFrame, market_id: str, as_of_date: str) -> pd.DataFrame:
    market = prices.loc[prices["market_id"] == market_id, ["date", "market_id", "adjusted_close"]].copy()
    if market.empty:
        raise MarketDataError("DATA_MISSING_MARKET", f"missing required market: {market_id}")
    if not market["date"].eq(as_of_date).any():
        raise MarketDataError(
            "DATA_INVALID_DATE",
            f"as_of_date is not an observation for {market_id}: {as_of_date}",
        )
    history = market.loc[market["date"] <= as_of_date].sort_values("date", kind="mergesort")
    duplicated = history.loc[history["date"].duplicated(), "date"]
    if not duplicated.empty:
        raise MarketDataError("DATA_DUPLICATE_DATE", f"duplicate date for {market_id}: {duplicated.iloc[0]}")
    if len(history) < MINIMUM_OBSERVATIONS:
        raise MarketDataError(
            "DATA_INSUFFICIENT_HISTORY",
            f"{market_id} has {len(history)} observations through {as_of_date}; "
            f"Benchmark Relative Performance requires at least {MINIMUM_OBSERVATIONS}",
        )
    return history


def _simple_return(price_t: float, lagged_price: float) -> float:
    """Return the 63-observation simple return.

    The definition is ``price_t / lagged_price - 1``. When that quotient is
    finite and the return is strictly greater than -1, that value is used.
    Ordinary boundary prices stay on the specified side of the classification
    thresholds.

    ``expm1(log(price_t) - log(lagged_price))`` is the same real number and
    does not form the quotient. It is evaluated when the direct quotient is
    not a usable return. A non-finite result, or a result that is not strictly
    greater than -1, including a collapse to exactly -1, is rejected. Nothing
    is clipped or replaced.
    """
    try:
        quotient = price_t / lagged_price
    except (ArithmeticError, ValueError) as error:
        raise MarketDataError(
            "DATA_INVALID_ACTIVE_RETURN",
            "simple return is not a finite number greater than -1",
        ) from error
    if math.isfinite(quotient) and quotient > 0:
        simple = quotient - 1.0
        if math.isfinite(simple) and simple > -1.0:
            return simple
    try:
        simple = math.expm1(math.log(price_t) - math.log(lagged_price))
    except (ArithmeticError, ValueError) as error:
        raise MarketDataError(
            "DATA_INVALID_ACTIVE_RETURN",
            "simple return is not a finite number greater than -1",
        ) from error
    if not math.isfinite(simple) or simple <= -1.0:
        raise MarketDataError(
            "DATA_INVALID_ACTIVE_RETURN",
            "simple return is not a finite number greater than -1",
        )
    return simple


def _finite_active_return(value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_ACTIVE_RETURN", "active return is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise MarketDataError("DATA_INVALID_ACTIVE_RETURN", "active return is not finite")
    return number


def _positive_price(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not finite")
    if number <= 0:
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} must be greater than 0")
    return number
