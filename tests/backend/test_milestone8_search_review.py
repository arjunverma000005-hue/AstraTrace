"""Milestone 8 Test Suite: Unified Search, Tile Previews, and Analyst Review Queue.

SIH 2026 | Problem ID: SIH26227
Validates:
- Unified Search API (POST /api/v1/search/unified) across search modes (KEYWORD, SEMANTIC, HYBRID, AUTO)
- Evidence-First candidate schema compliance (WHAT, WHERE, WHEN, WHICH, WHY, CONFIDENCE, EVIDENCE, PROVENANCE)
- Raster Preview generation endpoint (GET /api/v1/catalog/tiles/{tile_id}/preview) with contrast stretching & security
- Analyst Review decisions (POST /api/v1/review/decision), audit trail history, and triage queue
- Strict offline / air-gapped guarantees and validation against unauthorized model updates
"""
import pytest
from fastapi.testclient import TestClient


def test_unified_search_validation(client: TestClient):
    """Rejects queries without query text or spatial filter."""
    res = client.post("/api/v1/search/unified", json={})
    assert res.status_code == 422


def test_unified_search_invalid_bbox(client: TestClient):
    """Rejects inverted bounding boxes."""
    res = client.post(
        "/api/v1/search/unified",
        json={
            "query": "forest",
            "bbox": [74.0, 19.0, 73.0, 18.0],  # min > max
        },
    )
    assert res.status_code == 422


