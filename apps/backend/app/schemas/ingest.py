"""Data ingestion and preprocessing schemas for AstraTrace.

SIH 2026 | Problem ID: SIH26227
"""
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class IngestRequest(BaseModel):
    """Request payload for scene ingestion."""
    source_uri: str = Field(..., description="URI or path to the source GeoTIFF file (e.g. file:///data/raw/scene.tif)")
    sensor: str = Field(..., description="Satellite sensor name (e.g. SENTINEL-2, SENTINEL-1, LANDSAT-8)")
    collection: str = Field(default="demo_archive", description="Catalog collection name")
    acquired_at: datetime = Field(..., description="ISO 8601 acquisition timestamp")
    tile_size: int = Field(default=256, ge=64, le=1024, description="Tile dimension in pixels")
    overlap: int = Field(default=25, ge=0, le=128, description="Tile overlap in pixels (approx 10%)")

    @field_validator("sensor")
    @classmethod
    def validate_sensor(cls, v: str) -> str:
        allowed = {"SENTINEL-2", "SENTINEL-1", "LANDSAT-8", "LANDSAT-9", "GENERIC_OPTICAL", "GENERIC_SAR"}
        v_upper = v.strip().upper()
        if v_upper not in allowed:
            raise ValueError(f"Sensor '{v}' not recognized. Allowed sensors: {sorted(allowed)}")
        return v_upper


class TileMetadata(BaseModel):
    """Metadata describing a single tiled image patch."""
    tile_index: int
    tile_id: str
    path: str
    bounds_wgs84: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    pixel_window: List[int] = Field(..., description="[col_off, row_off, width, height]")
    cloud_cover_percent: float
    nodata_percent: float
    checksum: str = Field(..., description="Deterministic SHA-256 hash of tile")


class IngestResponse(BaseModel):
    """Response payload returned upon successful scene ingestion."""
    scene_id: str
    sensor: str
    collection: str
    acquired_at: datetime
    crs: str
    dimensions: List[int] = Field(..., description="[width, height, bands]")
    bbox_wgs84: List[float] = Field(..., description="Scene bounding box [min_lon, min_lat, max_lon, max_lat]")
    tiles_generated: int
    manifest_path: str
    checksum: str = Field(..., description="SHA-256 hash of original raw scene")
    status: str = "INDEXED"
