"""Compare categorical market state between two observations.

What Changed reports which of the four labels moved since the immediately
previous observation. It does not calculate a moving average, a return, a
realised volatility, a percentile, or an active return. It does not judge a
move as better or worse, and it carries no presentation formatting.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from market_state.errors import MarketRegimeError
from market_state.regime import MarketRegimeSnapshot, calculate_market_regime_snapshot
from market_state.volatility import MINIMUM_REGIME_OBSERVATIONS

_READINGS = (
    ("direction", lambda snapshot: snapshot.trend.trend_state),
    ("momentum", lambda snapshot: snapshot.momentum.momentum_state),
    ("volatility", lambda snapshot: snapshot.volatility.volatility_regime),
    ("relative_performance", lambda snapshot: snapshot.relative_performance.relative_performance_state),
)


@dataclass(frozen=True)
class ComponentStateTransition:
    """One categorical label change, from the previous state to the current state."""

    dimension: str
    previous_state: str
    current_state: str


@dataclass(frozen=True)
class MarketRegimeChange:
    """Categorical comparison of one market at two observations.

    ``transitions`` is empty when the status is ``UNCHANGED`` or ``UNAVAILABLE``.
    ``previous_snapshot`` is present only when a complete previous snapshot was calculated.
    """

    market_id: str
    current_as_of_date: str
    previous_as_of_date: str | None
    change_status: str
    current_snapshot: MarketRegimeSnapshot
    previous_snapshot: MarketRegimeSnapshot | None
    transitions: tuple[ComponentStateTransition, ...]
    reason_code: str


def compare_market_regime_snapshots(
    previous_snapshot: MarketRegimeSnapshot,
    current_snapshot: MarketRegimeSnapshot,
) -> MarketRegimeChange:
    """Compare two complete snapshots. This does not calculate finance.

    The snapshots must name the same market and the same relative-performance
    benchmark, and the previous observation date must be strictly earlier.
    ``UNAVAILABLE`` is not produced here.
    """
    if previous_snapshot.market_id != current_snapshot.market_id:
        raise MarketRegimeError(
            "CHANGE_SNAPSHOT_MISMATCH",
            "snapshots name different markets: "
            f"{previous_snapshot.market_id} and {current_snapshot.market_id}",
        )
    if previous_snapshot.as_of_date >= current_snapshot.as_of_date:
        raise MarketRegimeError(
            "CHANGE_SNAPSHOT_MISMATCH",
            "previous as_of_date is not before current as_of_date: "
            f"{previous_snapshot.as_of_date} then {current_snapshot.as_of_date}",
        )
    previous_benchmark = previous_snapshot.relative_performance.benchmark_id
    current_benchmark = current_snapshot.relative_performance.benchmark_id
    if previous_benchmark != current_benchmark:
        raise MarketRegimeError(
            "CHANGE_SNAPSHOT_MISMATCH",
            f"snapshots use different benchmarks: {previous_benchmark} and {current_benchmark}",
        )

    transitions = tuple(
        ComponentStateTransition(dimension, reading(previous_snapshot), reading(current_snapshot))
        for dimension, reading in _READINGS
        if reading(previous_snapshot) != reading(current_snapshot)
    )
    if transitions:
        status, reason = "CHANGED", "CHANGE_STATE_CHANGED"
    else:
        status, reason = "UNCHANGED", "CHANGE_NO_STATE_CHANGE"
    return MarketRegimeChange(
        market_id=current_snapshot.market_id,
        current_as_of_date=current_snapshot.as_of_date,
        previous_as_of_date=previous_snapshot.as_of_date,
        change_status=status,
        current_snapshot=current_snapshot,
        previous_snapshot=previous_snapshot,
        transitions=transitions,
        reason_code=reason,
    )


def calculate_market_regime_change(
    prices: pd.DataFrame,
    market_id: str,
    benchmark_id: str,
    as_of_date: str,
) -> MarketRegimeChange:
    """Compare the current snapshot with the immediately previous observation.

    The current as-of date must occur exactly. The previous date is the prior
    row in this market's ordered observations, not a calendar day earlier.
    A valid current snapshot with exactly the complete-snapshot history length
    returns ``UNAVAILABLE``. A longer history calculates the previous snapshot.
    An error from either snapshot propagates. A previous-snapshot history error
    is not rewritten as ``UNAVAILABLE``.
    """
    current = calculate_market_regime_snapshot(prices, market_id, benchmark_id, as_of_date)
    dates = _ordered_dates(prices, market_id, as_of_date)
    if not dates or dates[-1] != as_of_date or len(dates) < MINIMUM_REGIME_OBSERVATIONS:
        raise MarketRegimeError(
            "CHANGE_SNAPSHOT_MISMATCH",
            f"{market_id} history through {as_of_date} does not match the current snapshot",
        )
    if len(dates) == MINIMUM_REGIME_OBSERVATIONS:
        return MarketRegimeChange(
            market_id=market_id,
            current_as_of_date=as_of_date,
            previous_as_of_date=None,
            change_status="UNAVAILABLE",
            current_snapshot=current,
            previous_snapshot=None,
            transitions=(),
            reason_code="CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY",
        )
    previous = calculate_market_regime_snapshot(prices, market_id, benchmark_id, dates[-2])
    return compare_market_regime_snapshots(previous, current)


def _ordered_dates(prices: pd.DataFrame, market_id: str, as_of_date: str) -> list[str]:
    dates = prices.loc[prices["market_id"] == market_id, "date"]
    through = dates.loc[dates <= as_of_date].sort_values(kind="mergesort")
    return [str(value) for value in through.tolist()]
