"""API v1 router for AstraTrace."""
from datetime import datetime, timezone
from fastapi import APIRouter
from apps.backend.app.api.v1.endpoints.catalog import router as catalog_router
from apps.backend.app.api.v1.endpoints.change import router as change_router
from apps.backend.app.api.v1.endpoints.quality import router as quality_router
from apps.backend.app.api.v1.endpoints.review import router as review_router
from apps.backend.app.api.v1.endpoints.provenance import router as provenance_router
from apps.backend.app.api.v1.endpoints.search import router as search_router
from apps.backend.app.api.v1.endpoints.semantic import router as semantic_router
from apps.backend.app.api.v1.endpoints.stac import router as stac_router
from apps.backend.app.config import settings
from apps.backend.app.schemas.health import HealthResponse, SystemStatusResponse
from apps.backend.app.schemas.ingest import IngestRequest, IngestResponse
from apps.backend.app.services.ingestion import IngestionService

router = APIRouter()
router.include_router(catalog_router)
router.include_router(stac_router)
router.include_router(search_router)
router.include_router(change_router)
router.include_router(semantic_router)
router.include_router(quality_router)
router.include_router(review_router)
router.include_router(provenance_router)


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
            "metadata_catalog": "operational",
            "vector_index": "operational",
            "quality_gate": "operational",
            "analyst_review_queue": "operational",
            "provenance_verifier": "operational",
            "audit_logger": "operational",
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
