"""Unit tests for AstraTrace Unsupervised Discovery & Clustering.

SIH 2026 | Problem ID: SIH26227
"""
from fastapi.testclient import TestClient


def test_list_clusters_endpoint(client: TestClient):
    """Verifies /api/v1/clusters returns valid cluster groups with representative tiles and tags."""
    response = client.get("/api/v1/clusters?n_clusters=3")
    assert response.status_code == 200
    clusters = response.json()
    assert isinstance(clusters, list)
    if clusters:
        c0 = clusters[0]
        assert "cluster_id" in c0
        assert "cluster_label" in c0
        assert "n_samples" in c0
        assert "representative_tile_id" in c0
        assert "dominant_semantics" in c0
        assert "similarity_score" in c0


def test_get_cluster_by_id(client: TestClient):
    """Verifies /api/v1/clusters/{id} returns details for existing cluster."""
    # First discover
    res = client.get("/api/v1/clusters?n_clusters=2")
    assert res.status_code == 200
    clusters = res.json()
    if clusters:
        cid = clusters[0]["cluster_id"]
        detail_res = client.get(f"/api/v1/clusters/{cid}")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert detail["cluster_id"] == cid
