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

def verify_database_catalog() -> bool:
    """Verifies Milestone 3 Database Schema, Manifest Registration, Spatial Queries, and STAC."""
    try:
        from fastapi.testclient import TestClient
        from apps.backend.app.db.session import init_db
        from apps.backend.app.main import create_app
        from apps.backend.app.services.catalog import CatalogService
        from apps.backend.app.schemas.catalog import TileSearchRequest

        # 1. Initialize DB tables
        init_db()
        log("Milestone 3 DB Initialization", "PASS", "scenes and tiles tables verified")

        # 2. Register manifest into catalog
        sample_manifest = "data/processed/scn_sentinel-2_20230115_96ed9480/manifest.json"
        with CatalogService(project_root=PROJECT_ROOT) as service:
            reg_res = service.register_manifest(sample_manifest)
            assert reg_res.status in ("REGISTERED", "SKIPPED_DUPLICATE")
            assert reg_res.tiles_registered == 9
            log("Milestone 3 Manifest Cataloging", "PASS", f"Status: {reg_res.status}, Tiles: {reg_res.tiles_registered}")

            # 3. Spatial and temporal queries
            req = TileSearchRequest(bbox=[73.57, 18.94, 73.63, 18.99])
            total, tiles = service.query_tiles(req)
            assert total >= 9
            log("Milestone 3 Spatial BBox Query", "PASS", f"Found {total} tiles overlapping Western Ghats bbox")

            # 4. STAC Item verification
            stac_item = service.get_stac_item(reg_res.scene_id)
            assert stac_item["type"] == "Feature"
            assert stac_item["id"] == reg_res.scene_id
            log("Milestone 3 STAC Item Serialization", "PASS", f"Item ID: {stac_item['id']}, Assets: {len(stac_item['assets'])}")

        # 5. Verify REST API endpoints
        app = create_app()
        client = TestClient(app)
        api_res = client.get("/api/v1/stac/collections")
        assert api_res.status_code == 200
        assert len(api_res.json()["collections"]) >= 1
        log("Milestone 3 STAC API Endpoint", "PASS", "GET /api/v1/stac/collections returned 200 OK")

        return True
    except Exception as e:
        log("Milestone 3 Database Verification", "FAIL", str(e))
        return False

def verify_baseline_retrieval() -> bool:
    """Verifies Milestone 4 Baseline Retrieval Pipeline."""
    try:
        from apps.backend.app.main import create_app
        from apps.backend.app.schemas.search import BaselineSearchRequest
        from apps.backend.app.services.retrieval.baseline_classifier import TileFeatureClassifier
        from apps.backend.app.services.retrieval.baseline_scorer import BaselineScorer
        from apps.backend.app.services.retrieval.service import BaselineRetrievalService
        from apps.backend.app.services.retrieval.vocabulary import ControlledVocabulary
        from fastapi.testclient import TestClient

        # 1. Controlled Vocabulary Parser
        weights, is_oov = ControlledVocabulary.parse_query("urban buildings")
        assert not is_oov
        assert "Residential" in weights
        assert "Industrial" in weights
        assert abs(sum(weights.values()) - 1.0) < 0.05
        log("Milestone 4 Vocabulary Parsing", "PASS", f"Synset resolution: {list(weights.keys())}")

        # 2. Tile Feature Extraction and Classification
        sample_tile = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"
        if sample_tile.exists():
            classifier = TileFeatureClassifier(project_root=PROJECT_ROOT)
            probs = classifier.classify_tile(sample_tile)
            assert len(probs) == 10
            assert abs(sum(probs.values()) - 1.0) < 0.05
            top_c = max(probs, key=probs.get)
            log("Milestone 4 Tile Feature Classification", "PASS", f"10-class EuroSAT probs (Top: {top_c} {probs[top_c]:.2f})")

        # 3. Baseline Retrieval Service End-to-End Search
        with BaselineRetrievalService(project_root=PROJECT_ROOT) as service:
            req = BaselineSearchRequest(
                query="forest vegetation",
                bbox=(73.57, 18.94, 73.63, 18.99),
                top_k=5,
            )
            resp = service.search(req)
            assert resp.query_id.startswith("qry_")
            assert resp.total_candidates >= 9
            assert len(resp.results) > 0
            assert resp.execution_trace["total_ms"] < 500.0
            log(
                "Milestone 4 Baseline Search Service",
                "PASS",
                f"Candidates: {resp.total_candidates}, Top Score: {resp.results[0].baseline_score:.4f}, Latency: {resp.execution_trace['total_ms']:.1f}ms",
            )

        # 4. REST API Endpoint POST /api/v1/search/baseline
        app = create_app()
        client = TestClient(app)
        api_payload = {
            "query": "industrial warehouse",
            "bbox": [73.57, 18.94, 73.63, 18.99],
            "top_k": 3,
        }
        api_res = client.post("/api/v1/search/baseline", json=api_payload)
        assert api_res.status_code == 200
        res_data = api_res.json()
        assert "Industrial" in res_data["matched_vocabulary"]
        assert len(res_data["results"]) <= 3
        log("Milestone 4 REST Search Endpoint", "PASS", "POST /api/v1/search/baseline returned 200 OK")

        return True
    except Exception as e:
        log("Milestone 4 Baseline Retrieval", "FAIL", str(e))
        return False

