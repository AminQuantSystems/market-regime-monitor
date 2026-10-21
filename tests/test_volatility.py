import math

import pandas as pd
import pytest

from market_state import (
    MarketDataError,
    calculate_rv21,
    calculate_volatility,
    classify_volatility,
)

MARKET = "SPY"
REFERENCE = 252


def reference_values(below: int, equal: int, above: int, current: float) -> list[float]:
    """Build 252 values that produce the requested strict and tied counts."""
    assert below + equal + above == REFERENCE
    if current == 0:
        assert below == 0
        low = 0.0
    else:
        low = 0.0
    high = current + 1 if above else current
    return [low] * below + [current] * equal + [high] * above


def assert_midrank(below, equal, above, current, regime, reason):
    history = reference_values(below, equal, above, current)
    result = classify_volatility(current, history)
    percentile = 100 * (below + 0.5 * equal) / REFERENCE

    assert result.historical_below_count == below
    assert result.historical_equal_count == equal
    assert result.historical_reference_size == REFERENCE
    assert result.historical_percentile == percentile
    assert result.volatility_regime == regime
    assert result.reason_code == reason
    return result


def closes_frame(closes, market=MARKET, end="2026-03-01") -> pd.DataFrame:
    dates = pd.date_range(end=end, periods=len(closes), freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "date": list(dates),
            "market_id": [market] * len(closes),
            "adjusted_close": list(closes),
        }
    )


def test_constant_prices_have_zero_rv21():
    assert calculate_rv21([100.0] * 22) == 0


def test_constant_positive_log_return():
    prices = [math.exp(0.01 * step) for step in range(22)]

    assert calculate_rv21(prices) == pytest.approx(0.01 * math.sqrt(252))


def test_alternating_log_return_matches_constant_magnitude():
    level = 0.0
    prices = [math.exp(level)]
    for step in range(21):
        level += 0.01 if step % 2 == 0 else -0.01
        prices.append(math.exp(level))

    assert calculate_rv21(prices) == pytest.approx(0.01 * math.sqrt(252))
    assert calculate_rv21(prices) == pytest.approx(calculate_rv21([math.exp(0.01 * step) for step in range(22)]))


def test_rv21_requires_exactly_22_prices():
    with pytest.raises(MarketDataError) as short:
        calculate_rv21([100.0] * 21)
    assert short.value.code == "DATA_INSUFFICIENT_HISTORY"

    with pytest.raises(MarketDataError) as long:
        calculate_rv21([100.0] * 23)
    assert long.value.code == "DATA_INVALID_VOLATILITY"


@pytest.mark.parametrize(
    ("below", "equal", "above", "current", "regime", "reason", "display"),
    [
        (63, 0, 189, 1.0, "Low", "VOLATILITY_LOW", 25),
        (64, 0, 188, 1.0, "Normal", "VOLATILITY_NORMAL", 25.3968253968),
        (189, 0, 63, 1.0, "Normal", "VOLATILITY_NORMAL", 75),
        (190, 0, 62, 1.0, "Elevated", "VOLATILITY_ELEVATED", 75.3968253968),
        (226, 0, 26, 1.0, "Elevated", "VOLATILITY_ELEVATED", 89.6825396825),
        (227, 0, 25, 1.0, "High", "VOLATILITY_HIGH", 90.0793650794),
        (0, 252, 0, 0.0, "Normal", "VOLATILITY_NORMAL", 50),
        (62, 2, 188, 1.0, "Low", "VOLATILITY_LOW", 25),
        (188, 2, 62, 1.0, "Normal", "VOLATILITY_NORMAL", 75),
        (252, 0, 0, 1.0, "High", "VOLATILITY_HIGH", 100),
        (0, 0, 252, 0.0, "Low", "VOLATILITY_LOW", 0),
    ],
)
def test_midrank_regime_boundaries(below, equal, above, current, regime, reason, display):
    result = assert_midrank(below, equal, above, current, regime, reason)

    assert result.historical_percentile == pytest.approx(display)


def test_constant_zero_history_is_normal_not_high():
    frame = closes_frame([100.0] * 274)
    result = calculate_volatility(frame, MARKET, frame["date"].iloc[-1])

    assert result.realized_volatility_21 == 0
    assert result.historical_below_count == 0
    assert result.historical_equal_count == 252
    assert result.historical_reference_size == 252
    assert result.historical_percentile == 50
    assert result.volatility_regime == "Normal"
    assert result.reason_code == "VOLATILITY_NORMAL"
    assert result.adjusted_close == 100


def test_current_rv21_is_excluded_from_its_reference():
    closes = [100.0] * 273 + [200.0]
    frame = closes_frame(closes)
    result = calculate_volatility(frame, MARKET, frame["date"].iloc[-1])

    assert calculate_rv21([100.0] * 22) == 0
    assert result.realized_volatility_21 == calculate_rv21(closes[-22:])
    assert result.realized_volatility_21 > 0
    assert result.historical_below_count == 252
    assert result.historical_equal_count == 0
    assert result.historical_percentile == 100
    assert result.volatility_regime == "High"


