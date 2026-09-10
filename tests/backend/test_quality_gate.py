"""Automated Tests for Quality Gate & False-Alarm Suppression (Milestone 7).

SIH 2026 | Problem ID: SIH26227
Validates optical quality detection, cloud/shadow suppression, pair usability,
co-registration proxies, uncertainty states, and REST API endpoints.
"""
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.db.session import init_db
from apps.backend.app.main import create_app
from apps.backend.app.schemas.quality import (
    QualityDecision,
    QualityGatedChangeRequest,
    QualityStatus,
)
from apps.backend.app.services.quality.pair_quality import PairQualityEvaluator
from apps.backend.app.services.quality.quality_detector import TileQualityDetector
from apps.backend.app.services.quality.quality_gate import QualityGate
from apps.backend.app.services.quality.service import QualityService

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TILE_2023_0 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"
TILE_2024_0 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0000.tif"
TILE_2023_1 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0001.tif"
TILE_2024_1 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0001.tif"


@pytest.fixture
def test_client():
    """FastAPI TestClient configured with database."""
    init_db()
    app = create_app()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# 1. Optical Tile Quality Detector Unit Tests
# ==============================================================================

def test_tile_quality_clean_image():
    """Verifies that a clear observation achieves a high quality score and USABLE status."""
    detector = TileQualityDetector()
    if not TILE_2023_0.exists():
        pytest.skip("Sample raster missing")

    metrics, masks = detector.analyze_raster(TILE_2023_0)
    assert metrics.total_pixels == 65536
    assert metrics.valid_pixels > 60000
    assert metrics.quality_score >= 0.85
    assert metrics.quality_status in [QualityStatus.USABLE, QualityStatus.DEGRADED]
    assert "usable" in masks
    assert masks["usable"].shape == (256, 256)


def test_tile_quality_cloud_detection():
    """Verifies that high-reflectance white cloud pixels are detected and flagged."""
    detector = TileQualityDetector()
    # Create 256x256 4-band image
    arr = np.full((4, 256, 256), 1000.0, dtype=np.float32)
    # Inject bright white cloud patch (50x50) in center
    arr[:, 100:150, 100:150] = 6000.0

    metrics, masks = detector.analyze_raster(arr)
    assert metrics.cloud_pixels == 2500  # 50x50
    assert metrics.cloud_fraction == pytest.approx(2500 / 65536, abs=1e-3)
    assert np.sum(masks["cloud"]) == 2500
    assert "CLOUD_CONTAMINATION_MODERATE" in metrics.quality_flags or "CLOUD_CONTAMINATION_HIGH" in metrics.quality_flags


def test_tile_quality_shadow_detection():
    """Verifies that low visible and NIR non-water pixels are identified as cloud shadow."""
    detector = TileQualityDetector()
    arr = np.full((4, 256, 256), 2500.0, dtype=np.float32)
    # Inject shadow patch (40x40): very low NIR and visible, low NDWI
    arr[:, 50:90, 50:90] = 400.0

    metrics, masks = detector.analyze_raster(arr)
    assert metrics.shadow_pixels == 1600  # 40x40
    assert "CLOUD_SHADOW_DETECTED" in metrics.quality_flags
    assert np.sum(masks["shadow"]) == 1600


def test_tile_quality_nodata_detection():
    """Verifies that NoData values and all-zero edge pixels are accurately masked."""
    detector = TileQualityDetector()
    arr = np.full((4, 256, 256), 2000.0, dtype=np.float32)
    # 50 columns of nodata (all zeros)
    arr[:, :, :50] = 0.0

    metrics, masks = detector.analyze_raster(arr)
    expected_nodata = 50 * 256
    assert metrics.nodata_pixels == expected_nodata
    assert metrics.valid_pixels == (65536 - expected_nodata)
    assert "usable" in masks
    assert not np.any(masks["usable"][:, :50])


def test_tile_quality_saturation():
    """Verifies that sensor saturation pixels are detected and flagged."""
    detector = TileQualityDetector()
    arr = np.full((4, 256, 256), 2000.0, dtype=np.float32)
    # Inject saturated pixels (> 9800)
    arr[0, 10:20, 10:20] = 9950.0

    metrics, masks = detector.analyze_raster(arr)
    assert metrics.saturated_pixels == 100
    assert "SENSOR_SATURATION_DETECTED" in metrics.quality_flags


def test_tile_quality_all_zeros():
    """Verifies that an entirely empty/nodata raster fails safely with INSUFFICIENT status."""
    detector = TileQualityDetector()
    arr = np.zeros((4, 256, 256), dtype=np.float32)

    metrics, masks = detector.analyze_raster(arr)
    assert metrics.valid_pixels == 0
    assert metrics.nodata_pixels == 65536
    assert metrics.usable_pixels == 0
    assert metrics.quality_status == QualityStatus.INSUFFICIENT
    assert "ALL_NODATA" in metrics.quality_flags


# ==============================================================================
# 2. Temporal Pair Quality Evaluator Tests
# ==============================================================================

