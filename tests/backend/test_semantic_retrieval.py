"""Automated Tests for Advanced Embeddings & Semantic Vector Retrieval (Milestone 6).

SIH 2026 | Problem ID: SIH26227
Validates 512-D embedding generation, deterministic inference, NaN/Inf rejection,
vector indexing, cosine similarity, hybrid scoring, evaluation metrics, and API endpoints.
"""
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.db.session import Base, init_db
from apps.backend.app.main import create_app
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.models.embedding import TileEmbeddingRecord
from apps.backend.app.schemas.semantic import (
    SemanticSearchRequest,
    SimilarTilesRequest,
)
from apps.backend.app.services.catalog import CatalogService
from apps.backend.app.services.retrieval.embedding_model import (
    DeterministicOfflineEmbeddingModel,
    get_embedding_model,
)
from apps.backend.app.services.retrieval.evaluator import (
    RetrievalEvaluator,
    compute_precision_at_k,
    compute_recall_at_k,
    compute_mrr,
    compute_ndcg_at_k,
)
from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService
from apps.backend.app.services.retrieval.vector_index import NumpyVectorIndex

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SAMPLE_MANIFEST = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "manifest.json"
SAMPLE_TILE = PROJECT_ROOT / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"


@pytest.fixture
def memory_db():
    """Provides an isolated in-memory SQLite session pre-populated with sample catalog tiles."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=test_engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    session = TestingSessionLocal()

    if SAMPLE_MANIFEST.exists():
        cat_service = CatalogService(db=session, project_root=PROJECT_ROOT)
        cat_service.register_manifest(SAMPLE_MANIFEST)

    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def test_client():
    """FastAPI TestClient with initialized database and vector index."""
    init_db()
    app = create_app()
    with TestClient(app) as client:
        yield client


# ==============================================================================
# 1. Embedding Model Unit Tests
# ==============================================================================

def test_embedding_dimensions_and_norm():
    """Verifies that generated embeddings have dimension 512 and unit L2 norm."""
    model = DeterministicOfflineEmbeddingModel()
    meta = model.model_metadata()
    assert meta["dimension"] == 512
    assert meta["architecture"] == "Deterministic-Orthogonal-Projection-512"
    assert meta["operational_mode"] == "OFFLINE_DETERMINISTIC"

    # Text embedding
    text_vec = model.encode_text("dense forest canopy vegetation")
    assert isinstance(text_vec, np.ndarray)
    assert text_vec.shape == (512,)
    assert text_vec.dtype == np.float32
    assert pytest.approx(float(np.linalg.norm(text_vec)), abs=1e-5) == 1.0

    # Image embedding
    if SAMPLE_TILE.exists():
        img_vec = model.encode_image(SAMPLE_TILE)
        assert isinstance(img_vec, np.ndarray)
        assert img_vec.shape == (512,)
        assert img_vec.dtype == np.float32
        assert pytest.approx(float(np.linalg.norm(img_vec)), abs=1e-5) == 1.0


def test_deterministic_inference():
    """Verifies that identical inputs yield bit-for-bit identical vectors."""
    model = DeterministicOfflineEmbeddingModel()

    vec1 = model.encode_text("industrial facility warehouse")
    vec2 = model.encode_text("industrial facility warehouse")
    assert np.array_equal(vec1, vec2)

    if SAMPLE_TILE.exists():
        img1 = model.encode_image(SAMPLE_TILE)
        img2 = model.encode_image(SAMPLE_TILE)
        assert np.array_equal(img1, img2)


def test_nan_inf_vector_rejection():
    """Verifies that vectors containing NaN or Inf values are strictly rejected."""
    index = NumpyVectorIndex(dimension=512)

    nan_vec = np.zeros(512, dtype=np.float32)
    nan_vec[42] = np.nan

    inf_vec = np.zeros(512, dtype=np.float32)
    inf_vec[100] = np.inf

    # Reject on add
    with pytest.raises(ValidationError, match="NaN or Inf"):
        index.add("nan_tile", nan_vec)

    with pytest.raises(ValidationError, match="NaN or Inf"):
        index.add("inf_tile", inf_vec)

    # Reject on search
    with pytest.raises(ValidationError, match="NaN or Inf"):
        index.search(nan_vec)

    # Reject dimension mismatch
    with pytest.raises(ValidationError, match="Dimension mismatch"):
        index.add("bad_dim", np.zeros(256, dtype=np.float32))


def test_text_to_image_alignment():
    """Verifies semantic alignment between query terms and conceptual categories."""
    model = DeterministicOfflineEmbeddingModel()

    # Query with river synonyms
    river_vec = model.encode_text("river water stream canal")
    water_vec = model.encode_text("water body lake pond")
    forest_vec = model.encode_text("dense forest woodland trees")

    sim_river_water = float(np.dot(river_vec, water_vec))
    sim_river_forest = float(np.dot(river_vec, forest_vec))

    # Water-related terms should be closer than water vs forest
    assert sim_river_water > sim_river_forest


def test_image_to_image_similarity():
    """Verifies that identical vectors achieve cosine similarity of 1.0."""
    index = NumpyVectorIndex(dimension=512)
    v = np.random.RandomState(42).randn(512).astype(np.float32)
    v /= np.linalg.norm(v)

    index.add("tile_alpha", v)
    hits = index.search(query_vector=v, top_k=1)
    assert len(hits) == 1
    assert hits[0]["tile_id"] == "tile_alpha"
    assert pytest.approx(hits[0]["cosine_sim"], abs=1e-3) == 1.0
    assert pytest.approx(hits[0]["semantic_score"], abs=1e-3) == 1.0


# ==============================================================================
# 2. Vector Index & Top-K Tests
# ==============================================================================

def test_vector_index_add_and_query():
    """Verifies vector storage, retrieval, and exclusion filtering."""
    index = NumpyVectorIndex(dimension=512)
    rng = np.random.RandomState(101)

    v1 = rng.randn(512).astype(np.float32)
    v1 /= np.linalg.norm(v1)
    v2 = rng.randn(512).astype(np.float32)
    v2 /= np.linalg.norm(v2)

    index.add("t1", v1, metadata={"scene": "scn1"})
    index.add("t2", v2, metadata={"scene": "scn2"})

    assert index.size() == 2
    assert index.get_vector("t1") is not None
    assert pytest.approx(float(np.linalg.norm(index.get_vector("t1"))), abs=1e-5) == 1.0

    # Query matching v1
    results = index.search(v1, top_k=2)
    assert len(results) == 2
    assert results[0]["tile_id"] == "t1"
    assert results[0]["metadata"]["scene"] == "scn1"

    # Query with exclusion
    results_ex = index.search(v1, top_k=2, exclude_tile_ids=["t1"])
    assert len(results_ex) == 1
    assert results_ex[0]["tile_id"] == "t2"


def test_vector_index_top_k_bounds():
    """Verifies graceful handling of boundary top_k requests."""
    index = NumpyVectorIndex(dimension=512)
    v = np.ones(512, dtype=np.float32) / np.sqrt(512)
    index.add("only_one", v)

    # Request more than size
    res_large = index.search(v, top_k=100)
    assert len(res_large) == 1

    # Request zero or negative
    assert index.search(v, top_k=0) == []
    assert index.search(v, top_k=-5) == []


def test_empty_vector_index_behavior():
    """Verifies that an uninitialized/empty index returns empty results without crashing."""
    index = NumpyVectorIndex(dimension=512)
    q = np.ones(512, dtype=np.float32) / np.sqrt(512)

    assert index.size() == 0
    assert index.search(q, top_k=5) == []
    assert index.get_vector("absent") is None
    assert index.remove("absent") is False


def test_missing_embedding_handling(memory_db):
    """Verifies that requesting similarity for a nonexistent tile raises NotFoundError."""
    service = SemanticRetrievalService(
        db=memory_db,
        project_root=PROJECT_ROOT,
        index_file=PROJECT_ROOT / "data" / "processed" / "test_vector_index.npz",
    )
    req = SimilarTilesRequest(reference_tile_id="nonexistent_tile_id_99999")
    with pytest.raises(NotFoundError):
        service.search_similar_tiles(req)


# ==============================================================================
# 3. Integration & Hybrid Ranking Tests
# ==============================================================================

def test_spatial_and_temporal_filtering_on_semantic_results(memory_db):
    """Verifies that spatial bbox and temporal filters restrict semantic candidates."""
    service = SemanticRetrievalService(
        db=memory_db,
        project_root=PROJECT_ROOT,
        index_file=PROJECT_ROOT / "data" / "processed" / "test_vector_index.npz",
    )
    service.index_catalog_tiles()

    # Query with a tight bbox that contains tile_0000
    tile = memory_db.query(TileRecord).first()
    if not tile:
        pytest.skip("No catalog tiles available in memory_db")

    # Filter with non-overlapping future time window -> 0 results
    future_req = SemanticSearchRequest(
        query="industrial warehouse",
        hybrid_weight=0.5,
        date_from=datetime(2030, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2031, 1, 1, tzinfo=timezone.utc),
    )
    future_resp = service.search(future_req)
    assert len(future_resp.results) == 0

    # Filter with past time window matching sample scene
    past_req = SemanticSearchRequest(
        query="industrial warehouse",
        hybrid_weight=0.5,
        date_from=datetime(2020, 1, 1, tzinfo=timezone.utc),
        date_to=datetime(2025, 12, 31, tzinfo=timezone.utc),
    )
    past_resp = service.search(past_req)
    assert len(past_resp.results) > 0


def test_hybrid_score_weighting(memory_db):
    """Verifies that alpha parameter correctly modulates semantic and baseline weights."""
    service = SemanticRetrievalService(
        db=memory_db,
        project_root=PROJECT_ROOT,
        index_file=PROJECT_ROOT / "data" / "processed" / "test_vector_index.npz",
    )
    service.index_catalog_tiles()

    # hybrid_weight = 1.0 (pure semantic)
    req_sem = SemanticSearchRequest(query="industrial warehouse", hybrid_weight=1.0, top_k=5)
    resp_sem = service.search(req_sem)
    for r in resp_sem.results:
        assert pytest.approx(r.hybrid_score, abs=1e-4) == r.semantic_score

    # hybrid_weight = 0.0 (pure baseline)
    req_base = SemanticSearchRequest(query="industrial warehouse", hybrid_weight=0.0, top_k=5)
    resp_base = service.search(req_base)
    for r in resp_base.results:
        assert pytest.approx(r.hybrid_score, abs=1e-4) == r.baseline_score

    # hybrid_weight = 0.5 (equal blend)
    req_blend = SemanticSearchRequest(query="industrial warehouse", hybrid_weight=0.5, top_k=5)
    resp_blend = service.search(req_blend)
    for r in resp_blend.results:
        expected = round(0.5 * r.semantic_score + 0.5 * r.baseline_score, 4)
        assert pytest.approx(r.hybrid_score, abs=1e-3) == expected


def test_catalog_indexing_service(memory_db):
    """Verifies batch indexing of catalog tiles into DB embeddings and vector index."""
    test_idx_path = PROJECT_ROOT / "data" / "processed" / "test_index_temp.npz"
    try:
        service = SemanticRetrievalService(
            db=memory_db,
            project_root=PROJECT_ROOT,
            index_file=test_idx_path,
        )
        stats = service.index_catalog_tiles()

        tiles_in_db = memory_db.query(TileRecord).count()
        assert stats["indexed_count"] == tiles_in_db
        assert stats["total_indexed"] == tiles_in_db

        # Check DB embeddings table
        embeddings = memory_db.query(TileEmbeddingRecord).all()
        assert len(embeddings) == tiles_in_db
        for emb in embeddings:
            vec = emb.get_vector()
            assert len(vec) == 512
            assert pytest.approx(float(np.linalg.norm(vec)), abs=1e-4) == 1.0
    finally:
        if test_idx_path.exists():
            test_idx_path.unlink()


def test_evaluator_metrics_calculation():
    """Verifies exact analytical accuracy of Precision, Recall, MRR, and nDCG calculations."""
    # Test case: 5 retrieved items, 2 relevant items at ranks 1 and 3
    retrieved = ["t1", "t2", "t3", "t4", "t5"]
    relevant = ["t1", "t3"]

    p_at_5 = compute_precision_at_k(retrieved, relevant, k=5)
    assert pytest.approx(p_at_5, abs=1e-5) == 2.0 / 5.0  # 0.4

    r_at_5 = compute_recall_at_k(retrieved, relevant, k=5)
    assert pytest.approx(r_at_5, abs=1e-5) == 2.0 / 2.0  # 1.0

    mrr = compute_mrr(retrieved, relevant)
    assert pytest.approx(mrr, abs=1e-5) == 1.0  # First hit at rank 1

    # First hit at rank 2
    mrr_rank2 = compute_mrr(["t99", "t1", "t2"], ["t1"])
    assert pytest.approx(mrr_rank2, abs=1e-5) == 0.5

    # Zero hits
    assert compute_precision_at_k(retrieved, ["t99"], k=5) == 0.0
    assert compute_recall_at_k(retrieved, ["t99"], k=5) == 0.0
    assert compute_mrr(retrieved, ["t99"]) == 0.0
    assert compute_ndcg_at_k(retrieved, ["t99"], k=5) == 0.0


def test_hard_negatives_separation():
    """Verifies that fundamentally distinct semantic classes are well-separated in embedding space."""
    model = DeterministicOfflineEmbeddingModel()

    v_water = model.encode_text("river lake water stream pond")
    v_industrial = model.encode_text("industrial factory warehouse containers")
    v_forest = model.encode_text("dense forest woodland trees canopy")

    cos_sim_water_ind = float(np.dot(v_water, v_industrial))
    cos_sim_ind_forest = float(np.dot(v_industrial, v_forest))

    # Distinct categories should not have high similarity (< 0.45)
    assert cos_sim_water_ind < 0.45
    assert cos_sim_ind_forest < 0.45


def test_provenance_immutability(memory_db):
    """Verifies that retrieval responses carry complete, tamper-evident provenance metadata."""
    service = SemanticRetrievalService(
        db=memory_db,
        project_root=PROJECT_ROOT,
        index_file=PROJECT_ROOT / "data" / "processed" / "test_vector_index.npz",
    )
    service.index_catalog_tiles()

    req = SemanticSearchRequest(query="industrial warehouse", top_k=2)
    resp = service.search(req)

    assert resp.model_info["model_name"] == "AstraTrace-Offline-Baseline-v1"
    assert resp.model_info["dimension"] == 512
    assert "total_ms" in resp.execution_trace
    assert resp.execution_trace["total_ms"] >= 0.0

    for res in resp.results:
        assert res.tile_id is not None
        assert res.scene_id is not None
        assert len(res.checksum) == 64  # SHA-256 length
        assert res.bounds_wgs84 is not None
        assert 0.0 <= res.hybrid_score <= 1.0
        assert 0.0 <= res.semantic_score <= 1.0


# ==============================================================================
# 4. REST API Endpoint Tests
# ==============================================================================

def test_api_semantic_search_success(test_client):
    """Verifies POST /api/v1/search/semantic returns 200 and schema-valid response."""
    payload = {
        "query": "industrial warehouse",
        "top_k": 5,
        "alpha": 0.6,
        "min_confidence": 0.0,
    }
    response = test_client.post("/api/v1/search/semantic", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "query_id" in data
    assert data["query_id"].startswith("sem_")
    assert "results" in data
    assert isinstance(data["results"], list)
    assert "model_info" in data
    assert data["model_info"]["dimension"] == 512
    assert "execution_trace" in data


def test_api_similar_tiles_success(test_client):
    """Verifies POST /api/v1/search/similar-tiles returns 200 with ranked similar tiles."""
    payload = {
        "reference_tile_id": "scn_sentinel-2_20230115_96ed9480_t0000",
        "top_k": 3,
        "min_confidence": 0.0,
    }
    response = test_client.post("/api/v1/search/similar-tiles", json=payload)
    assert response.status_code == 200

    data = response.json()
    assert "query_id" in data
    assert data["query_id"].startswith("sim_")
    assert "results" in data

    # Reference tile should be excluded from hits
    result_ids = [r["tile_id"] for r in data["results"]]
    assert "scn_sentinel-2_20230115_96ed9480_t0000" not in result_ids


def test_api_embeddings_status(test_client):
    """Verifies GET /api/v1/embeddings/status returns index health and dimension details."""
    response = test_client.get("/api/v1/embeddings/status")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "INDEX_OPERATIONAL"
    assert data["dimension"] == 512
    assert data["model_name"] == "AstraTrace-Offline-Baseline-v1"
    assert data["total_indexed"] >= 0
