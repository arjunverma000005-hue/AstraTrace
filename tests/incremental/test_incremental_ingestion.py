"""Integration tests for AstraTrace Atomic Incremental Ingestion Engine.

SIH 2026 | Problem ID: SIH26227
"""
from pathlib import Path
import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds

from apps.backend.app.core.errors import ValidationError
from apps.backend.app.services.ingestion_incremental import IncrementalIngestionService


@pytest.fixture
def synthetic_geotiff(tmp_path: Path) -> Path:
    """Creates a valid georeferenced synthetic GeoTIFF."""
    file_path = tmp_path / "valid_test_scene.tif"
    width, height = 512, 512
    transform = from_bounds(71.0, 26.0, 71.5, 26.5, width, height)
    data = np.random.randint(10, 200, size=(3, height, width), dtype=np.uint8)

    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=3,
        dtype=np.uint8,
        crs="EPSG:4326",
        transform=transform,
    ) as dst:
        dst.write(data)

    return file_path


@pytest.fixture
def non_georeferenced_tiff(tmp_path: Path) -> Path:
    """Creates a corrupt/non-georeferenced TIFF missing CRS."""
    file_path = tmp_path / "invalid_georef.tif"
    data = np.zeros((3, 256, 256), dtype=np.uint8)
    with rasterio.open(
        file_path,
        "w",
        driver="GTiff",
        height=256,
        width=256,
        count=3,
        dtype=np.uint8,
    ) as dst:
        dst.write(data)

    return file_path


import uuid


def test_incremental_ingestion_valid_scene(synthetic_geotiff: Path):
    """Verifies incremental ingestion slices tiles, embeds, and updates FAISS atomically."""
    service = IncrementalIngestionService()
    unique_scene_id = f"TEST_INCR_{uuid.uuid4().hex[:6]}"
    try:
        res = service.ingest_new_scene(
            raster_path=synthetic_geotiff,
            scene_id=unique_scene_id,
            sensor="SENTINEL-2",
        )
        assert res["status"] == "SUCCESS"
        assert res["scenes_after"] == res["scenes_before"] + 1
        assert res["tiles_after"] > res["tiles_before"]
        assert "index_update_time_ms" in res
        assert "total_storage_bytes" in res
    finally:
        service.close()


def test_incremental_ingestion_invalid_georeferencing(non_georeferenced_tiff: Path):
    """Verifies that non-georeferenced rasters are rejected with ERR_GEOREF_INVALID."""
    service = IncrementalIngestionService()
    try:
        with pytest.raises(ValidationError, match="ERR_GEOREF_INVALID"):
            service.ingest_new_scene(
                raster_path=non_georeferenced_tiff,
                scene_id="TEST_CORRUPT_SCENE",
            )
    finally:
        service.close()
