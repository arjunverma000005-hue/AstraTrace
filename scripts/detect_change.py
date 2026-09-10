#!/usr/bin/env python3
"""AstraTrace Baseline Change Detection CLI Tool.

SIH 2026 | Problem ID: SIH26227
Performs deterministic bitemporal satellite image differencing, pure NumPy
morphological filtering, change taxonomy classification, and mask generation.

Usage Examples:
    python scripts/detect_change.py --before data/processed/.../tile_0001.tif --after data/processed/.../tile_0001.tif
    python scripts/detect_change.py --before-tile scn_sentinel-2_20230115_96ed9480_t0001 --after-tile scn_sentinel-2_20241222_7acad713_t0001
    python scripts/detect_change.py --before-scene scn_sentinel-2_20230115_96ed9480 --after-scene scn_sentinel-2_20241222_7acad713 --tile-index 1 --json
"""
import argparse
import json
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.schemas.change import ChangeDetectionRequest, ScenePairChangeRequest
from apps.backend.app.services.change.service import ChangeDetectionService


def main():
    parser = argparse.ArgumentParser(
        description="AstraTrace Baseline Change Detection CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    # Direct raster paths
    parser.add_argument("--before", "-b", help="Path to T1 (Before) observation raster")
    parser.add_argument("--after", "-a", help="Path to T2 (After) observation raster")

    # Catalog tile IDs
    parser.add_argument("--before-tile", help="Catalog Tile ID for T1")
    parser.add_argument("--after-tile", help="Catalog Tile ID for T2")

    # Catalog scene IDs
    parser.add_argument("--before-scene", help="Catalog Scene ID for T1")
    parser.add_argument("--after-scene", help="Catalog Scene ID for T2")
    parser.add_argument("--tile-index", type=int, help="Tile index to compare when specifying scene IDs")

    # Algorithms and thresholds
    parser.add_argument("--threshold", "-t", type=float, default=None, help="Change magnitude threshold [0.01-0.99] (None = Otsu)")
    parser.add_argument("--min-pixels", "-m", type=int, default=10, help="Minimum connected component pixel size")
    parser.add_argument("--no-morphology", action="store_true", help="Disable morphological noise filtering")
    parser.add_argument("--output", "-o", help="Optional output path for change mask PNG")
    parser.add_argument("--json", action="store_true", help="Output result as raw JSON")

    args = parser.parse_args()

    try:
        with ChangeDetectionService(project_root=PROJECT_ROOT) as service:
            # Mode 1: Scene-level batch or specific tile index
            if args.before_scene and args.after_scene:
                if args.tile_index is not None:
                    # Resolve tile IDs for the specific index
                    scene1 = service.catalog.get_scene(args.before_scene)
                    scene2 = service.catalog.get_scene(args.after_scene)
                    t1_matches = [t for t in scene1.tiles if t.tile_index == args.tile_index]
                    t2_matches = [t for t in scene2.tiles if t.tile_index == args.tile_index]
                    if not t1_matches or not t2_matches:
                        print(f"[ERROR] Tile index {args.tile_index} not found in both scenes.", file=sys.stderr)
                        sys.exit(1)
                    req = ChangeDetectionRequest(
                        before_tile_id=t1_matches[0].tile_id,
                        after_tile_id=t2_matches[0].tile_id,
                        threshold=args.threshold,
                        min_component_pixels=args.min_pixels,
                        apply_morphology=not args.no_morphology,
                        generate_mask=True,
                    )
                    resp = service.detect_tile_pair(req)
                else:
                    batch_req = ScenePairChangeRequest(
                        scene_id_t1=args.before_scene,
                        scene_id_t2=args.after_scene,
                        threshold=args.threshold,
                        min_component_pixels=args.min_pixels,
                    )
                    batch_resp = service.detect_scene_pair(batch_req)
                    if args.json:
                        print(batch_resp.model_dump_json(indent=2))
                    else:
                        print("=" * 80)
                        print("ASTRATRACE BATCH SCENE PAIR CHANGE DETECTION")
                        print("=" * 80)
                        print(f"Scene T1:    {batch_resp.scene_id_t1}")
                        print(f"Scene T2:    {batch_resp.scene_id_t2}")
                        print(f"Evaluated:   {batch_resp.pairs_evaluated} tile pairs")
                        print(f"Detected:    {batch_resp.changes_detected} pairs with significant change")
                        print(f"Latency:     {batch_resp.total_execution_ms:.1f}ms")
                        print("-" * 80)
                        print(f"{'Tile':<6} {'Change Type':<24} {'Changed Px':<12} {'Change %':<10} {'Score':<8} {'Mask File'}")
                        print("-" * 80)
                        for r in batch_resp.results:
                            idx = r.before.tile_index if r.before.tile_index is not None else "N/A"
                            m = r.metrics
                            print(f"{idx:<6} {m.change_type:<24} {m.changed_pixels:<12} {m.change_percent:<10.2f} {m.composite_change_score:<8.4f} {r.mask_path}")
                        print("=" * 80)
                    sys.exit(0)

            # Mode 2: Tile IDs or direct raster paths
            elif (args.before_tile and args.after_tile) or (args.before and args.after):
                req = ChangeDetectionRequest(
                    before_tile_id=args.before_tile,
                    after_tile_id=args.after_tile,
                    before_raster_path=args.before,
                    after_raster_path=args.after,
                    threshold=args.threshold,
                    min_component_pixels=args.min_pixels,
                    apply_morphology=not args.no_morphology,
                    generate_mask=True,
                )
                resp = service.detect_tile_pair(req)
            else:
                parser.print_help()
                print("\n[ERROR] Must specify either (--before and --after) or (--before-tile and --after-tile) or (--before-scene and --after-scene).", file=sys.stderr)
                sys.exit(1)

        # Output single tile result
        if args.json:
            print(resp.model_dump_json(indent=2))
            sys.exit(0)

        print("=" * 80)
        print("ASTRATRACE BASELINE CHANGE DETECTION RESULTS")
        print("=" * 80)
        print(f"Change ID:       {resp.change_id}")
        print(f"Before (T1):     {resp.before.tile_id or resp.before.path} ({resp.before.acquired_at or 'N/A'})")
        print(f"After  (T2):     {resp.after.tile_id or resp.after.path} ({resp.after.acquired_at or 'N/A'})")
        print("-" * 80)
        m = resp.metrics
        print(f"Change Type:     {m.change_type.upper()}")
        print(f"Confidence:      {m.composite_change_score:.4f}")
        print(f"Changed Pixels:  {m.changed_pixels:,} of {m.valid_pixels:,} valid pixels ({m.change_percent:.2f}%)")
        print(f"Mean Magnitude:  {m.mean_magnitude:.4f} (Threshold: {m.effective_threshold:.4f})")
        id_means = m.index_deltas_mean
        print(f"Spectral Deltas: Delta Brightness: {id_means.get('delta_brightness', 0.0):+.3f} | Delta NDVI: {id_means.get('delta_ndvi', 0.0):+.3f} | Delta NDWI: {id_means.get('delta_ndwi', 0.0):+.3f}")
        print(f"Morphology:      Applied: {m.applied_morphology} (Min Area: {m.min_component_pixels} px)")
        print(f"Mask Artifact:   {resp.mask_path}")
        trace = resp.execution_trace
        print(f"Latency:         Total: {trace['total_ms']:.1f}ms (Preprocess: {trace['preprocess_ms']:.1f}ms, Diff: {trace['diff_ms']:.1f}ms, Morphology: {trace['morphology_ms']:.1f}ms)")
        print("=" * 80)
        sys.exit(0)

    except Exception as e:
        print(f"[ERROR] Change detection failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
