"""Pydantic v2 schemas for Analyst Review Queue & Decision Persistence.

SIH 2026 | Problem ID: SIH26227
Defines contracts for submitting, tracking, and retrieving human-in-the-loop decisions.
"""
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


class ReviewDecision(str, Enum):
    """Operational decision states assigned by a human analyst."""
    PENDING_REVIEW = "PENDING_REVIEW"
    CONFIRMED = "CONFIRMED"
    REJECTED = "REJECTED"
    FLAGGED_FOR_INSPECTION = "FLAGGED_FOR_INSPECTION"


class TargetType(str, Enum):
    """Classification of target reviewed by analyst."""
    TILE = "TILE"
    CHANGE = "CHANGE"


class SubmitReviewRequest(BaseModel):
    """Payload submitted by analyst to record an operational decision."""
    model_config = ConfigDict(extra="forbid")

    target_id: str = Field(..., min_length=3, max_length=128, description="Identifier of tile or change event")
    target_type: TargetType = Field(..., description="Target category: TILE or CHANGE")
    decision: ReviewDecision = Field(..., description="Decision: CONFIRMED, REJECTED, or FLAGGED_FOR_INSPECTION")
    analyst_id: str = Field("ANALYST_DGIS", min_length=2, max_length=64, description="Analyst callsign or badge ID")
    notes: Optional[str] = Field(None, max_length=1000, description="Sanitized analytical notes or tactical rationale")


class ReviewRecordResponse(BaseModel):
    """Auditable record response of a submitted analyst decision."""
    model_config = ConfigDict(from_attributes=True)

    review_id: str
    target_id: str
    target_type: str
    decision: ReviewDecision
    analyst_id: str
    notes: Optional[str] = None
    confidence_at_review: float
    quality_status_at_review: str
    provenance_snapshot: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str


class ReviewQueueItem(BaseModel):
    """Single ranked item in the analyst review queue structured according to Evidence-First principles."""
    model_config = ConfigDict(from_attributes=True)

    queue_id: str = Field(..., description="Queue item identifier")
    target_id: str = Field(..., description="Identifier of tile or change event")
    target_type: str = Field(..., description="TILE or CHANGE")
    
    # Evidence-First Dimensions
    what: str = Field(..., description="Classification or detected change description")
    where: Dict[str, Any] = Field(..., description="WGS84 bbox, centroid, and GeoJSON geometry")
    when: Optional[Union[str, Dict[str, Any]]] = Field(None, description="Acquisition datetime ISO 8601 or temporal range")
    which: Dict[str, Any] = Field(..., description="Sensor, collection, and scene metadata")
    why: Dict[str, Any] = Field(..., description="Score decomposition explaining ranking rationale")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated final confidence score")
    quality_status: str = Field(..., description="USABLE, DEGRADED, UNRELIABLE, UNCERTAIN, or INSUFFICIENT")
    quality_flags: List[str] = Field(default_factory=list, description="Quality alert flags")
    evidence: Dict[str, Any] = Field(..., description="Preview thumbnail URL, change mask URL, usable area metrics")
    provenance: Dict[str, Any] = Field(..., description="Cryptographic checksums, model information, execution timestamps")
    
    # Review state
    review_status: ReviewDecision = Field(default=ReviewDecision.PENDING_REVIEW, description="Current triage review status")
    current_review: Optional[ReviewRecordResponse] = Field(None, description="Latest recorded review if any")


class ReviewQueueResponse(BaseModel):
    """Paginated collection of review queue items with status summary counts."""
    total: int
    pending_count: int
    confirmed_count: int
    rejected_count: int
    flagged_count: int
    items: List[ReviewQueueItem]


class ReviewHistoryResponse(BaseModel):
    """Complete chronological audit history for a given target."""
    target_id: str
    total_reviews: int
    history: List[ReviewRecordResponse]
