"""Automated Tests for Baseline Change Detection Pipeline (Milestone 5).

SIH 2026 | Problem ID: SIH26227
Validates bitemporal raster comparison, spectral differencing, pure-NumPy morphology,
ground-truth synthetic change detection, API validation, and forensic provenance.
"""
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.db.session import init_db
from apps.backend.app.main import create_app
from apps.backend.app.schemas.change import ChangeDetectionRequest, ScenePairChangeRequest
from apps.backend.app.services.change.detector import BaselineChangeDetector
from apps.backend.app.services.change.differencing import (
    compute_index_deltas,
    compute_otsu_threshold,
    compute_spectral_difference,
)
from apps.backend.app.services.change.morphology import (
    binary_closing,
    binary_dilation,
    binary_erosion,
    binary_opening,
    filter_small_components,
)
from apps.backend.app.services.change.service import ChangeDetectionService

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TILE_2023_0 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"
TILE_2023_1 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0001.tif"
TILE_2024_0 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0000.tif"
TILE_2024_1 = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0001.tif"


@pytest.fixture
def test_client():
    """FastAPI TestClient with initialized database."""
    init_db()
    app = create_app()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# 1. Pure NumPy Morphology Tests
# ==============================================================================

def test_morphology_erosion_dilation():
    """Verifies binary erosion shrinks and dilation expands 1-pixel components."""
    mask = np.zeros((7, 7), dtype=bool)
    mask[2:5, 2:5] = True  # 3x3 square

    eroded = binary_erosion(mask, kernel_size=3)
    assert np.sum(eroded) == 1
    assert eroded[3, 3] is True or eroded[3, 3] == 1

    dilated = binary_dilation(mask, kernel_size=3)
    assert np.sum(dilated) == 25  # 5x5 square


def test_morphology_opening_closing():
    """Verifies opening eliminates isolated noise and closing fills internal holes."""
    # Opening removes isolated 1-pixel
    noise_mask = np.zeros((9, 9), dtype=bool)
    noise_mask[1, 1] = True  # isolated 1-pixel
    noise_mask[4:8, 4:8] = True  # large 4x4 block

    opened = binary_opening(noise_mask, kernel_size=3)
    assert opened[1, 1] is False or opened[1, 1] == 0
    assert np.sum(opened[4:8, 4:8]) > 0

    # Closing fills 1-pixel interior hole
    hole_mask = np.ones((7, 7), dtype=bool)
    hole_mask[3, 3] = False  # interior hole
    closed = binary_closing(hole_mask, kernel_size=3)
    assert closed[3, 3] is True or closed[3, 3] == 1


def test_filter_small_components():
    """Verifies connected-component filter discards blobs smaller than min_pixels."""
    mask = np.zeros((10, 10), dtype=bool)
    mask[1, 1] = True  # 1-pixel blob
    mask[1, 2] = True  # 2-pixel component
    mask[5:9, 5:9] = True  # 16-pixel component

    filtered = filter_small_components(mask, min_pixels=5)
    assert filtered[1, 1] is False or filtered[1, 1] == 0
    assert filtered[1, 2] is False or filtered[1, 2] == 0
    assert np.sum(filtered[5:9, 5:9]) == 16


# ==============================================================================
# 2. Spectral Differencing & Index Delta Mathematics
# ==============================================================================

def test_spectral_difference_math():
    """Verifies normalized Euclidean distance bounds and identity."""
    t1 = np.ones((4, 10, 10), dtype=np.float32) * 500.0
    t2 = t1.copy()

    # Identical rasters -> zero difference
    diff_zero = compute_spectral_difference(t1, t2)
    assert np.all(diff_zero == 0.0)

    # 100% higher reflectance
    t2_high = t1 * 2.0
    diff_high = compute_spectral_difference(t1, t2_high)
    assert np.all(diff_high > 0.0)
    assert np.all(diff_high <= 1.0)


