"""Audit Service for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Provides append-oriented logging and retrieval of system, operational, and
forensic events across the retrieval, change detection, and triage pipelines.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import uuid
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.backend.app.core.logging import get_logger
from apps.backend.app.db.session import StateSessionLocal
from apps.backend.app.models.audit import AuditEventRecord

logger = get_logger("astratrace.audit")


class AuditService:
    """Service managing append-oriented audit records."""

    def __init__(self, db: Optional[Session] = None):
        if db is not None:
            self.db = db
            self._owns_db = False
        else:
            self.db = StateSessionLocal()
            self._owns_db = True

    def close(self):
        """Closes internal database session if owned."""
        if self._owns_db and self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        target_id: str,
        target_type: str,
        status: str = "SUCCESS",
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditEventRecord:
        """Appends a new auditable event to the database."""
        event_id = f"evt_{uuid.uuid4().hex[:12]}"
        record = AuditEventRecord(
            event_id=event_id,
            event_type=event_type.upper(),
            actor=actor.strip(),
            action=action.upper(),
            target_id=target_id.strip(),
            target_type=target_type.upper(),
            status=status.upper(),
            details=details or {},
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            f"Audit event recorded: {event_id} | Type: {record.event_type} | "
            f"Actor: {record.actor} | Action: {record.action} | Target: {record.target_id} | Status: {record.status}"
        )
        return record

    def query_events(
        self,
        event_type: Optional[str] = None,
        actor: Optional[str] = None,
        target_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[AuditEventRecord]]:
        """Queries audit records with optional filtering and pagination."""
        query = self.db.query(AuditEventRecord)

        if event_type:
            query = query.filter(AuditEventRecord.event_type == event_type.upper())
        if actor:
            query = query.filter(AuditEventRecord.actor == actor)
        if target_id:
            query = query.filter(AuditEventRecord.target_id == target_id)
        if status:
            query = query.filter(AuditEventRecord.status == status.upper())

        total = query.count()
        events = (
            query.order_by(desc(AuditEventRecord.created_at))
            .offset(offset)
            .limit(limit)
            .all()
        )
        return total, events