def test_pair_quality_mutual_usable_area():
    """Verifies that mutual usable area is the boolean intersection of both observations."""
    evaluator = PairQualityEvaluator()
    arr1 = np.full((4, 100, 100), 2000.0, dtype=np.float32)
    arr2 = np.full((4, 100, 100), 2000.0, dtype=np.float32)

    # arr1 has cloud on left half (cols 0..50)
    arr1[:, :, :50] = 6000.0
    # arr2 has shadow on top half (rows 0..50)
    arr2[:, :50, :] = 300.0

    metrics, masks = evaluator.evaluate_pair(arr1, arr2)
    # Mutual usable should only be bottom-right quadrant (rows 50..100, cols 50..100) -> 50x50 = 2500 px
    assert metrics.mutual_usable_pixels == 2500
    assert pytest.approx(metrics.mutual_usable_fraction, abs=1e-2) == 0.25


def test_pair_quality_registration_check():
    """Verifies spatial co-registration proxy and gradient alignment score."""
    evaluator = PairQualityEvaluator()
    if not (TILE_2023_0.exists() and TILE_2024_0.exists()):
        pytest.skip("Sample rasters missing")

    metrics, masks = evaluator.evaluate_pair(TILE_2023_0, TILE_2024_0)
    assert metrics.registration_score >= 0.70
    assert metrics.pair_quality_score > 0.0
    assert masks["mutual_usable"].shape == (256, 256)


def test_pair_quality_temporal_ordering():
    """Verifies detection of inverted temporal acquisition sequence (T2 earlier than T1)."""
    evaluator = PairQualityEvaluator()
    arr = np.full((4, 100, 100), 2000.0, dtype=np.float32)

    t1_dt = datetime(2024, 1, 1, tzinfo=timezone.utc)
    t2_dt = datetime(2023, 1, 1, tzinfo=timezone.utc)  # Inverted!

    metrics, _ = evaluator.evaluate_pair(arr, arr, t1_acquired_at=t1_dt, t2_acquired_at=t2_dt)
    assert "TEMPORAL_ORDER_INVERTED" in metrics.pair_flags
    assert metrics.temporal_baseline_days < 0


# ==============================================================================
# 3. False-Alarm Suppression & Quality Gate Tests
# ==============================================================================

def test_false_alarm_suppression_cloud():
    """Verifies that changes induced solely by an injected cloud patch are completely suppressed."""
    gate = QualityGate(project_root=PROJECT_ROOT)
    arr1 = np.full((4, 256, 256), 2000.0, dtype=np.float32)
    arr2 = arr1.copy()

    # Inject bright cloud into T2 (50x50 patch)
    arr2[:, 100:150, 100:150] = 6000.0

    req = QualityGatedChangeRequest(
        before_tile_path="dummy1.tif",
        after_tile_path="dummy2.tif",
        threshold=0.15,
        suppress_clouds=True,
    )
    resp = gate.evaluate_change(arr1, arr2, request=req)

    assert resp.raw_changed_pixels >= 2500  # Baseline detector triggered
    assert resp.suppression_breakdown.cloud_suppressed_pixels >= 2500
    assert resp.verified_changed_pixels == 0  # Quality gate suppressed false alarm!
    assert resp.decision == QualityDecision.QUALITY_SUPPRESSED
    assert resp.final_confidence == 0.0
    assert resp.change_type == "no_change"


def test_false_alarm_suppression_shadow():
    """Verifies that changes induced solely by a cloud shadow patch are completely suppressed."""
    gate = QualityGate(project_root=PROJECT_ROOT)
    arr1 = np.full((4, 256, 256), 2500.0, dtype=np.float32)
    arr2 = arr1.copy()

    # Inject shadow into T2 (40x40 patch)
    arr2[:, 80:120, 80:120] = 400.0

    req = QualityGatedChangeRequest(
        before_tile_path="dummy1.tif",
        after_tile_path="dummy2.tif",
        threshold=0.15,
        suppress_shadows=True,
    )
    resp = gate.evaluate_change(arr1, arr2, request=req)

    assert resp.raw_changed_pixels >= 1600
    assert resp.suppression_breakdown.shadow_suppressed_pixels >= 1600
    assert resp.verified_changed_pixels == 0
    assert resp.decision == QualityDecision.QUALITY_SUPPRESSED


def test_false_alarm_boundary_artifacts():
    """Verifies suppression of edge artifacts near NoData borders."""
    gate = QualityGate(project_root=PROJECT_ROOT)
    arr1 = np.full((4, 256, 256), 2000.0, dtype=np.float32)
    arr2 = arr1.copy()

    # Set cols 0..20 to nodata (0)
    arr1[:, :, :20] = 0.0
    arr2[:, :, :20] = 0.0

    # Add a thin 1-pixel false edge shift at col 21
    arr2[:, :, 21] = 4000.0

    req = QualityGatedChangeRequest(
        before_tile_path="dummy1.tif",
        after_tile_path="dummy2.tif",
        threshold=0.15,
        suppress_clouds=False,
        suppress_boundaries=True,
        apply_morphology=False,
    )
    resp = gate.evaluate_change(arr1, arr2, request=req)
    assert resp.suppression_breakdown.boundary_suppressed_pixels > 0


