"""Unit tests for AstraTrace Image-to-Image Similarity Retrieval.

SIH 2026 | Problem ID: SIH26227
"""
from fastapi.testclient import TestClient


def test_image_search_by_tile_id(client: TestClient):
    """Verifies /api/v1/search/image returns Top-K similar tiles."""
    # Find a tile first from catalog
    cat_res = client.get("/api/v1/catalog/tiles?limit=1")
    if cat_res.status_code == 200 and cat_res.json():
        tile_id = cat_res.json()[0]["tile_id"]
        response = client.post("/api/v1/search/image", json={"reference_tile_id": tile_id, "top_k": 5})
        assert response.status_code == 200
        data = response.json()
        assert data["search_mode"] in ("similar_image", "semantic_text")
        assert "results" in data
        assert isinstance(data["results"], list)


def test_similar_sites_get_endpoint(client: TestClient):
    """Verifies /api/v1/similar/{tile_id} convenience endpoint."""
    cat_res = client.get("/api/v1/catalog/tiles?limit=1")
    if cat_res.status_code == 200 and cat_res.json():
        tile_id = cat_res.json()[0]["tile_id"]
        response = client.get(f"/api/v1/similar/{tile_id}?top_k=5")
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
