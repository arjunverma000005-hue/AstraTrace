"""SQLAlchemy database model for Audit Events in AstraTrace.

SIH 2026 | Problem ID: SIH26227
Provides append-oriented audit logging for forensic traceability across
queries, change detection, quality gating, analyst reviews, and integrity verification.
"""
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import Column, DateTime, Integer, JSON, String, Index

from apps.backend.app.db.session import Base


class AuditEventRecord(Base):
    """Append-oriented record of an operational, analytical, or verification event."""

    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    event_id = Column(String(64), unique=True, index=True, nullable=False)
    event_type = Column(String(64), nullable=False, index=True)
    actor = Column(String(64), nullable=False, index=True)
    action = Column(String(64), nullable=False)
    target_id = Column(String(128), nullable=False, index=True)
    target_type = Column(String(32), nullable=False)
    status = Column(String(32), nullable=False, index=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_audit_events_type_status", "event_type", "status"),
        Index("idx_audit_events_target_created", "target_id", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serializes audit record to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "actor": self.actor,
            "action": self.action,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "status": self.status,
            "details": self.details or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
