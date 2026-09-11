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

def verify_semantic_retrieval() -> bool:
    """Milestone 6: Validates embeddings, vector indexing, hybrid search, and REST endpoints."""
    try:
        from apps.backend.app.main import create_app
        from apps.backend.app.models.embedding import TileEmbeddingRecord
        from apps.backend.app.schemas.semantic import (
            SemanticSearchRequest,
            SimilarTilesRequest,
        )
        from apps.backend.app.services.retrieval.embedding_model import (
            DeterministicOfflineEmbeddingModel,
        )
        from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService
        from apps.backend.app.services.retrieval.vector_index import NumpyVectorIndex
        from apps.backend.app.db.session import SessionLocal
        from fastapi.testclient import TestClient
        import numpy as np

        # 1. Verify Embedding Model
        model = DeterministicOfflineEmbeddingModel()
        text_vec = model.encode_text("industrial facility warehouse")
        assert text_vec.shape == (512,)
        assert abs(float(np.linalg.norm(text_vec)) - 1.0) < 1e-4
        log("Milestone 6 Embedding Model", "PASS", "512-D unit-sphere vector generated deterministically")

        # 2. Verify Vector Index
        vidx = NumpyVectorIndex(dimension=512)
        vidx.add("test_tile", text_vec, metadata={"source": "verify"})
        hits = vidx.search(text_vec, top_k=1)
        assert len(hits) == 1
        assert hits[0]["tile_id"] == "test_tile"
        assert abs(hits[0]["cosine_sim"] - 1.0) < 1e-4
        log("Milestone 6 Vector Index", "PASS", "Exact cosine similarity Top-K verified")

        # 3. Verify Database Embeddings Table
        with SessionLocal() as db:
            emb_count = db.query(TileEmbeddingRecord).count()
            assert emb_count >= 18
            log("Milestone 6 DB Catalog", "PASS", f"{emb_count} tile embeddings cataloged in database")

        # 4. Semantic Search Service End-to-End
        with SemanticRetrievalService(project_root=PROJECT_ROOT) as service:
            req = SemanticSearchRequest(query="industrial warehouse", top_k=5, hybrid_weight=0.6)
            resp = service.search_semantic(req)
            assert resp.query_id.startswith("sem_")
            assert len(resp.results) > 0
            assert resp.results[0].hybrid_score > 0.0
            log(
                "Milestone 6 Semantic Retrieval Service",
                "PASS",
                f"Query: '{req.query}' -> Top Hit: {resp.results[0].tile_id} (Score: {resp.results[0].hybrid_score:.4f})",
            )

        # 5. REST API Endpoints
        app = create_app()
        client = TestClient(app)

        # A. Semantic Search Endpoint
        res_sem = client.post("/api/v1/search/semantic", json={"query": "mountain forest", "top_k": 3})
        assert res_sem.status_code == 200
        assert "results" in res_sem.json()

        # B. Similar Tiles Endpoint
        res_sim = client.post(
            "/api/v1/search/similar-tiles",
            json={"reference_tile_id": "scn_sentinel-2_20230115_96ed9480_t0000", "top_k": 3},
        )
        assert res_sim.status_code == 200

        # C. Index Status Endpoint
        res_stat = client.get("/api/v1/embeddings/status")
        assert res_stat.status_code == 200
        assert res_stat.json()["status"] == "INDEX_OPERATIONAL"
        log("Milestone 6 REST API Endpoints", "PASS", "POST /search/semantic, /search/similar-tiles, GET /embeddings/status 200 OK")

        return True
    except Exception as e:
        log("Milestone 6 Semantic Retrieval", "FAIL", str(e))
        return False

