"""AstraTrace Scene Ingestion and Tiling Engine.

SIH 2026 | Problem ID: SIH26227
Handles GeoTIFF inspection, path traversal protection, dimension checks,
windowed tiling, coordinate reference system reprojection bounds, and
deterministic SHA-256 provenance tracking.
"""
import hashlib
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import Window, transform as window_transform

from apps.backend.app.core.errors import ValidationError, NotFoundError
from apps.backend.app.core.logging import logger
from apps.backend.app.schemas.ingest import IngestRequest, IngestResponse, TileMetadata

# Maximum allowable dimensions to prevent decompression bombs
MAX_RASTER_DIMENSION = 15000
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB


def calculate_file_sha256(filepath: Path) -> str:
    """Computes SHA-256 checksum of a file in streaming chunks."""
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    return sha256.hexdigest()


def sanitize_source_path(source_uri: str, project_root: Path) -> Path:
    """Sanitizes and resolves the source URI, strictly preventing path traversal attacks.

    Rejects requests attempting to access files outside the project data directory.
    """
    # Strip file:// URI scheme
    clean_path_str = re.sub(r"^file:///?", "", source_uri)
    target_path = Path(clean_path_str)

    # If relative, resolve relative to project root
    if not target_path.is_absolute():
        resolved_path = (project_root / target_path).resolve()
    else:
        resolved_path = target_path.resolve()

    # Verify file exists
    if not resolved_path.exists() or not resolved_path.is_file():
        raise NotFoundError(f"Source scene file does not exist: {source_uri}")

    # Verify path is within allowed project workspace or system data directory
    allowed_base = project_root.resolve()
    try:
        resolved_path.relative_to(allowed_base)
    except ValueError:
        raise ValidationError(
            f"Security Violation: Path traversal detected. Access denied outside project boundary: {source_uri}"
        )

    # Check file size limits
    file_size = resolved_path.stat().st_size
    if file_size > MAX_FILE_SIZE_BYTES:
        raise ValidationError(
            f"File size ({file_size / (1024*1024):.1f} MB) exceeds maximum allowed threshold of 2 GB."
        )

    return resolved_path


