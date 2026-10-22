"""FastAPI application shell for the Market Regime Monitor adapter."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.access.frontend import install_frontend
from app.api.access.middleware import DemoAccessMiddleware
from app.api.access.rate_limit import AnalyseRateLimiter
from app.api.access.routes import register_access_routes
from app.api.access.settings import require_strong_signing_key
from app.api.errors import register_exception_handlers
from app.api.routes.analyse import router


def create_app() -> FastAPI:
    require_strong_signing_key()
    app = FastAPI(title="Market Regime Monitor")
    app.state.analyse_limiter = AnalyseRateLimiter()
    app.add_middleware(DemoAccessMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["GET", "HEAD", "POST"],
        allow_headers=["content-type"],
    )
    register_exception_handlers(app)
    register_access_routes(app)
    app.include_router(router)
    install_frontend(app)
    return app


app = create_app()
