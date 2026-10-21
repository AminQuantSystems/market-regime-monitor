"""Deterministic validation of local prices and market configuration.

This module does not calculate trend, momentum, volatility, benchmark relative
performance, or a directional state. It checks the input contract and returns a
canonical price table.
"""

from __future__ import annotations

import math
import re
from datetime import datetime
from numbers import Real

import pandas as pd

from market_state.errors import MarketDataError

PRICE_COLUMNS = ("date", "market_id", "adjusted_close")
CONFIG_COLUMNS = ("market_id", "display_name", "benchmark_id", "enabled")
REQUIRED_BOARD_MARKETS = ("SPY", "QQQ", "IWM", "EWU", "EWG", "EWJ", "EEM")
REQUIRED_BENCHMARK = "ACWI"
MINIMUM_OBSERVATIONS = 274
MAXIMUM_AGE_DAYS = 5
_DATE_TEXT = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def validate_configuration(configuration: pd.DataFrame) -> pd.DataFrame:
    """Return a copy of a valid configuration, sorted by market_id.

    Accepted ``enabled`` values are returned in a boolean column. Each value
    compares equal to Python ``True`` or ``False``. Text fields are not trimmed
    or rewritten. The input frame is not modified.
    """
    _require_frame(configuration, CONFIG_COLUMNS, "CONFIG_MISSING_FIELD", "CONFIG_INVALID_COLUMNS")
    config = configuration.loc[:, list(CONFIG_COLUMNS)].copy()
    _reject_duplicate_markets(config)
    _reject_invalid_config_values(config)
    _reject_universe_errors(config)
    config = config.sort_values("market_id", kind="mergesort").reset_index(drop=True)
    return config


def validate_market_data(
    prices: pd.DataFrame,
    configuration: pd.DataFrame,
    evaluation_date: str,
) -> pd.DataFrame:
    """Validate prices against the configuration and evaluation date.

    Returns a new frame with columns ``date``, ``market_id``, ``adjusted_close``,
    sorted by date and then market_id. Caller-owned frames are not modified.
    """
    config = validate_configuration(configuration)
    _require_frame(prices, PRICE_COLUMNS, "DATA_INVALID_COLUMNS", "DATA_INVALID_COLUMNS")
    frame = prices.loc[:, list(PRICE_COLUMNS)].copy()
    _validate_price_rows(frame)
    _reject_unknown_markets(frame, config)
    _reject_duplicate_dates(frame)

    required = _required_market_ids(config)
    _reject_missing_markets(frame, required)
    dates = _shared_dates(frame, required)
    if len(dates) < MINIMUM_OBSERVATIONS:
        raise MarketDataError(
            "DATA_INSUFFICIENT_HISTORY",
            f"required series have {len(dates)} observations; "
            f"at least {MINIMUM_OBSERVATIONS} are required",
        )

    latest = datetime.strptime(dates[-1], "%Y-%m-%d").date()
    as_of = _parse_date(evaluation_date, "evaluation_date")
    if latest > as_of:
        raise MarketDataError(
            "DATA_FUTURE_DATE",
            f"latest observation {dates[-1]} is later than evaluation_date {evaluation_date}",
        )
    age = (as_of - latest).days
    if age > MAXIMUM_AGE_DAYS:
        raise MarketDataError(
            "DATA_STALE",
            f"latest observation {dates[-1]} is {age} calendar days before "
            f"evaluation_date {evaluation_date}; the maximum age is {MAXIMUM_AGE_DAYS}",
        )

    canonical = frame.sort_values(["date", "market_id"], kind="mergesort").reset_index(drop=True)
    canonical["date"] = canonical["date"].astype("string")
    canonical["market_id"] = canonical["market_id"].astype("string")
    canonical["adjusted_close"] = canonical["adjusted_close"].astype("float64")
    return canonical


