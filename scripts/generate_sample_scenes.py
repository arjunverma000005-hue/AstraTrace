#!/usr/bin/env python3
"""AstraTrace Sample Scene Generator.

Generates realistic georeferenced synthetic Sentinel-2 GeoTIFF scenes (bitemporal pair)
with valid geospatial transforms, CRS (UTM EPSG:32643), multispectral bands (B2, B3, B4, B8),
and ground-truth simulated structural changes for testing ingestion and change detection.
"""
import sys
from pathlib import Path
import numpy as np

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import rasterio
from rasterio.transform import from_origin


def generate_scenes(output_dir: Path):
    output_dir.mkdir(parents=True, exist_ok=True)

    width = 512
    height = 512
    bands = 4  # 1: Blue, 2: Green, 3: Red, 4: NIR (10m resolution)
    pixel_size = 10.0  # 10 meters per pixel

    # Origin in UTM Zone 43N (covers western/central India e.g. Maharashtra/Gujarat)
    # Coordinates: ~ 350000m E, 2100000m N (approx 75.5°E, 19.0°N)
    origin_x = 350000.0
    origin_y = 2100000.0
    transform = from_origin(origin_x, origin_y, pixel_size, pixel_size)
    crs = "EPSG:32643"

    # Base terrain background (vegetation + soil texture)
    np.random.seed(42)
    base_soil = np.random.uniform(300, 600, (height, width)).astype(np.uint16)
    base_veg_nir = np.random.uniform(1500, 2500, (height, width)).astype(np.uint16)

    # Road corridor running north-south through the center (low NIR, moderate red/green)
    road_mask = np.zeros((height, width), dtype=bool)
    road_mask[:, 240:272] = True  # 320m wide highway/corridor

    # -------------------------------------------------------------
    # Scene 1: T1 (Before - 2023-01-15)
    # -------------------------------------------------------------
    t1_data = np.zeros((bands, height, width), dtype=np.uint16)
    # Band 1: Blue
    t1_data[0] = (base_soil * 0.8).astype(np.uint16)
    # Band 2: Green
    t1_data[1] = (base_soil * 0.9).astype(np.uint16)
    # Band 3: Red
    t1_data[2] = base_soil
    # Band 4: NIR
    t1_data[3] = base_veg_nir

    # Road appearance in T1 (asphalt: low reflectance across all bands)
    t1_data[0, road_mask] = 400
    t1_data[1, road_mask] = 420
    t1_data[2, road_mask] = 450
    t1_data[3, road_mask] = 500

    scene1_path = output_dir / "scene_2023_01_15.tif"
    with rasterio.open(
        scene1_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype=np.uint16,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(t1_data)
        dst.set_band_description(1, "B2_BLUE")
        dst.set_band_description(2, "B3_GREEN")
        dst.set_band_description(3, "B4_RED")
        dst.set_band_description(4, "B8_NIR")

    print(f"[OK] Generated T1 Scene: {scene1_path} ({width}x{height}, 4 bands, EPSG:32643)")

    # -------------------------------------------------------------
    # Scene 2: T2 (After - 2024-12-22)
    # Adds a new industrial structure (warehouse compound) near road:
    # rows 180:240, cols 280:360 (high Red, high Blue, bright concrete roof)
    # -------------------------------------------------------------
    t2_data = t1_data.copy()

    # Structural change area
    building_mask = np.zeros((height, width), dtype=bool)
    building_mask[180:240, 280:360] = True

    # High reflectance concrete/metal roof
    t2_data[0, building_mask] = 2200  # Blue
    t2_data[1, building_mask] = 2400  # Green
    t2_data[2, building_mask] = 2600  # Red
    t2_data[3, building_mask] = 3000  # NIR

    # Subtle seasonal background drift (dry season slightly lower NIR)
    t2_data[3, ~road_mask & ~building_mask] = (
        t2_data[3, ~road_mask & ~building_mask] * 0.9
    ).astype(np.uint16)

    scene2_path = output_dir / "scene_2024_12_22.tif"
    with rasterio.open(
        scene2_path,
        "w",
        driver="GTiff",
        height=height,
        width=width,
        count=bands,
        dtype=np.uint16,
        crs=crs,
        transform=transform,
        nodata=0,
    ) as dst:
        dst.write(t2_data)
        dst.set_band_description(1, "B2_BLUE")
        dst.set_band_description(2, "B3_GREEN")
        dst.set_band_description(3, "B4_RED")
        dst.set_band_description(4, "B8_NIR")

    print(f"[OK] Generated T2 Scene: {scene2_path} ({width}x{height}, 4 bands, EPSG:32643)")


if __name__ == "__main__":
    target_dir = PROJECT_ROOT / "data/samples/scenes"
    generate_scenes(target_dir)
