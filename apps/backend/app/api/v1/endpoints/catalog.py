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


@router.get(
    "/tiles/{tile_id}/preview",
    summary="Get Tile RGB Preview Image",
    description="Generates or retrieves a contrast-stretched 8-bit RGB preview PNG for a cataloged satellite tile.",
)
def get_tile_preview(
    tile_id: str,
    db: Session = Depends(get_db),
):
    """Returns an 8-bit RGB PNG preview for visual tactical inspection."""
    import re
    from pathlib import Path
    from fastapi.responses import FileResponse
    import numpy as np
    from PIL import Image
    import rasterio
    from apps.backend.app.core.errors import NotFoundError, ValidationError
    from apps.backend.app.models.catalog import TileRecord

    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", tile_id):
        raise ValidationError(f"Invalid tile ID format: {tile_id}")

    tile = db.query(TileRecord).filter(TileRecord.tile_id == tile_id).first()
    if not tile:
        raise NotFoundError(f"Tile '{tile_id}' not found in catalog.")

    # Locate project root
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").is_dir() and (parent / "README.md").is_file():
            project_root = parent
            break
    else:
        project_root = current.parents[4]

    thumb_dir = project_root / "data" / "processed" / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / f"{tile_id}.png"

    if not thumb_path.exists():
        # Resolve raster path
        r_path = Path(tile.path)
        if not r_path.is_absolute():
            r_path = (project_root / r_path).resolve()

        if not r_path.exists():
            raise NotFoundError(f"Raster file not found on disk: {tile.path}")

        with rasterio.open(r_path) as src:
            count = src.count
            if count >= 4:
                # Sentinel-2: Band 1=Blue, Band 2=Green, Band 3=Red, Band 4=NIR (or B2, B3, B4, B8)
                # Map Red=3, Green=2, Blue=1
                r = src.read(3).astype(np.float32)
                g = src.read(2).astype(np.float32)
                b = src.read(1).astype(np.float32)
            elif count == 3:
                r = src.read(1).astype(np.float32)
                g = src.read(2).astype(np.float32)
                b = src.read(3).astype(np.float32)
            else:
                gray = src.read(1).astype(np.float32)
                r = g = b = gray

            # Percentile stretch (2% to 98%)
            def stretch(ch: np.ndarray) -> np.ndarray:
                p2, p98 = np.percentile(ch, (2, 98))
                if p98 > p2:
                    clipped = np.clip((ch - p2) / (p98 - p2), 0.0, 1.0)
                else:
                    clipped = np.clip(ch / (ch.max() or 1.0), 0.0, 1.0)
                return (clipped * 255.0).astype(np.uint8)

            rgb_arr = np.stack([stretch(r), stretch(g), stretch(b)], axis=-1)
            img = Image.fromarray(rgb_arr, mode="RGB")
            img.save(thumb_path, format="PNG")

    return FileResponse(thumb_path, media_type="image/png", filename=f"{tile_id}_rgb.png")


@router.get(
    "/scenes/{scene_id}/preview",
    summary="Get Scene RGB Full Preview Image",
    description="Generates or retrieves a contrast-stretched 8-bit RGB preview PNG for a complete satellite analysis scene.",
)
def get_scene_preview(
    scene_id: str,
    db: Session = Depends(get_db),
):
    """Returns an 8-bit RGB PNG preview for the full georeferenced scene analysis window."""
    import re
    from pathlib import Path
    from fastapi.responses import FileResponse
    import numpy as np
    from PIL import Image
    import rasterio
    from apps.backend.app.core.errors import NotFoundError, ValidationError
    from apps.backend.app.models.catalog import SceneRecord

    if ".." in scene_id or not re.match(r"^[a-zA-Z0-9_\-\.]+$", scene_id):
        raise ValidationError(f"Invalid scene ID format: {scene_id}")

    scene = db.query(SceneRecord).filter(SceneRecord.scene_id == scene_id).first()
    if not scene:
        raise NotFoundError(f"Scene '{scene_id}' not found in catalog.")

    # Locate project root
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").is_dir() and (parent / "README.md").is_file():
            project_root = parent
            break
    else:
        project_root = current.parents[4]

    thumb_dir = project_root / "data" / "processed" / "thumbnails"
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / f"{scene_id}_full.png"

    if not thumb_path.exists():
        r_path = Path(scene.source_uri)
        if not r_path.is_absolute():
            r_path = (project_root / r_path).resolve()

        if not r_path.exists():
            raise NotFoundError(f"Scene raster file not found on disk: {scene.source_uri}")

        with rasterio.open(r_path) as src:
            count = src.count
            if count >= 4:
                # Sentinel-2: Band 1=Blue, Band 2=Green, Band 3=Red, Band 4=NIR (or B2, B3, B4, B8)
                # Map Red=3, Green=2, Blue=1
                r = src.read(3).astype(np.float32)
                g = src.read(2).astype(np.float32)
                b = src.read(1).astype(np.float32)
            elif count == 3:
                r = src.read(1).astype(np.float32)
                g = src.read(2).astype(np.float32)
                b = src.read(3).astype(np.float32)
            else:
                gray = src.read(1).astype(np.float32)
                r = g = b = gray

            # Percentile stretch (2% to 98%)
            def stretch(ch: np.ndarray) -> np.ndarray:
                p2, p98 = np.percentile(ch, (2, 98))
                if p98 > p2:
                    clipped = np.clip((ch - p2) / (p98 - p2), 0.0, 1.0)
                else:
                    clipped = np.clip(ch / (ch.max() or 1.0), 0.0, 1.0)
                return (clipped * 255.0).astype(np.uint8)

            rgb_arr = np.stack([stretch(r), stretch(g), stretch(b)], axis=-1)
            img = Image.fromarray(rgb_arr, mode="RGB")
            img.save(thumb_path, format="PNG")

    return FileResponse(thumb_path, media_type="image/png", filename=f"{scene_id}_rgb.png")


