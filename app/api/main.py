"""FastAPI application shell for the Market Regime Monitor adapter."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_exception_handlers
from app.api.routes.analyse import router


def create_app() -> FastAPI:
    app = FastAPI(title="Market Regime Monitor")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_methods=["POST"],
        allow_headers=["content-type"],
    )
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()