def verify_quality_gate() -> bool:
    """Verifies Milestone 7 Quality Gate & False-Alarm Suppression Pipeline."""
    try:
        import numpy as np
        from apps.backend.app.main import create_app
        from apps.backend.app.schemas.quality import QualityDecision, QualityGatedChangeRequest, QualityStatus
        from apps.backend.app.services.quality.pair_quality import PairQualityEvaluator
        from apps.backend.app.services.quality.quality_detector import TileQualityDetector
        from apps.backend.app.services.quality.quality_gate import QualityGate
        from fastapi.testclient import TestClient

        # 1. Tile Quality Detector
        detector = TileQualityDetector()
        clean_arr = np.full((4, 128, 128), 2000.0, dtype=np.float32)
        metrics_clean, masks_clean = detector.analyze_raster(clean_arr)
        assert metrics_clean.quality_status == QualityStatus.USABLE
        assert metrics_clean.cloud_pixels == 0

        # Inject cloud patch (60x60 patch = 3600 pixels, >20% of 128x128 tile)
        cloud_arr = clean_arr.copy()
        cloud_arr[:, 20:80, 20:80] = 5500.0
        metrics_cloud, masks_cloud = detector.analyze_raster(cloud_arr)
        assert metrics_cloud.cloud_pixels == 3600
        assert metrics_cloud.quality_status in [QualityStatus.DEGRADED, QualityStatus.UNRELIABLE]
        log("Milestone 7 Tile Quality Detector", "PASS", "Optical cloud/shadow masks & quality status verified")

        # 2. Pair Quality Evaluator
        pair_evaluator = PairQualityEvaluator()
        pair_metrics, pair_masks = pair_evaluator.evaluate_pair(clean_arr, clean_arr)
        assert pair_metrics.registration_score >= 0.70
        assert pair_metrics.pair_quality_score > 0.80
        log("Milestone 7 Pair Quality Evaluator", "PASS", f"Pair quality: {pair_metrics.pair_quality_score:.4f}, Reg score: {pair_metrics.registration_score:.4f}")

        # 3. Quality Gate False-Alarm Suppression
        gate = QualityGate(project_root=PROJECT_ROOT)
        req_cloud = QualityGatedChangeRequest(
            before_tile_path="dummy1.tif",
            after_tile_path="dummy2.tif",
            threshold=0.15,
            suppress_clouds=True,
        )
        resp_cloud = gate.evaluate_change(clean_arr, cloud_arr, request=req_cloud)
        assert resp_cloud.raw_changed_pixels >= 3600
        assert resp_cloud.suppression_breakdown.cloud_suppressed_pixels >= 3600
        assert resp_cloud.verified_changed_pixels == 0
        assert resp_cloud.decision == QualityDecision.QUALITY_SUPPRESSED
        log("Milestone 7 False-Alarm Suppression", "PASS", f"Suppressed {resp_cloud.suppression_breakdown.cloud_suppressed_pixels} cloud false-alarm pixels -> Decision: QUALITY_SUPPRESSED")

        # 4. Ground Truth True Change Preservation
        tile1_before = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0001.tif"
        tile1_after = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0001.tif"
        if tile1_before.exists() and tile1_after.exists():
            req_true = QualityGatedChangeRequest(
                before_tile_path=str(tile1_before),
                after_tile_path=str(tile1_after),
                threshold=0.15,
                min_pixels=10,
            )
            resp_true = gate.evaluate_change(tile1_before, tile1_after, request=req_true)
            assert resp_true.verified_changed_pixels == 4800
            assert resp_true.decision in [QualityDecision.QUALITY_PASSED, QualityDecision.QUALITY_DEGRADED]
            log("Milestone 7 True Change Preservation", "PASS", f"Preserved {resp_true.verified_changed_pixels} px (100% of construction ground truth) -> Decision: {resp_true.decision.value}")

        # 5. REST API Endpoints
        app = create_app()
        client = TestClient(app)

        # A. Quality Config
        res_cfg = client.get("/api/v1/quality/config")
        assert res_cfg.status_code == 200
        assert "thresholds" in res_cfg.json()
        assert "cloud_vis_threshold" in res_cfg.json()["thresholds"]

        # B. Assess Tile
        res_tile = client.post(
            "/api/v1/quality/assess-tile",
            json={"tile_id": "scn_sentinel-2_20230115_96ed9480_t0000"},
        )
        assert res_tile.status_code == 200
        assert res_tile.json()["quality_status"] == "USABLE"

        # C. Assess Pair
        res_pair = client.post(
            "/api/v1/quality/assess-pair",
            json={
                "t1_input": "scn_sentinel-2_20230115_96ed9480_t0000",
                "t2_input": "scn_sentinel-2_20241222_7acad713_t0000",
            },
        )
        assert res_pair.status_code == 200

        # D. Detect Gated Change
        res_chg = client.post(
            "/api/v1/change/detect-gated",
            json={
                "before_tile_path": "data/processed/scn_sentinel-2_20230115_96ed9480/tile_0001.tif",
                "after_tile_path": "data/processed/scn_sentinel-2_20241222_7acad713/tile_0001.tif",
                "threshold": 0.15,
            },
        )
        assert res_chg.status_code == 200
        assert res_chg.json()["decision"] in ["QUALITY_PASSED", "QUALITY_DEGRADED"]
        log("Milestone 7 REST API Endpoints", "PASS", "POST /quality/assess-tile, assess-pair, detect-gated, GET /config 200 OK")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        log("Milestone 7 Quality Gate", "FAIL", f"{type(e).__name__}: {e}")
        return False


