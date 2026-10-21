"""Categorical What Changed tests.

Label expectations in the pure comparator are set on the fixture. Price-panel
expectations follow from a flat history or from one final jump, not from a
prior call used to invent the expected labels.
"""

import dataclasses
import inspect

import pandas as pd
import pytest

from market_state import (
    MarketDataError,
    MarketRegimeError,
    MarketRegimeSnapshot,
    MomentumResult,
    RelativePerformanceResult,
    TrendResult,
    VolatilityResult,
    calculate_market_regime_change,
    compare_market_regime_snapshots,
)
from market_state import change as change_module

BENCHMARK = "ACWI"
AS_OF = "2026-03-01"
ORDER = ("direction", "momentum", "volatility", "relative_performance")


def dates_ending(count: int, end: str = AS_OF) -> list[str]:
    return list(pd.date_range(end=end, periods=count, freq="D").strftime("%Y-%m-%d"))


def series(market: str, closes: list[float], when: list[str]) -> pd.DataFrame:
    return pd.DataFrame({"date": when, "market_id": market, "adjusted_close": closes})


def panel(
    count: int,
    when: list[str] | None = None,
    asset_base: float = 100.0,
    asset_last: float = 100.0,
    benchmark_base: float = 100.0,
    benchmark_last: float = 100.0,
) -> pd.DataFrame:
    labels = dates_ending(count) if when is None else when
    asset = [asset_base] * (count - 1) + [asset_last]
    benchmark = [benchmark_base] * (count - 1) + [benchmark_last]
    return pd.concat(
        [series("SPY", asset, labels), series(BENCHMARK, benchmark, labels)],
        ignore_index=True,
    )


def jump_panel(count: int, when: list[str] | None = None) -> pd.DataFrame:
    """Flat 128 closes, then SPY 144 and ACWI 160 on the final date."""
    return panel(count, when, 128.0, 144.0, 128.0, 160.0)


def snapshot(
    as_of: str,
    direction: str = "Up",
    momentum: str = "Positive",
    volatility: str = "Normal",
    relative: str = "Neutral",
    market: str = "SPY",
    benchmark: str = BENCHMARK,
    realised: float = 0.10,
    active: float = 0.0,
) -> MarketRegimeSnapshot:
    trend = TrendResult(market, as_of, 100.0, 90.0, 80.0, 1, direction, "TREND_UP_ABOVE_200")
    pace = MomentumResult(market, as_of, 100.0, 0.01, 0.02, 0.001, 0.0005, momentum, "MOMENTUM_POSITIVE")
    movement = VolatilityResult(market, as_of, 100.0, realised, 100, 0, 252, 40.0, volatility, "VOLATILITY_NORMAL")
    relative_result = RelativePerformanceResult(
        market, benchmark, as_of, 100.0, 100.0, 0.04, 0.01, active, relative, "RELATIVE_PERFORMANCE_NEUTRAL"
    )
    return MarketRegimeSnapshot(market, as_of, trend, pace, movement, relative_result)


def changed_labels(previous: MarketRegimeSnapshot, **states: str) -> MarketRegimeSnapshot:
    current = previous
    if "direction" in states:
        current = dataclasses.replace(current, trend=dataclasses.replace(current.trend, trend_state=states["direction"]))
    if "momentum" in states:
        current = dataclasses.replace(
            current, momentum=dataclasses.replace(current.momentum, momentum_state=states["momentum"])
        )
    if "volatility" in states:
        current = dataclasses.replace(
            current, volatility=dataclasses.replace(current.volatility, volatility_regime=states["volatility"])
        )
    if "relative" in states:
        current = dataclasses.replace(
            current,
            relative_performance=dataclasses.replace(
                current.relative_performance, relative_performance_state=states["relative"]
            ),
        )
    return dataclasses.replace(current, as_of_date="2026-03-02", trend=dataclasses.replace(current.trend, as_of_date="2026-03-02"), momentum=dataclasses.replace(current.momentum, as_of_date="2026-03-02"), volatility=dataclasses.replace(current.volatility, as_of_date="2026-03-02"), relative_performance=dataclasses.replace(current.relative_performance, as_of_date="2026-03-02"))


