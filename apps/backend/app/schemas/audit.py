"""Pydantic schemas for AstraTrace Audit Logging.

SIH 2026 | Problem ID: SIH26227
Defines audit event creation, querying, and paginated response models.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditEventCreate(BaseModel):
    """Schema for recording a new audit event."""
    event_type: str = Field(..., description="Category (SEARCH, CHANGE, QUALITY, REVIEW, VERIFY, EXPORT)")
    actor: str = Field(..., description="Initiating actor or analyst ID")
    action: str = Field(..., description="Action performed")
    target_id: str = Field(..., description="Identifier of primary affected entity")
    target_type: str = Field(..., description="Entity type (TILE, SCENE, CHANGE, QUERY, REVIEW, EXPORT)")
    status: str = Field(..., description="Outcome status (SUCCESS, FAILED, WARNING, TAMPERED)")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Structured contextual attributes")


class AuditEventResponse(BaseModel):
    """Schema representing an auditable event record."""
    event_id: str = Field(..., description="Unique event identifier")
    event_type: str = Field(..., description="Event category")
    actor: str = Field(..., description="Actor identity")
    action: str = Field(..., description="Action name")
    target_id: str = Field(..., description="Target entity ID")
    target_type: str = Field(..., description="Target entity type")
    status: str = Field(..., description="Execution status")
    details: Dict[str, Any] = Field(default_factory=dict, description="Contextual payload")
    created_at: str = Field(..., description="ISO 8601 recording timestamp")


class AuditLogQueryRequest(BaseModel):
    """Filter parameters for querying audit log records."""
    event_type: Optional[str] = Field(None, description="Filter by event category")
    actor: Optional[str] = Field(None, description="Filter by actor ID")
    target_id: Optional[str] = Field(None, description="Filter by target entity ID")
    status: Optional[str] = Field(None, description="Filter by status")
    limit: int = Field(50, ge=1, le=500, description="Page limit")
    offset: int = Field(0, ge=0, description="Page offset")


class AuditLogResponse(BaseModel):
    """Paginated response containing audit events."""
    total: int = Field(..., description="Total matching audit records")
    limit: int = Field(..., description="Page limit")
    offset: int = Field(..., description="Page offset")
    events: List[AuditEventResponse] = Field(..., description="List of audit event records")
