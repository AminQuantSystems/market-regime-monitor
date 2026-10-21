"""Short/medium-horizon time-series market-state momentum.

Momentum asks whether the 21-observation and 63-observation adjusted-close
returns are positive or negative, and whether the recent log pace is
strengthening or weakening relative to the medium-term log pace. It is not a
trading signal, a 12-minus-1 factor, or a volatility-scaled allocation.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import pandas as pd

from market_state.errors import MarketDataError

RETURN_21_LOOKBACK = 21
RETURN_63_LOOKBACK = 63
MINIMUM_MOMENTUM_OBSERVATIONS = RETURN_63_LOOKBACK + 1


@dataclass(frozen=True)
class MomentumResult:
    """Full-precision Momentum measurement for one market observation."""

    market_id: str
    as_of_date: str
    adjusted_close: float
    return_21: float
    return_63: float
    pace_21: float
    pace_63: float
    momentum_state: str
    reason_code: str


def classify_momentum(
    return_21: float,
    return_63: float,
    pace_21: float,
    pace_63: float,
) -> tuple[str, str]:
    """Classify one observation from four pre-calculated numbers.

    This is a predicate. It applies the five-state table to ``return_21``,
    ``return_63``, ``pace_21``, and ``pace_63``. Those inputs are expected to
    be internally consistent: each return and its pace come from the same
    positive price ratio. The predicate does not recompute a price ratio and
    does not reject a finite tuple that could not have come from one ratio.

    ``calculate_momentum`` is the normal public calculation path. It builds
    both pairs from the same positive adjusted closes, so the values it
    classifies are consistent.

    A zero return, or opposite signs, is Mixed. Pace is consulted only when
    both returns are strictly positive or both are strictly negative.
    Comparisons are exact. There is no tolerance and no rounding.
    """
    return_21 = _finite_number(return_21, "return_21")
    return_63 = _finite_number(return_63, "return_63")
    pace_21 = _finite_number(pace_21, "pace_21")
    pace_63 = _finite_number(pace_63, "pace_63")
    if return_21 > 0 and return_63 > 0:
        if pace_21 > pace_63:
            return "Accelerating", "MOMENTUM_ACCELERATING"
        return "Positive", "MOMENTUM_POSITIVE"
    if return_21 < 0 and return_63 < 0:
        if pace_21 < pace_63:
            return "Deteriorating", "MOMENTUM_DETERIORATING"
        return "Negative", "MOMENTUM_NEGATIVE"
    return "Mixed", "MOMENTUM_MIXED"


def calculate_momentum(prices: pd.DataFrame, market_id: str, as_of_date: str) -> MomentumResult:
    """Calculate Momentum for ``market_id`` at ``as_of_date``.

    The caller supplies one market's adjusted-close history, or a wider frame
    from which this market is selected. Raw panel rules such as the 274-observation
    minimum, the shared date index, and staleness stay with market-data validation.

    This function uses only rows for ``market_id`` on or before ``as_of_date``.
    ``as_of_date`` must occur exactly. Duplicate dates in that slice fail.
    Fewer than 64 observations through that date fail. The three closes that
    enter R21, R63, P21, and P63 must be finite and greater than zero. Each
    price ratio must itself be finite and positive. A ratio that underflows
    to zero or overflows to a non-finite value is ``DATA_INVALID_PRICE``.
    The calculation does not clip, floor, or substitute an epsilon.
    """
    history = _history_through(prices, market_id, as_of_date)
    closes = list(history["adjusted_close"])
    price_t = _positive_price(closes[-1], "adjusted_close")
    price_21 = _positive_price(closes[-1 - RETURN_21_LOOKBACK], "adjusted_close")
    price_63 = _positive_price(closes[-1 - RETURN_63_LOOKBACK], "adjusted_close")
    ratio_21 = _positive_ratio(price_t, price_21)
    ratio_63 = _positive_ratio(price_t, price_63)
    return_21 = ratio_21 - 1
    return_63 = ratio_63 - 1
    try:
        pace_21 = math.log(ratio_21) / RETURN_21_LOOKBACK
        pace_63 = math.log(ratio_63) / RETURN_63_LOOKBACK
    except (ArithmeticError, ValueError) as error:
        raise MarketDataError("DATA_INVALID_PRICE", "price ratio is not a finite positive number") from error
    state, reason = classify_momentum(return_21, return_63, pace_21, pace_63)
    return MomentumResult(
        market_id=market_id,
        as_of_date=as_of_date,
        adjusted_close=price_t,
        return_21=return_21,
        return_63=return_63,
        pace_21=pace_21,
        pace_63=pace_63,
        momentum_state=state,
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
    if len(history) < MINIMUM_MOMENTUM_OBSERVATIONS:
        raise MarketDataError(
            "DATA_INSUFFICIENT_HISTORY",
            f"{market_id} has {len(history)} observations through {as_of_date}; "
            f"Momentum requires at least {MINIMUM_MOMENTUM_OBSERVATIONS}",
        )
    return history


def _finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not finite")
    return number


def _positive_ratio(price_t: float, lagged_price: float) -> float:
    try:
        ratio = price_t / lagged_price
    except (ArithmeticError, ValueError) as error:
        raise MarketDataError("DATA_INVALID_PRICE", "price ratio is not a finite positive number") from error
    if not math.isfinite(ratio) or ratio <= 0:
        raise MarketDataError("DATA_INVALID_PRICE", "price ratio is not a finite positive number")
    return ratio


def _positive_price(value: object, name: str) -> float:
    number = _finite_number(value, name)
    if number <= 0:
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} must be greater than 0")
    return number
