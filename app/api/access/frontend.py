"""Optional production hosting of the compiled Vite application."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.access.settings import serve_frontend


def install_frontend(app: FastAPI) -> None:
    if not serve_frontend():
        return
    dist = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    index = dist / "index.html"
    if not index.is_file():
        raise RuntimeError("MEEM_SERVE_FRONTEND is enabled but the compiled frontend is missing.")
    assets = dist / "assets"
    brand = dist / "brand"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="frontend-assets")
    if brand.is_dir():
        app.mount("/brand", StaticFiles(directory=brand), name="frontend-brand")

    def spa() -> FileResponse:
        return FileResponse(index)

    app.add_api_route("/access", spa, methods=["GET"], include_in_schema=False)
    app.add_api_route("/privacy", spa, methods=["GET"], include_in_schema=False)
    app.add_api_route("/", spa, methods=["GET"], include_in_schema=False)
