"""Automated Unit and Integration Tests for Baseline Retrieval Pipeline (Milestone 4).

SIH 2026 | Problem ID: SIH26227
Tests controlled vocabulary parsing, spectral feature extraction, multi-factor scoring,
service integration, API validation, and search determinism.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from sqlalchemy.pool import StaticPool

from apps.backend.app.main import create_app
from apps.backend.app.db.session import Base, init_db, get_db
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.schemas.search import BaselineSearchRequest
from apps.backend.app.services.catalog import CatalogService
from apps.backend.app.services.retrieval.baseline_classifier import TileFeatureClassifier
from apps.backend.app.services.retrieval.baseline_scorer import BaselineScorer
from apps.backend.app.services.retrieval.service import BaselineRetrievalService
from apps.backend.app.services.retrieval.vocabulary import (
    EUROSAT_CLASSES,
    ControlledVocabulary,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_MANIFEST = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "manifest.json"
SAMPLE_TILE = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"


@pytest.fixture
def memory_db():
    """Provides an isolated in-memory SQLite session with StaticPool for thread safety."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    # Pre-populate with sample manifest if present
    if SAMPLE_MANIFEST.exists():
        cat_service = CatalogService(db=session, project_root=PROJECT_ROOT)
        cat_service.register_manifest(SAMPLE_MANIFEST)

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client():
    """FastAPI TestClient configured with catalog database."""
    init_db()
    app = create_app()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# 1. Controlled Vocabulary & Synset Parser Tests
# ==============================================================================

def test_vocabulary_exact_matches():
    """Verifies direct EuroSAT class token matching."""
    for cls_name in EUROSAT_CLASSES:
        weights, is_oov = ControlledVocabulary.parse_query(cls_name.lower())
        assert not is_oov
        assert cls_name in weights
        assert weights[cls_name] > 0.5
        assert pytest.approx(sum(weights.values()), rel=1e-2) == 1.0


def test_vocabulary_synonym_resolution():
    """Verifies operational synonyms resolve to correct land-cover classes."""
    # "urban" -> Residential & Industrial
    weights, is_oov = ControlledVocabulary.parse_query("urban")
    assert not is_oov
    assert "Residential" in weights
    assert "Industrial" in weights

    # "warehouse" -> Industrial
    weights, is_oov = ControlledVocabulary.parse_query("industrial warehouse storage")
    assert not is_oov
    assert weights.get("Industrial", 0.0) > 0.6

    # "highway" / "corridor" -> Highway
    weights, is_oov = ControlledVocabulary.parse_query("highway road corridor")
    assert not is_oov
    assert weights.get("Highway", 0.0) > 0.6

    # "river stream canal" -> River
    weights, is_oov = ControlledVocabulary.parse_query("river stream canal")
    assert not is_oov
    assert weights.get("River", 0.0) > 0.7


def test_vocabulary_oov_and_empty():
    """Verifies out-of-vocabulary and empty queries fallback uniformly."""
    weights_empty, is_oov_empty = ControlledVocabulary.parse_query("")
    assert is_oov_empty
    assert len(weights_empty) == len(EUROSAT_CLASSES)
    assert pytest.approx(sum(weights_empty.values()), rel=1e-2) == 1.0

    weights_oov, is_oov = ControlledVocabulary.parse_query("xyzqwk12984 meaningless")
    assert is_oov
    assert len(weights_oov) == len(EUROSAT_CLASSES)
    assert pytest.approx(sum(weights_oov.values()), rel=1e-2) == 1.0


# ==============================================================================
# 2. Spectral Feature Extraction & Classification Tests
# ==============================================================================

