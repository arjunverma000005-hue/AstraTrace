"""AstraTrace Configuration Management.

Loads settings from environment variables and provides strict typing and validation.
"""
from typing import List, Union
from pydantic import Field, AliasChoices, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core Application
    app_name: str = "AstraTrace"
    app_version: str = "2.0.0"
    app_env: str = "production"
    log_level: str = "INFO"

    # Deployment Profile (OFFLINE_PROFILE: 100% air-gapped | WEB_DEMO_PROFILE)
    deployment_profile: str = Field(default="OFFLINE_PROFILE", validation_alias=AliasChoices("DEPLOYMENT_PROFILE", "deployment_profile"))

    # Server Binding
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "api_port", "API_PORT"))

    # Operational Invariant: Offline Mode
    offline_mode: bool = True

    # Security & CORS
    cors_origins: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ]

    # Three-Tier Storage Paths
    data_dir: str = "data"
    immutable_data_dir: str = "data/raw"
    scratch_dir: str = "data/scratch"
    models_dir: str = "models/weights"
    indexes_dir: str = "indexes/faiss"
    evaluation_dir: str = "data/evaluation"

    # Database Configuration (SQLite default for offline air-gapped execution)
    database_url: str = "sqlite:///./data/catalog.db"
    catalog_database_url: str = Field(default="sqlite:///./data/catalog.db", validation_alias=AliasChoices("CATALOG_DATABASE_URL", "catalog_database_url", "DATABASE_URL"))
    state_database_url: str = Field(default="sqlite:///./data/state.db", validation_alias=AliasChoices("STATE_DATABASE_URL", "state_database_url"))
    redis_url: str = "redis://localhost:6379/0"

    # Vector Search Settings
    vector_dimension: int = 512
    similarity_metric: str = "COSINE"
    faiss_index_path: str = "indexes/faiss/astratrace.index"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("app_env")
    @classmethod
    def validate_app_env(cls, v: str) -> str:
        valid_envs = {"development", "staging", "production", "testing"}
        if v.lower() not in valid_envs:
            raise ValueError(f"Invalid app_env '{v}'. Must be one of {valid_envs}")
        return v.lower()


settings = Settings()
