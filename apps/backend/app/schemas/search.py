"""Pydantic v2 Schemas for Baseline Retrieval Search.

SIH 2026 | Problem ID: SIH26227
Defines request contracts, tile search result structures, and execution trace metrics.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, field_validator


class BaselineSearchRequest(BaseModel):
    """Request schema for executing a baseline satellite tile search."""
    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search text e.g. 'urban buildings near roads', 'industrial warehouses', 'forest'",
    )
    bbox: Optional[Tuple[float, float, float, float]] = Field(
        default=None,
        description="Bounding box [min_lon, min_lat, max_lon, max_lat] in EPSG:4326",
    )
    point: Optional[Tuple[float, float]] = Field(
        default=None,
        description="Single point coordinate [lon, lat] in EPSG:4326",
    )
    date_from: Optional[datetime] = Field(
        default=None,
        description="Start acquisition timestamp filter",
    )
    date_to: Optional[datetime] = Field(
        default=None,
        description="End acquisition timestamp filter",
    )
    sensor: Optional[str] = Field(
        default=None,
        description="Satellite sensor identifier (e.g. SENTINEL-2, SENTINEL-1)",
    )
    top_k: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of ranked results to return",
    )
    min_confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum baseline composite score threshold for filtering results",
    )

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: Optional[Tuple[float, float, float, float]]):
        if v is not None:
            min_lon, min_lat, max_lon, max_lat = v
            if min_lon > max_lon or min_lat > max_lat:
                raise ValueError(f"Invalid bbox coordinates: min bounds must be <= max bounds. Got {v}")
            if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
                raise ValueError(f"Longitude coordinates out of range [-180, 180]: Got [{min_lon}, {max_lon}]")
            if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
                raise ValueError(f"Latitude coordinates out of range [-90, 90]: Got [{min_lat}, {max_lat}]")
        return v


class BaselineTileResult(BaseModel):
    """Ranked tile result with score breakdown, class predictions, and provenance."""
    rank: int = Field(..., description="1-based ranking position")
    tile_id: str = Field(..., description="Unique tile identifier")
    scene_id: str = Field(..., description="Parent satellite scene identifier")
    tile_index: int = Field(..., description="Sequential tile index in parent scene")
    baseline_score: float = Field(..., description="Calibrated composite baseline score in [0.0, 1.0]")
    score_breakdown: Dict[str, float] = Field(..., description="Individual factor scores and weights")
    top_class: str = Field(..., description="Highest probability EuroSAT land-cover class")
    top_class_confidence: float = Field(..., description="Confidence of top predicted class")
    matched_classes: List[str] = Field(..., description="EuroSAT classes matching query synsets")
    bounds_wgs84: List[float] = Field(..., description="Tile geographic bounds [min_lon, min_lat, max_lon, max_lat]")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON polygon representation of tile bounds")
    acquired_at: Optional[str] = Field(default=None, description="ISO-8601 acquisition timestamp")
    sensor: str = Field(..., description="Sensor platform name")
    checksum: str = Field(..., description="SHA-256 tile data checksum")
    cloud_cover_percent: float = Field(default=0.0, description="Estimated tile cloud cover percentage")
    nodata_percent: float = Field(default=0.0, description="Tile nodata percentage")


class BaselineSearchResponse(BaseModel):
    """Complete baseline search response containing ranked tiles and execution trace."""
    query_id: str = Field(..., description="Unique query execution trace ID")
    query: str = Field(..., description="Echoed input search query")
    matched_vocabulary: Dict[str, float] = Field(..., description="EuroSAT classes and weights derived from query")
    is_out_of_vocabulary: bool = Field(..., description="Flag indicating if uniform fallback was applied")
    total_candidates: int = Field(..., description="Total candidate tiles passing spatial/temporal filters")
    returned_results: int = Field(..., description="Number of results returned after top_k and thresholding")
    results: List[BaselineTileResult] = Field(..., description="Ranked list of tile search results")
    execution_trace: Dict[str, float] = Field(..., description="Sub-millisecond latency profile (query, sql, score, total)")
