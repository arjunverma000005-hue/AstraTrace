"""SQLAlchemy database model for Analyst Reviews in AstraTrace.

SIH 2026 | Problem ID: SIH26227
Stores human-in-the-loop analyst decisions, audit trails, evidence snapshots,
and decision rationales. Prohibited from modifying production model weights.
"""
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import Column, DateTime, Float, Integer, JSON, String, Text

from apps.backend.app.db.session import Base


class AnalystReviewRecord(Base):
    """Auditable record of a tactical analyst's review on a tile or change detection."""

    __tablename__ = "analyst_reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String(64), unique=True, index=True, nullable=False)
    target_id = Column(String(128), index=True, nullable=False)
    target_type = Column(String(32), nullable=False)  # "TILE" or "CHANGE"
    decision = Column(String(32), nullable=False, index=True)  # "CONFIRMED", "REJECTED", "FLAGGED_FOR_INSPECTION"
    analyst_id = Column(String(64), nullable=False, index=True)
    notes = Column(Text, nullable=True)

    # Immutable evidence snapshot captured at the exact moment of review
    confidence_at_review = Column(Float, nullable=False)
    quality_status_at_review = Column(String(32), nullable=False)
    provenance_snapshot = Column(JSON, nullable=True)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    def to_dict(self) -> Dict[str, Any]:
        """Serializes review record to dictionary."""
        return {
            "review_id": self.review_id,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "decision": self.decision,
            "analyst_id": self.analyst_id,
            "notes": self.notes,
            "confidence_at_review": self.confidence_at_review,
            "quality_status_at_review": self.quality_status_at_review,
            "provenance_snapshot": self.provenance_snapshot or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
