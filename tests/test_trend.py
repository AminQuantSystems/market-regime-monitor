import pandas as pd
import pytest

from market_state import MarketDataError, calculate_trend, classify_trend

MARKET = "SPY"


def history(closes: list[float], market_id: str = MARKET, end: str = "2026-03-01") -> pd.DataFrame:
    dates = pd.date_range(end=end, periods=len(closes), freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "date": list(dates),
            "market_id": [market_id] * len(closes),
            "adjusted_close": list(closes),
        }
    )


def as_of(frame: pd.DataFrame) -> str:
    return frame["date"].iloc[-1]


def test_strong_up():
    closes = [80] * 150 + [100] * 49 + [130]
    frame = history(closes)
    result = calculate_trend(frame, MARKET, as_of(frame))

    assert result.adjusted_close == 130
    assert result.sma_50 == pytest.approx((49 * 100 + 130) / 50)
    assert result.sma_200 == pytest.approx((150 * 80 + 49 * 100 + 130) / 200)
    assert result.sma_50 == pytest.approx(100.6)
    assert result.sma_200 == pytest.approx(85.15)
    assert result.trend_score == 2
    assert result.trend_state == "Strong Up"
    assert result.reason_code == "TREND_STRONG_UP_ALIGNMENT"
    assert classify_trend(130, 100.6, 85.15) == (2, "Strong Up", "TREND_STRONG_UP_ALIGNMENT")


def test_up():
    closes = [50] * 150 + [100] * 49 + [90]
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 90
    assert result.sma_50 == pytest.approx(99.8)
    assert result.sma_200 == pytest.approx(62.45)
    assert result.trend_score == 1
    assert result.trend_state == "Up"
    assert result.reason_code == "TREND_UP_ABOVE_200"


def test_neutral_when_price_equals_sma200():
    result = calculate_trend(history([100] * 200), MARKET, "2026-03-01")

    assert result.adjusted_close == 100
    assert result.sma_50 == 100
    assert result.sma_200 == 100
    assert result.trend_score == 0
    assert result.trend_state == "Neutral"
    assert result.reason_code == "TREND_NEUTRAL_AT_200"


def test_down():
    closes = [120] * 150 + [100] * 49 + [110]
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 110
    assert result.sma_50 == pytest.approx(100.2)
    assert result.sma_200 == pytest.approx(115.05)
    assert result.trend_score == -1
    assert result.trend_state == "Down"
    assert result.reason_code == "TREND_DOWN_BELOW_200"


def test_strong_down():
    closes = [150] * 150 + [120] * 49 + [100]
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 100
    assert result.sma_50 == pytest.approx(119.6)
    assert result.sma_200 == pytest.approx(142.4)
    assert result.trend_score == -2
    assert result.trend_state == "Strong Down"
    assert result.reason_code == "TREND_STRONG_DOWN_ALIGNMENT"
    assert classify_trend(100, 119.6, 142.4) == (-2, "Strong Down", "TREND_STRONG_DOWN_ALIGNMENT")


def test_price_equal_to_sma50_above_sma200_is_up():
    closes = [50] * 150 + [100] * 50
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 100
    assert result.sma_50 == 100
    assert result.sma_200 == (150 * 50 + 50 * 100) / 200
    assert result.sma_200 == 62.5
    assert result.trend_score == 1
    assert result.trend_state == "Up"
    assert result.reason_code == "TREND_UP_ABOVE_200"


def test_equal_moving_averages_above_sma200_is_up():
    closes = [100] * 150 + [100] * 48 + [90, 110]
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 110
    assert result.sma_50 == 100
    assert result.sma_200 == 100
    assert result.trend_score == 1
    assert result.reason_code == "TREND_UP_ABOVE_200"


def test_price_equal_to_sma50_below_sma200_is_down():
    closes = [150] * 150 + [100] * 50
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 100
    assert result.sma_50 == 100
    assert result.sma_200 == (150 * 150 + 50 * 100) / 200
    assert result.sma_200 == 137.5
    assert result.trend_score == -1
    assert result.trend_state == "Down"
    assert result.reason_code == "TREND_DOWN_BELOW_200"


def test_equal_moving_averages_below_sma200_is_down():
    closes = [100] * 150 + [100] * 48 + [110, 90]
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert result.adjusted_close == 90
    assert result.sma_50 == 100
    assert result.sma_200 == 100
    assert result.trend_score == -1
    assert result.reason_code == "TREND_DOWN_BELOW_200"


