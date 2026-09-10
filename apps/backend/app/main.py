"""AstraTrace FastAPI Application Entrypoint.

SIH 2026 | Problem ID: SIH26227
"""
import uuid
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
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