def test_index_deltas_math():
    """Verifies Delta NDVI, Delta NDWI, and Delta Brightness signatures."""
    # Bands: 0: Blue, 1: Green, 2: Red, 3: NIR
    t1 = np.zeros((4, 5, 5), dtype=np.float32)
    t1[2] = 400.0   # Red
    t1[3] = 2000.0  # High NIR (Dense vegetation)

    t2 = t1.copy()
    t2[0] = 2500.0  # Bright Blue
    t2[1] = 2500.0  # Bright Green
    t2[2] = 2500.0  # Bright Red (Concrete/Metal)
    t2[3] = 2500.0  # High NIR

    deltas = compute_index_deltas(t1, t2)
    # Vegetation should decrease (NIR was high relative to Red, now equal)
    assert np.mean(deltas["delta_ndvi"]) < 0.0
    # Brightness should increase significantly
    assert np.mean(deltas["delta_brightness"]) > 0.5


def test_otsu_threshold_bounds():
    """Verifies Otsu threshold calculation and clamping."""
    magnitude = np.zeros((50, 50), dtype=np.float32)
    magnitude[10:30, 10:30] = 0.8  # Distinct bright change region

    tau = compute_otsu_threshold(magnitude, min_threshold=0.15, max_threshold=0.65)
    assert 0.15 <= tau <= 0.65


# ==============================================================================
# 3. Baseline Change Detector Ground-Truth Verification
# ==============================================================================

def test_identical_rasters_zero_change():
    """Comparing identical rasters yields zero changed pixels and score 0.0."""
    if not TILE_2023_0.exists():
        pytest.skip(f"Tile {TILE_2023_0} does not exist.")

    detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
    result = detector.detect_change(TILE_2023_0, TILE_2023_0)

    assert result["changed_pixels"] == 0
    assert result["change_percent"] == 0.0
    assert result["composite_change_score"] == 0.0
    assert result["change_type"] == "no_change"


def test_ground_truth_synthetic_construction_change():
    """Tile 1 contains a known synthetic 60x80 (4800 px) warehouse construction."""
    if not TILE_2023_1.exists() or not TILE_2024_1.exists():
        pytest.skip("Bitemporal tile pair required.")

    detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
    result = detector.detect_change(
        TILE_2023_1,
        TILE_2024_1,
        threshold=0.15,
        min_pixels=10,
        apply_morphology=True,
    )

    # Exactly 4800 pixels were modified in tile 1 (rows 180:240, cols 280:360)
    assert result["changed_pixels"] == 4800
    assert result["change_type"] == "construction"
    assert result["composite_change_score"] > 0.40
    assert result["index_deltas_mean"]["delta_brightness"] > 0.50
    assert result["index_deltas_mean"]["delta_ndvi"] < -0.30


def test_negative_control_unchanged_tile0():
    """Tile 0 has no synthetic modifications between 2023 and 2024."""
    if not TILE_2023_0.exists() or not TILE_2024_0.exists():
        pytest.skip("Bitemporal tile pair required.")

    detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
    result = detector.detect_change(TILE_2023_0, TILE_2024_0, threshold=0.15)

    assert result["changed_pixels"] == 0
    assert result["change_type"] == "no_change"
    assert result["composite_change_score"] == 0.0


# ==============================================================================
# 4. Error Handling & Preprocessing Validation
# ==============================================================================

def test_validation_nonexistent_file():
    """Comparing against a nonexistent file raises NotFoundError."""
    detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
    with pytest.raises(NotFoundError):
        detector.detect_change("data/nonexistent_t1.tif", "data/nonexistent_t2.tif")


def test_validation_invalid_threshold():
    """Passing a threshold outside [0.01, 0.99] raises ValidationError."""
    if not TILE_2023_0.exists():
        pytest.skip("Sample tile required.")

    detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
    with pytest.raises(ValidationError):
        detector.detect_change(TILE_2023_0, TILE_2023_0, threshold=1.50)


# ==============================================================================
# 5. Service & Provenance Tracking Tests
# ==============================================================================

