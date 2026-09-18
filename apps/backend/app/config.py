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
    app_version: str = "0.1.0"
    app_env: str = "development"
    log_level: str = "INFO"

    # Server Binding
    api_host: str = "0.0.0.0"
    api_port: int = Field(default=8000, validation_alias=AliasChoices("PORT", "api_port", "API_PORT"))

    # Operational Invariant: Offline Mode
    offline_mode: bool = True

    # Security & CORS
    cors_origins: Union[str, List[str]] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://astra-trace.vercel.app",
    ]

    # Storage Paths
    data_dir: str = "data"
    models_dir: str = "models"

    # Database Configuration (PostgreSQL in production, SQLite fallback for offline local testing)
    database_url: str = "sqlite:///./data/catalog.db"
    catalog_database_url: str = Field(default="sqlite:///./data/catalog.db", validation_alias=AliasChoices("CATALOG_DATABASE_URL", "catalog_database_url"))
    state_database_url: str = Field(default="", validation_alias=AliasChoices("STATE_DATABASE_URL", "POSTGRES_URL", "state_database_url"))
    redis_url: str = "redis://localhost:6379/0"

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
