"""Unit tests for configuration management."""
import pytest
from apps.backend.app.config import Settings


def test_default_configuration():
    """Verifies default settings conform to offline and security standards."""
    cfg = Settings()
    assert cfg.app_name == "AstraTrace"
    assert cfg.app_version == "0.1.0"
    assert cfg.offline_mode is True
    assert cfg.api_port == 8000
    assert isinstance(cfg.cors_origins, list)


def test_cors_origins_parsing():
    """Verifies comma-separated CORS string is correctly parsed into a list."""
    cfg = Settings(cors_origins="http://localhost:3000, http://127.0.0.1:3000")
    assert cfg.cors_origins == ["http://localhost:3000", "http://127.0.0.1:3000"]


def test_invalid_environment():
    """Verifies an invalid APP_ENV raises a validation error."""
    with pytest.raises(ValueError, match="Invalid app_env"):
        Settings(app_env="invalid_environment_name")
