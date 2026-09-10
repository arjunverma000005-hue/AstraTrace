"""API v1 router for AstraTrace."""
from datetime import datetime, timezone
from fastapi import APIRouter
from apps.backend.app.config import settings
from apps.backend.app.schemas.health import HealthResponse, SystemStatusResponse
from apps.backend.app.schemas.ingest import IngestRequest, IngestResponse
from apps.backend.app.services.ingestion import IngestionService

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


@router.post(
    "/ingest",
    response_model=IngestResponse,
    status_code=201,
    summary="Ingest and Preprocess Scene",
    description="Validates geospatial raster, slices into georeferenced overlapping tiles, computes quality metrics, and generates a deterministic SHA-256 lineage manifest."
)
async def ingest_scene(request: IngestRequest) -> IngestResponse:
    """Ingests a satellite GeoTIFF scene, partitions into tiles, and generates provenance manifest."""
    service = IngestionService()
    return service.ingest_scene(request)


@router.get(
    "/ingest/manifest/{scene_id}",
    summary="Get Ingestion Manifest",
    description="Retrieves the full tiling and provenance manifest for an ingested satellite scene."
)
async def get_ingest_manifest(scene_id: str):
    """Returns the provenance manifest for a processed scene."""
    service = IngestionService()
    return service.get_manifest(scene_id)
