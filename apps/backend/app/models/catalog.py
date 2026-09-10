"""SQLAlchemy Declarative Models for AstraTrace Catalog.

SIH 2026 | Problem ID: SIH26227
Stores satellite scenes and tiled image patches with spatial bounds,
acquisition dates, sensor metadata, quality metrics, and SHA-256 provenance.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from apps.backend.app.db.session import Base


def bbox_to_wkt(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> str:
    """Converts bounding box to Well-Known Text (WKT) Polygon."""
    return f"POLYGON(({min_lon} {min_lat}, {max_lon} {min_lat}, {max_lon} {max_lat}, {min_lon} {max_lat}, {min_lon} {min_lat}))"


def bbox_to_geojson_polygon(min_lon: float, min_lat: float, max_lon: float, max_lat: float) -> Dict[str, Any]:
    """Converts bounding box to GeoJSON Polygon geometry dict."""
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [min_lon, min_lat],
                [max_lon, min_lat],
                [max_lon, max_lat],
                [min_lon, max_lat],
                [min_lon, min_lat],
            ]
        ],
    }


class SceneRecord(Base):
    """Catalog table representing an ingested satellite scene."""
    __tablename__ = "scenes"

    scene_id = Column(String(128), primary_key=True, index=True)
    source_uri = Column(Text, nullable=False)
    sensor = Column(String(64), nullable=False, index=True)
    collection = Column(String(128), nullable=False, default="demo_archive", index=True)
    acquired_at = Column(DateTime(timezone=True), nullable=False, index=True)
    crs = Column(String(64), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    bands = Column(Integer, nullable=False)
    resolution_meters = Column(Float, nullable=False, default=10.0)

    # Spatial extents (EPSG:4326)
    min_lon = Column(Float, nullable=False, index=True)
    min_lat = Column(Float, nullable=False, index=True)
    max_lon = Column(Float, nullable=False, index=True)
    max_lat = Column(Float, nullable=False, index=True)
    geom = Column(Text, nullable=False)  # WKT polygon

    # Integrity & Provenance
    checksum = Column(String(64), nullable=False)  # Raw scene SHA-256
    manifest_path = Column(Text, nullable=False)
    tiles_count = Column(Integer, nullable=False)
    tile_size = Column(Integer, nullable=False, default=256)
    overlap = Column(Integer, nullable=False, default=25)
    status = Column(String(32), nullable=False, default="INDEXED")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Parent-child relation
    tiles = relationship("TileRecord", back_populates="scene", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        Index("idx_scenes_sensor_date", "sensor", "acquired_at"),
        Index("idx_scenes_spatial_bbox", "min_lon", "min_lat", "max_lon", "max_lat"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts scene record to dict."""
        return {
            "scene_id": self.scene_id,
            "source_uri": self.source_uri,
            "sensor": self.sensor,
            "collection": self.collection,
            "acquired_at": self.acquired_at.isoformat() if self.acquired_at else None,
            "crs": self.crs,
            "dimensions": [self.width, self.height, self.bands],
            "resolution_meters": self.resolution_meters,
            "bbox_wgs84": [self.min_lon, self.min_lat, self.max_lon, self.max_lat],
            "checksum": self.checksum,
            "manifest_path": self.manifest_path,
            "tiles_count": self.tiles_count,
            "tile_size": self.tile_size,
            "overlap": self.overlap,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def to_stac_item(self) -> Dict[str, Any]:
        """Serializes scene to a STAC-compatible Item representation."""
        bbox = [self.min_lon, self.min_lat, self.max_lon, self.max_lat]
        geometry = bbox_to_geojson_polygon(self.min_lon, self.min_lat, self.max_lon, self.max_lat)

        assets: Dict[str, Any] = {
            "source_raster": {
                "href": self.source_uri,
                "type": "image/tiff; application=geotiff",
                "title": "Raw Input Satellite Scene",
                "roles": ["data"],
            },
            "manifest": {
                "href": self.manifest_path,
                "type": "application/json",
                "title": "Ingestion Lineage Manifest",
                "roles": ["metadata"],
            },
        }

        # Include tile assets if loaded
        if self.tiles:
            for t in self.tiles:
                assets[f"tile_{t.tile_index:04d}"] = {
                    "href": t.path,
                    "type": "image/tiff; application=geotiff",
                    "title": f"Tile {t.tile_index}",
                    "roles": ["data", "overview"],
                    "properties": {
                        "checksum:sha256": t.checksum,
                        "cloud_cover_percent": t.cloud_cover_percent,
                        "nodata_percent": t.nodata_percent,
                    },
                }

        return {
            "type": "Feature",
            "stac_version": "1.0.0",
            "stac_extensions": [
                "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
                "https://stac-extensions.github.io/file/v2.1.0/schema.json",
            ],
            "id": self.scene_id,
            "collection": self.collection,
            "geometry": geometry,
            "bbox": bbox,
            "properties": {
                "datetime": self.acquired_at.isoformat() if self.acquired_at else None,
                "platform": self.sensor,
                "sensor": self.sensor,
                "proj:epsg": int(self.crs.replace("EPSG:", "")) if "EPSG:" in self.crs and self.crs.replace("EPSG:", "").isdigit() else None,
                "proj:shape": [self.height, self.width],
                "eo:bands": [{"name": f"B{i+1}"} for i in range(self.bands)],
                "astratrace:checksum": self.checksum,
                "astratrace:tiles_count": self.tiles_count,
                "astratrace:status": self.status,
            },
            "assets": assets,
            "links": [
                {"rel": "self", "href": f"/api/v1/stac/collections/{self.collection}/items/{self.scene_id}"},
                {"rel": "parent", "href": f"/api/v1/stac/collections/{self.collection}"},
                {"rel": "collection", "href": f"/api/v1/stac/collections/{self.collection}"},
                {"rel": "root", "href": "/api/v1/stac"},
            ],
        }


class TileRecord(Base):
    """Catalog table representing an individual tiled raster patch."""
    __tablename__ = "tiles"

    tile_id = Column(String(160), primary_key=True, index=True)
    scene_id = Column(String(128), ForeignKey("scenes.scene_id", ondelete="CASCADE"), nullable=False, index=True)
    tile_index = Column(Integer, nullable=False)
    path = Column(Text, nullable=False)

    # Spatial extents (EPSG:4326)
    min_lon = Column(Float, nullable=False, index=True)
    min_lat = Column(Float, nullable=False, index=True)
    max_lon = Column(Float, nullable=False, index=True)
    max_lat = Column(Float, nullable=False, index=True)
    geom = Column(Text, nullable=False)  # WKT polygon

    # Pixel window offsets
    col_off = Column(Integer, nullable=False)
    row_off = Column(Integer, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)

    # Quality flags & Integrity
    cloud_cover_percent = Column(Float, nullable=False, default=0.0)
    nodata_percent = Column(Float, nullable=False, default=0.0)
    checksum = Column(String(64), nullable=False)  # Tile SHA-256

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    # Relationship back to parent
    scene = relationship("SceneRecord", back_populates="tiles")

    __table_args__ = (
        Index("idx_tiles_spatial_bbox", "min_lon", "min_lat", "max_lon", "max_lat"),
        Index("idx_tiles_scene_idx", "scene_id", "tile_index"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts tile record to dict."""
        return {
            "tile_id": self.tile_id,
            "scene_id": self.scene_id,
            "tile_index": self.tile_index,
            "path": self.path,
            "bounds_wgs84": [self.min_lon, self.min_lat, self.max_lon, self.max_lat],
            "pixel_window": [self.col_off, self.row_off, self.width, self.height],
            "cloud_cover_percent": self.cloud_cover_percent,
            "nodata_percent": self.nodata_percent,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_geojson_feature(self) -> Dict[str, Any]:
        """Converts tile to GeoJSON feature."""
        return {
            "type": "Feature",
            "id": self.tile_id,
            "geometry": bbox_to_geojson_polygon(self.min_lon, self.min_lat, self.max_lon, self.max_lat),
            "bbox": [self.min_lon, self.min_lat, self.max_lon, self.max_lat],
            "properties": {
                "tile_id": self.tile_id,
                "scene_id": self.scene_id,
                "tile_index": self.tile_index,
                "path": self.path,
                "cloud_cover_percent": self.cloud_cover_percent,
                "nodata_percent": self.nodata_percent,
                "checksum": self.checksum,
            },
        }
