"""Orchestration tests for MarketRegimeSnapshot.

Expectations below are derived from the price construction, not from a prior
call to the production functions. The snapshot is compared with independent
component calls only after those expectations are fixed.
"""

import inspect

import pandas as pd
import pytest

from market_state import (
    MarketDataError,
    calculate_market_regime_snapshot,
    calculate_momentum,
    calculate_relative_performance,
    calculate_trend,
    calculate_volatility,
)
from market_state import regime as regime_module

BENCHMARK = "ACWI"
AS_OF = "2026-03-01"
BOARD = ("SPY", "QQQ", "IWM", "EWU", "EWG", "EWJ", "EEM")
SNAPSHOT_FIELDS = {
    "market_id",
    "as_of_date",
    "trend",
    "momentum",
    "volatility",
    "relative_performance",
}
FORBIDDEN_FIELDS = {
    "regime_score",
    "confidence",
    "probability",
    "recommendation",
    "signal",
    "risk_on",
    "risk_off",
    "expected_return",
    "position_size",
}


def dates_ending(count: int, end: str = AS_OF) -> list[str]:
    return list(pd.date_range(end=end, periods=count, freq="D").strftime("%Y-%m-%d"))


def series(market: str, closes: list[float], when: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"date": when, "market_id": market, "adjusted_close": closes})


def flat_jump(count: int, base: float, last: float, when: list[str], market: str) -> pd.DataFrame:
    closes = [base] * (count - 1) + [last]
    return series(market, closes, when)


def golden_panel(count: int = 274) -> pd.DataFrame:
    """273 closes at 128, then SPY 144 and ACWI 160.

    SMA50 = (49 * 128 + 144) / 50 = 128.32.
    SMA200 = (199 * 128 + 144) / 200 = 128.08.
    144 > 128.32 > 128.08, so Trend is Strong Up.
    Both 21- and 63-observation ratios are 144/128 = 1.125, so both returns
    are +0.125 and the shorter pace is larger: Momentum is Accelerating.
    Every historical RV21 window ends before the final close and is flat, so
    those RV21 values are 0. The current window contains the jump, so it is
    positive. L = 252, E = 0, percentile = 100, Volatility is High.
    Asset return 0.125 minus ACWI return 0.25 is -0.125: Strong Underperform.
    """
    labels = dates_ending(count)
    return pd.concat(
        [
            flat_jump(count, 128.0, 144.0, labels, "SPY"),
            flat_jump(count, 128.0, 160.0, labels, BENCHMARK),
        ],
        ignore_index=True,
    )


def disagreement_panel() -> pd.DataFrame:
    """Strong Up trend with deteriorating recent pace.

    Index 210 (t-63) is 400, index 252 (t-21) is 300, and the final close is
    200. The other 271 SPY closes, and every ACWI close, are 100.
    SMA50 = (48 * 100 + 300 + 200) / 50 = 106.
    SMA200 = (197 * 100 + 400 + 300 + 200) / 200 = 103.
    200 > 106 > 103, so Trend is Strong Up.
    R21 = 200/300 - 1 < 0 and R63 = 200/400 - 1 = -0.5.
    (2/3)^3 = 8/27 < 1/2, so the 21-observation pace is more negative:
    Momentum is Deteriorating.
    Active return = -0.5 - 0 = -0.5: Strong Underperform.
    """
    count = 274
    labels = dates_ending(count)
    asset = [100.0] * count
    asset[210] = 400.0
    asset[252] = 300.0
    asset[273] = 200.0
    return pd.concat(
        [series("SPY", asset, labels), series(BENCHMARK, [100.0] * count, labels)],
        ignore_index=True,
    )


def board_panel() -> pd.DataFrame:
    labels = dates_ending(274)
    last = {"SPY": 144.0, "QQQ": 152.0, "IWM": 140.0, "EWU": 136.0, "EWG": 132.0, "EWJ": 130.0, "EEM": 129.0}
    frames = [flat_jump(274, 128.0, last[market], labels, market) for market in BOARD]
    frames.append(flat_jump(274, 128.0, 160.0, labels, BENCHMARK))
    return pd.concat(frames, ignore_index=True)


def snapshot_for(prices: pd.DataFrame, market: str = "SPY", as_of: str = AS_OF):
    return calculate_market_regime_snapshot(prices, market, BENCHMARK, as_of)


