import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi.testclient import TestClient
from apps.backend.app.main import create_app


@pytest.fixture
def client() -> TestClient:
    """Provides a FastAPI test client instance."""
    app = create_app()
    return TestClient(app)
