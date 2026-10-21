import math

import pandas as pd
import pytest

from market_state import (
    MarketDataError,
    calculate_momentum,
    calculate_relative_performance,
    classify_relative_performance,
)

MARKET = "SPY"
BENCHMARK = "ACWI"
FIELDS = {
    "market_id",
    "benchmark_id",
    "as_of_date",
    "adjusted_close",
    "benchmark_adjusted_close",
    "asset_return_63",
    "benchmark_return_63",
    "active_return_63",
    "relative_performance_state",
    "reason_code",
}


def dates_ending(count: int, end: str = "2026-03-01") -> list[str]:
    return list(pd.date_range(end=end, periods=count, freq="D").strftime("%Y-%m-%d"))


def series(market: str, closes: list[float], when: list[str] | None = None) -> pd.DataFrame:
    labels = dates_ending(len(closes)) if when is None else when
    return pd.DataFrame({"date": labels, "market_id": market, "adjusted_close": closes})


def pair(asset_end: float, benchmark_end: float, count: int = 64, end: str = "2026-03-01") -> pd.DataFrame:
    """64 flat closes of 100, with the named endpoints at t-63 and t."""
    labels = dates_ending(count, end)
    asset = [100.0] * count
    benchmark = [100.0] * count
    asset[0] = 100.0
    benchmark[0] = 100.0
    asset[-1] = asset_end
    benchmark[-1] = benchmark_end
    return pd.concat(
        [series(MARKET, asset, labels), series(BENCHMARK, benchmark, labels)],
        ignore_index=True,
    )


def as_of(frame: pd.DataFrame) -> str:
    return frame.loc[frame["market_id"] == MARKET, "date"].iloc[-1]


def simple(price_t: float, lagged: float) -> float:
    return price_t / lagged - 1


def assert_case(asset_end: float, benchmark_end: float, state: str, reason: str):
    frame = pair(asset_end, benchmark_end)
    result = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    asset_return = simple(asset_end, 100.0)
    benchmark_return = simple(benchmark_end, 100.0)
    active = asset_return - benchmark_return

    assert result.market_id == MARKET
    assert result.benchmark_id == BENCHMARK
    assert result.adjusted_close == asset_end
    assert result.benchmark_adjusted_close == benchmark_end
    assert result.asset_return_63 == asset_return
    assert result.benchmark_return_63 == benchmark_return
    assert result.active_return_63 == active
    assert result.relative_performance_state == state
    assert result.reason_code == reason
    assert classify_relative_performance(active) == (state, reason)
    assert set(result.__dataclass_fields__) == FIELDS
    return result


