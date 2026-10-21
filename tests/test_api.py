"""HTTP contract for the board adapter. Expected finance values come from market_state."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from market_state.change import calculate_market_regime_change
from market_state.validation import validate_market_data

from app.api.configuration import v1_configuration
from app.api.input import DEMO_CSV, MAX_UPLOAD_BYTES
from app.api.main import create_app

DEMO_AS_OF = "2026-03-06"
DEMO_DATES = {"data_source": "demo", "evaluation_date": DEMO_AS_OF, "as_of_date": DEMO_AS_OF}
ORDER = ("SPY", "QQQ", "IWM", "EWU", "EWG", "EWJ", "EEM")
NAMES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "EWU": "UK Equities",
    "EWG": "Germany Equities",
    "EWJ": "Japan Equities",
    "EEM": "Emerging Markets",
}


def _client() -> TestClient:
    return TestClient(create_app(), raise_server_exceptions=False)


def _json_number(value: float) -> float:
    return json.loads(json.dumps(value))


def test_demo_board_matches_finance_core() -> None:
    response = _client().post("/api/v1/market-regime/analyse", data=DEMO_DATES)
    assert response.status_code == 200
    body = response.json()
    assert body["benchmark_id"] == "ACWI"
    assert body["universe_size"] == 7
    assert body["validation_status"] == "VALID"
    assert body["data_source"] == "demo"
    assert body["data_label"] == "DEMO DATA"
    assert body["as_of_date"] == DEMO_AS_OF
    assert body["evaluation_date"] == DEMO_AS_OF
    assert [market["market_id"] for market in body["markets"]] == list(ORDER)
    assert "ACWI" not in [market["market_id"] for market in body["markets"]]

    prices = pd.read_csv(DEMO_CSV, dtype={"date": "string", "market_id": "string", "adjusted_close": "float64"})
    observed = sorted(set(prices["date"]))
    assert len(observed) == 275
    assert observed[0] == "2025-02-17"
    assert observed[-1] == DEMO_AS_OF
    assert all(date.fromisoformat(item).weekday() < 5 for item in observed)
    panel = validate_market_data(prices, v1_configuration(), DEMO_AS_OF)
    for market in body["markets"]:
        assert market["display_name"] == NAMES[market["market_id"]]
        change = calculate_market_regime_change(panel, market["market_id"], "ACWI", DEMO_AS_OF)
        snapshot = change.current_snapshot
        current = market["current"]
        assert current["trend"]["trend_state"] == snapshot.trend.trend_state
        assert current["trend"]["reason_code"] == snapshot.trend.reason_code
        assert current["trend"]["sma_50"] == _json_number(snapshot.trend.sma_50)
        assert current["trend"]["sma_200"] == _json_number(snapshot.trend.sma_200)
        assert current["trend"]["adjusted_close"] == _json_number(snapshot.trend.adjusted_close)
        assert current["momentum"]["momentum_state"] == snapshot.momentum.momentum_state
        assert current["momentum"]["reason_code"] == snapshot.momentum.reason_code
        assert current["momentum"]["return_21"] == _json_number(snapshot.momentum.return_21)
        assert current["momentum"]["return_63"] == _json_number(snapshot.momentum.return_63)
        assert current["momentum"]["pace_21"] == _json_number(snapshot.momentum.pace_21)
        assert current["momentum"]["pace_63"] == _json_number(snapshot.momentum.pace_63)
        assert current["volatility"]["volatility_regime"] == snapshot.volatility.volatility_regime
        assert current["volatility"]["reason_code"] == snapshot.volatility.reason_code
        assert current["volatility"]["realized_volatility_21"] == _json_number(snapshot.volatility.realized_volatility_21)
        assert current["volatility"]["historical_percentile"] == _json_number(snapshot.volatility.historical_percentile)
        relative = current["relative_performance"]
        assert relative["relative_performance_state"] == snapshot.relative_performance.relative_performance_state
        assert relative["reason_code"] == snapshot.relative_performance.reason_code
        assert relative["active_return_63"] == _json_number(snapshot.relative_performance.active_return_63)
        assert relative["benchmark_id"] == "ACWI"
        assert market["change"]["status"] == change.change_status
        assert market["change"]["reason_code"] == change.reason_code
        assert market["change"]["previous_as_of_date"] == change.previous_as_of_date
        assert market["change"]["transitions"] == [
            {
                "dimension": transition.dimension,
                "previous_state": transition.previous_state,
                "current_state": transition.current_state,
            }
            for transition in change.transitions
        ]
        assert "previous_snapshot" not in market["change"]
    text = response.text
    assert "Traceback" not in text
    assert "colour" not in text
    assert "color" not in text


def test_invalid_data_source() -> None:
    response = _client().post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "live"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "API_INVALID_DATA_SOURCE"


def test_upload_requires_a_file() -> None:
    response = _client().post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "API_FILE_REQUIRED"


def test_upload_of_the_same_bytes_matches_demo_finance() -> None:
    client = _client()
    demo = client.post("/api/v1/market-regime/analyse", data=DEMO_DATES)
    upload = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("v1_market_data.csv", Path(DEMO_CSV).read_bytes(), "text/csv")},
    )
    assert demo.status_code == 200
    assert upload.status_code == 200
    demo_body = demo.json()
    upload_body = upload.json()
    assert demo_body["data_source"] == "demo"
    assert demo_body["data_label"] == "DEMO DATA"
    assert upload_body["data_source"] == "upload"
    assert upload_body["data_label"] is None
    assert upload_body["markets"] == demo_body["markets"]
    assert upload_body["as_of_date"] == demo_body["as_of_date"]
    assert upload_body["evaluation_date"] == demo_body["evaluation_date"]
    assert upload_body["benchmark_id"] == demo_body["benchmark_id"]
    assert upload_body["validation_status"] == demo_body["validation_status"]


def test_upload_rejects_oversized_content() -> None:
    payload = b"a" * (MAX_UPLOAD_BYTES + 1)
    response = _client().post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("prices.csv", payload, "text/csv")},
    )
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "API_FILE_TOO_LARGE"
    assert "Traceback" not in response.text


def test_upload_rejects_unsupported_media_and_binary() -> None:
    client = _client()
    media = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("prices.csv", b"date,market_id,adjusted_close\n", "image/png")},
    )
    assert media.status_code == 415
    assert media.json()["error"]["code"] == "API_UNSUPPORTED_MEDIA_TYPE"
    binary = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("prices.csv", b"date\x00market", "text/csv")},
    )
    assert binary.status_code == 400
    assert binary.json()["error"]["code"] == "API_INVALID_CSV"


def test_upload_rejects_invalid_utf8_and_ragged_csv() -> None:
    client = _client()
    utf8 = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("prices.csv", b"\xff", "text/csv")},
    )
    assert utf8.status_code == 400
    assert utf8.json()["error"]["code"] == "API_INVALID_UTF8"
    ragged = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("prices.csv", b"date,market_id,adjusted_close\n2026-03-01,SPY\n", "text/csv")},
    )
    assert ragged.status_code == 400
    assert ragged.json()["error"]["code"] == "API_INVALID_CSV"


def test_finance_error_code_is_preserved() -> None:
    csv_text = "date,market_id,adjusted_close\n2026-03-01,SPY,not-a-price\n"
    response = _client().post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "data_source": "upload"},
        files={"prices": ("prices.csv", csv_text, "text/csv")},
    )
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "DATA_INVALID_PRICE"
    assert error["category"] == "market_data"
    assert "Traceback" not in response.text


def test_invalid_dates_stay_explicit() -> None:
    client = _client()
    malformed = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "evaluation_date": "01/03/2026"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["error"]["code"] == "API_INVALID_DATE_FORMAT"
    future = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "evaluation_date": "1999-01-01"},
    )
    assert future.status_code == 422
    assert future.json()["error"]["code"] == "DATA_FUTURE_DATE"
    missing = client.post(
        "/api/v1/market-regime/analyse",
        data={**DEMO_DATES, "as_of_date": "2020-01-01"},
    )
    assert missing.status_code == 422
    assert missing.json()["error"]["code"] == "DATA_INVALID_DATE"


def test_unexpected_exception_hides_the_traceback(monkeypatch: pytest.MonkeyPatch) -> None:
    def explode(*_args, **_kwargs):
        raise RuntimeError("secret panel path C:/private/prices.csv")

    monkeypatch.setattr("app.api.routes.analyse.calculate_market_regime_change", explode)
    response = _client().post("/api/v1/market-regime/analyse", data=DEMO_DATES)
    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "API_UNEXPECTED"
    assert error["category"] == "unexpected"
    assert "Traceback" not in response.text
    assert "secret panel" not in response.text
    assert "RuntimeError" not in response.text


def test_adapter_source_has_no_finance_formula() -> None:
    root = Path(__file__).resolve().parents[1] / "app"
    source = "\n".join(path.read_text(encoding="utf-8") for path in root.rglob("*.py"))
    for token in ("math.log", "expm1", "CLASSIFICATION_TOLERANCE", "SMA_50_WINDOW", "datetime.now", "date.today"):
        assert token not in source
