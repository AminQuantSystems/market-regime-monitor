"""Board analysis route. Finance calls go to market_state unchanged."""

from __future__ import annotations

from fastapi import APIRouter, File, Form, UploadFile

from market_state.change import calculate_market_regime_change
from market_state.validation import REQUIRED_BENCHMARK, REQUIRED_BOARD_MARKETS, validate_configuration, validate_market_data

from app.api.configuration import v1_configuration
from app.api.errors import APIError
from app.api.input import load_demo_csv, load_demo_metadata, read_upload, require_iso_date
from app.api.mapping import market_dto
from app.api.schemas import BoardResponse

router = APIRouter()


@router.post("/api/v1/market-regime/analyse", response_model=BoardResponse)
async def analyse(
    data_source: str = Form(...),
    evaluation_date: str = Form(...),
    as_of_date: str = Form(...),
    prices: UploadFile | None = File(None),
) -> BoardResponse:
    if data_source not in {"demo", "upload"}:
        raise APIError(400, "API_INVALID_DATA_SOURCE", "data_source must be demo or upload")
    evaluation_date = require_iso_date(evaluation_date, "evaluation_date")
    as_of_date = require_iso_date(as_of_date, "as_of_date")
    if data_source == "demo":
        frame = load_demo_csv()
        label = str(load_demo_metadata()["label"])
    else:
        frame = await read_upload(prices)
        label = None

    configuration = validate_configuration(v1_configuration())
    panel = validate_market_data(frame, configuration, evaluation_date)
    names = {
        str(row.market_id): str(row.display_name)
        for row in configuration.itertuples(index=False)
    }
    markets = [
        market_dto(
            calculate_market_regime_change(panel, market_id, REQUIRED_BENCHMARK, as_of_date),
            names[market_id],
        )
        for market_id in REQUIRED_BOARD_MARKETS
    ]
    return BoardResponse(
        as_of_date=as_of_date,
        evaluation_date=evaluation_date,
        benchmark_id=REQUIRED_BENCHMARK,
        universe_size=len(markets),
        validation_status="VALID",
        data_source=data_source,
        data_label=label,
        markets=markets,
    )