def test_feature_extraction():
    """Verifies spectral and texture feature computation on actual GeoTIFF tile."""
    if not SAMPLE_TILE.exists():
        pytest.skip(f"Sample tile {SAMPLE_TILE} does not exist.")

    classifier = TileFeatureClassifier(project_root=PROJECT_ROOT)
    features = classifier.extract_features(SAMPLE_TILE)

    assert "mean_ndvi" in features
    assert "mean_ndwi" in features
    assert "mean_brightness" in features
    assert "edge_density" in features
    assert "road_contrast" in features

    # Check realistic physical boundaries
    assert -1.0 <= features["mean_ndvi"] <= 1.0
    assert -1.0 <= features["mean_ndwi"] <= 1.0
    assert features["mean_brightness"] >= 0.0
    assert features["edge_density"] >= 0.0


def test_tile_classification_probabilities():
    """Verifies classifier returns valid normalized probability distribution."""
    if not SAMPLE_TILE.exists():
        pytest.skip(f"Sample tile {SAMPLE_TILE} does not exist.")

    classifier = TileFeatureClassifier(project_root=PROJECT_ROOT)
    probs = classifier.classify_tile(SAMPLE_TILE)

    assert len(probs) == len(EUROSAT_CLASSES)
    for c in EUROSAT_CLASSES:
        assert c in probs
        assert 0.0 <= probs[c] <= 1.0

    prob_sum = sum(probs.values())
    assert pytest.approx(prob_sum, rel=1e-2) == 1.0

    # Test caching
    classifier.classify_tile(SAMPLE_TILE)
    assert str(SAMPLE_TILE).replace("\\", "/") in classifier._cache


# ==============================================================================
# 3. Multi-Factor Scorer Mathematical Boundaries
# ==============================================================================

def test_scorer_class_alignment():
    """Verifies dot product semantic alignment score."""
    scorer = BaselineScorer()
    target_weights = {"Forest": 0.8, "HerbaceousVegetation": 0.2}

    # High match tile
    high_tile = {"Forest": 0.9, "HerbaceousVegetation": 0.1, "Highway": 0.0}
    score, top_cls, top_conf, matched = scorer.compute_class_score(target_weights, high_tile)
    assert score > 0.7
    assert top_cls == "Forest"
    assert "Forest" in matched

    # Low match tile
    low_tile = {"SeaLake": 0.9, "River": 0.1, "Forest": 0.0}
    score_low, _, _, _ = scorer.compute_class_score(target_weights, low_tile)
    assert score_low == 0.0


def test_scorer_spatial_overlap():
    """Verifies 2D bounding box intersection and IoU scoring."""
    scorer = BaselineScorer()
    tile_bbox = [73.50, 18.50, 73.60, 18.60]

    # Perfect identical bbox
    score_exact = scorer.compute_spatial_score(tile_bbox, query_bbox=(73.50, 18.50, 73.60, 18.60))
    assert pytest.approx(score_exact, rel=1e-2) == 1.0

    # Completely disjoint bbox
    score_disjoint = scorer.compute_spatial_score(tile_bbox, query_bbox=(74.00, 19.00, 74.10, 19.10))
    assert score_disjoint == 0.0

    # Partial overlap
    score_partial = scorer.compute_spatial_score(tile_bbox, query_bbox=(73.55, 18.55, 73.65, 18.65))
    assert 0.0 < score_partial < 1.0

    # Point query inside
    score_pt_inside = scorer.compute_spatial_score(tile_bbox, query_point=(73.55, 18.55))
    assert score_pt_inside == 1.0

    # Point query outside
    score_pt_outside = scorer.compute_spatial_score(tile_bbox, query_point=(74.00, 19.00))
    assert score_pt_outside == 0.0


def test_scorer_temporal_decay():
    """Verifies temporal recency ranking."""
    scorer = BaselineScorer()
    date_from = datetime(2023, 1, 1, tzinfo=timezone.utc)
    date_to = datetime(2025, 1, 1, tzinfo=timezone.utc)

    # Earlier observation
    t_early = datetime(2023, 6, 1, tzinfo=timezone.utc)
    score_early = scorer.compute_temporal_score(t_early, date_from, date_to)

    # Later observation
    t_late = datetime(2024, 12, 1, tzinfo=timezone.utc)
    score_late = scorer.compute_temporal_score(t_late, date_from, date_to)

    assert score_late > score_early
    assert 0.70 <= score_early <= 1.0
    assert 0.70 <= score_late <= 1.0


