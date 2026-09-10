"""AstraTrace CLI Scene Ingestion and Tiling Utility.

SIH 2026 | Problem ID: SIH26227
Executes offline GeoTIFF ingestion, CRS validation, windowed tiling,
quality metric generation, and SHA-256 provenance manifest creation.
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add project root to sys.path so backend modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.schemas.ingest import IngestRequest
from apps.backend.app.services.ingestion import IngestionService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AstraTrace Satellite Scene Ingestion CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--source",
        "-s",
        required=True,
        help="Path or URI to the raw input GeoTIFF file (e.g. data/samples/scenes/scene_2023_01_15.tif)",
    )
    parser.add_argument(
        "--sensor",
        default="SENTINEL-2",
        help="Satellite sensor (e.g. SENTINEL-2, SENTINEL-1, LANDSAT-8)",
    )
    parser.add_argument(
        "--collection",
        default="demo_archive",
        help="Target catalog collection identifier",
    )
    parser.add_argument(
        "--acquired-at",
        default=None,
        help="Acquisition ISO-8601 timestamp (e.g. 2023-01-15T10:30:00Z). Defaults to current time if omitted.",
    )
    parser.add_argument(
        "--tile-size",
        type=int,
        default=256,
        help="Tile dimension in pixels (width and height)",
    )
    parser.add_argument(
        "--overlap",
        type=int,
        default=25,
        help="Tile overlap stride in pixels",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    # Parse acquisition time
    if args.acquired_at:
        try:
            acquired_dt = datetime.fromisoformat(args.acquired_at.replace("Z", "+00:00"))
        except ValueError as e:
            print(f"Error parsing --acquired-at: {e}", file=sys.stderr)
            return 1
    else:
        acquired_dt = datetime.now(timezone.utc)

    # Construct request
    try:
        req = IngestRequest(
            source_uri=args.source,
            sensor=args.sensor,
            collection=args.collection,
            acquired_at=acquired_dt,
            tile_size=args.tile_size,
            overlap=args.overlap,
        )
    except Exception as e:
        print(f"Validation Error: {e}", file=sys.stderr)
        return 1

    # Execute ingestion service
    try:
        service = IngestionService(project_root=PROJECT_ROOT)
        result = service.ingest_scene(req)
    except Exception as e:
        print(f"Ingestion Failed: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result.model_dump(mode="json"), indent=2))
    else:
        print("=" * 60)
        print(" ASTRATRACE SCENE INGESTION COMPLETE")
        print("=" * 60)
        print(f" Scene ID:         {result.scene_id}")
        print(f" Sensor:           {result.sensor}")
        print(f" Collection:       {result.collection}")
        print(f" Acquired At:      {result.acquired_at.isoformat()}")
        print(f" CRS:              {result.crs}")
        print(f" Dimensions:       {result.dimensions[0]} x {result.dimensions[1]} ({result.dimensions[2]} bands)")
        print(f" WGS84 BBox:       {result.bbox_wgs84}")
        print(f" Tiles Generated:  {result.tiles_generated}")
        print(f" Scene Checksum:   {result.checksum}")
        print(f" Lineage Manifest: {result.manifest_path}")
        print(f" Status:           {result.status}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
