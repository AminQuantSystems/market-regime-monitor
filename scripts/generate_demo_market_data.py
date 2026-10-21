"""Write the bundled synthetic demonstration panel.

The sequences are fixed. There is no randomness, no clock, and no network call.
Observations are weekdays only so the demonstration does not show Saturday or
Sunday sessions. Holidays are not removed and no exchange calendar is used.
The script checks the finished file with the finance package and stops if the
board labels drift. It does not change the finance engine.
"""

from __future__ import annotations

import json
import sys
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from market_state.change import calculate_market_regime_change
from market_state.validation import validate_configuration, validate_market_data

from app.api.configuration import v1_configuration

OBSERVATIONS = 275
AS_OF_DATE = "2026-03-06"
EVALUATION_DATE = "2026-03-06"
CSV_PATH = ROOT / "app" / "demo" / "v1_market_data.csv"
METADATA_PATH = ROOT / "app" / "demo" / "metadata.json"

EXPECTED = {
    "SPY": ("Strong Up", "Positive", "Low", "Outperform", "UNCHANGED"),
    "QQQ": ("Strong Up", "Accelerating", "Elevated", "Outperform", "UNCHANGED"),
    "IWM": ("Strong Down", "Deteriorating", "High", "Strong Underperform", "UNCHANGED"),
    "EWU": ("Up", "Mixed", "Low", "Neutral", "UNCHANGED"),
    "EWG": ("Down", "Mixed", "Low", "Underperform", "UNCHANGED"),
    "EWJ": ("Neutral", "Mixed", "Normal", "Neutral", "UNCHANGED"),
    "EEM": ("Strong Down", "Deteriorating", "High", "Strong Underperform", "CHANGED"),
}


def _dates() -> list[str]:
    cursor = date.fromisoformat(AS_OF_DATE)
    if cursor.weekday() >= 5:
        raise SystemExit("demo as-of must be a Monday–Friday date")
    collected: list[date] = []
    while len(collected) < OBSERVATIONS:
        if cursor.weekday() < 5:
            collected.append(cursor)
        cursor -= timedelta(days=1)
    collected.reverse()
    return [item.isoformat() for item in collected]


def _geometric(start: float, daily: float, count: int) -> list[float]:
    price = float(start)
    values: list[float] = []
    for _ in range(count):
        values.append(round(price, 6))
        price *= daily
    return values


def _two_speed(start: float, first_daily: float, first_count: int, second_daily: float) -> list[float]:
    first = _geometric(start, first_daily, first_count)
    second = _geometric(first[-1] * second_daily, second_daily, OBSERVATIONS - first_count)
    return first + second


def _shocked(daily: float, shocks: tuple[tuple[int, float], ...]) -> list[float]:
    price = 100.0
    shock_at = dict(shocks)
    values: list[float] = []
    for index in range(OBSERVATIONS):
        if index in shock_at:
            price *= shock_at[index]
        elif index:
            price *= daily
        values.append(round(price, 6))
    return values


def _alternating_then_flat() -> list[float]:
    price = 120.0
    values: list[float] = []
    for index in range(OBSERVATIONS):
        price *= 1.008 if index % 2 == 0 else 0.9922
        values.append(round(price, 6))
    tail = 45
    return values[: OBSERVATIONS - tail] + [values[OBSERVATIONS - tail - 1]] * tail


def _last_day_drop() -> list[float]:
    first = _geometric(180.0, 0.9975, OBSERVATIONS - 25)
    second = _geometric(first[-1] * 1.0025, 1.0025, 25)
    series = first + second
    series[-1] = round(series[-1] * 0.9, 6)
    return series


def _prices() -> dict[str, list[float]]:
    return {
        "SPY": _two_speed(100.0, 1.0011, OBSERVATIONS - 21, 1.00035),
        "QQQ": _shocked(1.0003, ((80, 1.06), (160, 1.06), (260, 1.02))),
        "IWM": _two_speed(140.0, 0.9994, OBSERVATIONS - 21, 0.9988),
        "EWU": _alternating_then_flat(),
        "EWG": _two_speed(180.0, 0.9975, OBSERVATIONS - 25, 1.0025),
        "EWJ": [100.0] * OBSERVATIONS,
        "EEM": _last_day_drop(),
        "ACWI": _geometric(100.0, 1.0002, OBSERVATIONS),
    }


def _frame(prices: dict[str, list[float]]) -> pd.DataFrame:
    dates = _dates()
    rows = []
    for market_id in ("ACWI", "EEM", "EWG", "EWJ", "EWU", "IWM", "QQQ", "SPY"):
        for observed, price in zip(dates, prices[market_id], strict=True):
            rows.append({"date": observed, "market_id": market_id, "adjusted_close": f"{price:.6f}"})
    return pd.DataFrame(rows)


def _verify(csv_path: Path) -> None:
    prices = pd.read_csv(csv_path, dtype={"date": "string", "market_id": "string", "adjusted_close": "float64"})
    observed = sorted(set(prices["date"]))
    if len(observed) != OBSERVATIONS or observed[-1] != AS_OF_DATE:
        raise SystemExit("demo observations must be 275 dates ending on the fixed as-of date")
    if any(date.fromisoformat(item).weekday() >= 5 for item in observed):
        raise SystemExit("demo observations include a weekend")
    configuration = validate_configuration(v1_configuration())
    panel = validate_market_data(prices, configuration, EVALUATION_DATE)
    for market_id, expected in EXPECTED.items():
        change = calculate_market_regime_change(panel, market_id, "ACWI", AS_OF_DATE)
        snapshot = change.current_snapshot
        actual = (
            snapshot.trend.trend_state,
            snapshot.momentum.momentum_state,
            snapshot.volatility.volatility_regime,
            snapshot.relative_performance.relative_performance_state,
            change.change_status,
        )
        if actual != expected:
            raise SystemExit(f"{market_id} demo labels {actual} != {expected}")
        if market_id == "EEM" and tuple(item.dimension for item in change.transitions) != (
            "direction",
            "momentum",
            "volatility",
            "relative_performance",
        ):
            raise SystemExit("EEM demo did not change all four dimensions")


def main() -> None:
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    frame = _frame(_prices())
    frame.to_csv(CSV_PATH, index=False, lineterminator="\n")
    metadata = {
        "data_source": "demo",
        "label": "DEMO DATA",
        "evaluation_date": EVALUATION_DATE,
        "as_of_date": AS_OF_DATE,
        "description": "Synthetic weekday demonstration panel for the Market State Board. Not vendor history, not an exchange calendar, and not a live feed.",
        "synthetic": True,
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    _verify(CSV_PATH)


if __name__ == "__main__":
    main()
