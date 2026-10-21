"""Backward-looking realised-movement magnitude.

Volatility asks how large recent daily adjusted-close moves have been relative
to this market's own previous 252 realised-volatility observations. It is not a
direction, a probability, a forecast, or a position size.

The 21-return measurement follows a transparent Cboe-style realised-volatility
construction: log returns, a zero return mean, and annualisation with 252.
The midrank percentile and the 25/75/90 regimes are a Market Regime Monitor
classification. They are not part of that Cboe methodology.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from numbers import Real

import pandas as pd

from market_state.errors import MarketDataError

RETURN_COUNT = 21
RV21_PRICE_COUNT = RETURN_COUNT + 1
REFERENCE_SIZE = 252
ANNUALISATION_DAYS = 252
MINIMUM_REGIME_OBSERVATIONS = RV21_PRICE_COUNT + REFERENCE_SIZE


@dataclass(frozen=True)
class VolatilityClassification:
    """Midrank regime for one current RV21 and its 252-value reference."""

    historical_below_count: int
    historical_equal_count: int
    historical_reference_size: int
    historical_percentile: float
    volatility_regime: str
    reason_code: str


@dataclass(frozen=True)
class VolatilityResult:
    """Full-precision realised-volatility measurement for one market observation."""

    market_id: str
    as_of_date: str
    adjusted_close: float
    realized_volatility_21: float
    historical_below_count: int
    historical_equal_count: int
    historical_reference_size: int
    historical_percentile: float
    volatility_regime: str
    reason_code: str


def calculate_rv21(prices) -> float:
    """Return annualised 21-return realised volatility for exactly 22 closes.

    The closes are ordered oldest first. The function does not choose a window
    from a longer series. Each return is ``ln(price) - ln(previous price)``.
    The mean return is zero by construction: the result is the square root of
    252 times the mean of the 21 squared log returns.
    """
    closes = _exactly_22_prices(prices)
    squares = []
    try:
        for previous, current in zip(closes, closes[1:]):
            log_return = math.log(current) - math.log(previous)
            squares.append(log_return * log_return)
        realised = math.sqrt(ANNUALISATION_DAYS * math.fsum(squares) / RETURN_COUNT)
    except (ArithmeticError, ValueError) as error:
        raise MarketDataError("DATA_INVALID_PRICE", "log return is not finite") from error
    if not math.isfinite(realised):
        raise MarketDataError("DATA_INVALID_VOLATILITY", "realised volatility is not finite")
    return realised


def classify_volatility(current_rv21, historical_rv21_values) -> VolatilityClassification:
    """Classify one RV21 against exactly 252 previous RV21 values.

    ``L`` counts values strictly below the current value. ``E`` counts exact
    ties. The percentile is ``100 * (L + 0.5 * E) / 252``. Ties receive half
    weight. Comparisons are exact. The current value is not added to the
    reference list by this function.
    """
    current = _non_negative_volatility(current_rv21, "current_rv21")
    if isinstance(historical_rv21_values, (str, bytes)):
        raise MarketDataError("DATA_INVALID_VOLATILITY", "historical RV21 values are not a sequence")
    try:
        history = list(historical_rv21_values)
    except TypeError as error:
        raise MarketDataError("DATA_INVALID_VOLATILITY", "historical RV21 values are not a sequence") from error
    if len(history) != REFERENCE_SIZE:
        raise MarketDataError(
            "DATA_INVALID_VOLATILITY",
            f"expected {REFERENCE_SIZE} historical RV21 values, received {len(history)}",
        )
    values = [_non_negative_volatility(value, "historical_rv21") for value in history]
    below = sum(value < current for value in values)
    equal = sum(value == current for value in values)
    percentile = 100 * (below + 0.5 * equal) / REFERENCE_SIZE
    regime, reason = _regime(percentile)
    return VolatilityClassification(
        historical_below_count=below,
        historical_equal_count=equal,
        historical_reference_size=REFERENCE_SIZE,
        historical_percentile=percentile,
        volatility_regime=regime,
        reason_code=reason,
    )


def calculate_volatility(prices: pd.DataFrame, market_id: str, as_of_date: str) -> VolatilityResult:
    """Calculate the realised-volatility regime for one market at an exact date.

    Uses only that market's rows on or before ``as_of_date``. The current RV21
    uses the 21 returns ending at that date. The reference set is RV21 at the
    previous 252 observation dates, each using only prices available on its own
    date. The current RV21 is not a member of that set. Fewer than 274
    observations through the as-of date fail. Raw panel rules such as the
    shared date index stay with market-data validation.
    """
    history = _history_through(prices, market_id, as_of_date)
    closes = [_positive_price(value, "adjusted_close") for value in history["adjusted_close"]]
    window = closes[-MINIMUM_REGIME_OBSERVATIONS:]
    current = calculate_rv21(window[-RV21_PRICE_COUNT:])
    historical = [
        calculate_rv21(window[end - RETURN_COUNT : end + 1])
        for end in range(len(window) - 1 - REFERENCE_SIZE, len(window) - 1)
    ]
    classification = classify_volatility(current, historical)
    return VolatilityResult(
        market_id=market_id,
        as_of_date=as_of_date,
        adjusted_close=window[-1],
        realized_volatility_21=current,
        historical_below_count=classification.historical_below_count,
        historical_equal_count=classification.historical_equal_count,
        historical_reference_size=classification.historical_reference_size,
        historical_percentile=classification.historical_percentile,
        volatility_regime=classification.volatility_regime,
        reason_code=classification.reason_code,
    )


def _regime(percentile: float) -> tuple[str, str]:
    if percentile <= 25:
        return "Low", "VOLATILITY_LOW"
    if percentile <= 75:
        return "Normal", "VOLATILITY_NORMAL"
    if percentile <= 90:
        return "Elevated", "VOLATILITY_ELEVATED"
    return "High", "VOLATILITY_HIGH"


def _exactly_22_prices(prices) -> list[float]:
    if isinstance(prices, (str, bytes)) or isinstance(prices, pd.DataFrame):
        raise MarketDataError("DATA_INVALID_PRICE", "expected exactly 22 adjusted closes")
    try:
        values = list(prices)
    except TypeError as error:
        raise MarketDataError("DATA_INVALID_PRICE", "expected exactly 22 adjusted closes") from error
    if len(values) < RV21_PRICE_COUNT:
        raise MarketDataError(
            "DATA_INSUFFICIENT_HISTORY",
            f"RV21 requires {RV21_PRICE_COUNT} adjusted closes; received {len(values)}",
        )
    if len(values) > RV21_PRICE_COUNT:
        raise MarketDataError(
            "DATA_INVALID_VOLATILITY",
            f"RV21 requires exactly {RV21_PRICE_COUNT} adjusted closes; received {len(values)}",
        )
    return [_positive_price(value, "adjusted_close") for value in values]


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
    if len(history) < MINIMUM_REGIME_OBSERVATIONS:
        raise MarketDataError(
            "DATA_INSUFFICIENT_HISTORY",
            f"{market_id} has {len(history)} observations through {as_of_date}; "
            f"Volatility requires at least {MINIMUM_REGIME_OBSERVATIONS}",
        )
    return history


def _positive_price(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise MarketDataError("DATA_INVALID_PRICE", f"{name} must be finite and greater than 0")
    return number


def _non_negative_volatility(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_VOLATILITY", f"{name} is not numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise MarketDataError("DATA_INVALID_VOLATILITY", f"{name} must be finite and at least 0")
    return number