def verify_milestone8_search_and_review() -> bool:
    """Verifies Milestone 8: Unified Search API, Tile Preview Generator, and Analyst Review Queue."""
    try:
        from fastapi.testclient import TestClient
        from apps.backend.app.main import create_app
        from apps.backend.app.schemas.review import ReviewDecision, TargetType

        app = create_app()
        client = TestClient(app)

        # 1. Unified Search REST API (Keyword, Semantic, Spatial)
        res_kw = client.post(
            "/api/v1/search/unified",
            json={"query": "Sentinel-2", "search_mode": "KEYWORD", "top_k": 5},
        )
        assert res_kw.status_code == 200
        kw_data = res_kw.json()
        assert "results" in kw_data
        assert "execution_trace" in kw_data
        assert len(kw_data["results"]) > 0

        sample_cand = kw_data["results"][0]
        for dim in ["what", "where", "when", "which", "why", "confidence", "quality_status", "evidence", "provenance"]:
            assert dim in sample_cand, f"Missing Evidence-First dimension: {dim}"
        assert "preview_url" in sample_cand["evidence"]
        log("Milestone 8 Unified Search (Keyword)", "PASS", f"Returned {len(kw_data['results'])} candidates with all 8 Evidence-First dimensions")

        # 2. Semantic Search Modality
        res_sem = client.post(
            "/api/v1/search/unified",
            json={"query": "dense forest canopy", "search_mode": "SEMANTIC", "top_k": 3},
        )
        assert res_sem.status_code == 200
        sem_data = res_sem.json()
        assert sem_data["search_mode"] == "SEMANTIC"
        assert len(sem_data["results"]) > 0
        log("Milestone 8 Unified Search (Semantic)", "PASS", f"Returned {len(sem_data['results'])} semantic matches")

        # 3. Tile Preview Generator
        target_tile_id = sample_cand["target_id"]
        res_prev = client.get(f"/api/v1/catalog/tiles/{target_tile_id}/preview")
        assert res_prev.status_code == 200
        assert res_prev.headers["content-type"] == "image/png"
        assert res_prev.content[:8] == b"\x89PNG\r\n\x1a\n"
        log("Milestone 8 Tile Preview Generator", "PASS", f"Generated 8-bit RGB PNG preview for {target_tile_id} ({len(res_prev.content)} bytes)")

        # 4. Preview Security (Traversal Rejection)
        res_bad = client.get("/api/v1/catalog/tiles/..%2F..%2Fsecret/preview")
        assert res_bad.status_code in [400, 404, 422]
        log("Milestone 8 Preview Traversal Guard", "PASS", "Rejected directory traversal tile preview request")

        # 5. Analyst Review Decision & Audit Trail
        res_dec = client.post(
            "/api/v1/review/decision",
            json={
                "target_id": target_tile_id,
                "target_type": "TILE",
                "decision": "CONFIRMED",
                "analyst_id": "analyst_foundation_audit",
                "notes": "Verified clear satellite observation via foundation check",
            },
        )
        assert res_dec.status_code == 201
        dec_data = res_dec.json()
        assert dec_data["decision"] == "CONFIRMED"
        assert "review_id" in dec_data
        assert "provenance_snapshot" in dec_data
        log("Milestone 8 Analyst Review Decision", "PASS", f"Recorded review {dec_data['review_id']} for target {target_tile_id}")

        # 6. Review History & Queue Aggregation
        res_hist = client.get(f"/api/v1/review/history/{target_tile_id}")
        assert res_hist.status_code == 200
        assert res_hist.json()["total_reviews"] >= 1

        res_q = client.get("/api/v1/review/queue?status_filter=CONFIRMED")
        assert res_q.status_code == 200
        q_data = res_q.json()
        assert q_data["confirmed_count"] >= 1
        log("Milestone 8 Review Queue & Audit Trail", "PASS", f"Queue summary: Pending={q_data['pending_count']}, Confirmed={q_data['confirmed_count']}")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        log("Milestone 8 Search & Review", "FAIL", f"{type(e).__name__}: {e}")
        return False


