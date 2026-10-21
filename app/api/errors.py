"""HTTP error mapping. Responses never include a traceback."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from market_state.errors import MarketDataError, MarketRegimeError


class APIError(Exception):
    """A request-boundary failure with a stable adapter code."""

    def __init__(self, status_code: int, code: str, message: str, category: str = "request") -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.category = category
        super().__init__(message)


def _body(code: str, message: str, category: str) -> dict[str, dict[str, str]]:
    return {"error": {"code": code, "message": message, "category": category}}


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(APIError)
    async def api_error(_request, exc: APIError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content=_body(exc.code, exc.message, exc.category))

    @app.exception_handler(MarketDataError)
    async def market_data_error(_request, exc: MarketDataError) -> JSONResponse:
        return JSONResponse(status_code=422, content=_body(exc.code, str(exc), "market_data"))

    @app.exception_handler(MarketRegimeError)
    async def regime_error(_request, exc: MarketRegimeError) -> JSONResponse:
        return JSONResponse(status_code=500, content=_body(exc.code, str(exc), "regime"))

    @app.exception_handler(Exception)
    async def unexpected_error(_request, _exc: Exception) -> JSONResponse:
        return JSONResponse(
            status_code=500,
            content=_body("API_UNEXPECTED", "The analysis could not be completed.", "unexpected"),
        )
