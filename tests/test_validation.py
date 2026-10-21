import math

import pandas as pd
import pytest

from market_state import MarketDataError, validate_configuration, validate_market_data

MARKETS = ["SPY", "QQQ", "IWM", "EWU", "EWG", "EWJ", "EEM", "ACWI"]


def configuration() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "market_id": MARKETS,
            "display_name": MARKETS,
            "benchmark_id": ["ACWI"] * len(MARKETS),
            "enabled": [market != "ACWI" for market in MARKETS],
        }
    )


def prices(observations: int = 273, end: str = "2026-03-01", close: float = 100.0) -> pd.DataFrame:
    dates = pd.date_range(end=end, periods=observations, freq="D").strftime("%Y-%m-%d")
    return pd.DataFrame(
        {
            "date": [date for date in dates for _market in MARKETS],
            "market_id": MARKETS * len(dates),
            "adjusted_close": [close] * (len(dates) * len(MARKETS)),
        }
    )


def test_golden_dataset_is_accepted_and_canonical():
    frame = prices().iloc[::-1][["adjusted_close", "market_id", "date"]].reset_index(drop=True)
    before = frame.copy(deep=True)
    config = configuration()
    config_before = config.copy(deep=True)

    validated = validate_market_data(frame, config, "2026-03-01")
    again = validate_market_data(frame, config, "2026-03-01")

    assert list(validated.columns) == ["date", "market_id", "adjusted_close"]
    assert validated["date"].dtype == "string"
    assert validated["market_id"].dtype == "string"
    assert validated["adjusted_close"].dtype == "float64"
    assert len(validated) == 273 * len(MARKETS)
    assert validated["date"].is_monotonic_increasing
    ordered = validated.sort_values(["date", "market_id"], kind="mergesort").reset_index(drop=True)
    pd.testing.assert_frame_equal(validated, ordered)
    pd.testing.assert_frame_equal(validated, again)
    pd.testing.assert_frame_equal(frame, before)
    pd.testing.assert_frame_equal(config, config_before)


def test_market_id_must_match_exactly():
    frame = prices()
    frame.loc[frame["market_id"] == "SPY", "market_id"] = "spy"

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_UNKNOWN_MARKET"


def test_unknown_market_is_rejected():
    frame = prices()
    extra = frame.iloc[[0]].copy()
    extra["market_id"] = "VT"
    frame = pd.concat([frame, extra], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_UNKNOWN_MARKET"


def test_missing_required_market_is_rejected():
    frame = prices()
    frame = frame[frame["market_id"] != "EEM"]

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_MISSING_MARKET"


def test_duplicate_date_and_market_is_rejected():
    frame = prices()
    frame = pd.concat([frame, frame.iloc[[0]]], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_DUPLICATE_DATE"


def test_mismatched_date_index_is_rejected():
    frame = prices()
    drop = frame[(frame["market_id"] == "QQQ") & (frame["date"] == frame["date"].iloc[0])].index
    frame = frame.drop(drop)

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_DATE_INDEX_MISMATCH"


def test_malformed_date_is_rejected():
    frame = prices()
    frame.loc[0, "date"] = "2026/03/01"

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_INVALID_DATE"


def test_impossible_date_is_rejected():
    frame = prices()
    frame.loc[0, "date"] = "2026-02-31"

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_INVALID_DATE"


@pytest.mark.parametrize(
    ("value", "code"),
    [
        (None, "DATA_MISSING_VALUE"),
        ("", "DATA_MISSING_VALUE"),
        ("not-a-price", "DATA_INVALID_PRICE"),
        (0, "DATA_INVALID_PRICE"),
        (-1, "DATA_INVALID_PRICE"),
        (float("nan"), "DATA_INVALID_PRICE"),
        (math.inf, "DATA_INVALID_PRICE"),
        (-math.inf, "DATA_INVALID_PRICE"),
    ],
)
def test_bad_adjusted_close_is_rejected(value, code):
    frame = prices()
    frame["adjusted_close"] = frame["adjusted_close"].astype(object)
    frame.loc[0, "adjusted_close"] = value

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == code


def test_273_observations_are_accepted():
    validated = validate_market_data(prices(273), configuration(), "2026-03-01")

    assert validated["date"].nunique() == 273


def test_272_observations_are_rejected():
    with pytest.raises(MarketDataError) as error:
        validate_market_data(prices(272), configuration(), "2026-03-01")

    assert error.value.code == "DATA_INSUFFICIENT_HISTORY"


def test_five_calendar_days_are_accepted():
    validated = validate_market_data(prices(), configuration(), "2026-03-06")

    assert validated["date"].max() == "2026-03-01"


def test_six_calendar_days_are_rejected():
    with pytest.raises(MarketDataError) as error:
        validate_market_data(prices(), configuration(), "2026-03-07")

    assert error.value.code == "DATA_STALE"


def test_future_observation_is_rejected():
    with pytest.raises(MarketDataError) as error:
        validate_market_data(prices(), configuration(), "2026-02-28")

    assert error.value.code == "DATA_FUTURE_DATE"


def test_disabled_configured_market_may_have_a_different_date():
    config = configuration()
    extra = pd.DataFrame(
        {
            "market_id": ["GLD"],
            "display_name": ["Gold"],
            "benchmark_id": ["ACWI"],
            "enabled": [False],
        }
    )
    config = pd.concat([config, extra], ignore_index=True)
    frame = prices()
    stray = pd.DataFrame(
        {"date": ["1999-01-01"], "market_id": ["GLD"], "adjusted_close": [50.0]}
    )
    frame = pd.concat([frame, stray], ignore_index=True)

    validated = validate_market_data(frame, config, "2026-03-01")

    assert "GLD" in set(validated["market_id"])
    assert validated["date"].nunique() == 274 or "1999-01-01" in set(validated["date"])


def test_duplicate_config_market_is_rejected():
    config = pd.concat([configuration(), configuration().iloc[[0]]], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_DUPLICATE_MARKET"


def test_missing_acwi_is_rejected():
    config = configuration()
    config = config[config["market_id"] != "ACWI"]

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_MISSING_BENCHMARK"


def test_required_board_market_disabled_is_rejected():
    config = configuration()
    config.loc[config["market_id"] == "SPY", "enabled"] = False

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_MARKET_DISABLED"


def test_wrong_benchmark_is_rejected():
    config = configuration()
    config.loc[config["market_id"] == "SPY", "benchmark_id"] = "QQQ"

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_WRONG_BENCHMARK"


def test_unknown_benchmark_is_rejected():
    config = configuration()
    config.loc[config["market_id"] == "ACWI", "benchmark_id"] = "VT"

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_UNKNOWN_BENCHMARK"


def test_missing_config_field_is_rejected():
    config = configuration().drop(columns=["display_name"])

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_MISSING_FIELD"