def verify_milestone9_provenance_and_hardening() -> bool:
    """Verifies Milestone 9: Provenance DAG, Cryptographic Verification, Dossier Export, and Air-Gap."""
    try:
        from fastapi.testclient import TestClient
        from apps.backend.app.main import create_app
        from apps.backend.app.models.catalog import TileRecord
        from apps.backend.app.db.session import SessionLocal
        from apps.backend.app.services.provenance.service import ProvenanceService
        from apps.backend.app.services.provenance.verifier import ProvenanceVerifier
        from apps.backend.app.services.provenance.dossier import EvidencePackageService
        from apps.backend.app.services.audit.service import AuditService
        import socket

        # 1. Resolve sample tile from catalog
        with SessionLocal() as db:
            tile = db.query(TileRecord).first()
            assert tile is not None, "At least one tile required for verification."
            sample_tile_id = tile.tile_id

        # 2. Lineage DAG Reconstruction
        with SessionLocal() as db:
            prov_service = ProvenanceService(db=db, project_root=PROJECT_ROOT)
            graph = prov_service.get_provenance_graph(sample_tile_id)
            assert graph.root_id == sample_tile_id
            assert len(graph.nodes) >= 3
            assert len(graph.edges) >= 2
            log("Milestone 9 Lineage DAG", "PASS", f"Reconstructed DAG with {len(graph.nodes)} nodes and {len(graph.edges)} edges")

        # 3. Cryptographic Integrity Verification
        with SessionLocal() as db:
            verifier = ProvenanceVerifier(db=db, project_root=PROJECT_ROOT)
            report = verifier.verify_target(sample_tile_id)
            assert report.overall_status.value == "VERIFIED"
            assert report.verified_count > 0
            assert report.tampered_count == 0
            log("Milestone 9 Cryptographic Verification", "PASS", f"Verified {report.verified_count} artifacts (Status: {report.overall_status.value})")

        # 4. Forensic Evidence Dossier Export
        with SessionLocal() as db:
            dossier_service = EvidencePackageService(db=db, project_root=PROJECT_ROOT)
            dossier_res = dossier_service.export_dossier(sample_tile_id, actor="analyst_foundation_verifier")
            assert dossier_res.export_id.startswith("exp_")
            assert (PROJECT_ROOT / dossier_res.package_path).exists()
            log("Milestone 9 Evidence Dossier Export", "PASS", f"Exported {dossier_res.package_path} ({dossier_res.package_size_bytes} bytes, SHA-256: {dossier_res.package_checksum[:10]}...)")

        # 5. Append-Oriented Audit Logging
        with SessionLocal() as db:
            audit_svc = AuditService(db=db)
            total, events = audit_svc.query_events(limit=5)
            assert total >= 1
            log("Milestone 9 Structured Audit Log", "PASS", f"Cataloged {total} audit records across pipeline lifecycle")

        # 6. REST API Endpoints
        app = create_app()
        client = TestClient(app)

        res_g = client.get(f"/api/v1/provenance/graph/{sample_tile_id}")
        assert res_g.status_code == 200

        res_v = client.post("/api/v1/provenance/verify", json={"target_id": sample_tile_id})
        assert res_v.status_code == 200

        res_e = client.get(f"/api/v1/provenance/export/{sample_tile_id}")
        assert res_e.status_code == 201

        res_a = client.get("/api/v1/provenance/audit-log?limit=5")
        assert res_a.status_code == 200
        log("Milestone 9 REST API Endpoints", "PASS", "GET /provenance/graph, POST /verify, GET /export, GET /audit-log 200/201 OK")

        # 7. Air-Gapped Network Isolation Guard
        orig_connect = socket.socket.connect
        def block_external(self, address):
            host = address[0]
            if str(host) in ("127.0.0.1", "localhost", "::1"):
                return orig_connect(self, address)
            raise RuntimeError(f"Air-gap violation: outbound socket to {host}")

        try:
            socket.socket.connect = block_external
            res_airgap = client.get(f"/api/v1/provenance/graph/{sample_tile_id}")
            assert res_airgap.status_code == 200
            log("Milestone 9 Air-Gap Network Isolation", "PASS", "Zero outbound network calls verified under strict socket interception")
        finally:
            socket.socket.connect = orig_connect

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        log("Milestone 9 Provenance & Hardening", "FAIL", f"{type(e).__name__}: {e}")
        return False


