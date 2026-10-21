"""Deterministic Trend instrument.

Trend answers where the current adjusted close sits relative to its
50-observation and 200-observation simple moving averages. It is not a
trading signal and does not use momentum, volatility, or relative strength.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import pandas as pd

from market_state.errors import MarketDataError

SMA_50_WINDOW = 50
SMA_200_WINDOW = 200
MINIMUM_TREND_OBSERVATIONS = SMA_200_WINDOW

_STATES = {
    2: ("Strong Up", "TREND_STRONG_UP_ALIGNMENT"),
    1: ("Up", "TREND_UP_ABOVE_200"),
    0: ("Neutral", "TREND_NEUTRAL_AT_200"),
    -1: ("Down", "TREND_DOWN_BELOW_200"),
    -2: ("Strong Down", "TREND_STRONG_DOWN_ALIGNMENT"),
}


@dataclass(frozen=True)
class TrendResult:
    """Full-precision Trend measurement for one market observation."""

    market_id: str
    as_of_date: str
    adjusted_close: float
    sma_50: float
    sma_200: float
    trend_score: int
    trend_state: str
    reason_code: str


def classify_trend(price: float, sma_50: float, sma_200: float) -> tuple[int, str, str]:
    """Classify one observation from an exact price and the two simple averages.

    Comparisons are strict, except Neutral, which is ``price == sma_200``.
    There is no tolerance and no rounding.
    """
    price = _finite_price(price, "price")
    sma_50 = _finite_price(sma_50, "sma_50")
    sma_200 = _finite_price(sma_200, "sma_200")
    if price > sma_200:
        score = 2 if price > sma_50 > sma_200 else 1
    elif price == sma_200:
        score = 0
    elif price < sma_50 < sma_200:
        score = -2
    else:
        score = -1
    state, reason = _STATES[score]
    return score, state, reason


def calculate_trend(prices: pd.DataFrame, market_id: str, as_of_date: str) -> TrendResult:
    """Calculate Trend for ``market_id`` at ``as_of_date``.

    Uses only that market's adjusted closes on or before ``as_of_date``.
    Later rows are ignored. ``as_of_date`` must be one of that market's
    observation dates; a missing date is not replaced with a neighbour.
    """
    history = _history_through(prices, market_id, as_of_date)
    closes = [_finite_price(value, "adjusted_close") for value in history["adjusted_close"]]
    sma_50 = _mean(closes[-SMA_50_WINDOW:])
    sma_200 = _mean(closes[-SMA_200_WINDOW:])
    price = closes[-1]
    score, state, reason = classify_trend(price, sma_50, sma_200)
    return TrendResult(
        market_id=market_id,
        as_of_date=as_of_date,
        adjusted_close=price,
        sma_50=sma_50,
        sma_200=sma_200,
        trend_score=score,
        trend_state=state,
        reason_code=reason,
    )


def _history_through(prices: pd.DataFrame, market_id: str, as_of_date: str) -> pd.DataFrame:
    if not isinstance(prices, pd.DataFrame):
        raise MarketDataError("DATA_INVALID_COLUMNS", "expected a pandas DataFrame")
    missing = [column for column in ("date", "market_id", "adjusted_close") if column not in prices.columns]
    if missing:
        raise MarketDataError("DATA_INVALID_COLUMNS", f"missing columns {missing}")

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
    if len(history) < MINIMUM_TREND_OBSERVATIONS:
        raise MarketDataError(
            "DATA_INSUFFICIENT_HISTORY",
            f"{market_id} has {len(history)} observations through {as_of_date}; "
            f"Trend requires at least {MINIMUM_TREND_OBSERVATIONS}",
        )
    return history


def _mean(values: list[float]) -> float:
    return math.fsum(values) / len(values)


def _finite_price(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not finite")
    return number
