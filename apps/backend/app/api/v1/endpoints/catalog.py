"""API endpoints for AstraTrace metadata catalog.

SIH 2026 | Problem ID: SIH26227
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.schemas.catalog import (
    CatalogIngestRequest,
    CatalogIngestResponse,
    TileSearchRequest,
    TileSearchResponse,
)
from apps.backend.app.services.catalog import CatalogService

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.post(
    "/ingest-manifest",
    response_model=CatalogIngestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register Manifest into Catalog",
    description="Registers an ingested Milestone 2 scene and tile manifest into PostgreSQL/PostGIS. Idempotent."
)
def ingest_manifest(
    request: CatalogIngestRequest,
    db: Session = Depends(get_db),
) -> CatalogIngestResponse:
    """Consumes an ingestion manifest and stores spatial records in the database."""
    service = CatalogService(db=db)
    if request.manifest_path:
        return service.register_manifest(request.manifest_path)
    elif request.manifest_data:
        return service.register_manifest(request.manifest_data)
    else:
        from apps.backend.app.core.errors import ValidationError
        raise ValidationError("Either 'manifest_path' or 'manifest_data' must be provided.")


@router.get(
    "/scenes",
    summary="Query Catalog Scenes",
    description="Filters catalog scenes by sensor, collection, date range, and spatial bounding box."
)
def query_scenes(
    sensor: Optional[str] = Query(None, description="Satellite sensor (e.g. SENTINEL-2)"),
    collection: Optional[str] = Query(None, description="Catalog collection name"),
    date_from: Optional[datetime] = Query(None, description="Start acquisition date (ISO 8601)"),
    date_to: Optional[datetime] = Query(None, description="End acquisition date (ISO 8601)"),
    min_lon: Optional[float] = Query(None, description="Minimum longitude for bbox"),
    min_lat: Optional[float] = Query(None, description="Minimum latitude for bbox"),
    max_lon: Optional[float] = Query(None, description="Maximum longitude for bbox"),
    max_lat: Optional[float] = Query(None, description="Maximum latitude for bbox"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Returns matching scenes."""
    bbox = [min_lon, min_lat, max_lon, max_lat] if all(v is not None for v in [min_lon, min_lat, max_lon, max_lat]) else None
    service = CatalogService(db=db)
    total, scenes = service.query_scenes(
        sensor=sensor,
        collection=collection,
        date_from=date_from,
        date_to=date_to,
        bbox=bbox,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "scenes": [s.to_dict() for s in scenes],
    }


@router.get(
    "/scenes/{scene_id}",
    summary="Get Scene Record",
    description="Retrieves full scene metadata and spatial extent for a single scene."
)
def get_scene(scene_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns single scene record."""
    service = CatalogService(db=db)
    scene = service.get_scene(scene_id)
    return scene.to_dict()


@router.get(
    "/scenes/{scene_id}/tiles",
    summary="Get Scene Tiles",
    description="Lists all tiled sub-window raster patches for a scene."
)
def get_scene_tiles(scene_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns tiles for a scene."""
    service = CatalogService(db=db)
    scene = service.get_scene(scene_id)
    return {
        "scene_id": scene.scene_id,
        "tiles_count": len(scene.tiles),
        "tiles": [t.to_dict() for t in scene.tiles],
    }


@router.post(
    "/tiles/search",
    response_model=TileSearchResponse,
    summary="Search Tiles",
    description="Performs spatial bounding box or point intersection and temporal range filtering across all catalog tiles."
)
def search_tiles(
    request: TileSearchRequest,
    db: Session = Depends(get_db),
) -> TileSearchResponse:
    """Executes spatial and temporal query over tiles."""
    service = CatalogService(db=db)
    total, tiles = service.query_tiles(request)
    return TileSearchResponse(
        total=total,
        limit=request.limit,
        offset=request.offset,
        tiles=tiles,
    )
