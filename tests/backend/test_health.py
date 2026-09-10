"""Unit tests for health and status endpoints."""
from fastapi.testclient import TestClient


def test_root_endpoint(client: TestClient):
    """Verifies root endpoint returns online status."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["app"] == "AstraTrace"
    assert data["status"] == "online"
    assert data["offline_mode"] is True
    assert "X-Request-ID" in response.headers


def test_health_endpoint(client: TestClient):
    """Verifies /api/v1/health returns valid schema and offline mode."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app"] == "AstraTrace"
    assert data["version"] == "0.1.0"
    assert data["offline_mode"] is True
    assert "timestamp" in data


def test_system_status_endpoint(client: TestClient):
    """Verifies /api/v1/status returns service dictionary and operational status."""
    response = client.get("/api/v1/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert data["environment"] in {"development", "testing", "staging", "production"}
    assert "services" in data
    assert data["services"]["api"] == "healthy"


def test_request_id_tracing(client: TestClient):
    """Verifies custom X-Request-ID header is preserved."""
    custom_id = "req_custom_trace_12345"
    response = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == custom_id