def test_within_band_numbers_are_not_a_state_change():
    previous = snapshot("2026-03-01", volatility="Normal", relative="Outperform", realised=0.181, active=0.031)
    current = snapshot("2026-03-02", volatility="Normal", relative="Outperform", realised=0.187, active=0.041)
    assert previous.volatility.realized_volatility_21 != current.volatility.realized_volatility_21
    assert previous.relative_performance.active_return_63 != current.relative_performance.active_return_63
    result = compare_market_regime_snapshots(previous, current)
    assert result.change_status == "UNCHANGED"
    assert result.reason_code == "CHANGE_NO_STATE_CHANGE"
    assert result.transitions == ()


@pytest.mark.parametrize(
    ("field", "previous_label", "current_label", "dimension"),
    [
        ("direction", "Up", "Strong Up", "direction"),
        ("momentum", "Positive", "Accelerating", "momentum"),
        ("volatility", "Normal", "Elevated", "volatility"),
        ("relative", "Neutral", "Outperform", "relative_performance"),
    ],
)
def test_one_dimension_changes(field, previous_label, current_label, dimension):
    previous = snapshot("2026-03-01", **{field: previous_label})
    current = changed_labels(previous, **{field: current_label})
    result = compare_market_regime_snapshots(previous, current)
    assert result.change_status == "CHANGED"
    assert result.reason_code == "CHANGE_STATE_CHANGED"
    assert len(result.transitions) == 1
    assert result.transitions[0] == type(result.transitions[0])(dimension, previous_label, current_label)


def test_direction_and_momentum_keep_both_transitions_in_order():
    previous = snapshot("2026-03-01")
    current = changed_labels(previous, direction="Strong Up", momentum="Accelerating")
    result = compare_market_regime_snapshots(previous, current)
    assert tuple(item.dimension for item in result.transitions) == ("direction", "momentum")
    assert result.transitions[0].previous_state == "Up"
    assert result.transitions[0].current_state == "Strong Up"
    assert result.transitions[1].previous_state == "Positive"
    assert result.transitions[1].current_state == "Accelerating"


def test_all_four_dimensions_keep_deterministic_order():
    previous = snapshot("2026-03-01", direction="Up", momentum="Positive", volatility="Normal", relative="Neutral")
    current = changed_labels(
        previous,
        direction="Strong Up",
        momentum="Accelerating",
        volatility="Elevated",
        relative="Outperform",
    )
    result = compare_market_regime_snapshots(previous, current)
    assert tuple(item.dimension for item in result.transitions) == ORDER
    assert [(item.previous_state, item.current_state) for item in result.transitions] == [
        ("Up", "Strong Up"),
        ("Positive", "Accelerating"),
        ("Normal", "Elevated"),
        ("Neutral", "Outperform"),
    ]


@pytest.mark.parametrize(
    "mutate",
    [
        (lambda previous, current: (dataclasses.replace(previous, market_id="QQQ"), current)),
        (lambda previous, current: (dataclasses.replace(previous, as_of_date=current.as_of_date), current)),
        (lambda previous, current: (dataclasses.replace(previous, as_of_date="2026-04-01"), dataclasses.replace(current, as_of_date="2026-03-02"))),
        (
            lambda previous, current: (
                dataclasses.replace(
                    previous,
                    relative_performance=dataclasses.replace(previous.relative_performance, benchmark_id="SPX"),
                ),
                current,
            )
        ),
    ],
)
def test_snapshot_pair_mismatch_fails_closed(mutate):
    previous = snapshot("2026-03-01")
    current = snapshot("2026-03-02")
    left, right = mutate(previous, current)
    with pytest.raises(MarketRegimeError) as raised:
        compare_market_regime_snapshots(left, right)
    assert raised.value.code == "CHANGE_SNAPSHOT_MISMATCH"
    assert not isinstance(raised.value, MarketDataError)


def test_change_objects_are_frozen():
    result = compare_market_regime_snapshots(snapshot("2026-03-01"), changed_labels(snapshot("2026-03-01"), momentum="Accelerating"))
    with pytest.raises(AttributeError):
        result.change_status = "UNCHANGED"
    with pytest.raises(AttributeError):
        result.transitions[0].current_state = "Mixed"
    with pytest.raises(TypeError):
        result.transitions[0] = result.transitions[0]
    assert result.__dataclass_fields__["transitions"].type in {
        "tuple[ComponentStateTransition, ...]",
        tuple[change_module.ComponentStateTransition, ...],
    }