def _require_frame(
    frame: pd.DataFrame,
    columns: tuple[str, ...],
    missing_code: str,
    extra_code: str,
) -> None:
    if not isinstance(frame, pd.DataFrame):
        raise MarketDataError(missing_code, "expected a pandas DataFrame")
    found = list(frame.columns)
    missing = [column for column in columns if column not in found]
    if missing:
        raise MarketDataError(missing_code, f"missing columns {missing}")
    extra = [column for column in found if column not in columns]
    if extra:
        raise MarketDataError(extra_code, f"unexpected columns {extra}")


def _reject_duplicate_markets(config: pd.DataFrame) -> None:
    market_ids = config["market_id"]
    if market_ids.duplicated().any():
        duplicated = market_ids[market_ids.duplicated()].iloc[0]
        raise MarketDataError(
            "CONFIG_DUPLICATE_MARKET",
            f"duplicate market_id: {duplicated}",
        )


def _reject_invalid_config_values(config: pd.DataFrame) -> None:
    enabled: list[bool] = []
    for position in range(len(config)):
        enabled.append(_require_enabled(config["enabled"].iloc[position]))
    config["enabled"] = enabled

    for column in ("market_id", "display_name", "benchmark_id"):
        for position in range(len(config)):
            _require_config_text(config[column].iloc[position], column)


def _reject_universe_errors(config: pd.DataFrame) -> None:
    rows = {row.market_id: row for row in config.itertuples(index=False)}
    known = set(rows)
    if REQUIRED_BENCHMARK not in known:
        raise MarketDataError("CONFIG_MISSING_BENCHMARK", "ACWI is required as the V1 benchmark")

    acwi = rows[REQUIRED_BENCHMARK]
    if _require_enabled(acwi.enabled):
        raise MarketDataError(
            "CONFIG_BENCHMARK_ENABLED",
            "ACWI must have enabled = False",
        )

    for market_id in REQUIRED_BOARD_MARKETS:
        if market_id not in known:
            raise MarketDataError(
                "CONFIG_MISSING_MARKET",
                f"required board market is missing: {market_id}",
            )
        row = rows[market_id]
        if not _require_enabled(row.enabled):
            raise MarketDataError(
                "CONFIG_MARKET_DISABLED",
                f"required board market is disabled: {market_id}",
            )
        if row.benchmark_id != REQUIRED_BENCHMARK:
            raise MarketDataError(
                "CONFIG_WRONG_BENCHMARK",
                f"{market_id} must use benchmark_id ACWI, found {row.benchmark_id}",
            )

    for row in config.itertuples(index=False):
        if row.benchmark_id not in known:
            raise MarketDataError(
                "CONFIG_UNKNOWN_BENCHMARK",
                f"unknown benchmark reference: {row.benchmark_id}",
            )

    for row in config.itertuples(index=False):
        if row.benchmark_id != REQUIRED_BENCHMARK:
            raise MarketDataError(
                "CONFIG_WRONG_BENCHMARK",
                f"{row.market_id} must use benchmark_id ACWI, found {row.benchmark_id}",
            )


def _validate_price_rows(frame: pd.DataFrame) -> None:
    for row in frame.itertuples(index=False):
        _parse_date(row.date, "date")
        if not isinstance(row.market_id, str) or row.market_id == "":
            raise MarketDataError("DATA_UNKNOWN_MARKET", f"invalid market_id: {row.market_id!r}")
        _require_positive_price(row.adjusted_close, row.market_id, row.date)


def _require_positive_price(value: object, market_id: str, date_text: object) -> None:
    where = f"{market_id} on {date_text}"
    if _is_missing(value):
        raise MarketDataError("DATA_MISSING_VALUE", f"adjusted_close is missing for {where}")
    if isinstance(value, str) or isinstance(value, bool) or not isinstance(value, Real):
        raise MarketDataError("DATA_INVALID_PRICE", f"adjusted_close is not numeric for {where}")
    number = float(value)
    if math.isnan(number):
        raise MarketDataError("DATA_INVALID_PRICE", f"adjusted_close is NaN for {where}")
    if not math.isfinite(number):
        raise MarketDataError("DATA_INVALID_PRICE", f"adjusted_close is not finite for {where}")
    if number <= 0:
        raise MarketDataError(
            "DATA_INVALID_PRICE",
            f"adjusted_close must be greater than 0 for {where}",
        )


