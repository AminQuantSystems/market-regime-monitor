import math

import pandas as pd
import pytest

from market_state import MarketDataError, calculate_momentum, classify_momentum

MARKET = "SPY"
FIELDS = {
    "market_id",
    "as_of_date",
    "adjusted_close",
    "return_21",
    "return_63",
    "pace_21",
    "pace_63",
    "momentum_state",
    "reason_code",
}


def history_from(price_t: float, price_21: float, price_63: float, filler: float = 50.0, extra_before: int = 0) -> pd.DataFrame:
    count = 64 + extra_before
    closes = [filler] * count
    closes[-1] = price_t
    closes[-1 - 21] = price_21
    closes[-1 - 63] = price_63
    dates = pd.date_range(end="2026-03-01", periods=count, freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "date": list(dates),
            "market_id": [MARKET] * count,
            "adjusted_close": closes,
        }
    )


def as_of(frame: pd.DataFrame) -> str:
    return frame["date"].iloc[-1]


def assert_state(price_t, price_21, price_63, state, reason):
    frame = history_from(price_t, price_21, price_63)
    result = calculate_momentum(frame, MARKET, as_of(frame))
    expected_r21 = price_t / price_21 - 1
    expected_r63 = price_t / price_63 - 1
    expected_p21 = math.log(price_t / price_21) / 21
    expected_p63 = math.log(price_t / price_63) / 63
    assert result.adjusted_close == price_t
    assert result.return_21 == expected_r21
    assert result.return_63 == expected_r63
    assert result.pace_21 == expected_p21
    assert result.pace_63 == expected_p63
    assert result.momentum_state == state
    assert result.reason_code == reason
    assert classify_momentum(expected_r21, expected_r63, expected_p21, expected_p63) == (state, reason)
    assert set(result.__dataclass_fields__) == FIELDS
    return result


def test_accelerating():
    result = assert_state(121, 100, 110, "Accelerating", "MOMENTUM_ACCELERATING")
    assert result.return_21 == pytest.approx(0.21)
    assert result.return_63 == pytest.approx(0.10)
    assert result.pace_21 > result.pace_63


def test_positive():
    result = assert_state(200, 198, 100, "Positive", "MOMENTUM_POSITIVE")
    assert result.return_63 == 1
    assert result.pace_21 < result.pace_63


def test_mixed_positive_short_and_negative_medium():
    result = assert_state(100, 90, 110, "Mixed", "MOMENTUM_MIXED")
    assert result.return_21 > 0
    assert result.return_63 < 0


def test_mixed_negative_short_and_positive_medium():
    result = assert_state(100, 110, 90, "Mixed", "MOMENTUM_MIXED")
    assert result.return_21 < 0
    assert result.return_63 > 0


def test_mixed_when_r21_is_zero():
    result = assert_state(100, 100, 80, "Mixed", "MOMENTUM_MIXED")
    assert result.return_21 == 0
    assert result.return_63 == 0.25


def test_mixed_when_r63_is_zero():
    result = assert_state(100, 80, 100, "Mixed", "MOMENTUM_MIXED")
    assert result.return_63 == 0
    assert result.return_21 == 0.25


def test_negative():
    result = assert_state(90, 91, 150, "Negative", "MOMENTUM_NEGATIVE")
    assert result.return_21 < 0
    assert result.return_63 < 0
    assert result.pace_21 > result.pace_63


def test_deteriorating():
    result = assert_state(70, 100, 110, "Deteriorating", "MOMENTUM_DETERIORATING")
    assert result.return_21 == pytest.approx(-0.30)
    assert result.return_63 < 0
    assert result.pace_21 < result.pace_63


def test_equal_positive_pace_is_positive():
    result = assert_state(27, 9, 1, "Positive", "MOMENTUM_POSITIVE")
    assert result.return_21 == 2
    assert result.return_63 == 26
    assert result.pace_21 == result.pace_63
    assert classify_momentum(2, 26, result.pace_21, result.pace_21) == ("Positive", "MOMENTUM_POSITIVE")


def test_equal_negative_pace_is_negative():
    result = assert_state(1, 3, 27, "Negative", "MOMENTUM_NEGATIVE")
    assert result.return_21 < 0
    assert result.return_63 < 0
    assert result.pace_21 == result.pace_63
    assert classify_momentum(-2 / 3, 1 / 27 - 1, result.pace_21, result.pace_21) == (
        "Negative",
        "MOMENTUM_NEGATIVE",
    )


def test_exactly_64_observations_are_accepted():
    frame = history_from(121, 100, 110)
    result = calculate_momentum(frame, MARKET, "2026-03-01")

    assert len(frame) == 64
    assert result.momentum_state == "Accelerating"
    assert result.as_of_date == "2026-03-01"
    assert result.market_id == MARKET


def test_63_observations_are_rejected():
    frame = history_from(121, 100, 110).iloc[1:].reset_index(drop=True)

    with pytest.raises(MarketDataError) as error:
        calculate_momentum(frame, MARKET, as_of(frame))

    assert len(frame) == 63
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_r21_uses_price_t_and_price_t_minus_21():
    frame = history_from(121, 100, 110)
    result = calculate_momentum(frame, MARKET, as_of(frame))

    assert result.return_21 == 121 / 100 - 1
    assert result.return_21 != frame["adjusted_close"].iloc[-1] / frame["adjusted_close"].iloc[-23] - 1