def test_composite_score_bounds():
    """Verifies composite score stays bounded in [0.0, 1.0]."""
    scorer = BaselineScorer(weight_class=0.6, weight_spatial=0.25, weight_temporal=0.15)
    comp, bd = scorer.compute_composite_score(0.8, 0.9, 0.7)
    assert 0.0 <= comp <= 1.0
    assert bd["class_score"] == 0.8
    assert bd["spatial_score"] == 0.9
    assert bd["temporal_score"] == 0.7


# ==============================================================================
# 4. Baseline Retrieval Service End-to-End Tests
# ==============================================================================

def test_retrieval_service_search(memory_db):
    """Verifies end-to-end baseline search against cataloged tiles."""
    if not SAMPLE_MANIFEST.exists():
        pytest.skip("Sample manifest required for service test.")

    service = BaselineRetrievalService(db=memory_db, project_root=PROJECT_ROOT)
    req = BaselineSearchRequest(
        query="forest vegetation",
        bbox=(73.57, 18.94, 73.63, 18.99),
        top_k=5,
    )
    response = service.search(req)

    assert response.query == "forest vegetation"
    assert "Forest" in response.matched_vocabulary
    assert response.total_candidates >= 9
    assert len(response.results) <= 5
    assert len(response.results) > 0

    # Ensure results are sorted descending by baseline_score
    scores = [r.baseline_score for r in response.results]
    assert scores == sorted(scores, reverse=True)

    # Ensure rank numbers are 1-based sequential
    for i, r in enumerate(response.results, start=1):
        assert r.rank == i
        assert r.baseline_score > 0.0
        assert r.geometry["type"] == "Polygon"
        assert len(r.checksum) == 64

    # Latency check: should execute well under 500ms
    assert response.execution_trace["total_ms"] < 500.0


def test_retrieval_service_min_confidence_filter(memory_db):
    """Verifies min_confidence threshold filters low scoring candidates."""
    if not SAMPLE_MANIFEST.exists():
        pytest.skip("Sample manifest required.")

    service = BaselineRetrievalService(db=memory_db, project_root=PROJECT_ROOT)
    # Impossible high threshold
    req = BaselineSearchRequest(
        query="forest",
        min_confidence=0.999,
    )
    response = service.search(req)
    assert len(response.results) == 0


# ==============================================================================
# 5. REST API Search Endpoint Tests
# ==============================================================================

def test_api_baseline_search_success(test_client):
    """Verifies POST /api/v1/search/baseline endpoint."""
    payload = {
        "query": "urban buildings",
        "bbox": [73.57, 18.94, 73.63, 18.99],
        "top_k": 3,
        "min_confidence": 0.0,
    }
    response = test_client.post("/api/v1/search/baseline", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert data["query"] == "urban buildings"
    assert "Residential" in data["matched_vocabulary"]
    assert len(data["results"]) <= 3
    assert data["execution_trace"]["total_ms"] > 0.0


def test_api_baseline_search_empty_query_validation(test_client):
    """Verifies empty query triggers 422 Unprocessable Entity."""
    payload = {"query": ""}
    response = test_client.post("/api/v1/search/baseline", json=payload)
    assert response.status_code == 422


def test_api_baseline_search_invalid_bbox_validation(test_client):
    """Verifies invalid bbox (min > max) triggers 422 Unprocessable Entity."""
    payload = {
        "query": "forest",
        "bbox": [75.0, 20.0, 74.0, 19.0],  # Inverted coords
    }
    response = test_client.post("/api/v1/search/baseline", json=payload)
    assert response.status_code == 422
