"""Schemas for health and status endpoints."""
from datetime import datetime
from typing import Dict
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Basic health check response."""
    status: str = Field(..., json_schema_extra={"example": "healthy"})
    app: str = Field(..., json_schema_extra={"example": "AstraTrace"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    offline_mode: bool = Field(..., json_schema_extra={"example": True})
    timestamp: datetime = Field(..., json_schema_extra={"example": "2026-09-11T00:30:00Z"})


class SystemStatusResponse(BaseModel):
    """Detailed system and operational status response."""
    status: str = Field(..., json_schema_extra={"example": "operational"})
    app: str = Field(..., json_schema_extra={"example": "AstraTrace"})
    version: str = Field(..., json_schema_extra={"example": "0.1.0"})
    environment: str = Field(..., json_schema_extra={"example": "development"})
    offline_mode: bool = Field(..., json_schema_extra={"example": True})
    services: Dict[str, str] = Field(
        default_factory=lambda: {
            "api": "healthy",
            "catalog": "staged",
            "storage": "local"
        }
    )
    timestamp: datetime