def verify_milestone10_evaluation() -> bool:
    """Verifies Milestone 10 automated benchmark evaluation engine, schemas, and REST endpoints."""
    try:
        from apps.backend.app.services.evaluation.benchmark_runner import BenchmarkRunnerService
        from apps.backend.app.main import create_app
        from fastapi.testclient import TestClient

        # 1. Benchmark Runner Service
        runner = BenchmarkRunnerService(project_root=PROJECT_ROOT)
        report = runner.get_latest_report(run_if_missing=True)

        assert report.report_id.startswith("bench_")
        assert report.all_benchmarks_passed is True
        assert report.retrieval.queries_evaluated >= 4
        assert report.change_detection.true_positive_preservation_pct >= 95.0
        assert report.change_detection.false_alarm_suppression_pct >= 95.0
        assert report.provenance.tampered_artifacts_detected >= 1
        assert report.system.evidence_first_completeness_pct == 100.0
        assert report.system.airgap_isolation_verified is True

        log(
            "Milestone 10 Automated Benchmark Suite",
            "PASS",
            f"Report {report.report_id} ({report.duration_seconds}s, P@5={report.retrieval.semantic.mean_precision_at_k:.2f}, Suppress={report.change_detection.false_alarm_suppression_pct:.0f}%)"
        )

        # 2. REST Endpoints
        app = create_app()
        client = TestClient(app)

        res_sum = client.get("/api/v1/evaluation/summary")
        assert res_sum.status_code == 200
        data_sum = res_sum.json()
        assert data_sum["report_id"] == report.report_id

        res_run = client.post("/api/v1/evaluation/run?top_k=3")
        assert res_run.status_code == 201
        data_run = res_run.json()
        assert data_run["retrieval"]["top_k"] == 3

        log("Milestone 10 REST API Endpoints", "PASS", "GET /api/v1/evaluation/summary & POST /api/v1/evaluation/run 200/201 OK")

        # 3. Benchmark Artifact Verification
        md_file = PROJECT_ROOT / "docs" / "BENCHMARK_REPORT.md"
        json_file = PROJECT_ROOT / "data" / "processed" / "evaluation" / "benchmark_report.json"
        assert md_file.exists(), "docs/BENCHMARK_REPORT.md missing"
        assert json_file.exists(), "data/processed/evaluation/benchmark_report.json missing"
        log("Milestone 10 Report Artifacts", "PASS", f"Verified {md_file.name} ({md_file.stat().st_size} bytes) & {json_file.name}")

        return True
    except Exception as e:
        import traceback
        traceback.print_exc()
        log("Milestone 10 Benchmark Evaluation", "FAIL", f"{type(e).__name__}: {e}")
        return False


def main():
    print("=" * 60)
    print("ASTRATRACE MILESTONE 1 - 10 COMPLETE VERIFICATION SUITE")
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
        verify_semantic_retrieval(),
        verify_quality_gate(),
        verify_milestone8_search_and_review(),
        verify_milestone9_provenance_and_hardening(),
        verify_milestone10_evaluation(),
    ]

    print("=" * 60)
    if all(results):
        print("\033[92m[SUCCESS] All Milestone 1 through 10 verification checks PASSED.\033[0m")
        sys.exit(0)
    else:
        print("\033[91m[FAILURE] One or more verification checks FAILED.\033[0m")
        sys.exit(1)


if __name__ == "__main__":
    main()