def test_274_observations_are_unavailable_and_do_not_calculate_previous(monkeypatch):
    calls = []
    real = change_module.calculate_market_regime_snapshot

    def wrapped(*args, **kwargs):
        calls.append(args[3])
        return real(*args, **kwargs)

    monkeypatch.setattr(change_module, "calculate_market_regime_snapshot", wrapped)
    result = calculate_market_regime_change(panel(274), "SPY", BENCHMARK, AS_OF)
    assert calls == [AS_OF]
    assert result.change_status == "UNAVAILABLE"
    assert result.reason_code == "CHANGE_PREVIOUS_STATE_INSUFFICIENT_HISTORY"
    assert result.previous_as_of_date is None
    assert result.previous_snapshot is None
    assert result.transitions == ()
    assert result.current_snapshot.market_id == "SPY"
    assert result.current_snapshot.as_of_date == AS_OF
    assert result.reason_code != "CHANGE_NO_STATE_CHANGE"


def test_275_flat_sessions_are_unchanged():
    prices = panel(275)
    result = calculate_market_regime_change(prices, "SPY", BENCHMARK, AS_OF)
    assert result.change_status == "UNCHANGED"
    assert result.reason_code == "CHANGE_NO_STATE_CHANGE"
    assert result.transitions == ()
    assert result.previous_as_of_date == dates_ending(275)[-2]
    assert result.previous_snapshot is not None
    assert result.current_snapshot.trend.trend_state == "Neutral"
    assert result.current_snapshot.momentum.momentum_state == "Mixed"
    assert result.current_snapshot.volatility.volatility_regime == "Normal"
    assert result.current_snapshot.relative_performance.relative_performance_state == "Neutral"
    assert result.previous_snapshot.trend.trend_state == result.current_snapshot.trend.trend_state
    assert result.previous_snapshot.momentum.momentum_state == result.current_snapshot.momentum.momentum_state
    assert result.previous_snapshot.volatility.volatility_regime == result.current_snapshot.volatility.volatility_regime
    assert (
        result.previous_snapshot.relative_performance.relative_performance_state
        == result.current_snapshot.relative_performance.relative_performance_state
    )


def test_final_jump_changes_all_four_labels_in_order():
    result = calculate_market_regime_change(jump_panel(275), "SPY", BENCHMARK, AS_OF)
    assert result.change_status == "CHANGED"
    assert result.reason_code == "CHANGE_STATE_CHANGED"
    assert tuple(item.dimension for item in result.transitions) == ORDER
    assert [(item.previous_state, item.current_state) for item in result.transitions] == [
        ("Neutral", "Strong Up"),
        ("Mixed", "Accelerating"),
        ("Normal", "High"),
        ("Neutral", "Strong Underperform"),
    ]


def test_monday_uses_friday_and_a_gap_uses_the_stored_previous_observation():
    friday = "2026-03-06"
    monday = "2026-03-09"
    labels = dates_ending(273, "2026-03-05") + [friday, monday]
    result = calculate_market_regime_change(panel(275, labels), "SPY", BENCHMARK, monday)
    assert result.previous_as_of_date == friday
    assert result.previous_as_of_date != "2026-03-08"
    assert result.change_status == "UNCHANGED"

    gap_current = "2026-03-25"
    gap_previous = "2026-03-10"
    gap_labels = dates_ending(273, "2026-03-01") + [gap_previous, gap_current]
    gap = calculate_market_regime_change(panel(275, gap_labels), "SPY", BENCHMARK, gap_current)
    assert gap.previous_as_of_date == gap_previous
    assert gap.previous_as_of_date != "2026-03-24"


def test_future_rows_and_other_markets_do_not_change_the_result():
    prices = jump_panel(275)
    original = calculate_market_regime_change(prices, "SPY", BENCHMARK, AS_OF)
    future = dates_ending(20, "2026-03-21")
    extra = pd.concat(
        [
            prices,
            series("SPY", [1_000_000.0] * 20, future),
            series(BENCHMARK, [0.01] * 20, future),
            series("EEM", [1.0] * 20, future),
        ],
        ignore_index=True,
    )
    assert calculate_market_regime_change(extra, "SPY", BENCHMARK, AS_OF) == original

    labels = dates_ending(275)
    extreme = [1.0 if index % 2 == 0 else 1_000_000.0 for index in range(275)]
    contaminated = pd.concat([prices, series("QQQ", extreme, labels), series("IWM", extreme, labels)], ignore_index=True)
    assert calculate_market_regime_change(contaminated, "SPY", BENCHMARK, AS_OF) == original


