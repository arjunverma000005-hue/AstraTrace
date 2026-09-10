"""API endpoints for AstraTrace Quality Assessment and Gating.

SIH 2026 | Problem ID: SIH26227
Provides per-tile optical quality assessment, bitemporal pair evaluation,
and transparent configuration inspection.
"""
from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import ValidationError
from apps.backend.app.db.session import get_db
from apps.backend.app.schemas.quality import (
    TemporalPairQualityMetrics,
    TileQualityMetrics,
)
from apps.backend.app.services.quality.service import QualityService

router = APIRouter(prefix="/quality", tags=["quality"])


class AssessTileRequest(BaseModel):
    """Request payload for assessing optical quality of a single tile."""
    tile_id: Optional[str] = Field(None, description="Catalog tile identifier")
    raster_path: Optional[str] = Field(None, description="Direct filesystem path to GeoTIFF raster")


class AssessPairRequest(BaseModel):
    """Request payload for assessing mutual quality across an observation pair."""
    t1_input: str = Field(..., description="T1 (before) tile ID or raster file path")
    t2_input: str = Field(..., description="T2 (after) tile ID or raster file path")


@router.post(
    "/assess-tile",
    response_model=TileQualityMetrics,
    status_code=status.HTTP_200_OK,
    summary="Assess Optical Tile Quality",
    description="Extracts optical quality metrics: nodata, cloud fraction, shadow fraction, saturation, and usable area.",
)
def assess_tile_quality(
    request: AssessTileRequest,
    db: Session = Depends(get_db),
) -> TileQualityMetrics:
    """Evaluates optical quality signals for a single satellite observation."""
    service = QualityService(db=db)
    target = request.tile_id or request.raster_path
    if not target:
        raise ValidationError("Must provide either tile_id or raster_path.")
    return service.assess_tile(target)


@router.post(
    "/assess-pair",
    response_model=TemporalPairQualityMetrics,
    status_code=status.HTTP_200_OK,
    summary="Assess Temporal Observation Pair Quality",
    description="Evaluates pair quality, mutual usable area intersection, co-registration proxy, and temporal baseline.",
)
def assess_pair_quality(
    request: AssessPairRequest,
    db: Session = Depends(get_db),
) -> TemporalPairQualityMetrics:
    """Evaluates mutual usability and alignment between two temporal observations."""
    service = QualityService(db=db)
    return service.assess_pair(request.t1_input, request.t2_input)


@router.get(
    "/config",
    status_code=status.HTTP_200_OK,
    summary="Get Quality Gate Thresholds & Configuration",
    description="Returns active quality thresholds, bounding ranges, and operational constants.",
)
def get_quality_config() -> Dict[str, Any]:
    """Exposes all active quality thresholds and bounds for auditability."""
    return {
        "gate_version": "1.0.0",
        "thresholds": {
            "cloud_vis_threshold": 0.35,
            "cloud_nir_threshold": 0.30,
            "cloud_whiteness_tolerance": 0.25,
            "shadow_nir_threshold": 0.12,
            "shadow_vis_threshold": 0.10,
            "saturation_threshold": 0.98,
            "min_usable_fraction_default": 0.20,
            "high_quality_cutoff": 0.80,
            "unreliable_quality_cutoff": 0.35,
            "insufficient_quality_cutoff": 0.10,
        },
        "supported_signals": [
            "nodata_fraction",
            "cloud_contamination",
            "cloud_shadow",
            "sensor_saturation",
            "extreme_darkness",
            "usable_area_fraction",
            "mutual_usable_intersection",
            "coregistration_edge_gradient_proxy",
            "temporal_baseline_suitability",
        ],
    }
