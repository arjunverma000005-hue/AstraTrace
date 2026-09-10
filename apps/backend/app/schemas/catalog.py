"""Pydantic schemas for AstraTrace catalog queries and responses.

SIH 2026 | Problem ID: SIH26227
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


class CatalogIngestRequest(BaseModel):
    """Request payload to register an ingested scene manifest into the database catalog."""
    manifest_path: Optional[str] = Field(None, description="Path to manifest.json file relative to project root")
    manifest_data: Optional[Dict[str, Any]] = Field(None, description="Direct manifest dictionary payload")


class CatalogIngestResponse(BaseModel):
    """Result of registering a scene and its tiles into the catalog."""
    scene_id: str
    sensor: str
    collection: str
    tiles_registered: int
    status: str = Field(..., description="'REGISTERED', 'UPDATED', or 'SKIPPED_DUPLICATE'")
    message: str


class SceneSummary(BaseModel):
    """Summary of a registered scene in the catalog."""
    scene_id: str
    sensor: str
    collection: str
    acquired_at: datetime
    crs: str
    dimensions: List[int]
    resolution_meters: float
    bbox_wgs84: List[float]
    checksum: str
    tiles_count: int
    status: str
    created_at: datetime


class TileSearchRequest(BaseModel):
    """Spatial and temporal search request for tiled raster patches."""
    bbox: Optional[List[float]] = Field(None, description="Bounding box [min_lon, min_lat, max_lon, max_lat]")
    point: Optional[List[float]] = Field(None, description="Point coordinates [lon, lat]")
    date_from: Optional[datetime] = Field(None, description="Earliest acquisition timestamp")
    date_to: Optional[datetime] = Field(None, description="Latest acquisition timestamp")
    sensor: Optional[str] = Field(None, description="Filter by satellite sensor")
    max_cloud_cover: Optional[float] = Field(None, ge=0.0, le=100.0, description="Max allowable cloud cover percentage")
    limit: int = Field(50, ge=1, le=500, description="Maximum records to return")
    offset: int = Field(0, ge=0, description="Query offset")

    @field_validator("bbox")
    @classmethod
    def validate_bbox(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            if len(v) != 4:
                raise ValueError("bbox must contain exactly 4 numbers: [min_lon, min_lat, max_lon, max_lat]")
            min_lon, min_lat, max_lon, max_lat = v
            if min_lon > max_lon:
                raise ValueError(f"min_lon ({min_lon}) cannot be greater than max_lon ({max_lon})")
            if min_lat > max_lat:
                raise ValueError(f"min_lat ({min_lat}) cannot be greater than max_lat ({max_lat})")
        return v

    @field_validator("point")
    @classmethod
    def validate_point(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None:
            if len(v) != 2:
                raise ValueError("point must contain exactly 2 numbers: [lon, lat]")
            lon, lat = v
            if not (-180.0 <= lon <= 180.0):
                raise ValueError(f"Longitude ({lon}) must be between -180 and 180")
            if not (-90.0 <= lat <= 90.0):
                raise ValueError(f"Latitude ({lat}) must be between -90 and 90")
        return v


class TileSearchResponse(BaseModel):
    """Response payload containing matching catalog tiles."""
    total: int
    limit: int
    offset: int
    tiles: List[Dict[str, Any]]