def test_as_of_calculation_ignores_future_observations():
    past = closes_frame([100.0] * 274)
    as_of_date = past["date"].iloc[-1]
    future_dates = pd.date_range(start="2026-03-02", periods=30, freq="D").strftime("%Y-%m-%d")
    future = pd.DataFrame(
        {
            "date": list(future_dates),
            "market_id": [MARKET] * len(future_dates),
            "adjusted_close": [1_000_000_000] * len(future_dates),
        }
    )
    combined = pd.concat([past, future], ignore_index=True)
    original = calculate_volatility(past, MARKET, as_of_date)
    later = calculate_volatility(combined, MARKET, as_of_date)

    assert later == original

    short = past.iloc[:-1].reset_index(drop=True)
    poisoned = pd.concat([short, future], ignore_index=True)
    with pytest.raises(MarketDataError) as error:
        calculate_volatility(poisoned, MARKET, short["date"].iloc[-1])
    assert len(short) == 273
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_classifier_rejects_wrong_reference_length():
    with pytest.raises(MarketDataError) as short:
        classify_volatility(1.0, [0.0] * 251)
    assert short.value.code == "DATA_INVALID_VOLATILITY"

    accepted = classify_volatility(1.0, [0.0] * 252)
    assert accepted.historical_reference_size == 252

    with pytest.raises(MarketDataError) as long:
        classify_volatility(1.0, [0.0] * 253)
    assert long.value.code == "DATA_INVALID_VOLATILITY"


@pytest.mark.parametrize(
    "value",
    [float("nan"), math.inf, -math.inf, True, False, "0.2", None],
)
def test_classifier_rejects_invalid_volatility_values(value):
    with pytest.raises(MarketDataError) as current_error:
        classify_volatility(value, [0.0] * 252)
    assert current_error.value.code == "DATA_INVALID_VOLATILITY"

    history = [0.2] * 252
    history[0] = value
    with pytest.raises(MarketDataError) as historical_error:
        classify_volatility(0.2, history)
    assert historical_error.value.code == "DATA_INVALID_VOLATILITY"


def test_classifier_rejects_negative_volatility():
    with pytest.raises(MarketDataError) as current_error:
        classify_volatility(-0.01, [0.0] * 252)
    assert current_error.value.code == "DATA_INVALID_VOLATILITY"

    history = [0.2] * 252
    history[3] = -0.01
    with pytest.raises(MarketDataError) as historical_error:
        classify_volatility(0.2, history)
    assert historical_error.value.code == "DATA_INVALID_VOLATILITY"


def test_extreme_prices_use_log_difference():
    closes = [1e300 if step % 2 == 0 else 1e-300 for step in range(22)]
    assert closes[0] / closes[1] == math.inf

    squares = [(math.log(current) - math.log(previous)) ** 2 for previous, current in zip(closes, closes[1:])]
    expected = math.sqrt(252 * math.fsum(squares) / 21)
    first = calculate_rv21(closes)
    second = calculate_rv21(list(closes))

    assert first == second == expected
    assert math.isfinite(first)


def test_another_market_cannot_contaminate_the_calculation():
    spy = closes_frame([100.0] * 274)
    other = spy.copy()
    other["market_id"] = "QQQ"
    other["adjusted_close"] = 1_000_000_000
    mixed = pd.concat([spy, other], ignore_index=True)
    mixed = mixed.sample(frac=1, random_state=3).reset_index(drop=True)
    as_of_date = spy["date"].iloc[-1]

    assert calculate_volatility(mixed, MARKET, as_of_date) == calculate_volatility(spy, MARKET, as_of_date)


def test_missing_as_of_observation_is_rejected():
    frame = closes_frame([100.0] * 274)

    with pytest.raises(MarketDataError) as error:
        calculate_volatility(frame, MARKET, "2026-03-02")

    assert error.value.code == "DATA_INVALID_DATE"


def test_duplicate_date_is_rejected():
    frame = closes_frame([100.0] * 274)
    frame.loc[1, "date"] = frame.loc[0, "date"]

    with pytest.raises(MarketDataError) as error:
        calculate_volatility(frame, MARKET, frame["date"].iloc[-1])

    assert error.value.code == "DATA_DUPLICATE_DATE"


def test_input_history_is_not_mutated():
    frame = closes_frame([100.0] * 274)
    before = frame.copy(deep=True)
    calculate_volatility(frame, MARKET, frame["date"].iloc[-1])
    pd.testing.assert_frame_equal(frame, before)

    short = frame.iloc[:-1].reset_index(drop=True)
    short_before = short.copy(deep=True)
    with pytest.raises(MarketDataError):
        calculate_volatility(short, MARKET, short["date"].iloc[-1])
    pd.testing.assert_frame_equal(short, short_before)


def test_repeated_calculation_is_identical():
    frame = closes_frame([100.0] * 273 + [130.0])
    as_of_date = frame["date"].iloc[-1]
    first = calculate_volatility(frame, MARKET, as_of_date)
    second = calculate_volatility(frame.iloc[::-1].reset_index(drop=True), MARKET, as_of_date)

    assert first == second


def test_absent_market_is_rejected():
    frame = closes_frame([100.0] * 274)

    with pytest.raises(MarketDataError) as error:
        calculate_volatility(frame, "QQQ", frame["date"].iloc[-1])

    assert error.value.code == "DATA_MISSING_MARKET"


def test_rv21_rejects_non_positive_prices():
    closes = [100.0] * 22
    closes[4] = 0
    with pytest.raises(MarketDataError) as error:
        calculate_rv21(closes)
    assert error.value.code == "DATA_INVALID_PRICE"

    closes[4] = True
    with pytest.raises(MarketDataError) as boolean_error:
        calculate_rv21(closes)
    assert boolean_error.value.code == "DATA_INVALID_PRICE"