def test_uncertainty_state_assignment():
    """Verifies that observations with <20% mutual usable area transition to UNCERTAIN state."""
    gate = QualityGate(project_root=PROJECT_ROOT)
    arr1 = np.full((4, 256, 256), 2000.0, dtype=np.float32)
    arr2 = arr1.copy()

    # 90% cloud cover
    arr2[:, :, :230] = 6000.0

    req = QualityGatedChangeRequest(
        before_tile_path="dummy1.tif",
        after_tile_path="dummy2.tif",
        min_usable_fraction=0.20,
    )
    resp = gate.evaluate_change(arr1, arr2, request=req)

    assert resp.decision == QualityDecision.UNCERTAIN
    assert resp.is_uncertain is True
    assert resp.final_confidence == 0.0
    assert "UNCERTAIN" in resp.explanation


def test_true_change_preservation():
    """Verifies that genuine surface change in clear mutual usable areas is fully preserved."""
    if not (TILE_2023_1.exists() and TILE_2024_1.exists()):
        pytest.skip("Synthetic construction tiles missing")

    gate = QualityGate(project_root=PROJECT_ROOT)
    req = QualityGatedChangeRequest(
        before_tile_path=str(TILE_2023_1),
        after_tile_path=str(TILE_2024_1),
        threshold=0.15,
    )
    resp = gate.evaluate_change(TILE_2023_1, TILE_2024_1, request=req)

    assert resp.raw_changed_pixels == 4800
    assert resp.verified_changed_pixels == 4800  # Ground truth 100% preserved
    assert resp.change_type == "construction"
    assert resp.is_uncertain is False
    assert resp.final_confidence > 0.0


def test_confidence_modulation():
    """Verifies that final confidence is mathematically modulated by the pair quality score."""
    gate = QualityGate(project_root=PROJECT_ROOT)
    if not (TILE_2023_1.exists() and TILE_2024_1.exists()):
        pytest.skip("Synthetic tiles missing")

    req = QualityGatedChangeRequest(
        before_tile_path=str(TILE_2023_1),
        after_tile_path=str(TILE_2024_1),
        threshold=0.15,
    )
    resp = gate.evaluate_change(TILE_2023_1, TILE_2024_1, request=req)

    expected_conf = round(resp.raw_change_score * resp.pair_quality_score, 4)
    assert pytest.approx(resp.final_confidence, abs=1e-3) == expected_conf


def test_nan_inf_safe_handling():
    """Verifies that arrays containing NaN and Inf values are safely sanitized and processed."""
    detector = TileQualityDetector()
    arr = np.full((4, 100, 100), 2000.0, dtype=np.float32)
    arr[0, 10, 10] = np.nan
    arr[1, 20, 20] = np.inf
    arr[2, 30, 30] = -np.inf

    metrics, masks = detector.analyze_raster(arr)
    assert "NAN_INF_VALUES_DETECTED" in metrics.quality_flags
    assert metrics.valid_pixels < 10000


# ==============================================================================
# 4. REST API Endpoint Tests
# ==============================================================================

def test_api_assess_tile(test_client):
    """Verifies POST /api/v1/quality/assess-tile returns 200 with schema-valid metrics."""
    payload = {"tile_id": "scn_sentinel-2_20230115_96ed9480_t0000"}
    res = test_client.post("/api/v1/quality/assess-tile", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert "quality_score" in data
    assert "quality_status" in data
    assert "usable_fraction" in data
    assert 0.0 <= data["quality_score"] <= 1.0


def test_api_assess_pair(test_client):
    """Verifies POST /api/v1/quality/assess-pair returns 200 with pair quality diagnostics."""
    payload = {
        "t1_input": "scn_sentinel-2_20230115_96ed9480_t0001",
        "t2_input": "scn_sentinel-2_20241222_7acad713_t0001",
    }
    res = test_client.post("/api/v1/quality/assess-pair", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert "pair_quality_score" in data
    assert "mutual_usable_fraction" in data
    assert "registration_score" in data


def test_api_detect_gated_change(test_client):
    """Verifies POST /api/v1/change/detect-gated returns 200 with complete quality-gated response."""
    payload = {
        "before_tile_id": "scn_sentinel-2_20230115_96ed9480_t0001",
        "after_tile_id": "scn_sentinel-2_20241222_7acad713_t0001",
        "threshold": 0.15,
        "suppress_clouds": True,
        "suppress_shadows": True,
    }
    res = test_client.post("/api/v1/change/detect-gated", json=payload)
    assert res.status_code == 200

    data = res.json()
    assert data["change_id"].startswith("qchg_")
    assert "decision" in data
    assert "suppression_breakdown" in data
    assert "raw_change_score" in data
    assert "final_confidence" in data
    assert data["verified_changed_pixels"] == 4800
    assert "mask_url" in data
    assert "provenance" in data
