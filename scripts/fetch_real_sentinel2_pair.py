#!/usr/bin/env python3
"""AstraTrace Real Sentinel-2 Level-2A Data Acquisition and Staging Utility.

SIH 2026 | Problem ID: SIH26227
Fetches genuine 10m surface reflectance bands (B02, B03, B04, B08) from the public
AWS Open Data Registry Sentinel-2 L2A COG archive for the Jewar Airport development corridor.
Performs windowed HTTP range reads (approx 12.8 MB total) without full 2.3 GB product downloads,
stacks into 4-band GeoTIFFs, embeds provenance tags, and supports offline staging.
"""
import argparse
import sys
import time
from pathlib import Path
import numpy as np
import rasterio
from rasterio.windows import Window

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# AOI Coordinates: Jewar / Noida International Airport Corridor
# EPSG:32643 Center: X=753297.10, Y=3119836.49 (Row 8020, Col 5333)
# 1024x1024 window (10.24 km x 10.24 km)
COL_OFF = 4821
ROW_OFF = 7508
WIDTH = 1024
HEIGHT = 1024
WINDOW = Window(COL_OFF, ROW_OFF, WIDTH, HEIGHT)

SCENES = {
    "BEFORE": {
        "date": "2023-02-03T05:30:29Z",
        "product_name": "S2B_MSIL2A_20230203T053029_N0509_R105_T43RGM_20230203T081251.SAFE",
        "stac_item": "S2B_43RGM_20230203_0_L2A",
        "filename": "real_s2b_20230203_jewar.tif",
        "bands": {
            1: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2023/2/S2B_43RGM_20230203_0_L2A/B02.tif",
            2: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2023/2/S2B_43RGM_20230203_0_L2A/B03.tif",
            3: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2023/2/S2B_43RGM_20230203_0_L2A/B04.tif",
            4: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2023/2/S2B_43RGM_20230203_0_L2A/B08.tif",
        },
    },
    "AFTER": {
        "date": "2024-11-29T05:32:01Z",
        "product_name": "S2A_MSIL2A_20241129T053201_N0511_R105_T43RGM_20241129T085053.SAFE",
        "stac_item": "S2A_43RGM_20241129_0_L2A",
        "filename": "real_s2a_20241129_jewar.tif",
        "bands": {
            1: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2024/11/S2A_43RGM_20241129_0_L2A/B02.tif",
            2: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2024/11/S2A_43RGM_20241129_0_L2A/B03.tif",
            3: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2024/11/S2A_43RGM_20241129_0_L2A/B04.tif",
            4: "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs/43/R/GM/2024/11/S2A_43RGM_20241129_0_L2A/B08.tif",
        },
    },
}


def download_and_stage(output_dir: Path) -> dict:
    """Extracts windowed bands from remote COGs and writes local 4-band GeoTIFFs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    generated = {}

    for key, scn in SCENES.items():
        out_path = output_dir / scn["filename"]
        if out_path.exists() and out_path.stat().st_size > 1_000_000:
            print(f"[*] {key} scene already staged: {out_path} ({out_path.stat().st_size / (1024*1024):.2f} MB)")
            generated[key] = out_path
            continue

        print(f"\n[*] Fetching {key} scene from AWS Open Data COGs ({scn['stac_item']})...")
        t0 = time.time()
        band_arrays = []
        win_transform = None
        crs = None

        for b_idx in [1, 2, 3, 4]:
            url = scn["bands"][b_idx]
            b_name = ["B02_BLUE", "B03_GREEN", "B04_RED", "B08_NIR"][b_idx - 1]
            print(f"  Reading {b_name} (HTTP range read)...")
            with rasterio.open(url) as src:
                if win_transform is None:
                    win_transform = rasterio.windows.transform(WINDOW, src.transform)
                    crs = src.crs
                arr = src.read(1, window=WINDOW)
                band_arrays.append(arr)

        stacked = np.stack(band_arrays, axis=0)
        with rasterio.open(
            out_path,
            "w",
            driver="GTiff",
            height=HEIGHT,
            width=WIDTH,
            count=4,
            dtype=stacked.dtype,
            crs=crs,
            transform=win_transform,
            nodata=0,
            compress="deflate",
        ) as dst:
            dst.write(stacked)
            dst.set_band_description(1, "B02_BLUE")
            dst.set_band_description(2, "B03_GREEN")
            dst.set_band_description(3, "B04_RED")
            dst.set_band_description(4, "B08_NIR")
            dst.update_tags(
                DATASET_TYPE="real_sentinel2_l2a",
                PLATFORM="SENTINEL-2" + ("B" if "S2B" in scn["stac_item"] else "A"),
                MGRS_TILE="43RGM",
                ACQUISITION_DATE=scn["date"],
                ORIGINAL_PRODUCT=scn["product_name"],
                STAC_ITEM=scn["stac_item"],
                SOURCE="AWS Open Data Registry Sentinel-2 L2A COG",
                AOI_DESCRIPTION="Jewar / Noida International Airport Corridor",
                PROCESSED_WINDOW=f"col_off={COL_OFF},row_off={ROW_OFF},width={WIDTH},height={HEIGHT}",
            )

        elapsed = time.time() - t0
        print(f"[OK] Staged {key} scene in {elapsed:.1f}s: {out_path} ({out_path.stat().st_size / (1024*1024):.2f} MB)")
        generated[key] = out_path

    return generated


def main():
    parser = argparse.ArgumentParser(
        description="AstraTrace Real Sentinel-2 Data Acquisition and Staging CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output-dir",
        default="data/samples/real",
        help="Local output directory for raw GeoTIFF scenes",
    )
    args = parser.parse_args()

    out_dir = PROJECT_ROOT / args.output_dir
    res = download_and_stage(out_dir)
    print("\n" + "=" * 60)
    print(" REAL SENTINEL-2 DATA STAGING COMPLETE")
    print("=" * 60)
    for k, p in res.items():
        print(f" {k:<6}: {p}")
    print("=" * 60)


if __name__ == "__main__":
    main()