def test_r63_uses_price_t_and_price_t_minus_63():
    frame = history_from(121, 100, 110)
    result = calculate_momentum(frame, MARKET, as_of(frame))

    assert result.return_63 == 121 / 110 - 1
    assert frame["adjusted_close"].iloc[0] == 110
    assert result.return_63 == frame["adjusted_close"].iloc[-1] / frame["adjusted_close"].iloc[0] - 1


def test_observation_outside_21_lookback_does_not_change_r21():
    baseline = calculate_momentum(history_from(121, 100, 110), MARKET, "2026-03-01")
    shifted = history_from(121, 100, 110)
    shifted.loc[shifted.index[-1 - 22], "adjusted_close"] = 1_000_000
    result = calculate_momentum(shifted, MARKET, "2026-03-01")

    assert result.return_21 == baseline.return_21
    assert result.pace_21 == baseline.pace_21


def test_observation_outside_63_lookback_does_not_change_r63():
    baseline = calculate_momentum(history_from(121, 100, 110), MARKET, "2026-03-01")
    extended = history_from(121, 100, 110, extra_before=1)
    extended.loc[0, "adjusted_close"] = 1_000_000
    result = calculate_momentum(extended, MARKET, as_of(extended))

    assert result.return_63 == baseline.return_63 == 121 / 110 - 1
    assert result.pace_63 == baseline.pace_63
    assert result.momentum_state == baseline.momentum_state


def test_as_of_calculation_ignores_future_observations():
    past = history_from(121, 100, 110)
    as_of_date = as_of(past)
    future_dates = pd.date_range(start="2026-03-02", periods=30, freq="D").strftime("%Y-%m-%d")
    future = pd.DataFrame(
        {
            "date": list(future_dates),
            "market_id": [MARKET] * len(future_dates),
            "adjusted_close": [1_000_000_000] * len(future_dates),
        }
    )
    combined = pd.concat([past, future], ignore_index=True)
    original = calculate_momentum(past, MARKET, as_of_date)
    later = calculate_momentum(combined, MARKET, as_of_date)

    assert later == original
    assert later.return_21 == pytest.approx(0.21)
    assert later.momentum_state == "Accelerating"

    short = past.iloc[:-1].reset_index(drop=True)
    poisoned = pd.concat([short, future], ignore_index=True)
    with pytest.raises(MarketDataError) as error:
        calculate_momentum(poisoned, MARKET, as_of(short))
    assert len(short) == 63
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_missing_as_of_observation_is_rejected():
    frame = history_from(121, 100, 110)

    with pytest.raises(MarketDataError) as error:
        calculate_momentum(frame, MARKET, "2026-03-02")

    assert error.value.code == "DATA_INVALID_DATE"


def test_input_history_is_not_mutated():
    frame = history_from(121, 100, 110)
    before = frame.copy(deep=True)
    calculate_momentum(frame, MARKET, as_of(frame))
    pd.testing.assert_frame_equal(frame, before)

    short = frame.iloc[:-1].reset_index(drop=True)
    short_before = short.copy(deep=True)
    with pytest.raises(MarketDataError):
        calculate_momentum(short, MARKET, as_of(short))
    pd.testing.assert_frame_equal(short, short_before)


def test_repeated_calculation_is_identical():
    frame = history_from(70, 100, 110)
    first = calculate_momentum(frame, MARKET, "2026-03-01")
    second = calculate_momentum(frame, MARKET, "2026-03-01")

    assert first == second


def test_another_market_cannot_contaminate_the_calculation():
    spy = history_from(121, 100, 110)
    other = spy.copy()
    other["market_id"] = "QQQ"
    other["adjusted_close"] = 1_000_000
    mixed = pd.concat([spy, other], ignore_index=True)
    mixed = mixed.sample(frac=1, random_state=2).reset_index(drop=True)

    assert calculate_momentum(mixed, MARKET, "2026-03-01") == calculate_momentum(spy, MARKET, "2026-03-01")


def test_reason_codes_match_the_specification():
    expected = {
        "Accelerating": "MOMENTUM_ACCELERATING",
        "Positive": "MOMENTUM_POSITIVE",
        "Mixed": "MOMENTUM_MIXED",
        "Negative": "MOMENTUM_NEGATIVE",
        "Deteriorating": "MOMENTUM_DETERIORATING",
    }
    samples = [
        assert_state(121, 100, 110, "Accelerating", "MOMENTUM_ACCELERATING"),
        assert_state(200, 198, 100, "Positive", "MOMENTUM_POSITIVE"),
        assert_state(100, 90, 110, "Mixed", "MOMENTUM_MIXED"),
        assert_state(90, 91, 150, "Negative", "MOMENTUM_NEGATIVE"),
        assert_state(70, 100, 110, "Deteriorating", "MOMENTUM_DETERIORATING"),
    ]
    for result in samples:
        assert result.reason_code == expected[result.momentum_state]


@pytest.mark.parametrize(
    "value",
    [float("nan"), math.inf, -math.inf, True, False, "100", None],
)
def test_classifier_rejects_invalid_direct_inputs(value):
    with pytest.raises(MarketDataError) as error:
        classify_momentum(value, 0.1, 0.01, 0.01)

    assert error.value.code == "DATA_INVALID_PRICE"


def test_underflowing_price_ratio_raises_market_data_error():
    frame = history_from(1e-300, 1e300, 1e300)

    with pytest.raises(MarketDataError) as error:
        calculate_momentum(frame, MARKET, as_of(frame))

    assert error.value.code == "DATA_INVALID_PRICE"
