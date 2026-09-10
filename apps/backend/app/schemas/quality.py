"""Pydantic v2 Schemas for Quality Gate & False-Alarm Suppression.

SIH 2026 | Problem ID: SIH26227
Defines quality metrics, pair evaluations, gate decisions, suppression statistics,
and transparent analytical response models.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class QualityStatus(str, Enum):
    """Categorical quality tier for satellite observations."""
    USABLE = "USABLE"
    DEGRADED = "DEGRADED"
    UNRELIABLE = "UNRELIABLE"
    UNCERTAIN = "UNCERTAIN"
    INSUFFICIENT = "INSUFFICIENT"


class QualityDecision(str, Enum):
    """Decision outcome of the quality gate applied to an analytical result."""
    QUALITY_PASSED = "QUALITY_PASSED"
    QUALITY_DEGRADED = "QUALITY_DEGRADED"
    QUALITY_SUPPRESSED = "QUALITY_SUPPRESSED"
    QUALITY_REJECTED = "QUALITY_REJECTED"
    UNCERTAIN = "UNCERTAIN"


class TileQualityMetrics(BaseModel):
    """Per-tile optical and geometric quality assessment."""
    tile_id: Optional[str] = Field(None, description="Tile identifier if cataloged")
    total_pixels: int = Field(..., description="Total pixel count (H x W)")
    valid_pixels: int = Field(..., description="Non-nodata, finite pixels")
    nodata_pixels: int = Field(..., description="NoData or edge zero pixels")
    cloud_pixels: int = Field(..., description="Cloud-contaminated pixels")
    shadow_pixels: int = Field(..., description="Cloud-shadow pixels")
    saturated_pixels: int = Field(..., description="Sensor saturation pixels")
    dark_pixels: int = Field(..., description="Extremely dark non-water pixels")
    usable_pixels: int = Field(..., description="Valid pixels free from clouds, shadows, and saturation")
    nodata_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of nodata pixels")
    cloud_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of cloud pixels")
    shadow_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of shadow pixels")
    usable_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of usable pixels relative to total")
    quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall tile quality score [0.0, 1.0]")
    quality_status: QualityStatus = Field(..., description="Categorical quality tier")
    quality_flags: List[str] = Field(default_factory=list, description="Diagnostic flags")


class TemporalPairQualityMetrics(BaseModel):
    """Pair-level quality assessment across two temporal observations."""
    t1_quality: TileQualityMetrics = Field(..., description="Quality of before observation (T1)")
    t2_quality: TileQualityMetrics = Field(..., description="Quality of after observation (T2)")
    mutual_usable_pixels: int = Field(..., description="Pixels usable in BOTH T1 and T2")
    mutual_usable_fraction: float = Field(..., ge=0.0, le=1.0, description="Fraction of mutually usable pixels")
    registration_score: float = Field(..., ge=0.0, le=1.0, description="Spatial alignment quality proxy [0.0, 1.0]")
    temporal_baseline_days: Optional[float] = Field(None, description="Days between T1 and T2 acquisitions")
    pair_quality_score: float = Field(..., ge=0.0, le=1.0, description="Overall pair quality score [0.0, 1.0]")
    pair_status: QualityStatus = Field(..., description="Overall pair quality status")
    pair_flags: List[str] = Field(default_factory=list, description="Pair-level diagnostic flags")


class SuppressionBreakdown(BaseModel):
    """Granular accounting of suppressed false-alarm change pixels."""
    cloud_suppressed_pixels: int = Field(..., description="Change pixels suppressed due to cloud overlap")
    shadow_suppressed_pixels: int = Field(..., description="Change pixels suppressed due to cloud shadow overlap")
    boundary_suppressed_pixels: int = Field(..., description="Change pixels suppressed near NoData borders")
    noise_suppressed_pixels: int = Field(..., description="Isolated change pixels suppressed below area threshold")
    total_suppressed_pixels: int = Field(..., description="Total false-alarm pixels filtered")


class QualityGatedChangeRequest(BaseModel):
    """Request contract for quality-gated change detection."""
    before_tile_id: Optional[str] = Field(None, description="Catalog tile ID of before image (T1)")
    after_tile_id: Optional[str] = Field(None, description="Catalog tile ID of after image (T2)")
    before_tile_path: Optional[str] = Field(None, description="Direct file path to before GeoTIFF")
    after_tile_path: Optional[str] = Field(None, description="Direct file path to after GeoTIFF")
    threshold: Optional[float] = Field(None, ge=0.01, le=0.99, description="Spectral difference threshold")
    min_pixels: int = Field(10, ge=1, le=1000, description="Minimum contiguous pixels for valid change object")
    apply_morphology: bool = Field(True, description="Whether to apply morphological opening and closing")
    suppress_clouds: bool = Field(True, description="Suppress changes overlapping clouds in T1 or T2")
    suppress_shadows: bool = Field(True, description="Suppress changes overlapping shadows in T1 or T2")
    suppress_boundaries: bool = Field(True, description="Suppress edge artifacts near NoData boundaries")
    min_usable_fraction: float = Field(
        0.20, ge=0.05, le=0.90, description="Minimum mutual usable fraction before declaring UNCERTAIN"
    )

    @model_validator(mode="after")
    def validate_inputs(self):
        has_ids = self.before_tile_id and self.after_tile_id
        has_paths = self.before_tile_path and self.after_tile_path
        if not has_ids and not has_paths:
            raise ValueError("Must provide either (before_tile_id and after_tile_id) or (before_tile_path and after_tile_path).")
        return self


class QualityGatedChangeResponse(BaseModel):
    """Complete, transparent response payload with quality, suppression, and provenance details."""
    change_id: str = Field(..., description="Unique change detection event identifier")
    decision: QualityDecision = Field(..., description="Quality gate decision outcome")
    quality_status: QualityStatus = Field(..., description="Overall observation pair quality status")
    is_uncertain: bool = Field(..., description="True if evidence is insufficient to verify change")
    
    # Granular Scores (explicitly decoupled for analyst transparency)
    raw_change_score: float = Field(..., description="Unadjusted change score from spectral detector [0.0, 1.0]")
    pair_quality_score: float = Field(..., description="Quality score of the observation pair [0.0, 1.0]")
    final_confidence: float = Field(..., description="Quality-modulated tactical confidence [0.0, 1.0]")
    
    # Detection Metrics (Before vs. After Quality Gate)
    raw_changed_pixels: int = Field(..., description="Changed pixels detected prior to quality gating")
    verified_changed_pixels: int = Field(..., description="Changed pixels verified after false-alarm suppression")
    verified_change_percent: float = Field(..., description="Verified change percentage of mutually usable area")
    change_type: str = Field(..., description="Classified physical change taxonomy")
    
    # Detailed Diagnostic Objects
    suppression_breakdown: SuppressionBreakdown = Field(..., description="Detailed accounting of filtered pixels")
    pair_quality: TemporalPairQualityMetrics = Field(..., description="Pair quality and alignment diagnostics")
    explanation: str = Field(..., description="Structured, human-readable analyst explanation")
    
    # Artifacts & Lineage
    mask_url: str = Field(..., description="URL to download verified binary change mask PNG")
    execution_trace: Dict[str, float] = Field(..., description="Detailed millisecond latency breakdown")
    provenance: Dict[str, Any] = Field(..., description="Cryptographic lineage and configuration record")