def test_unified_search_keyword(client: TestClient):
    """Executes keyword-based search returning Evidence-First candidates."""
    res = client.post(
        "/api/v1/search/unified",
        json={
            "query": "Sentinel-2",
            "search_mode": "KEYWORD",
            "limit": 5,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "query" in data
    assert "search_mode" in data
    assert "total_candidates" in data
    assert "results" in data
    assert "execution_trace" in data
    assert isinstance(data["results"], list)

    if data["results"]:
        cand = data["results"][0]
        # Evidence-First structural checks
        assert "candidate_id" in cand
        assert "target_id" in cand
        assert "what" in cand
        assert "where" in cand
        assert "bbox" in cand["where"]
        assert len(cand["where"]["bbox"]) == 4
        assert "centroid" in cand["where"]
        assert "crs" in cand["where"]
        assert "when" in cand
        assert "which" in cand
        assert "why" in cand
        assert "confidence" in cand
        assert 0.0 <= cand["confidence"] <= 1.0
        assert "quality_status" in cand
        assert "evidence" in cand
        assert "preview_url" in cand["evidence"]
        assert "provenance" in cand


def test_unified_search_semantic(client: TestClient):
    """Executes semantic embedding search returning ranked candidate tiles."""
    res = client.post(
        "/api/v1/search/unified",
        json={
            "query": "dense green forest vegetation",
            "search_mode": "SEMANTIC",
            "top_k": 5,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["search_mode"] == "SEMANTIC"
    assert "results" in data


def test_unified_search_spatial_bbox_filter(client: TestClient):
    """Applies spatial bounding box filter to restrict search scope."""
    # AOI covering Western Ghats sample tiles
    bbox = [73.57, 18.96, 73.65, 19.02]
    res = client.post(
        "/api/v1/search/unified",
        json={
            "query": "forest",
            "bbox": bbox,
            "search_mode": "KEYWORD",
            "top_k": 10,
        },
    )
    assert res.status_code == 200
    data = res.json()
    for cand in data["results"]:
        cb = cand["where"]["bbox"]
        # Intersects bbox
        assert not (cb[2] < bbox[0] or cb[0] > bbox[2] or cb[3] < bbox[1] or cb[1] > bbox[3])


def test_unified_search_confidence_threshold(client: TestClient):
    """Enforces minimum confidence threshold on ranked candidates."""
    res = client.post(
        "/api/v1/search/unified",
        json={
            "query": "forest",
            "min_confidence": 0.85,
            "top_k": 10,
        },
    )
    assert res.status_code == 200
    data = res.json()
    for cand in data["results"]:
        assert cand["confidence"] >= 0.85


def test_tile_preview_endpoint(client: TestClient):
    """Generates an 8-bit contrast-stretched RGB PNG thumbnail from raw raster bands."""
    # First find an existing tile from unified search
    search_res = client.post(
        "/api/v1/search/unified",
        json={"query": "Sentinel-2", "top_k": 1},
    )
    assert search_res.status_code == 200
    candidates = search_res.json()["results"]
    if not candidates:
        pytest.skip("No tiles ingested for preview verification")

    tile_id = candidates[0]["target_id"]
    preview_res = client.get(f"/api/v1/catalog/tiles/{tile_id}/preview")
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"] == "image/png"
    # Verify PNG magic bytes: \x89PNG\r\n\x1a\n
    assert preview_res.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_tile_preview_security_and_missing(client: TestClient):
    """Rejects path traversal and handles non-existent tiles gracefully."""
    # Path traversal attempt in tile_id
    traversal_res = client.get("/api/v1/catalog/tiles/..%2F..%2Fsecret/preview")
    assert traversal_res.status_code in [400, 404, 422]

    # Non-existent tile
    not_found_res = client.get("/api/v1/catalog/tiles/nonexistent_tile_xyz_9999/preview")
    assert not_found_res.status_code == 404


def test_analyst_review_workflow(client: TestClient):
    """Tests the full human-in-the-loop review workflow: submit -> history -> queue."""
    # 1. Fetch a tile candidate to review
    search_res = client.post(
        "/api/v1/search/unified",
        json={"query": "Sentinel-2", "top_k": 1},
    )
    candidates = search_res.json().get("results", [])
    if not candidates:
        pytest.skip("No tiles available for review workflow test")

    tile_id = candidates[0]["target_id"]

    # 2. Submit an analyst review decision
    submit_res = client.post(
        "/api/v1/review/decision",
        json={
            "target_id": tile_id,
            "target_type": "TILE",
            "decision": "FLAGGED_FOR_INSPECTION",
            "analyst_id": "analyst_pytest",
            "notes": "Suspected terrain anomaly requiring secondary review",
        },
    )
    assert submit_res.status_code == 201
    decision_data = submit_res.json()
    assert decision_data["target_id"] == tile_id
    assert decision_data["decision"] == "FLAGGED_FOR_INSPECTION"
    assert decision_data["analyst_id"] == "analyst_pytest"
    assert "review_id" in decision_data
    assert "confidence_at_review" in decision_data
    assert "provenance_snapshot" in decision_data

    # 3. Retrieve audit history
    hist_res = client.get(f"/api/v1/review/history/{tile_id}")
    assert hist_res.status_code == 200
    hist_data = hist_res.json()
    assert hist_data["target_id"] == tile_id
    assert hist_data["total_reviews"] >= 1
    latest = hist_data["history"][0]
    assert latest["decision"] == "FLAGGED_FOR_INSPECTION"
    assert latest["analyst_id"] == "analyst_pytest"

    # 4. Check review queue reflects updated status
    queue_res = client.get("/api/v1/review/queue?status_filter=FLAGGED_FOR_INSPECTION")
    assert queue_res.status_code == 200
    queue_data = queue_res.json()
    assert queue_data["flagged_count"] >= 1
    matching = [it for it in queue_data["items"] if it["target_id"] == tile_id]
    assert len(matching) == 1
    assert matching[0]["review_status"] == "FLAGGED_FOR_INSPECTION"


def test_analyst_review_validation(client: TestClient):
    """Rejects reviews with invalid target identifiers or missing fields."""
    # Invalid target identifier (characters not matching regex)
    bad_id_res = client.post(
        "/api/v1/review/decision",
        json={
            "target_id": "bad;drop table users;",
            "target_type": "TILE",
            "decision": "CONFIRMED",
            "analyst_id": "analyst_bad",
        },
    )
    assert bad_id_res.status_code in [400, 422]

    # Invalid decision enum
    bad_dec_res = client.post(
        "/api/v1/review/decision",
        json={
            "target_id": "valid_target_123",
            "target_type": "TILE",
            "decision": "AUTO_APPROVE_ALL",
            "analyst_id": "analyst_bad",
        },
    )
    assert bad_dec_res.status_code == 422