def test_caller_frame_is_not_mutated():
    cases = [
        jump_panel(275),
        panel(275),
        panel(274),
    ]
    for prices in cases:
        before = prices.copy(deep=True)
        calculate_market_regime_change(prices, "SPY", BENCHMARK, AS_OF)
        pd.testing.assert_frame_equal(prices, before)

    failure = panel(275)
    before = failure.copy(deep=True)
    with pytest.raises(MarketDataError):
        calculate_market_regime_change(failure, "SPY", BENCHMARK, "1999-01-01")
    pd.testing.assert_frame_equal(failure, before)


def test_same_inputs_and_reordered_rows_match_and_use_no_clock():
    prices = jump_panel(275)
    assert calculate_market_regime_change(prices, "SPY", BENCHMARK, AS_OF) == calculate_market_regime_change(
        prices.copy(), "SPY", BENCHMARK, AS_OF
    )
    reversed_rows = prices.iloc[::-1].reset_index(drop=True)
    shuffled = prices.sample(frac=1, random_state=7).reset_index(drop=True)
    assert calculate_market_regime_change(reversed_rows, "SPY", BENCHMARK, AS_OF) == calculate_market_regime_change(
        prices, "SPY", BENCHMARK, AS_OF
    )
    assert calculate_market_regime_change(shuffled, "SPY", BENCHMARK, AS_OF) == calculate_market_regime_change(
        prices, "SPY", BENCHMARK, AS_OF
    )
    source = inspect.getsource(change_module)
    assert "datetime" not in source
    assert "locale" not in source
    assert "timezone" not in source
    assert "colour" not in source
    assert "color" not in source
    assert "N/A" not in source


def test_273_and_unrelated_errors_propagate():
    with pytest.raises(MarketDataError) as short:
        calculate_market_regime_change(panel(273), "SPY", BENCHMARK, AS_OF)
    assert short.value.code == "DATA_INSUFFICIENT_HISTORY"

    with pytest.raises(MarketDataError) as missing:
        calculate_market_regime_change(panel(275).loc[lambda frame: frame["market_id"] != "SPY"], "SPY", BENCHMARK, AS_OF)
    assert missing.value.code == "DATA_MISSING_MARKET"

    with pytest.raises(MarketDataError) as missing_benchmark:
        calculate_market_regime_change(panel(275).loc[lambda frame: frame["market_id"] != BENCHMARK], "SPY", BENCHMARK, AS_OF)
    assert missing_benchmark.value.code == "DATA_MISSING_MARKET"

    with pytest.raises(MarketDataError) as wrong_benchmark:
        calculate_market_regime_change(panel(275), "SPY", "SPX", AS_OF)
    assert wrong_benchmark.value.code == "CONFIG_WRONG_BENCHMARK"

    with pytest.raises(MarketDataError) as bad_date:
        calculate_market_regime_change(panel(275), "SPY", BENCHMARK, "1999-01-01")
    assert bad_date.value.code == "DATA_INVALID_DATE"

    mismatch = panel(275).copy()
    acwi_rows = mismatch.index[mismatch["market_id"] == BENCHMARK]
    mismatch.loc[acwi_rows[-30], "date"] = "1999-06-01"
    with pytest.raises(MarketDataError) as dates:
        calculate_market_regime_change(mismatch, "SPY", BENCHMARK, AS_OF)
    assert dates.value.code == "DATA_DATE_INDEX_MISMATCH"


def test_unexpected_previous_history_error_is_not_unavailable(monkeypatch):
    real = change_module.calculate_market_regime_snapshot

    def wrapped(prices, market_id, benchmark_id, as_of_date):
        if as_of_date != AS_OF:
            raise MarketDataError("DATA_INSUFFICIENT_HISTORY", "previous history failed unexpectedly")
        return real(prices, market_id, benchmark_id, as_of_date)

    monkeypatch.setattr(change_module, "calculate_market_regime_snapshot", wrapped)
    with pytest.raises(MarketDataError) as raised:
        calculate_market_regime_change(panel(275), "SPY", BENCHMARK, AS_OF)
    assert raised.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_component_integrity_error_propagates(monkeypatch):
    def broken(*_args, **_kwargs):
        raise MarketRegimeError("REGIME_COMPONENT_MISMATCH", "component identity disagreed")

    monkeypatch.setattr(change_module, "calculate_market_regime_snapshot", broken)
    with pytest.raises(MarketRegimeError) as raised:
        calculate_market_regime_change(panel(275), "SPY", BENCHMARK, AS_OF)
    assert raised.value.code == "REGIME_COMPONENT_MISMATCH"
