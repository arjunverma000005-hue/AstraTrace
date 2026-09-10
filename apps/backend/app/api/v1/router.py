"""API v1 router for AstraTrace."""
from datetime import datetime, timezone
from fastapi import APIRouter
from apps.backend.app.config import settings
from apps.backend.app.schemas.health import HealthResponse, SystemStatusResponse

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description="Returns the operational health status and core configuration flags of AstraTrace."
)
async def health_check() -> HealthResponse:
    """Returns basic service health and offline mode status."""
    return HealthResponse(
        status="healthy",
        app=settings.app_name,
        version=settings.app_version,
        offline_mode=settings.offline_mode,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    summary="System Status",
    description="Provides detailed operational status of backend services without exposing sensitive configurations."
)
async def system_status() -> SystemStatusResponse:
    """Returns environment profile and service health mappings."""
    return SystemStatusResponse(
        status="operational",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        offline_mode=settings.offline_mode,
        services={
            "api": "healthy",
            "metadata_catalog": "staged",
            "vector_index": "staged",
            "storage": "local_filesystem",
        },
        timestamp=datetime.now(timezone.utc),
    )
