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

def main():
    print("=" * 60)
    print("ASTRATRACE MILESTONE 1 FOUNDATION VERIFICATION")
    print("=" * 60)

    results = [
        verify_directories(),
        verify_configuration(),
        verify_backend_health(),
        verify_sample_metadata(),
    ]

    print("=" * 60)
    if all(results):
        print("\033[92m[SUCCESS] All Milestone 1 verification checks PASSED.\033[0m")
        sys.exit(0)
    else:
        print("\033[91m[FAILURE] One or more verification checks FAILED.\033[0m")
        sys.exit(1)

if __name__ == "__main__":
    main()