def test_golden_snapshot_matches_hand_states_and_components():
    prices = golden_panel()
    trend = calculate_trend(prices, "SPY", AS_OF)
    momentum = calculate_momentum(prices, "SPY", AS_OF)
    volatility = calculate_volatility(prices, "SPY", AS_OF)
    relative = calculate_relative_performance(prices, "SPY", BENCHMARK, AS_OF)
    snapshot = snapshot_for(prices)

    assert snapshot.trend == trend
    assert snapshot.momentum == momentum
    assert snapshot.volatility == volatility
    assert snapshot.relative_performance == relative
    assert snapshot.market_id == trend.market_id == momentum.market_id == volatility.market_id == relative.market_id == "SPY"
    assert snapshot.as_of_date == trend.as_of_date == momentum.as_of_date == volatility.as_of_date == relative.as_of_date == AS_OF
    assert relative.benchmark_id == BENCHMARK
    assert snapshot.trend.trend_state == "Strong Up"
    assert snapshot.trend.reason_code == "TREND_STRONG_UP_ALIGNMENT"
    assert snapshot.momentum.momentum_state == "Accelerating"
    assert snapshot.momentum.reason_code == "MOMENTUM_ACCELERATING"
    assert snapshot.volatility.volatility_regime == "High"
    assert snapshot.volatility.reason_code == "VOLATILITY_HIGH"
    assert snapshot.volatility.historical_below_count == 252
    assert snapshot.volatility.historical_equal_count == 0
    assert snapshot.volatility.historical_percentile == 100
    assert snapshot.relative_performance.relative_performance_state == "Strong Underperform"
    assert snapshot.relative_performance.reason_code == "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"
    assert snapshot.relative_performance.active_return_63 == -0.125


def test_each_component_calculation_is_called_once(monkeypatch):
    calls = []
    originals = {
        "calculate_trend": regime_module.calculate_trend,
        "calculate_momentum": regime_module.calculate_momentum,
        "calculate_volatility": regime_module.calculate_volatility,
        "calculate_relative_performance": regime_module.calculate_relative_performance,
    }

    def wrapping(name, real):
        def wrapped(*args, **kwargs):
            calls.append(name)
            return real(*args, **kwargs)

        return wrapped

    for name, real in originals.items():
        monkeypatch.setattr(regime_module, name, wrapping(name, real))

    snapshot_for(golden_panel())
    assert calls == [
        "calculate_trend",
        "calculate_momentum",
        "calculate_volatility",
        "calculate_relative_performance",
    ]


def test_snapshot_preserves_strong_up_with_deteriorating_momentum():
    prices = disagreement_panel()
    snapshot = snapshot_for(prices)
    assert snapshot.trend.adjusted_close == 200
    assert snapshot.trend.sma_50 == 106
    assert snapshot.trend.sma_200 == 103
    assert snapshot.trend.trend_state == "Strong Up"
    assert snapshot.trend.reason_code == "TREND_STRONG_UP_ALIGNMENT"
    assert snapshot.momentum.momentum_state == "Deteriorating"
    assert snapshot.momentum.reason_code == "MOMENTUM_DETERIORATING"
    assert snapshot.relative_performance.active_return_63 == -0.5
    assert snapshot.relative_performance.relative_performance_state == "Strong Underperform"
    assert snapshot.trend == calculate_trend(prices, "SPY", AS_OF)
    assert snapshot.momentum == calculate_momentum(prices, "SPY", AS_OF)
    assert snapshot.volatility == calculate_volatility(prices, "SPY", AS_OF)
    assert snapshot.relative_performance == calculate_relative_performance(prices, "SPY", BENCHMARK, AS_OF)


@pytest.mark.parametrize(
    ("builder", "market", "benchmark", "as_of", "code"),
    [
        (lambda: golden_panel(273), "SPY", BENCHMARK, AS_OF, "DATA_INSUFFICIENT_HISTORY"),
        (lambda: golden_panel().loc[lambda frame: frame["market_id"] != "SPY"], "SPY", BENCHMARK, AS_OF, "DATA_MISSING_MARKET"),
        (lambda: golden_panel().loc[lambda frame: frame["market_id"] != BENCHMARK], "SPY", BENCHMARK, AS_OF, "DATA_MISSING_MARKET"),
        (lambda: golden_panel(), "SPY", BENCHMARK, "1999-01-01", "DATA_INVALID_DATE"),
        (lambda: golden_panel(), "SPY", "SPX", AS_OF, "CONFIG_WRONG_BENCHMARK"),
        (lambda: golden_panel(), BENCHMARK, BENCHMARK, AS_OF, "DATA_BENCHMARK_EXCLUDED"),
    ],
)
def test_component_errors_propagate(builder, market, benchmark, as_of, code):
    with pytest.raises(MarketDataError) as raised:
        calculate_market_regime_snapshot(builder(), market, benchmark, as_of)
    assert raised.value.code == code