def test_strong_outperform():
    result = assert_case(110, 104, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM")
    assert result.active_return_63 == pytest.approx(0.06)
    assert result.active_return_63 >= 0.05


def test_exact_plus_five_percent_boundary():
    result = assert_case(110, 105, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM")
    assert result.active_return_63 >= 0.05


def test_outperform():
    result = assert_case(106, 103, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM")
    assert result.active_return_63 == pytest.approx(0.03)
    assert 0.02 <= result.active_return_63 < 0.05


def test_exact_plus_two_percent_boundary():
    result = assert_case(105, 103, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM")
    assert result.active_return_63 >= 0.02
    assert result.active_return_63 < 0.05


def test_neutral_positive():
    result = assert_case(104, 103, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL")
    assert result.active_return_63 == pytest.approx(0.01)
    assert -0.02 < result.active_return_63 < 0.02


def test_exact_zero_is_neutral():
    result = assert_case(103, 103, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL")
    assert result.active_return_63 == 0.0


def test_neutral_negative():
    result = assert_case(102, 103, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL")
    assert result.active_return_63 == pytest.approx(-0.01)
    assert -0.02 < result.active_return_63 < 0.02


def test_exact_minus_two_percent_boundary():
    result = assert_case(101, 103, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM")
    assert result.active_return_63 <= -0.02
    assert result.active_return_63 > -0.05


def test_underperform():
    result = assert_case(100, 103, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM")
    assert result.active_return_63 == pytest.approx(-0.03)
    assert -0.05 < result.active_return_63 <= -0.02


def test_exact_minus_five_percent_boundary():
    result = assert_case(98, 103, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM")
    assert result.active_return_63 <= -0.05


def test_strong_underperform():
    result = assert_case(95, 103, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM")
    assert result.active_return_63 == pytest.approx(-0.08)
    assert result.active_return_63 <= -0.05


def test_both_negative_and_asset_ahead_of_benchmark():
    result = assert_case(98, 92, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM")
    assert result.asset_return_63 < 0
    assert result.benchmark_return_63 < 0
    assert result.active_return_63 == pytest.approx(0.06)
    assert result.active_return_63 >= 0.05


def test_both_positive_and_asset_behind_benchmark():
    result = assert_case(105, 110, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM")
    assert result.asset_return_63 > 0
    assert result.benchmark_return_63 > 0
    assert result.active_return_63 <= -0.05


def test_positive_momentum_can_coexist_with_strong_underperform():
    frame = pair(105, 110)
    relative = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    momentum = calculate_momentum(frame, MARKET, as_of(frame))

    assert relative.relative_performance_state == "Strong Underperform"
    assert relative.active_return_63 <= -0.05
    assert momentum.return_63 > 0
    assert momentum.momentum_state == "Accelerating"


@pytest.mark.parametrize(
    ("active", "state", "reason"),
    [
        (0.05, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM"),
        (0.02, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (0.0, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL"),
        (-0.02, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (-0.05, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
        (0.05 + 1e-12, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM"),
        (0.05 - 1e-12, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM"),
        (0.02 + 1e-12, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (0.02 - 1e-12, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (-0.02 + 1e-12, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (-0.02 - 1e-12, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (-0.05 + 1e-12, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
        (-0.05 - 1e-12, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
        (math.nextafter(0.05, 0.0), "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM"),
        (math.nextafter(0.02, 0.0), "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (math.nextafter(-0.02, 0.0), "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (math.nextafter(-0.02, -1.0), "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (math.nextafter(-0.05, 0.0), "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
        (math.nextafter(-0.05, -1.0), "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
        (0.05 - 2e-12, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (0.02 - 2e-12, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL"),
        (0.02 + 2e-12, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (-0.02 + 2e-12, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL"),
        (-0.02 - 2e-12, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (-0.05 + 2e-12, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (-0.05 - 2e-12, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
        (0.03, "Outperform", "RELATIVE_PERFORMANCE_OUTPERFORM"),
        (0.01, "Neutral", "RELATIVE_PERFORMANCE_NEUTRAL"),
        (-0.03, "Underperform", "RELATIVE_PERFORMANCE_UNDERPERFORM"),
        (-0.08, "Strong Underperform", "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"),
    ],
)
def test_classifier_endpoints_and_adjacent_values(active, state, reason):
    assert classify_relative_performance(active) == (state, reason)


@pytest.mark.parametrize("value", [math.nan, math.inf, -math.inf, True, False, "0.03", None])
def test_classifier_rejects_invalid_active_return(value):
    with pytest.raises(MarketDataError) as error:
        classify_relative_performance(value)
    assert error.value.code == "DATA_INVALID_ACTIVE_RETURN"


def endpoints(asset_start, asset_end, benchmark_start, benchmark_end) -> pd.DataFrame:
    labels = dates_ending(64)
    asset = [100.0] * 64
    benchmark = [100.0] * 64
    asset[0] = asset_start
    asset[-1] = asset_end
    benchmark[0] = benchmark_start
    benchmark[-1] = benchmark_end
    return pd.concat(
        [series(MARKET, asset, labels), series(BENCHMARK, benchmark, labels)],
        ignore_index=True,
    )


@pytest.mark.parametrize("scale", [0.01, 0.1, 1, 10, 100, 1000, 1e6])
@pytest.mark.parametrize(
    ("name", "asset_end", "benchmark_end", "state"),
    [
        ("plus_five", 110, 105, "Strong Outperform"),
        ("plus_two", 105, 103, "Outperform"),
        ("minus_two", 101, 103, "Underperform"),
        ("minus_five", 98, 103, "Strong Underperform"),
    ],
)
def test_boundary_classification_is_stable_across_price_scales(scale, name, asset_end, benchmark_end, state):
    frame = endpoints(100 * scale, asset_end * scale, 100 * scale, benchmark_end * scale)
    result = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    raw = simple(asset_end * scale, 100 * scale) - simple(benchmark_end * scale, 100 * scale)

    assert result.relative_performance_state == state
    assert result.active_return_63 == raw


def test_known_negative_two_percent_price_scale_stays_underperform():
    frame = endpoints(10, 10.1, 10, 10.3)
    result = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    raw = simple(10.1, 10) - simple(10.3, 10)

    assert raw != -0.02
    assert abs(raw - (-0.02)) <= 1e-12
    assert result.active_return_63 == raw
    assert result.relative_performance_state == "Underperform"
    assert result.reason_code == "RELATIVE_PERFORMANCE_UNDERPERFORM"


def test_known_negative_five_percent_price_scale_stays_strong_underperform():
    frame = endpoints(10, 9.8, 10, 10.3)
    result = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    raw = simple(9.8, 10) - simple(10.3, 10)

    assert raw != -0.05
    assert abs(raw - (-0.05)) <= 1e-12
    assert result.active_return_63 == raw
    assert result.relative_performance_state == "Strong Underperform"
    assert result.reason_code == "RELATIVE_PERFORMANCE_STRONG_UNDERPERFORM"


def test_sixty_four_observations_are_accepted_and_sixty_three_are_rejected():
    accepted = pair(110, 100, count=64)
    result = calculate_relative_performance(accepted, MARKET, BENCHMARK, as_of(accepted))
    assert result.asset_return_63 == simple(110, 100)

    short = pair(110, 100, count=63)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(short, MARKET, BENCHMARK, as_of(short))
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_future_rows_cannot_complete_a_63_observation_history():
    early = dates_ending(63, "2026-02-01")
    future = dates_ending(10, "2026-03-01")
    labels = early + future
    asset = [100.0] * 63 + [1e12] * 10
    benchmark = [100.0] * 63 + [1e12] * 10
    frame = pd.concat(
        [series(MARKET, asset, labels), series(BENCHMARK, benchmark, labels)],
        ignore_index=True,
    )

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, early[-1])
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_later_prices_do_not_change_the_result_at_the_original_date():
    original = pair(110, 104)
    original_date = as_of(original)
    baseline = calculate_relative_performance(original, MARKET, BENCHMARK, original_date)

    future = dates_ending(5, "2026-03-06")
    extra = pd.concat(
        [
            series(MARKET, [1e12] * 5, future),
            series(BENCHMARK, [1e-12] * 5, future),
        ],
        ignore_index=True,
    )
    extended = pd.concat([original, extra], ignore_index=True)
    later = calculate_relative_performance(extended, MARKET, BENCHMARK, original_date)

    assert later == baseline


def test_aligned_dates_are_accepted():
    frame = pair(110, 104)
    result = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    assert result.reason_code == "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM"


def test_missing_oldest_date_on_a_64_observation_asset_is_insufficient():
    frame = pair(110, 104)
    asset = frame.loc[frame["market_id"] == MARKET].iloc[1:]
    benchmark = frame.loc[frame["market_id"] == BENCHMARK]
    trimmed = pd.concat([asset, benchmark], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(trimmed, MARKET, BENCHMARK, benchmark["date"].iloc[-1])
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_asset_missing_an_internal_date_is_a_mismatch():
    labels = dates_ending(65)
    asset_labels = labels[:10] + labels[11:]
    asset = series(MARKET, [100.0] * 64, asset_labels)
    asset.loc[asset.index[-1], "adjusted_close"] = 110
    benchmark = series(BENCHMARK, [100.0] * 65, labels)
    frame = pd.concat([asset, benchmark], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, labels[-1])
    assert error.value.code == "DATA_DATE_INDEX_MISMATCH"


def test_benchmark_missing_an_internal_date_is_a_mismatch():
    labels = dates_ending(65)
    benchmark_labels = labels[:10] + labels[11:]
    asset = series(MARKET, [100.0] * 65, labels)
    benchmark = series(BENCHMARK, [100.0] * 64, benchmark_labels)
    frame = pd.concat([asset, benchmark], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, labels[-1])
    assert error.value.code == "DATA_DATE_INDEX_MISMATCH"


def test_same_row_count_with_one_different_date_is_a_mismatch():
    labels = dates_ending(64)
    asset_labels = labels.copy()
    asset_labels[20] = "1999-01-15"
    frame = pd.concat(
        [
            series(MARKET, [100.0] * 64, asset_labels),
            series(BENCHMARK, [100.0] * 64, labels),
        ],
        ignore_index=True,
    )

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, labels[-1])
    assert error.value.code == "DATA_DATE_INDEX_MISMATCH"


def test_missing_as_of_date_on_the_asset_is_rejected():
    frame = pair(110, 104)
    requested = as_of(frame)
    asset_index = frame.index[frame["market_id"] == MARKET][-1]
    frame.loc[asset_index, "date"] = "2026-02-28"

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, requested)
    assert error.value.code == "DATA_INVALID_DATE"


def test_missing_as_of_date_on_the_benchmark_is_rejected():
    frame = pair(110, 104)
    requested = as_of(frame)
    benchmark_index = frame.index[frame["market_id"] == BENCHMARK][-1]
    frame.loc[benchmark_index, "date"] = "2026-02-28"

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, requested)
    assert error.value.code == "DATA_INVALID_DATE"


def test_duplicate_asset_date_is_rejected():
    frame = pair(110, 104)
    asset_indexes = frame.index[frame["market_id"] == MARKET]
    frame.loc[asset_indexes[1], "date"] = frame.loc[asset_indexes[0], "date"]

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    assert error.value.code == "DATA_DUPLICATE_DATE"


def test_duplicate_benchmark_date_is_rejected():
    frame = pair(110, 104)
    benchmark_indexes = frame.index[frame["market_id"] == BENCHMARK]
    frame.loc[benchmark_indexes[1], "date"] = frame.loc[benchmark_indexes[0], "date"]

    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    assert error.value.code == "DATA_DUPLICATE_DATE"


def test_absent_market_is_rejected():
    frame = pair(110, 104)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, "QQQ", BENCHMARK, as_of(frame))
    assert error.value.code == "DATA_MISSING_MARKET"


def test_absent_benchmark_is_rejected():
    frame = pair(110, 104)
    asset_only = frame.loc[frame["market_id"] == MARKET].reset_index(drop=True)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(asset_only, MARKET, BENCHMARK, as_of(frame))
    assert error.value.code == "DATA_MISSING_MARKET"


def test_acwi_is_not_classified_against_itself():
    frame = pair(110, 104)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, BENCHMARK, BENCHMARK, as_of(frame))
    assert error.value.code == "DATA_BENCHMARK_EXCLUDED"


def test_same_market_and_benchmark_identifier_is_excluded():
    frame = pair(110, 104)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, MARKET, as_of(frame))
    assert error.value.code == "DATA_BENCHMARK_EXCLUDED"


def test_benchmark_other_than_acwi_is_rejected():
    frame = pair(110, 104)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, "EWU", as_of(frame))
    assert error.value.code == "CONFIG_WRONG_BENCHMARK"


def test_another_market_cannot_contaminate_the_pair():
    original = pair(110, 104)
    other = series("QQQ", [1e12] * 64, dates_ending(64))
    mixed = pd.concat([original, other], ignore_index=True)
    mixed = mixed.sample(frac=1, random_state=5).reset_index(drop=True)
    requested = as_of(original)

    assert calculate_relative_performance(mixed, MARKET, BENCHMARK, requested) == calculate_relative_performance(
        original, MARKET, BENCHMARK, requested
    )


def test_interior_prices_do_not_change_the_63_observation_return():
    original = pair(110, 104)
    changed = original.copy(deep=True)
    asset = changed["market_id"] == MARKET
    changed.loc[asset, "adjusted_close"] = 100.0
    indexes = changed.index[asset]
    changed.loc[indexes[0], "adjusted_close"] = 100.0
    changed.loc[indexes[-1], "adjusted_close"] = 110.0
    changed.loc[indexes[10], "adjusted_close"] = 1e9
    requested = as_of(original)

    assert calculate_relative_performance(changed, MARKET, BENCHMARK, requested) == calculate_relative_performance(
        original, MARKET, BENCHMARK, requested
    )


def test_extreme_ratio_fails_closed():
    overflow = pair(1e300, 100)
    asset = overflow["market_id"] == MARKET
    overflow.loc[overflow.index[asset][0], "adjusted_close"] = 1e-300
    assert math.isinf(1e300 / 1e-300)
    with pytest.raises(MarketDataError) as overflow_error:
        calculate_relative_performance(overflow, MARKET, BENCHMARK, as_of(overflow))
    assert overflow_error.value.code == "DATA_INVALID_ACTIVE_RETURN"
    assert type(overflow_error.value) is MarketDataError

    underflow = pair(1e-300, 100)
    under_asset = underflow["market_id"] == MARKET
    underflow.loc[underflow.index[under_asset][0], "adjusted_close"] = 1e300
    assert 1e-300 / 1e300 == 0.0
    with pytest.raises(MarketDataError) as underflow_error:
        calculate_relative_performance(underflow, MARKET, BENCHMARK, as_of(underflow))
    assert underflow_error.value.code == "DATA_INVALID_ACTIVE_RETURN"


def test_very_close_prices_keep_a_small_positive_return():
    end = 100.0 + 1e-8
    frame = pair(end, 100.0)
    result = calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))

    assert result.asset_return_63 == simple(end, 100.0)
    assert result.benchmark_return_63 == 0.0
    assert result.active_return_63 > 0
    assert result.active_return_63 < 1e-6
    assert result.relative_performance_state == "Neutral"


@pytest.mark.parametrize("bad", [0, -5, True, False, "100", None, math.nan, math.inf])
def test_invalid_endpoint_price_is_rejected(bad):
    labels = dates_ending(64)
    asset_closes = [100.0] * 64
    asset_closes[-1] = bad
    asset = pd.DataFrame(
        {
            "date": labels,
            "market_id": [MARKET] * 64,
            "adjusted_close": pd.Series(asset_closes, dtype=object),
        }
    )
    benchmark = series(BENCHMARK, [100.0] * 64, labels)
    frame = pd.concat([asset, benchmark], ignore_index=True)
    frame["adjusted_close"] = frame["adjusted_close"].astype(object)
    with pytest.raises(MarketDataError) as error:
        calculate_relative_performance(frame, MARKET, BENCHMARK, labels[-1])
    assert error.value.code == "DATA_INVALID_PRICE"


def test_caller_frame_is_not_mutated_on_success_or_failure():
    frame = pair(110, 104)
    before = frame.copy(deep=True)
    calculate_relative_performance(frame, MARKET, BENCHMARK, as_of(frame))
    pd.testing.assert_frame_equal(frame, before)

    short = pair(110, 104, count=63)
    short_before = short.copy(deep=True)
    with pytest.raises(MarketDataError):
        calculate_relative_performance(short, MARKET, BENCHMARK, as_of(short))
    pd.testing.assert_frame_equal(short, short_before)


def test_repeated_calculation_is_identical():
    frame = pair(110, 104)
    requested = as_of(frame)
    first = calculate_relative_performance(frame, MARKET, BENCHMARK, requested)
    second = calculate_relative_performance(frame.iloc[::-1].reset_index(drop=True), MARKET, BENCHMARK, requested)
    assert first == second


def test_result_is_frozen():
    result = assert_case(110, 104, "Strong Outperform", "RELATIVE_PERFORMANCE_STRONG_OUTPERFORM")
    with pytest.raises(AttributeError):
        result.active_return_63 = 0.0
