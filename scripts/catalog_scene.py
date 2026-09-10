"""CLI Utility to Register Ingested Scene Manifests into AstraTrace Catalog.

SIH 2026 | Problem ID: SIH26227
"""
import argparse
import json
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.db.session import init_db
from apps.backend.app.services.catalog import CatalogService


def main() -> int:
    parser = argparse.ArgumentParser(
        description="AstraTrace Scene Catalog Registration CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--manifest",
        "-m",
        required=True,
        help="Path to the scene manifest.json file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    # Ensure database tables exist
    init_db()

    with CatalogService(project_root=PROJECT_ROOT) as service:
        try:
            result = service.register_manifest(args.manifest)
        except Exception as e:
            print(f"Catalog registration failed: {e}", file=sys.stderr)
            return 1

    if args.json:
        print(json.dumps(result.model_dump(), indent=2))
    else:
        print("=" * 60)
        print(" ASTRATRACE SCENE CATALOG REGISTRATION")
        print("=" * 60)
        print(f" Scene ID:         {result.scene_id}")
        print(f" Sensor:           {result.sensor}")
        print(f" Collection:       {result.collection}")
        print(f" Tiles Registered: {result.tiles_registered}")
        print(f" Status:           {result.status}")
        print(f" Message:          {result.message}")
        print("=" * 60)

    return 0


if __name__ == "__main__":
    sys.exit(main())
