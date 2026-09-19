"""API endpoints for AstraTrace Atomic Incremental Ingestion.

SIH 2026 | Problem ID: SIH26227
Processes new satellite GeoTIFF/COG scenes, performs georeference checks,
slices tiles, generates embeddings, and updates the vector index atomically.
"""
from pathlib import Path
import shutil
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.services.ingestion_incremental import IncrementalIngestionService

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.post(
    "",
    response_model=Dict[str, Any],
    status_code=status.HTTP_201_CREATED,
    summary="Incremental Scene Ingestion (GeoTIFF / COG)",
    description=(
        "Processes a single new satellite GeoTIFF/COG scene without rebuilding the entire database or vector index. "
        "Validates georeferencing, slices into tiles, computes quality metrics, generates vision embeddings, "
        "and atomically updates the FAISS vector index in O(N_new) time."
    ),
)
async def ingest_scene_incremental(
    file: Optional[UploadFile] = File(None, description="Uploaded GeoTIFF/COG file"),
    file_path: Optional[str] = Form(None, description="Local path to staged GeoTIFF/COG"),
    scene_id: Optional[str] = Form(None, description="Optional custom scene identifier"),
    sensor: str = Form("SENTINEL-2", description="Sensor name (e.g. SENTINEL-2, LANDSAT-9)"),
    collection: str = Form("archive", description="Collection identifier"),
    data_type: str = Form("CONTROLLED_DEMO", description="Data provenance classification"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Ingests a new satellite scene incrementally."""
    service = IncrementalIngestionService(db=db)

    if file:
        # Save uploaded file to scratch staging directory
        staging_dir = service.scratch_dir / "uploads"
        staging_dir.mkdir(parents=True, exist_ok=True)
        target_path = staging_dir / (file.filename or "upload.tif")
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        target_file_path = target_path
    elif file_path:
        target_file_path = Path(file_path)
    else:
        # Fallback to demo staging raster if neither provided
        demo_path = service.project_root / "data" / "staging" / "sample_scene.tif"
        if not demo_path.exists():
            demo_path = service.project_root / "data" / "samples" / "sample_scene.tif"
        target_file_path = demo_path

    return service.ingest_new_scene(
        raster_path=target_file_path,
        scene_id=scene_id,
        sensor=sensor,
        collection=collection,
        data_type=data_type,
    )


@router.get(
    "/history",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="Get Incremental Ingestion History",
    description="Returns the audit ledger of incremental scene additions, index latencies, and storage deltas.",
)
def get_ingestion_history(
    limit: int = Query(50, ge=1, le=100, description="Max history records to return"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Retrieves the incremental ingestion audit ledger."""
    service = IncrementalIngestionService(db=db)
    return service.get_ingestion_history(limit=limit)
