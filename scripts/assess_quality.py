#!/usr/bin/env python3
"""AstraTrace Optical Quality Assessment CLI.

SIH 2026 | Problem ID: SIH26227
Command-line utility for evaluating per-tile optical quality metrics and
bitemporal pair usability/co-registration proxies.
"""
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.services.quality.service import QualityService


def parse_args():
    parser = argparse.ArgumentParser(
        description="AstraTrace Optical Quality Assessment CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tile-id", type=str, help="Catalog tile ID for single-tile quality evaluation")
    group.add_argument("--raster-path", type=str, help="Filesystem path to GeoTIFF for single-tile evaluation")
    group.add_argument("--pair", nargs=2, metavar=("T1", "T2"), help="Pair of tile IDs or file paths for pair quality evaluation")

    parser.add_argument("--json", action="store_true", help="Output raw JSON response payload")
    return parser.parse_args()


def main():
    args = parse_args()

    with QualityService(project_root=PROJECT_ROOT) as service:
        if args.tile_id or args.raster_path:
            target = args.tile_id or args.raster_path
            metrics = service.assess_tile(target)

            if args.json:
                print(metrics.model_dump_json(indent=2))
                return

            print("=" * 60)
            print(f"ASTRATRACE OPTICAL TILE QUALITY ASSESSMENT: {target}")
            print("=" * 60)
            print(f"Status:        {metrics.quality_status.value}")
            print(f"Quality Score: {metrics.quality_score:.4f} / 1.0000")
            print(f"Total Pixels:  {metrics.total_pixels} (Valid: {metrics.valid_pixels}, NoData: {metrics.nodata_pixels})")
            print(f"Usable Pixels: {metrics.usable_pixels} ({metrics.usable_fraction * 100.0:.2f}%)")
            print(f"Clouds:        {metrics.cloud_pixels} px ({metrics.cloud_fraction * 100.0:.2f}%)")
            print(f"Shadows:       {metrics.shadow_pixels} px ({metrics.shadow_fraction * 100.0:.2f}%)")
            print(f"Saturation:    {metrics.saturated_pixels} px")
            print(f"Quality Flags: {', '.join(metrics.quality_flags) if metrics.quality_flags else 'None'}")
            print("=" * 60)

        elif args.pair:
            t1, t2 = args.pair
            metrics = service.assess_pair(t1, t2)

            if args.json:
                print(metrics.model_dump_json(indent=2))
                return

            print("=" * 60)
            print(f"ASTRATRACE TEMPORAL PAIR QUALITY ASSESSMENT")
            print("=" * 60)
            print(f"T1 (Before):       {t1} (Score: {metrics.t1_quality.quality_score:.2f}, Status: {metrics.t1_quality.quality_status.value})")
            print(f"T2 (After):        {t2} (Score: {metrics.t2_quality.quality_score:.2f}, Status: {metrics.t2_quality.quality_status.value})")
            print(f"Pair Status:       {metrics.pair_status.value}")
            print(f"Pair Quality Score:{metrics.pair_quality_score:.4f}")
            print(f"Mutual Usable Area:{metrics.mutual_usable_pixels} px ({metrics.mutual_usable_fraction * 100.0:.2f}%)")
            print(f"Co-Registration:   {metrics.registration_score:.4f}")
            if metrics.temporal_baseline_days is not None:
                print(f"Temporal Baseline: {metrics.temporal_baseline_days:.1f} days")
            print(f"Pair Flags:        {', '.join(metrics.pair_flags) if metrics.pair_flags else 'None'}")
            print("=" * 60)


if __name__ == "__main__":
    main()
