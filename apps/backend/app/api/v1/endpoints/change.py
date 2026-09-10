"""API endpoints for AstraTrace baseline change detection.

SIH 2026 | Problem ID: SIH26227
Provides bitemporal satellite image differencing, scene pairing, and mask retrieval.
"""
from pathlib import Path
from fastapi import APIRouter, Depends, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError
from apps.backend.app.db.session import get_db
from apps.backend.app.schemas.change import (
    ChangeDetectionRequest,
    ChangeDetectionResponse,
    ScenePairChangeRequest,
    ScenePairChangeResponse,
)
from apps.backend.app.schemas.quality import (
    QualityGatedChangeRequest,
    QualityGatedChangeResponse,
)
from apps.backend.app.services.change.service import ChangeDetectionService

router = APIRouter(prefix="/change", tags=["change"])


@router.post(
    "/detect",
    response_model=ChangeDetectionResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect Change Between Observation Pair",
    description=(
        "Executes deterministic baseline change detection between two co-registered observation tiles. "
        "Computes normalized Euclidean spectral difference, index deltas (Delta NDVI, Delta NDWI, Delta Brightness), "
        "applies pure-NumPy morphological noise filtering, and classifies the physical change type."
    ),
)
def detect_change(
    request: ChangeDetectionRequest,
    db: Session = Depends(get_db),
) -> ChangeDetectionResponse:
    """Compares two observation tiles and returns metrics, physical taxonomy, and mask URI."""
    service = ChangeDetectionService(db=db)
    return service.detect_tile_pair(request)


@router.post(
    "/scene-pair",
    response_model=ScenePairChangeResponse,
    status_code=status.HTTP_200_OK,
    summary="Batch Change Detection Between Two Scenes",
    description=(
        "Automatically discovers, pairs, and analyzes all overlapping tiles between two cataloged scenes. "
        "Enforces chronological temporal ordering (T1 before T2) and returns batch metrics."
    ),
)
def detect_scene_pair(
    request: ScenePairChangeRequest,
    db: Session = Depends(get_db),
) -> ScenePairChangeResponse:
    """Evaluates all co-located tile pairs across two cataloged scenes."""
    service = ChangeDetectionService(db=db)
    return service.detect_scene_pair(request)


@router.post(
    "/detect-gated",
    response_model=QualityGatedChangeResponse,
    status_code=status.HTTP_200_OK,
    summary="Detect Change with Quality Gate & False-Alarm Suppression",
    description=(
        "Executes quality assessment, baseline change detection, and false-alarm suppression. "
        "Suppresses false alarms from clouds, shadows, and boundary artifacts, assigns explicit "
        "uncertainty states, and returns transparent quality and confidence breakdowns."
    ),
)
def detect_gated_change(
    request: QualityGatedChangeRequest,
    db: Session = Depends(get_db),
) -> QualityGatedChangeResponse:
    """Evaluates observation pair with quality gating, false-alarm suppression, and confidence calibration."""
    from apps.backend.app.services.quality.service import QualityService
    service = QualityService(db=db)
    return service.detect_gated_change(request)


@router.get(
    "/mask/{change_id}",
    summary="Download Change Mask Image",
    description="Retrieves the generated binary change mask PNG for an analyzed observation pair.",
)
def get_change_mask(
    change_id: str,
) -> FileResponse:
    """Returns the binary change mask PNG image file."""
    # Prevent path traversal in change_id
    valid_prefix = change_id.startswith("chg_") or change_id.startswith("qchg_")
    clean_part = change_id.replace("chg_", "").replace("qchg_", "")
    if not valid_prefix or not clean_part.isalnum():
        raise NotFoundError(f"Invalid change ID format: {change_id}")

    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").is_dir() and (parent / "README.md").is_file():
            project_root = parent
            break
    else:
        project_root = current.parents[4]

    changes_dir = project_root / "data" / "processed" / "changes"
    # Check possible filename patterns
    candidates = [
        changes_dir / f"{change_id}.png",
        changes_dir / f"{change_id}_verified_mask.png",
        changes_dir / f"{change_id}_mask.png",
    ]
    mask_path = next((p for p in candidates if p.exists() and p.is_file()), None)
    if not mask_path:
        raise NotFoundError(f"Change mask not found for ID: {change_id}")

    return FileResponse(mask_path, media_type="image/png", filename=f"{change_id}_mask.png")
