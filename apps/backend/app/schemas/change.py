"""Pydantic v2 Schemas for Baseline Change Detection.

SIH 2026 | Problem ID: SIH26227
Defines request contracts, change metrics, provenance tracking, and response models.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class TileProvenance(BaseModel):
    """Provenance details for an individual observation tile."""
    tile_id: Optional[str] = Field(None, description="Unique tile identifier in catalog")
    scene_id: Optional[str] = Field(None, description="Parent scene identifier")
    tile_index: Optional[int] = Field(None, description="Tile index in scene grid")
    path: str = Field(..., description="Raster file path")
    acquired_at: Optional[str] = Field(None, description="Observation timestamp")
    sensor: Optional[str] = Field(None, description="Satellite sensor name")
    checksum: Optional[str] = Field(None, description="SHA-256 raster checksum")
    bounds_wgs84: Optional[List[float]] = Field(None, description="Bounding coordinates [min_lon, min_lat, max_lon, max_lat]")


class ChangeMetrics(BaseModel):
    """Quantitative change detection metrics and physical categorization."""
    total_pixels: int = Field(..., description="Total pixels in raster window")
    valid_pixels: int = Field(..., description="Pixels with valid data (excluding NoData)")
    changed_pixels: int = Field(..., description="Pixels exceeding change threshold after morphology")
    change_percent: float = Field(..., description="Percentage of valid pixels changed")
    mean_magnitude: float = Field(..., description="Mean spectral distance over changed pixels")
    composite_change_score: float = Field(..., description="Normalized confidence score in [0.0, 1.0]")
    change_type: str = Field(..., description="Physical category: construction, vegetation_loss, vegetation_gain, water_shift, no_change, unclassified")
    effective_threshold: float = Field(..., description="Otsu or user threshold applied")
    applied_morphology: bool = Field(..., description="Whether morphological noise filtering was applied")
    min_component_pixels: int = Field(..., description="Minimum connected component pixel size")
    index_deltas_mean: Dict[str, float] = Field(default_factory=dict, description="Mean Delta NDVI, Delta NDWI, Delta Brightness")


class ChangeDetectionRequest(BaseModel):
    """Request schema for comparing two satellite observations."""
    before_tile_id: Optional[str] = Field(None, description="Catalog tile ID for T1 (Before)")
    after_tile_id: Optional[str] = Field(None, description="Catalog tile ID for T2 (After)")
    before_raster_path: Optional[str] = Field(None, description="Direct file path to T1 raster")
    after_raster_path: Optional[str] = Field(None, description="Direct file path to T2 raster")
    threshold: Optional[float] = Field(None, ge=0.01, le=0.99, description="Optional manual threshold (None = Otsu)")
    min_component_pixels: int = Field(10, ge=1, le=500, description="Minimum connected component size to retain")
    apply_morphology: bool = Field(True, description="Enable morphological noise filtering")
    generate_mask: bool = Field(True, description="Save binary change mask artifact")

    @model_validator(mode="after")
    def validate_inputs(self):
        has_tile_ids = bool(self.before_tile_id and self.after_tile_id)
        has_paths = bool(self.before_raster_path and self.after_raster_path)
        if not (has_tile_ids or has_paths):
            raise ValueError("Must provide either (before_tile_id and after_tile_id) or (before_raster_path and after_raster_path).")
        return self


class ChangeDetectionResponse(BaseModel):
    """Complete change detection response with provenance, metrics, and mask URI."""
    change_id: str = Field(..., description="Unique change detection audit record ID")
    before: TileProvenance = Field(..., description="T1 observation metadata")
    after: TileProvenance = Field(..., description="T2 observation metadata")
    metrics: ChangeMetrics = Field(..., description="Quantitative change metrics")
    mask_path: Optional[str] = Field(None, description="Relative path to binary mask PNG")
    mask_url: Optional[str] = Field(None, description="API endpoint to download change mask")
    execution_trace: Dict[str, float] = Field(..., description="Latency breakdown in milliseconds")


class ScenePairChangeRequest(BaseModel):
    """Request schema for batch bitemporal comparison between two cataloged scenes."""
    scene_id_t1: str = Field(..., description="Scene ID for T1 (Before)")
    scene_id_t2: str = Field(..., description="Scene ID for T2 (After)")
    threshold: Optional[float] = Field(None, ge=0.01, le=0.99, description="Change threshold")
    min_component_pixels: int = Field(10, ge=1, le=500, description="Minimum connected component size")
    max_tiles: int = Field(20, ge=1, le=100, description="Maximum tile pairs to evaluate")


class ScenePairChangeResponse(BaseModel):
    """Batch change response for bitemporal scene pairing."""
    scene_id_t1: str = Field(..., description="T1 parent scene ID")
    scene_id_t2: str = Field(..., description="T2 parent scene ID")
    pairs_evaluated: int = Field(..., description="Total matching tile pairs evaluated")
    changes_detected: int = Field(..., description="Number of tile pairs with detectable change")
    results: List[ChangeDetectionResponse] = Field(..., description="Individual tile change results")
    total_execution_ms: float = Field(..., description="Total batch processing latency")
