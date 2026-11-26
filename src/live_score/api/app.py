"""FastAPI application factory for the Arabic football live score platform."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from live_score.api.admin_routes import router as admin_router
from live_score.api.fixtures import build_demo_fixtures, create_catalog
from live_score.api.presenters import resolve_timezone
from live_score.api.public_routes import router as public_router
from live_score.api.security import (
    RateLimitMiddleware,
    RequestSizeLimiterMiddleware,
    SecurityHeadersMiddleware,
)
from live_score.api.store import AdminStore
from live_score.domain.models import MatchDetail

DEFAULT_ADMIN_TOKEN = "dev-admin-token"
DEFAULT_TIMEZONE = "Asia/Riyadh"
DEFAULT_DB_PATH = "data/live_score.db"


def _cors_origins() -> list[str]:
    raw = os.getenv("LIVE_SCORE_CORS_ORIGINS", "")
    if raw.strip():
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
        "https://kora-live-to.blogspot.com",
    ]


def create_app(
    fixtures: Optional[list[MatchDetail]] = None,
    db_path: Optional[str] = None,
    admin_token: Optional[str] = None,
    clock: Optional[Callable[[], datetime]] = None,
    timezone_name: Optional[str] = None,
) -> FastAPI:
    """Build an isolated app instance (tests pass fixtures + a temp SQLite file)."""

    now = (clock() if clock else datetime.now(timezone.utc))
    catalog = None
    if fixtures is not None:
        fixture_list = fixtures
    else:
        catalog = create_catalog(now)
        fixture_list = (
            catalog.fixtures(now) if catalog is not None else build_demo_fixtures(now)
        )
    fixture_map = {detail.match.id: detail for detail in fixture_list}

    resolved_db_path = db_path or os.getenv("LIVE_SCORE_DB_PATH", DEFAULT_DB_PATH)
    resolved_token = admin_token or os.getenv(
        "LIVE_SCORE_ADMIN_TOKEN", DEFAULT_ADMIN_TOKEN
    )
    resolved_timezone = timezone_name or os.getenv(
        "LIVE_SCORE_TIMEZONE", DEFAULT_TIMEZONE
    )
    resolve_timezone(resolved_timezone)  # fail fast on a bad configuration

    store = AdminStore(resolved_db_path)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            yield
        finally:
            store.close()

    app = FastAPI(
        title="Arabic Football Live Score & Streaming Platform",
        description=(
            "RTL-first football schedule, hybrid match center, multi-server streams, "
            "and admin emergency override API."
        ),
        version="1.0.0",
        lifespan=lifespan,
    )
    app.state.fixtures = fixture_map
    app.state.catalog = catalog
    app.state.store = store
    app.state.admin_token = resolved_token
    app.state.clock = clock or (lambda: datetime.now(timezone.utc))
    app.state.timezone_name = resolved_timezone

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimiterMiddleware)
    app.add_middleware(RateLimitMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_cors_origins(),
        allow_origin_regex=r"^https?://((localhost|127\.0\.0\.1)(:\d+)?|.*\.blogspot\.com|.*\.trycloudflare\.com)$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(public_router)
    app.include_router(admin_router)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, object]:
        payload: dict[str, object] = {
            "status": "ok",
            "matches": len(app.state.fixtures),
            "timezone": app.state.timezone_name,
        }
        if catalog is not None:
            payload.update(catalog.status())
        else:
            payload["data_source"] = "demo"
        return payload

    # Mount static assets and SPA fallback if frontend/dist exists
    dist_dir = Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if not dist_dir.exists():
        dist_dir = Path("frontend/dist")

    if dist_dir.exists():
        assets_dir = dist_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/", include_in_schema=False)
        def serve_index():
            return FileResponse(dist_dir / "index.html")

        @app.get("/{full_path:path}", include_in_schema=False)
        def serve_spa(full_path: str):
            if full_path.startswith("api/") or full_path == "health" or full_path.startswith("assets/"):
                raise HTTPException(status_code=404, detail="Not Found")
            candidate = dist_dir / full_path
            if candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(dist_dir / "index.html")

    return app