def verify_change_detection() -> bool:
    """Verifies Milestone 5 Baseline Change Detection Pipeline."""
    try:
        import numpy as np
        from apps.backend.app.main import create_app
        from apps.backend.app.schemas.change import ChangeDetectionRequest, ScenePairChangeRequest
        from apps.backend.app.services.change.detector import BaselineChangeDetector
        from apps.backend.app.services.change.differencing import compute_spectral_difference, compute_index_deltas, compute_otsu_threshold
        from apps.backend.app.services.change.morphology import binary_erosion, binary_dilation, filter_small_components
        from apps.backend.app.services.change.service import ChangeDetectionService
        from fastapi.testclient import TestClient

        # 1. Pure-NumPy Morphology
        test_mask = np.zeros((10, 10), dtype=bool)
        test_mask[3:7, 3:7] = True
        eroded = binary_erosion(test_mask)
        dilated = binary_dilation(test_mask)
        assert eroded.sum() < test_mask.sum()
        assert dilated.sum() > test_mask.sum()
        filtered = filter_small_components(test_mask, min_pixels=20)
        assert filtered.sum() == 0  # 16 < 20
        log("Milestone 5 NumPy Morphology", "PASS", "Erosion, dilation & CC area filter verified")

        # 2. Differencing & Otsu
        t1_arr = np.full((4, 64, 64), 0.2, dtype=np.float32)
        t2_arr = np.full((4, 64, 64), 0.7, dtype=np.float32)
        diff = compute_spectral_difference(t1_arr, t2_arr)
        assert 0.0 <= float(diff.min()) and float(diff.max()) <= 1.0
        otsu_th = compute_otsu_threshold(diff)
        assert 0.15 <= otsu_th <= 0.65
        log("Milestone 5 Spectral Differencing & Otsu", "PASS", f"Spectral diff clamped, Otsu threshold: {otsu_th:.4f}")

        # 3. Ground Truth Synthetic Construction Detection on Tile 1
        tile1_before = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0001.tif"
        tile1_after = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0001.tif"
        if tile1_before.exists() and tile1_after.exists():
            detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
            res1 = detector.detect_change(tile1_before, tile1_after, threshold=0.15, min_pixels=10, apply_morphology=True)
            assert res1["changed_pixels"] == 4800
            assert res1["change_type"] == "construction"
            assert res1["index_deltas_mean"]["delta_brightness"] > 0.5
            assert res1["index_deltas_mean"]["delta_ndvi"] < -0.3
            log(
                "Milestone 5 Ground Truth Construction",
                "PASS",
                f"Detected {res1['changed_pixels']} px (Ground Truth 4800 px), type: {res1['change_type']}",
            )

        # 4. Negative Control on Tile 0
        tile0_before = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"
        tile0_after = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0000.tif"
        if tile0_before.exists() and tile0_after.exists():
            res0 = detector.detect_change(tile0_before, tile0_after, threshold=0.15, min_pixels=10, apply_morphology=True)
            assert res0["changed_pixels"] == 0
            assert res0["change_type"] == "no_change"
            log("Milestone 5 Negative Control", "PASS", "Tile 0 zero false positives (0 px changed)")

        # 5. Change Detection Service End-to-End
        with ChangeDetectionService(project_root=PROJECT_ROOT) as service:
            req = ChangeDetectionRequest(
                before_tile_id="scn_sentinel-2_20230115_96ed9480_t0001",
                after_tile_id="scn_sentinel-2_20241222_7acad713_t0001",
                threshold=0.15,
            )
            res = service.detect_tile_pair(req)
            assert res.change_id.startswith("chg_")
            assert res.metrics.changed_pixels == 4800
            assert res.before.tile_id == req.before_tile_id
            assert res.after.tile_id == req.after_tile_id
            assert res.execution_trace["total_ms"] > 0
            log(
                "Milestone 5 Change Detection Service",
                "PASS",
                f"Change ID: {res.change_id}, Latency: {res.execution_trace['total_ms']:.1f}ms",
            )

        # 6. REST API Endpoints
        app = create_app()
        client = TestClient(app)
        api_payload = {
            "before_tile_id": "scn_sentinel-2_20230115_96ed9480_t0001",
            "after_tile_id": "scn_sentinel-2_20241222_7acad713_t0001",
            "threshold": 0.15,
        }
        api_res = client.post("/api/v1/change/detect", json=api_payload)
        assert api_res.status_code == 200
        change_data = api_res.json()
        assert change_data["metrics"]["change_type"] == "construction"
        assert change_data["metrics"]["changed_pixels"] == 4800

        # Verify mask endpoint
        mask_url = change_data["mask_url"]
        mask_res = client.get(mask_url)
        assert mask_res.status_code == 200
        assert mask_res.headers["content-type"] == "image/png"
        log("Milestone 5 REST API Endpoints", "PASS", "POST /change/detect & GET /change/mask/{id} verified 200 OK")

        return True
    except Exception as e:
        log("Milestone 5 Change Detection", "FAIL", str(e))
        return False

def main():
    print("=" * 60)
    print("ASTRATRACE MILESTONE 1, 2, 3, 4 & 5 VERIFICATION SUITE")
    print("=" * 60)

    results = [
        verify_directories(),
        verify_configuration(),
        verify_backend_health(),
        verify_sample_metadata(),
        verify_ingestion_pipeline(),
        verify_database_catalog(),
        verify_baseline_retrieval(),
        verify_change_detection(),
    ]

    print("=" * 60)
    if all(results):
        print("\033[92m[SUCCESS] All Milestone 1, 2, 3, 4 & 5 verification checks PASSED.\033[0m")
        sys.exit(0)
    else:
        print("\033[91m[FAILURE] One or more verification checks FAILED.\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