def _reject_unknown_markets(frame: pd.DataFrame, config: pd.DataFrame) -> None:
    known = set(config["market_id"])
    unknown = [market_id for market_id in frame["market_id"] if market_id not in known]
    if unknown:
        raise MarketDataError("DATA_UNKNOWN_MARKET", f"unknown market_id: {unknown[0]}")


def _reject_duplicate_dates(frame: pd.DataFrame) -> None:
    duplicated = frame.duplicated(["date", "market_id"], keep=False)
    if duplicated.any():
        row = frame.loc[duplicated].iloc[0]
        raise MarketDataError(
            "DATA_DUPLICATE_DATE",
            f"duplicate date for {row['market_id']}: {row['date']}",
        )


def _required_market_ids(config: pd.DataFrame) -> list[str]:
    enabled = set(config.loc[config["enabled"], "market_id"])
    required = enabled | set(REQUIRED_BOARD_MARKETS) | {REQUIRED_BENCHMARK}
    return sorted(required)


def _reject_missing_markets(frame: pd.DataFrame, required: list[str]) -> None:
    present = set(frame["market_id"])
    missing = [market_id for market_id in required if market_id not in present]
    if missing:
        raise MarketDataError("DATA_MISSING_MARKET", f"missing required market: {missing[0]}")


def _shared_dates(frame: pd.DataFrame, required: list[str]) -> list[str]:
    dates_by_market = {
        market_id: set(frame.loc[frame["market_id"] == market_id, "date"])
        for market_id in required
    }
    reference_id = required[0]
    reference = dates_by_market[reference_id]
    for market_id, dates in dates_by_market.items():
        if dates != reference:
            raise MarketDataError(
                "DATA_DATE_INDEX_MISMATCH",
                f"{market_id} does not share the date index of {reference_id}",
            )
    return sorted(reference)


def _parse_date(value: object, field_name: str) -> datetime.date:
    if not isinstance(value, str) or _DATE_TEXT.fullmatch(value) is None:
        raise MarketDataError("DATA_INVALID_DATE", f"{field_name} must be YYYY-MM-DD, found {value!r}")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise MarketDataError("DATA_INVALID_DATE", f"{field_name} is not a real date: {value}") from None
    return parsed.date()


def _is_missing(value: object) -> bool:
    if value is None:
        return True
    if isinstance(value, str):
        return value == ""
    return value is pd.NA or value is pd.NaT


def _semantic_enabled(value: object) -> bool | None:
    """Return a Python bool for an accepted boolean value.

    Column dtype is irrelevant. ``1 == True`` in Python, so integers and
    strings are rejected before any equality comparison.
    """
    if isinstance(value, bool):
        return bool(value)
    dtype = getattr(value, "dtype", None)
    if getattr(dtype, "kind", None) == "b":
        return bool(value)
    return None


def _require_enabled(value: object) -> bool:
    if _is_missing(value):
        raise MarketDataError("CONFIG_MISSING_FIELD", "enabled is missing")
    flag = _semantic_enabled(value)
    if flag is None:
        raise MarketDataError("CONFIG_INVALID_FIELD", f"enabled must be boolean, found {value!r}")
    return flag


def _require_config_text(value: object, column: str) -> None:
    if _is_missing(value) or (isinstance(value, str) and value.strip() == ""):
        raise MarketDataError("CONFIG_MISSING_FIELD", f"{column} is missing")
    if not isinstance(value, str) or value != value.strip():
        raise MarketDataError(
            "CONFIG_INVALID_FIELD",
            f"{column} must be a non-empty string with no surrounding whitespace",
        )
