"""Tests for AstraTrace Metadata Catalog, Spatial Indexing, and STAC Representation.

SIH 2026 | Problem ID: SIH26227
Validates schema creation, idempotent ingestion, spatial/temporal filtering,
STAC-compatible metadata serialization, and REST endpoints.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from apps.backend.app.db.session import Base
from apps.backend.app.main import create_app
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.schemas.catalog import TileSearchRequest
from apps.backend.app.services.catalog import CatalogService

SAMPLE_MANIFEST_REL = "data/processed/scn_sentinel-2_20230115_96ed9480/manifest.json"


@pytest.fixture
def memory_db():
    """Provides a fresh isolated in-memory SQLite session for unit testing."""
    test_engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def app_client():
    """FastAPI TestClient configured with initialized catalog."""
    from apps.backend.app.db.session import init_db
    init_db()
    app = create_app()
    return TestClient(app)


def test_schema_creation(memory_db):
    """Verifies that scenes and tiles tables are initialized with expected columns."""
    assert SceneRecord.__tablename__ == "scenes"
    assert TileRecord.__tablename__ == "tiles"
    # Ensure tables exist in sqlite_master
    tables = [r[0] for r in memory_db.execute(Base.metadata.tables["scenes"].select().limit(0)).cursor.description]
    assert "scene_id" in tables
    assert "checksum" in tables


def test_catalog_ingest_manifest_success(memory_db):
    """Manifest registration inserts scene and 9 tile records."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)

    res = service.register_manifest(SAMPLE_MANIFEST_REL)
    assert res.status == "REGISTERED"
    assert res.tiles_registered == 9

    # Verify scene record in database
    scene = memory_db.query(SceneRecord).filter(SceneRecord.scene_id == res.scene_id).first()
    assert scene is not None
    assert scene.sensor == "SENTINEL-2"
    assert scene.tiles_count == 9
    assert len(scene.tiles) == 9
    assert scene.min_lon < scene.max_lon
    assert scene.min_lat < scene.max_lat
    assert "POLYGON" in scene.geom


def test_catalog_idempotent_duplicate_handling(memory_db):
    """Re-registering identical manifest returns SKIPPED_DUPLICATE without creating new rows."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)

    # First registration
    res1 = service.register_manifest(SAMPLE_MANIFEST_REL)
    assert res1.status == "REGISTERED"

    # Second registration of identical manifest
    res2 = service.register_manifest(SAMPLE_MANIFEST_REL)
    assert res2.status == "SKIPPED_DUPLICATE"
    assert res2.tiles_registered == 9

    # Verify database still has exactly 1 scene and 9 tiles
    total_scenes = memory_db.query(SceneRecord).count()
    total_tiles = memory_db.query(TileRecord).count()
    assert total_scenes == 1
    assert total_tiles == 9


def test_scene_tile_foreign_key_cascade(memory_db):
    """Deleting a scene cascades and deletes all associated tile records."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)
    res = service.register_manifest(SAMPLE_MANIFEST_REL)

    scene = memory_db.query(SceneRecord).filter(SceneRecord.scene_id == res.scene_id).first()
    memory_db.delete(scene)
    memory_db.commit()

    assert memory_db.query(SceneRecord).count() == 0
    assert memory_db.query(TileRecord).count() == 0


def test_spatial_filtering_bbox(memory_db):
    """Spatial bounding box intersection filters tiles correctly."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)
    service.register_manifest(SAMPLE_MANIFEST_REL)

    # 1. Query bbox covering Western Ghats Pune region
    req_matching = TileSearchRequest(
        bbox=[73.57, 18.94, 73.63, 18.99],
        limit=50,
    )
    total, tiles = service.query_tiles(req_matching)
    assert total == 9
    assert len(tiles) == 9

    # 2. Query bbox completely outside (e.g. Eastern Himalayas)
    req_outside = TileSearchRequest(
        bbox=[92.0, 27.0, 93.0, 28.0],
        limit=50,
    )
    total_out, tiles_out = service.query_tiles(req_outside)
    assert total_out == 0
    assert len(tiles_out) == 0


def test_spatial_filtering_point(memory_db):
    """Point intersection identifies the specific overlapping tile."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)
    service.register_manifest(SAMPLE_MANIFEST_REL)

    # Coordinates located inside tile_0000
    req_point = TileSearchRequest(
        point=[73.58, 18.97],
    )
    total, tiles = service.query_tiles(req_point)
    assert total >= 1
    assert any(t["tile_id"].endswith("_t0000") for t in tiles)


