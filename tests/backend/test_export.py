"""Unit tests for AstraTrace Multi-Format Report Export.

SIH 2026 | Problem ID: SIH26227
"""
from fastapi.testclient import TestClient


def test_export_html_report(client: TestClient):
    """Verifies /api/v1/export/report generates valid HTML evidence dossier."""
    payload = {
        "format": "HTML",
        "pair_ids": ["test_pair_01"],
        "candidate_data": {
            "pair_id": "test_pair_01",
            "query": "newly built structures near roads",
            "location": "Rajasthan / Thar Sector",
            "sensor": "Sentinel-2A",
            "confidence": 0.92,
            "quality": 0.96,
            "decision": "CONFIRMED",
            "earliest_change_date": "2023-08-14",
        }
    }
    response = client.post("/api/v1/export/report", json=payload)
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "ASTRATRACE 2.0 // FORENSIC INTELLIGENCE DOSSIER" in response.text
    assert "test_pair_01" in response.text


def test_export_csv_report(client: TestClient):
    """Verifies /api/v1/export/report generates tabular CSV summary."""
    payload = {
        "format": "CSV",
        "candidate_data": {
            "pair_id": "test_pair_01",
            "scene_id": "S2A_TEST",
            "tile_id": "T01",
            "change_type": "CONSTRUCTION",
            "confidence": 0.92,
            "quality": 0.96,
            "earliest_change_date": "2023-08-14",
            "status": "CONFIRMED",
        }
    }
    response = client.post("/api/v1/export/report", json=payload)
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "pair_id,scene_id,tile_id" in response.text