def test_caller_frame_is_not_mutated_on_success_or_failure():
    success = golden_panel()
    success_before = success.copy(deep=True)
    snapshot_for(success)
    pd.testing.assert_frame_equal(success, success_before)

    failure = golden_panel(273)
    failure_before = failure.copy(deep=True)
    with pytest.raises(MarketDataError):
        snapshot_for(failure)
    pd.testing.assert_frame_equal(failure, failure_before)


def test_unrelated_market_does_not_change_the_snapshot():
    prices = golden_panel()
    labels = dates_ending(274)
    extreme = [1.0 if index % 2 == 0 else 1_000_000.0 for index in range(274)]
    contaminated = pd.concat([prices, series("EEM", extreme, labels)], ignore_index=True)
    assert snapshot_for(contaminated) == snapshot_for(prices)


def test_future_rows_do_not_change_the_historical_snapshot():
    prices = golden_panel()
    original = snapshot_for(prices)
    future = dates_ending(30, "2026-03-31")
    extra = pd.concat(
        [
            series("SPY", [1_000_000.0] * 30, future),
            series(BENCHMARK, [0.01] * 30, future),
            series("EEM", [1.0] * 30, future),
        ],
        ignore_index=True,
    )
    assert snapshot_for(pd.concat([prices, extra], ignore_index=True)) == original

    short = golden_panel(200)
    later = dates_ending(80, "2026-05-20")
    padded = pd.concat(
        [
            short,
            series("SPY", [144.0] * 80, later),
            series(BENCHMARK, [160.0] * 80, later),
        ],
        ignore_index=True,
    )
    with pytest.raises(MarketDataError) as raised:
        snapshot_for(padded)
    assert raised.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_snapshot_is_frozen_and_exposes_only_orchestration_fields():
    snapshot = snapshot_for(golden_panel())
    assert set(snapshot.__dataclass_fields__) == SNAPSHOT_FIELDS
    assert FORBIDDEN_FIELDS.isdisjoint(snapshot.__dataclass_fields__)
    with pytest.raises(AttributeError):
        snapshot.market_id = "QQQ"
    with pytest.raises(AttributeError):
        snapshot.trend = None
    with pytest.raises(AttributeError):
        snapshot.trend.trend_state = "Neutral"


def test_same_inputs_and_reordered_rows_match_and_use_no_clock():
    prices = golden_panel()
    assert snapshot_for(prices) == snapshot_for(prices.copy())
    reversed_rows = prices.iloc[::-1].reset_index(drop=True)
    shuffled = prices.sample(frac=1, random_state=7).reset_index(drop=True)
    assert snapshot_for(reversed_rows) == snapshot_for(prices)
    assert snapshot_for(shuffled) == snapshot_for(prices)
    source = inspect.getsource(regime_module)
    assert "datetime" not in source
    assert "locale" not in source
    assert "timezone" not in source


def test_seven_board_markets_are_isolated_and_share_acwi():
    """Seven board snapshots from one panel.

    One local timing of this shape is recorded in PROJECT_STATE.md as
    diagnostic evidence. This test does not assert a duration.
    """
    prices = board_panel()
    labels = dates_ending(274)
    acwi = flat_jump(274, 128.0, 160.0, labels, BENCHMARK)
    snapshots = [snapshot_for(prices, market) for market in BOARD]
    again = [snapshot_for(prices, market) for market in BOARD]

    assert [item.market_id for item in snapshots] == list(BOARD)
    assert BENCHMARK not in [item.market_id for item in snapshots]
    assert {item.as_of_date for item in snapshots} == {AS_OF}
    assert {item.relative_performance.benchmark_id for item in snapshots} == {BENCHMARK}
    assert snapshots == again
    for market, assembled in zip(BOARD, snapshots):
        alone = pd.concat(
            [prices.loc[prices["market_id"] == market], acwi],
            ignore_index=True,
        )
        assert assembled == snapshot_for(alone, market)
        assert assembled.trend.market_id == market
        assert assembled.relative_performance.market_id == market
