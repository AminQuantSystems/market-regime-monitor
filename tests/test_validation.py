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


def test_nullable_boolean_cannot_bypass_benchmark_validation():
    extra = pd.DataFrame(
        {
            "market_id": ["GLD"],
            "display_name": ["Gold"],
            "benchmark_id": ["SPY"],
            "enabled": [True],
        }
    )
    config = pd.concat([configuration(), extra], ignore_index=True)
    config["enabled"] = config["enabled"].astype("boolean")
    assert isinstance(config["enabled"].dtype, pd.BooleanDtype)

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_WRONG_BENCHMARK"


def test_nullable_boolean_configuration_is_accepted():
    config = configuration()
    config["enabled"] = config["enabled"].astype("boolean")

    validated = validate_configuration(config)

    spy = validated.loc[validated["market_id"] == "SPY", "enabled"].iloc[0]
    acwi = validated.loc[validated["market_id"] == "ACWI", "enabled"].iloc[0]
    assert spy == True and acwi == False


def test_numpy_boolean_scalars_are_accepted():
    numpy = pytest.importorskip("numpy")
    config = configuration()
    config["enabled"] = pd.Series(
        [numpy.bool_(market != "ACWI") for market in MARKETS],
        dtype=object,
    )

    validated = validate_configuration(config)

    for market_id, enabled in zip(validated["market_id"], validated["enabled"], strict=True):
        assert enabled == (market_id != "ACWI")


def test_same_row_count_with_different_dates_is_rejected():
    frame = prices()
    assert (frame.groupby("market_id").size() == 273).all()
    first = sorted(frame["date"].unique())[0]
    shifted = (frame["market_id"] == "QQQ") & (frame["date"] == first)
    frame.loc[shifted, "date"] = "1999-12-31"
    assert (frame.groupby("market_id").size() == 273).all()

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_DATE_INDEX_MISMATCH"


def test_canonical_output_preserves_non_uniform_price():
    frame = prices()
    target_date = frame.loc[0, "date"]
    target_market = frame.loc[0, "market_id"]
    frame.loc[0, "adjusted_close"] = 100.25

    validated = validate_market_data(frame, configuration(), "2026-03-01")

    match = validated[
        (validated["date"] == target_date) & (validated["market_id"] == target_market)
    ]
    others = validated.drop(index=match.index)
    assert match["adjusted_close"].iloc[0] == 100.25
    assert (others["adjusted_close"] == 100.0).all()


@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("True", "CONFIG_INVALID_FIELD"),
        ("False", "CONFIG_INVALID_FIELD"),
        ("yes", "CONFIG_INVALID_FIELD"),
        ("no", "CONFIG_INVALID_FIELD"),
        (1, "CONFIG_INVALID_FIELD"),
        (0, "CONFIG_INVALID_FIELD"),
        (1.0, "CONFIG_INVALID_FIELD"),
        (0.0, "CONFIG_INVALID_FIELD"),
        (None, "CONFIG_MISSING_FIELD"),
        (pd.NA, "CONFIG_MISSING_FIELD"),
    ],
)
def test_non_boolean_enabled_is_rejected(value, code):
    config = configuration()
    config["enabled"] = config["enabled"].astype(object)
    config.loc[config["market_id"] == "SPY", "enabled"] = value

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == code


@pytest.mark.parametrize("evaluation_date", ["2026-1-5", "2026/03/01", "2026-02-30"])
def test_malformed_evaluation_date_is_rejected(evaluation_date):
    with pytest.raises(MarketDataError) as error:
        validate_market_data(prices(), configuration(), evaluation_date)

    assert error.value.code == "DATA_INVALID_DATE"


def test_missing_price_column_is_rejected():
    frame = prices().drop(columns=["adjusted_close"])

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_INVALID_COLUMNS"


def test_extra_price_column_is_rejected():
    frame = prices().assign(volume=1)

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, configuration(), "2026-03-01")

    assert error.value.code == "DATA_INVALID_COLUMNS"


def test_required_board_market_absent_from_configuration_is_rejected():
    config = configuration()
    config = config[config["market_id"] != "QQQ"]

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_MISSING_MARKET"


def test_enabled_acwi_is_rejected():
    config = configuration()
    config.loc[config["market_id"] == "ACWI", "enabled"] = True

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_BENCHMARK_ENABLED"


def test_acwi_benchmark_must_be_acwi():
    config = configuration()
    config.loc[config["market_id"] == "ACWI", "benchmark_id"] = "SPY"

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_WRONG_BENCHMARK"


def test_object_dtype_python_bools_are_accepted():
    config = configuration()
    config["enabled"] = pd.Series(
        [market != "ACWI" for market in MARKETS],
        index=config.index,
        dtype=object,
    )
    assert config["enabled"].dtype == object
    assert all(isinstance(value, bool) for value in config["enabled"].tolist())

    validated = validate_market_data(prices(), config, "2026-03-01")

    assert len(validated) == 273 * len(MARKETS)


def test_failed_validation_does_not_mutate_caller_frames():
    frame = prices()
    frame["adjusted_close"] = frame["adjusted_close"].astype(object)
    frame.loc[0, "adjusted_close"] = "abc"
    config = configuration()
    frame_before = frame.copy(deep=True)
    config_before = config.copy(deep=True)

    with pytest.raises(MarketDataError) as error:
        validate_market_data(frame, config, "2026-03-01")

    assert error.value.code == "DATA_INVALID_PRICE"
    pd.testing.assert_frame_equal(frame, frame_before)
    pd.testing.assert_frame_equal(config, config_before)


@pytest.mark.parametrize("column", ["market_id", "display_name", "benchmark_id"])
@pytest.mark.parametrize(
    ("value", "code"),
    [
        ("", "CONFIG_MISSING_FIELD"),
        (" ", "CONFIG_MISSING_FIELD"),
        (" SPY", "CONFIG_INVALID_FIELD"),
        ("SPY ", "CONFIG_INVALID_FIELD"),
    ],
)
def test_configuration_text_is_not_repaired(column, value, code):
    config = configuration()
    config[column] = config[column].astype(object)
    config.loc[config["market_id"] == "EEM", column] = value
    before = config.copy(deep=True)

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == code
    pd.testing.assert_frame_equal(config, before)


def test_disabled_extra_market_must_use_acwi():
    extra = pd.DataFrame(
        {
            "market_id": ["GLD"],
            "display_name": ["Gold"],
            "benchmark_id": ["SPY"],
            "enabled": [False],
        }
    )
    config = pd.concat([configuration(), extra], ignore_index=True)

    with pytest.raises(MarketDataError) as error:
        validate_configuration(config)

    assert error.value.code == "CONFIG_WRONG_BENCHMARK"