def test_exactly_200_observations_are_accepted():
    result = calculate_trend(history([100] * 200), MARKET, "2026-03-01")

    assert result.trend_score == 0
    assert result.as_of_date == "2026-03-01"


def test_199_observations_are_rejected():
    frame = history([100] * 199)

    with pytest.raises(MarketDataError) as error:
        calculate_trend(frame, MARKET, as_of(frame))

    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_sma50_uses_exactly_the_latest_50_observations():
    closes = [80] * 149 + [10_000] + [100] * 50
    result = calculate_trend(history(closes), MARKET, "2026-03-01")

    assert len(closes) == 200
    assert result.sma_50 == 100
    assert result.adjusted_close == 100


def test_sma200_uses_exactly_the_latest_200_observations():
    closes = [10_000] + [100] * 200
    frame = history(closes)
    result = calculate_trend(frame, MARKET, as_of(frame))

    assert len(closes) == 201
    assert result.sma_200 == 100
    assert result.sma_50 == 100
    assert result.trend_score == 0


def test_outlier_just_outside_sma50_window_does_not_change_sma50():
    without = [80] * 150 + [100] * 50
    with_outlier = [80] * 149 + [10_000] + [100] * 50
    baseline = calculate_trend(history(without), MARKET, "2026-03-01")
    shifted = calculate_trend(history(with_outlier), MARKET, "2026-03-01")

    assert baseline.sma_50 == 100
    assert shifted.sma_50 == baseline.sma_50
    assert shifted.sma_200 != baseline.sma_200


def test_outlier_just_outside_sma200_window_does_not_change_sma200():
    baseline = calculate_trend(history([100] * 200), MARKET, "2026-03-01")
    extended = history([10_000] + [100] * 200)
    shifted = calculate_trend(extended, MARKET, as_of(extended))

    assert shifted.sma_200 == baseline.sma_200 == 100
    assert shifted.sma_50 == baseline.sma_50 == 100


def test_as_of_calculation_ignores_future_observations():
    past = history([80] * 150 + [100] * 49 + [130])
    as_of_date = as_of(past)
    future_dates = pd.date_range(start="2026-03-02", periods=40, freq="D").strftime("%Y-%m-%d")
    future = pd.DataFrame(
        {
            "date": list(future_dates),
            "market_id": [MARKET] * len(future_dates),
            "adjusted_close": [1_000_000_000] * len(future_dates),
        }
    )
    combined = pd.concat([past, future], ignore_index=True)
    original = calculate_trend(past, MARKET, as_of_date)
    later = calculate_trend(combined, MARKET, as_of_date)

    assert later == original
    assert later.sma_50 == pytest.approx(100.6)
    assert later.sma_200 == pytest.approx(85.15)
    assert later.trend_score == 2

    short = past.iloc[:-1].reset_index(drop=True)
    poisoned = pd.concat([short, future], ignore_index=True)
    with pytest.raises(MarketDataError) as error:
        calculate_trend(poisoned, MARKET, as_of(short))
    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_missing_as_of_observation_is_rejected():
    frame = history([100] * 200)

    with pytest.raises(MarketDataError) as error:
        calculate_trend(frame, MARKET, "2026-03-02")

    assert error.value.code == "DATA_INVALID_DATE"


def test_input_history_is_not_mutated():
    frame = history([80] * 150 + [100] * 49 + [130])
    before = frame.copy(deep=True)
    calculate_trend(frame, MARKET, as_of(frame))
    pd.testing.assert_frame_equal(frame, before)

    short = history([100] * 199)
    short_before = short.copy(deep=True)
    with pytest.raises(MarketDataError):
        calculate_trend(short, MARKET, as_of(short))
    pd.testing.assert_frame_equal(short, short_before)


def test_another_market_does_not_change_spy_trend():
    spy = history([80] * 150 + [100] * 49 + [130])
    other = spy.copy()
    other["market_id"] = "QQQ"
    other["adjusted_close"] = 1_000_000
    mixed = pd.concat([spy, other], ignore_index=True)

    assert calculate_trend(mixed, MARKET, as_of(spy)) == calculate_trend(spy, MARKET, as_of(spy))


def test_repeated_calculation_is_identical():
    frame = history([120] * 150 + [100] * 49 + [110])
    first = calculate_trend(frame, MARKET, "2026-03-01")
    second = calculate_trend(frame, MARKET, "2026-03-01")

    assert first == second
    assert first.sma_50 == second.sma_50
    assert first.sma_200 == second.sma_200
