"""AstraTrace FastAPI Application Entrypoint.

SIH 2026 | Problem ID: SIH26227
"""
import sys
import uuid
from pathlib import Path

# Ensure repository root is on sys.path for monorepo namespace imports
_current_file = Path(__file__).resolve()
for _p in _current_file.parents:
    if (_p / "data").is_dir() and (_p / "apps").is_dir():
        if str(_p) not in sys.path:
            sys.path.insert(0, str(_p))
        break

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import FileResponse, JSONResponse
from starlette.staticfiles import StaticFiles
from apps.backend.app.api.v1.router import router as api_v1_router
from apps.backend.app.config import settings
from apps.backend.app.core.errors import register_error_handlers
from apps.backend.app.core.logging import logger, request_id_ctx, setup_logging


def create_app() -> FastAPI:
    """Application factory for AstraTrace backend."""
    # Initialize structured JSON logging
    setup_logging(level=settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="AstraTrace — Offline Geospatial Intelligence & Satellite AI Platform (SIH26227)",
        docs_url="/docs" if settings.app_env != "production" else None,
        redoc_url="/redoc" if settings.app_env != "production" else None,
    )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins if isinstance(settings.cors_origins, list) else [settings.cors_origins],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    # Correlation / Request ID Middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next) -> Response:
        req_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:12]}")
        token = request_id_ctx.set(req_id)
        try:
            logger.info(f"Incoming {request.method} {request.url.path}")
            response: Response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_ctx.reset(token)

    # Global Exception Handlers
    register_error_handlers(app)

    # Mount API Routers
    app.include_router(api_v1_router, prefix="/api/v1")

    # Static files & SPA routing for unified production deployment
    frontend_dist = Path(__file__).resolve().parent.parent.parent.parent / "apps" / "frontend" / "dist"
    if not frontend_dist.exists():
        frontend_dist = Path("apps/frontend/dist")

    if frontend_dist.exists() and (frontend_dist / "index.html").exists():
        assets_dir = frontend_dist / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(request: Request, full_path: str):
            if full_path.startswith("api/") or full_path in ("docs", "redoc", "openapi.json"):
                return JSONResponse(status_code=404, content={"detail": "Not Found"})
            # Content negotiation for root path: return JSON status if not browser HTML request
            if full_path == "" and "text/html" not in request.headers.get("accept", ""):
                return {
                    "app": settings.app_name,
                    "status": "online",
                    "version": settings.app_version,
                    "offline_mode": settings.offline_mode,
                    "docs": "/docs" if settings.app_env != "production" else "disabled",
                }
            target_file = frontend_dist / full_path
            if full_path and target_file.is_file():
                return FileResponse(target_file)
            return FileResponse(frontend_dist / "index.html")
    else:
        @app.get("/", tags=["Root"])
        async def root():
            """Root status ping."""
            return {
                "app": settings.app_name,
                "status": "online",
                "version": settings.app_version,
                "offline_mode": settings.offline_mode,
                "docs": "/docs" if settings.app_env != "production" else "disabled",
            }

    return app


app = create_app()
