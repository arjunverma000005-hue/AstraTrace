#!/usr/bin/env python3
"""AstraTrace Foundation & Milestone 1 Verification Script.

Executes comprehensive checks across directory structure, configuration,
backend health endpoints, and data integrity.
"""
import sys
import json
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def log(step: str, status: str, details: str = ""):
    color = "\033[92m" if status == "PASS" else ("\033[91m" if status == "FAIL" else "\033[93m")
    reset = "\033[0m"
    print(f"[{color}{status:4}{reset}] {step:<40} {details}")

def verify_directories() -> bool:
    required_dirs = [
        "apps/backend/app",
        "apps/backend/app/api/v1",
        "apps/backend/app/core",
        "apps/backend/app/schemas",
        "apps/frontend/src/api",
        "apps/frontend/src/components",
        "apps/frontend/src/types",
        "data/raw",
        "data/processed",
        "data/samples",
        "models",
        "docker",
        "docs",
        "tests/backend",
    ]
    all_ok = True
    for d in required_dirs:
        p = PROJECT_ROOT / d
        if p.exists() and p.is_dir():
            log(f"Dir: {d}", "PASS")
        else:
            log(f"Dir: {d}", "FAIL", "Directory missing")
            all_ok = False
    return all_ok

def verify_configuration() -> bool:
    try:
        from apps.backend.app.config import Settings
        cfg = Settings()
        assert cfg.app_name == "AstraTrace"
        assert cfg.offline_mode is True
        assert cfg.api_port == 8000
        assert isinstance(cfg.cors_origins, list)
        log("Configuration Loading & Defaults", "PASS", f"App: {cfg.app_name}, Offline: {cfg.offline_mode}")
        return True
    except Exception as e:
        log("Configuration Loading", "FAIL", str(e))
        return False

def verify_backend_health() -> bool:
    try:
        from fastapi.testclient import TestClient
        from apps.backend.app.main import create_app

        app = create_app()
        client = TestClient(app)

        # 1. Root Ping
        res_root = client.get("/")
        assert res_root.status_code == 200
        data_root = res_root.json()
        assert data_root["status"] == "online"
        assert "X-Request-ID" in res_root.headers
        log("Endpoint GET /", "PASS", f"X-Request-ID: {res_root.headers['X-Request-ID']}")

        # 2. Health Check
        res_health = client.get("/api/v1/health")
        assert res_health.status_code == 200
        data_health = res_health.json()
        assert data_health["status"] == "healthy"
        assert data_health["offline_mode"] is True
        log("Endpoint GET /api/v1/health", "PASS", f"Status: {data_health['status']}, Version: {data_health['version']}")

        # 3. System Status
        res_status = client.get("/api/v1/status")
        assert res_status.status_code == 200
        data_status = res_status.json()
        assert data_status["status"] == "operational"
        assert data_status["services"]["api"] == "healthy"
        log("Endpoint GET /api/v1/status", "PASS", f"Services: {list(data_status['services'].keys())}")

        return True
    except Exception as e:
        log("Backend Health Verification", "FAIL", str(e))
        return False

def verify_sample_metadata() -> bool:
    sample_file = PROJECT_ROOT / "data/samples/sample_metadata.json"
    if not sample_file.exists():
        log("Sample Metadata Fixture", "FAIL", "Missing sample_metadata.json")
        return False
    try:
        with open(sample_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert "samples" in data and len(data["samples"]) > 0
        log("Sample Metadata Fixture", "PASS", f"Found {len(data['samples'])} sample scene record(s)")
        return True
    except Exception as e:
        log("Sample Metadata Fixture", "FAIL", str(e))
        return False

def verify_ingestion_pipeline() -> bool:
    """Verifies Milestone 2 GeoTIFF parsing, tiling, and manifest creation."""
    try:
        from fastapi.testclient import TestClient
        from apps.backend.app.main import create_app
        from apps.backend.app.services.ingestion import IngestionService
        from apps.backend.app.schemas.ingest import IngestRequest
        from datetime import datetime, timezone
        import rasterio

        # 1. Verify sample GeoTIFF exists and has valid geospatial headers
        sample_tiff = PROJECT_ROOT / "data/samples/scenes/scene_2023_01_15.tif"
        if not sample_tiff.exists():
            log("Milestone 2 Sample GeoTIFF", "FAIL", f"Missing {sample_tiff}")
            return False

        with rasterio.open(sample_tiff) as src:
            assert src.width == 512 and src.height == 512
            assert src.count == 4
            assert str(src.crs) == "EPSG:32643"
        log("Milestone 2 GeoTIFF Inspection", "PASS", f"512x512 4-band EPSG:32643 verified")

        # 2. Ingest via IngestionService
        service = IngestionService(project_root=PROJECT_ROOT)
        req = IngestRequest(
            source_uri="data/samples/scenes/scene_2023_01_15.tif",
            sensor="SENTINEL-2",
            collection="verification_collection",
            acquired_at=datetime(2023, 1, 15, 10, 30, tzinfo=timezone.utc),
            tile_size=256,
            overlap=25,
        )
        res = service.ingest_scene(req)
        assert res.tiles_generated == 9
        assert res.status == "INDEXED"
        assert (PROJECT_ROOT / res.manifest_path).exists()
        log("Milestone 2 Ingestion Service", "PASS", f"Scene: {res.scene_id}, Tiles: {res.tiles_generated}")

        # 3. Verify API endpoint POST /api/v1/ingest and GET /api/v1/ingest/manifest/{scene_id}
        app = create_app()
        client = TestClient(app)
        api_res = client.get(f"/api/v1/ingest/manifest/{res.scene_id}")
        assert api_res.status_code == 200
        manifest_data = api_res.json()
        assert manifest_data["scene_id"] == res.scene_id
        assert len(manifest_data["tiles"]) == 9
        log("Milestone 2 Ingestion API", "PASS", f"GET /api/v1/ingest/manifest/{res.scene_id} returned 200 OK")

        return True
    except Exception as e:
        log("Milestone 2 Ingestion Verification", "FAIL", str(e))
        return False

def main():
    print("=" * 60)
    print("ASTRATRACE MILESTONE 1 & 2 FOUNDATION & INGESTION VERIFICATION")
    print("=" * 60)

    results = [
        verify_directories(),
        verify_configuration(),
        verify_backend_health(),
        verify_sample_metadata(),
        verify_ingestion_pipeline(),
    ]

    print("=" * 60)
    if all(results):
        print("\033[92m[SUCCESS] All Milestone 1 & 2 verification checks PASSED.\033[0m")
        sys.exit(0)
    else:
        print("\033[91m[FAILURE] One or more verification checks FAILED.\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