def test_change_service_detect_tile_pair():
    """Verifies service resolves catalog tile IDs, computes change, and records provenance."""
    tile_id_t1 = "scn_sentinel-2_20230115_96ed9480_t0001"
    tile_id_t2 = "scn_sentinel-2_20241222_7acad713_t0001"

    with ChangeDetectionService(project_root=PROJECT_ROOT) as service:
        req = ChangeDetectionRequest(
            before_tile_id=tile_id_t1,
            after_tile_id=tile_id_t2,
            threshold=0.15,
        )
        response = service.detect_tile_pair(req)

        assert response.change_id.startswith("chg_")
        assert response.before.tile_id == tile_id_t1
        assert response.after.tile_id == tile_id_t2
        assert len(response.before.checksum) == 64
        assert len(response.after.checksum) == 64
        assert response.metrics.changed_pixels == 4800
        assert response.metrics.change_type == "construction"
        assert response.mask_path is not None
        assert Path(PROJECT_ROOT / response.mask_path).exists()


def test_change_service_batch_scene_pair():
    """Verifies batch pairing and analysis across two scenes."""
    scene_id_t1 = "scn_sentinel-2_20230115_96ed9480"
    scene_id_t2 = "scn_sentinel-2_20241222_7acad713"

    with ChangeDetectionService(project_root=PROJECT_ROOT) as service:
        req = ScenePairChangeRequest(
            scene_id_t1=scene_id_t1,
            scene_id_t2=scene_id_t2,
            threshold=0.15,
            max_tiles=5,
        )
        response = service.detect_scene_pair(req)

        assert response.pairs_evaluated == 5
        assert response.changes_detected >= 1
        assert len(response.results) == 5


# ==============================================================================
# 6. REST API Endpoints Tests
# ==============================================================================

def test_api_detect_change_endpoint_success(test_client):
    """Verifies POST /api/v1/change/detect endpoint."""
    payload = {
        "before_tile_id": "scn_sentinel-2_20230115_96ed9480_t0001",
        "after_tile_id": "scn_sentinel-2_20241222_7acad713_t0001",
        "threshold": 0.15,
    }
    response = test_client.post("/api/v1/change/detect", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["change_id"].startswith("chg_")
    assert data["metrics"]["change_type"] == "construction"
    assert data["metrics"]["changed_pixels"] == 4800
    assert data["mask_url"] is not None

    # Test downloading mask
    mask_res = test_client.get(data["mask_url"])
    assert mask_res.status_code == 200
    assert mask_res.headers["content-type"] == "image/png"


def test_api_detect_change_validation_error(test_client):
    """Verifies missing required tile identifiers returns 422."""
    payload = {"threshold": 0.50}
    response = test_client.post("/api/v1/change/detect", json=payload)
    assert response.status_code == 422


def test_api_scene_pair_endpoint_success(test_client):
    """Verifies POST /api/v1/change/scene-pair endpoint."""
    payload = {
        "scene_id_t1": "scn_sentinel-2_20230115_96ed9480",
        "scene_id_t2": "scn_sentinel-2_20241222_7acad713",
        "max_tiles": 3,
    }
    response = test_client.post("/api/v1/change/scene-pair", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["pairs_evaluated"] == 3
    assert len(data["results"]) == 3


def test_deterministic_repeated_execution():
    """Running detection twice produces bitwise identical change metrics and scores."""
    if not TILE_2023_1.exists() or not TILE_2024_1.exists():
        pytest.skip("Tile files required.")

    detector = BaselineChangeDetector(project_root=PROJECT_ROOT)
    run1 = detector.detect_change(TILE_2023_1, TILE_2024_1, threshold=0.15)
    run2 = detector.detect_change(TILE_2023_1, TILE_2024_1, threshold=0.15)

    assert run1["changed_pixels"] == run2["changed_pixels"]
    assert run1["composite_change_score"] == run2["composite_change_score"]
    assert run1["mean_magnitude"] == run2["mean_magnitude"]
    assert run1["change_type"] == run2["change_type"]
