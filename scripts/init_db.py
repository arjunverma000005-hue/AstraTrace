"""Database Initialization Utility for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Initializes all database tables, spatial columns, and indexes.
"""
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.config import settings
from apps.backend.app.db.session import engine, init_db
from apps.backend.app.models import SceneRecord, TileRecord  # noqa: F401


def main() -> int:
    print("=" * 60)
    print(" ASTRATRACE DATABASE INITIALIZATION")
    print("=" * 60)
    print(f" Target Database URL: {engine.url.render_as_string(hide_password=True)}")
    print(f" Dialect:             {engine.dialect.name}")

    try:
        init_db(engine)
        print(" Tables Initialized:")
        print("   - scenes (SceneRecord)")
        print("   - tiles  (TileRecord)")
        print(" Indexes Created:")
        print("   - idx_scenes_sensor_date")
        print("   - idx_scenes_spatial_bbox")
        print("   - idx_tiles_spatial_bbox")
        print("   - idx_tiles_scene_idx")
        print("=" * 60)
        print(" Database initialization COMPLETED successfully.")
        return 0
    except Exception as e:
        print(f" Database initialization FAILED: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
