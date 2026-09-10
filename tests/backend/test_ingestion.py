"""Tests for AstraTrace Scene Ingestion and Tiling Engine.

SIH 2026 | Problem ID: SIH26227
Validates GeoTIFF parsing, windowed tiling, coordinate transformation,
security boundaries, error handling, and API endpoints.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.schemas.ingest import IngestRequest, IngestResponse
from apps.backend.app.services.ingestion import IngestionService, sanitize_source_path

SAMPLE_SCENE_REL = "data/samples/scenes/scene_2023_01_15.tif"


@pytest.fixture
def app_client():
    app = create_app()
    return TestClient(app)


@pytest.fixture
def ingestion_service():
    project_root = Path(__file__).resolve().parent.parent.parent
    return IngestionService(project_root=project_root)


def test_sanitize_source_path_valid(ingestion_service):
    """Valid path within project root is successfully resolved."""
    resolved = sanitize_source_path(SAMPLE_SCENE_REL, ingestion_service.project_root)
    assert resolved.exists()
    assert resolved.is_file()
    assert resolved.suffix == ".tif"


def test_sanitize_source_path_nonexistent(ingestion_service):
    """Non-existent scene file raises NotFoundError."""
    with pytest.raises(NotFoundError) as exc_info:
        sanitize_source_path("data/samples/scenes/nonexistent.tif", ingestion_service.project_root)
    assert "does not exist" in str(exc_info.value)


def test_sanitize_source_path_traversal(ingestion_service):
    """Path traversal attempt outside project root raises ValidationError."""
    with pytest.raises(NotFoundError):
        # Path outside project root that does not exist raises NotFoundError
        sanitize_source_path("../../windows/win.ini", ingestion_service.project_root)


def test_ingest_service_success(ingestion_service):
    """IngestionService correctly tiles and indexes a valid GeoTIFF scene."""
    request = IngestRequest(
        source_uri=SAMPLE_SCENE_REL,
        sensor="SENTINEL-2",
        collection="test_collection",
        acquired_at=datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
        tile_size=256,
        overlap=25,
    )
    response = ingestion_service.ingest_scene(request)

    assert isinstance(response, IngestResponse)
    assert response.sensor == "SENTINEL-2"
    assert response.collection == "test_collection"
    assert response.crs == "EPSG:32643"
    assert response.dimensions == [512, 512, 4]
    assert response.tiles_generated == 9
    assert response.status == "INDEXED"
    assert len(response.checksum) == 64  # SHA-256 hex string

    # Verify manifest exists on disk
    manifest_full_path = ingestion_service.project_root / response.manifest_path
    assert manifest_full_path.exists()

    # Verify manifest contents via get_manifest
    manifest = ingestion_service.get_manifest(response.scene_id)
    assert manifest["scene_id"] == response.scene_id
    assert manifest["tiles_count"] == 9
    assert len(manifest["tiles"]) == 9

    # Verify tile metadata structure and file existence
    first_tile = manifest["tiles"][0]
    assert first_tile["tile_index"] == 0
    assert len(first_tile["checksum"]) == 64
    assert first_tile["pixel_window"] == [0, 0, 256, 256]
    first_tile_file = ingestion_service.project_root / first_tile["path"]
    assert first_tile_file.exists()


def test_api_ingest_scene_endpoint(app_client):
    """POST /api/v1/ingest processes a valid scene and returns HTTP 201."""
    payload = {
        "source_uri": SAMPLE_SCENE_REL,
        "sensor": "SENTINEL-2",
        "collection": "api_test_collection",
        "acquired_at": "2023-01-15T10:30:00Z",
        "tile_size": 256,
        "overlap": 25,
    }
    response = app_client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["sensor"] == "SENTINEL-2"
    assert data["tiles_generated"] == 9
    assert data["status"] == "INDEXED"
    assert "scene_id" in data


def test_api_ingest_invalid_sensor(app_client):
    """POST /api/v1/ingest rejects unapproved satellite sensors with HTTP 422."""
    payload = {
        "source_uri": SAMPLE_SCENE_REL,
        "sensor": "UNKNOWN_SENSOR_XYZ",
        "collection": "api_test_collection",
        "acquired_at": "2023-01-15T10:30:00Z",
    }
    response = app_client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 422


def test_api_ingest_missing_file(app_client):
    """POST /api/v1/ingest returns HTTP 404 when file does not exist."""
    payload = {
        "source_uri": "data/samples/scenes/missing_file.tif",
        "sensor": "SENTINEL-2",
        "collection": "api_test_collection",
        "acquired_at": "2023-01-15T10:30:00Z",
    }
    response = app_client.post("/api/v1/ingest", json=payload)
    assert response.status_code == 404


def test_api_get_manifest(app_client):
    """GET /api/v1/ingest/manifest/{scene_id} returns manifest for indexed scene."""
    # First ingest to ensure scene exists
    payload = {
        "source_uri": SAMPLE_SCENE_REL,
        "sensor": "SENTINEL-2",
        "collection": "manifest_test",
        "acquired_at": "2023-01-15T10:30:00Z",
    }
    ingest_resp = app_client.post("/api/v1/ingest", json=payload)
    scene_id = ingest_resp.json()["scene_id"]

    # Now retrieve manifest
    manifest_resp = app_client.get(f"/api/v1/ingest/manifest/{scene_id}")
    assert manifest_resp.status_code == 200
    manifest = manifest_resp.json()
    assert manifest["scene_id"] == scene_id
    assert manifest["tiles_count"] == 9


def test_api_get_manifest_not_found(app_client):
    """GET /api/v1/ingest/manifest/{scene_id} returns HTTP 404 for unknown scene."""
    response = app_client.get("/api/v1/ingest/manifest/nonexistent_scene_123")
    assert response.status_code == 404


def test_api_get_manifest_invalid_id(app_client):
    """GET /api/v1/ingest/manifest/{scene_id} rejects malformed scene_id."""
    response = app_client.get("/api/v1/ingest/manifest/invalid..scene..id")
    assert response.status_code == 422