class IngestionService:
    """Core service for satellite scene ingestion, validation, and deterministic tiling."""

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            current = Path(__file__).resolve()
            for parent in current.parents:
                if (parent / "data").is_dir() and (parent / "README.md").is_file():
                    self.project_root = parent
                    break
            else:
                self.project_root = current.parents[4]
        else:
            self.project_root = project_root

        self.processed_dir = self.project_root / "data" / "processed"
        self.processed_dir.mkdir(parents=True, exist_ok=True)

    def ingest_scene(self, request: IngestRequest) -> IngestResponse:
        """Validates raster, generates tiled patches, computes quality flags, and writes manifest."""
        logger.info(f"Starting scene ingestion for sensor {request.sensor} from {request.source_uri}")

        # 1. Path sanitization & security bounds
        resolved_path = sanitize_source_path(request.source_uri, self.project_root)

        # 2. Compute raw scene SHA-256 hash
        scene_checksum = calculate_file_sha256(resolved_path)

        # Generate unique deterministic scene ID based on sensor, date, and checksum prefix
        date_str = request.acquired_at.strftime("%Y%m%d")
        scene_id = f"scn_{request.sensor.lower()}_{date_str}_{scene_checksum[:8]}"

        # Destination directory for this scene's tiles
        scene_output_dir = self.processed_dir / scene_id
        scene_output_dir.mkdir(parents=True, exist_ok=True)

        # 3. Open raster and validate geospatial dimensions
        with rasterio.open(resolved_path) as src:
            width = src.width
            height = src.height
            count = src.count
            crs = src.crs

            if width > MAX_RASTER_DIMENSION or height > MAX_RASTER_DIMENSION:
                raise ValidationError(
                    f"Raster dimensions ({width}x{height}) exceed maximum allowed dimension of {MAX_RASTER_DIMENSION}px."
                )

            if crs is None:
                raise ValidationError(f"Raster missing valid Coordinate Reference System (CRS): {resolved_path.name}")

            # Compute WGS84 bounding box (EPSG:4326)
            try:
                minx, miny, maxx, maxy = transform_bounds(crs, "EPSG:4326", *src.bounds)
                bbox_wgs84 = [round(minx, 6), round(miny, 6), round(maxx, 6), round(maxy, 6)]
            except Exception as e:
                logger.warning(f"Could not reproject bounds to WGS84: {e}. Using raw bounds.")
                bbox_wgs84 = [round(src.bounds.left, 6), round(src.bounds.bottom, 6), round(src.bounds.right, 6), round(src.bounds.top, 6)]

            tile_size = request.tile_size
            overlap = request.overlap
            stride = tile_size - overlap

            tile_records: List[TileMetadata] = []
            tile_index = 0

            # 4. Windowed tiling loop
            for row in range(0, height, stride):
                for col in range(0, width, stride):
                    # Adjust window width/height at borders
                    actual_width = min(tile_size, width - col)
                    actual_height = min(tile_size, height - row)

                    window = Window(col_off=col, row_off=row, width=actual_width, height=actual_height)
                    tile_data = src.read(window=window)
                    tile_transform = window_transform(window, src.transform)

                    # Compute tile geographic bounds in WGS84
                    tile_raw_bounds = rasterio.windows.bounds(window, src.transform)
                    try:
                        t_minx, t_miny, t_maxx, t_maxy = transform_bounds(crs, "EPSG:4326", *tile_raw_bounds)
                        tile_bounds_wgs84 = [round(t_minx, 6), round(t_miny, 6), round(t_maxx, 6), round(t_maxy, 6)]
                    except Exception:
                        tile_bounds_wgs84 = [round(t, 6) for t in tile_raw_bounds]

                    # 5. Quality metrics calculation
                    # NoData percentage
                    nodata_val = src.nodata if src.nodata is not None else 0
                    nodata_pixels = np.count_nonzero(tile_data[0] == nodata_val)
                    total_pixels = actual_width * actual_height
                    nodata_pct = round((nodata_pixels / total_pixels) * 100.0, 2)

                    # Cloud cover estimate (for optical 4-band Sentinel-2: high reflectance in Red/Green/Blue > 2000)
                    cloud_pct = 0.0
                    if count >= 3:
                        bright_pixels = np.count_nonzero(
                            (tile_data[0] > 2000) & (tile_data[1] > 2000) & (tile_data[2] > 2000)
                        )
                        cloud_pct = round((bright_pixels / total_pixels) * 100.0, 2)

                    # 6. Write tile as georeferenced GeoTIFF
                    tile_filename = f"tile_{tile_index:04d}.tif"
                    tile_path = scene_output_dir / tile_filename

                    tile_profile = src.profile.copy()
                    tile_profile.pop("blockxsize", None)
                    tile_profile.pop("blockysize", None)
                    tile_profile.pop("tiled", None)
                    tile_profile.update({
                        "height": actual_height,
                        "width": actual_width,
                        "transform": tile_transform,
                        "compress": "deflate",
                    })

                    with rasterio.open(tile_path, "w", **tile_profile) as dst:
                        dst.write(tile_data)

                    # Compute tile checksum
                    tile_checksum = calculate_file_sha256(tile_path)

                    tile_id = f"{scene_id}_t{tile_index:04d}"
                    rel_tile_path = str(tile_path.relative_to(self.project_root)).replace("\\", "/")

                    tile_records.append(
                        TileMetadata(
                            tile_index=tile_index,
                            tile_id=tile_id,
                            path=rel_tile_path,
                            bounds_wgs84=tile_bounds_wgs84,
                            pixel_window=[col, row, actual_width, actual_height],
                            cloud_cover_percent=cloud_pct,
                            nodata_percent=nodata_pct,
                            checksum=tile_checksum,
                        )
                    )
                    tile_index += 1

        # 7. Write complete scene lineage manifest
        manifest_data = {
            "scene_id": scene_id,
            "sensor": request.sensor,
            "collection": request.collection,
            "acquired_at": request.acquired_at.isoformat(),
            "source_uri": request.source_uri,
            "crs": str(crs),
            "dimensions": [width, height, count],
            "bbox_wgs84": bbox_wgs84,
            "scene_checksum": scene_checksum,
            "tile_size": tile_size,
            "overlap": overlap,
            "tiles_count": len(tile_records),
            "ingested_at": datetime.now(timezone.utc).isoformat(),
            "tiles": [t.model_dump() for t in tile_records],
        }

        manifest_path = scene_output_dir / "manifest.json"
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)

        rel_manifest_path = str(manifest_path.relative_to(self.project_root)).replace("\\", "/")
        logger.info(f"Ingestion complete for {scene_id}: {len(tile_records)} tiles created at {rel_manifest_path}")

        return IngestResponse(
            scene_id=scene_id,
            sensor=request.sensor,
            collection=request.collection,
            acquired_at=request.acquired_at,
            crs=str(crs),
            dimensions=[width, height, count],
            bbox_wgs84=bbox_wgs84,
            tiles_generated=len(tile_records),
            manifest_path=rel_manifest_path,
            checksum=scene_checksum,
            status="INDEXED",
        )

    def get_manifest(self, scene_id: str) -> Dict[str, Any]:
        """Retrieves the ingestion manifest for a given scene ID."""
        # Sanitize scene_id against path traversal
        if not re.match(r"^[a-zA-Z0-9_\-]+$", scene_id):
            raise ValidationError(f"Invalid scene_id format: {scene_id}")

        manifest_file = self.processed_dir / scene_id / "manifest.json"
        if not manifest_file.exists() or not manifest_file.is_file():
            raise NotFoundError(f"No ingestion manifest found for scene: {scene_id}")

        with open(manifest_file, "r", encoding="utf-8") as f:
            return json.load(f)