def test_temporal_filtering(memory_db):
    """Temporal range filtering correctly isolates observations by acquisition window."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)

    # Ingest 2023 scene and 2024 scene
    service.register_manifest("data/processed/scn_sentinel-2_20230115_96ed9480/manifest.json")
    service.register_manifest("data/processed/scn_sentinel-2_20241222_7acad713/manifest.json")

    # Filter for 2023 only
    total_2023, scenes_2023 = service.query_scenes(
        date_from=datetime(2023, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2023, 12, 31, tzinfo=timezone.utc),
    )
    assert total_2023 == 1
    assert "20230115" in scenes_2023[0].scene_id

    # Filter for 2024 only
    total_2024, scenes_2024 = service.query_scenes(
        date_from=datetime(2024, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2024, 12, 31, tzinfo=timezone.utc),
    )
    assert total_2024 == 1
    assert "20241222" in scenes_2024[0].scene_id

    # Filter for 2020 (no data)
    total_2020, scenes_2020 = service.query_scenes(
        date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2020, 12, 31, tzinfo=timezone.utc),
    )
    assert total_2020 == 0


def test_stac_compatible_representation(memory_db):
    """STAC item serialization adheres to STAC-compatible GeoJSON Feature format."""
    project_root = Path(__file__).resolve().parents[2]
    service = CatalogService(db=memory_db, project_root=project_root)
    service.register_manifest(SAMPLE_MANIFEST_REL)

    scene = memory_db.query(SceneRecord).first()
    stac_item = service.get_stac_item(scene.scene_id)

    assert stac_item["type"] == "Feature"
    assert stac_item["stac_version"] == "1.0.0"
    assert stac_item["id"] == scene.scene_id
    assert stac_item["geometry"]["type"] == "Polygon"
    assert len(stac_item["bbox"]) == 4
    assert "datetime" in stac_item["properties"]
    assert "source_raster" in stac_item["assets"]
    assert "manifest" in stac_item["assets"]


def test_api_catalog_endpoints(app_client):
    """API endpoints for catalog registration and querying respond with valid schemas."""
    # 1. Ingest manifest via API
    ingest_res = app_client.post(
        "/api/v1/catalog/ingest-manifest",
        json={"manifest_path": SAMPLE_MANIFEST_REL},
    )
    assert ingest_res.status_code in (200, 201)
    data = ingest_res.json()
    assert data["scene_id"] == "scn_sentinel-2_20230115_96ed9480"
    assert data["tiles_registered"] == 9

    # 2. Query scenes
    scenes_res = app_client.get("/api/v1/catalog/scenes?sensor=SENTINEL-2")
    assert scenes_res.status_code == 200
    scenes_data = scenes_res.json()
    assert scenes_data["total"] >= 1

    # 3. Get single scene
    scene_id = data["scene_id"]
    scene_res = app_client.get(f"/api/v1/catalog/scenes/{scene_id}")
    assert scene_res.status_code == 200
    assert scene_res.json()["scene_id"] == scene_id

    # 4. Get scene tiles
    tiles_res = app_client.get(f"/api/v1/catalog/scenes/{scene_id}/tiles")
    assert tiles_res.status_code == 200
    assert tiles_res.json()["tiles_count"] == 9

    # 5. Search tiles
    search_res = app_client.post(
        "/api/v1/catalog/tiles/search",
        json={"bbox": [73.57, 18.94, 73.63, 18.99], "limit": 10},
    )
    assert search_res.status_code == 200
    assert search_res.json()["total"] >= 9


def test_api_stac_endpoints(app_client):
    """STAC-compatible API endpoints return compliant Collections and Items."""
    # Ensure at least one scene is cataloged
    app_client.post("/api/v1/catalog/ingest-manifest", json={"manifest_path": SAMPLE_MANIFEST_REL})

    # Root STAC
    root_res = app_client.get("/api/v1/stac")
    assert root_res.status_code == 200
    assert root_res.json()["type"] == "Catalog"

    # Collections
    cols_res = app_client.get("/api/v1/stac/collections")
    assert cols_res.status_code == 200
    cols = cols_res.json()["collections"]
    assert len(cols) >= 1
    collection_id = cols[0]["id"]

    # Collection Items
    items_res = app_client.get(f"/api/v1/stac/collections/{collection_id}/items")
    assert items_res.status_code == 200
    assert items_res.json()["type"] == "FeatureCollection"
    assert len(items_res.json()["features"]) >= 1

    # Single STAC Item
    item_id = items_res.json()["features"][0]["id"]
    item_res = app_client.get(f"/api/v1/stac/collections/{collection_id}/items/{item_id}")
    assert item_res.status_code == 200
    assert item_res.json()["id"] == item_id
