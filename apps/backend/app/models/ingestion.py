"""SQLAlchemy Declarative Model for AstraTrace Incremental Ingestion History.

SIH 2026 | Problem ID: SIH26227
Tracks atomic additions of satellite scenes, tile deltas, vector index update
latencies, and storage deltas without full index rebuilds.
"""
from datetime import datetime, timezone
from typing import Any, Dict
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    BigInteger,
    Index,
)

from apps.backend.app.db.session import Base


class IngestionHistoryRecord(Base):
    """Audit ledger table tracking incremental scene ingestion and index deltas."""
    __tablename__ = "ingestion_history"

    batch_id = Column(String(64), primary_key=True, index=True)
    scene_id = Column(String(128), nullable=False, index=True)
    source_filename = Column(String(256), nullable=False)
    status = Column(String(32), nullable=False, default="SUCCESS")  # SUCCESS, REJECTED, FAILED
    error_details = Column(Text, nullable=True)

    # Invariant Deltas
    scenes_before = Column(Integer, nullable=False, default=0)
    scenes_after = Column(Integer, nullable=False, default=0)
    tiles_before = Column(Integer, nullable=False, default=0)
    tiles_after = Column(Integer, nullable=False, default=0)

    # Performance & Storage
    index_update_time_ms = Column(Float, nullable=False, default=0.0)
    total_ingestion_time_ms = Column(Float, nullable=False, default=0.0)
    new_storage_bytes = Column(BigInteger, nullable=False, default=0)
    total_storage_bytes = Column(BigInteger, nullable=False, default=0)

    # Verification
    checksum_sha256 = Column(String(64), nullable=False)
    crs = Column(String(64), nullable=False)
    resolution_meters = Column(Float, nullable=False, default=10.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_ingestion_scene_status", "scene_id", "status"),
        Index("idx_ingestion_created_at", "created_at"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts record to dictionary representation."""
        return {
            "batch_id": self.batch_id,
            "scene_id": self.scene_id,
            "source_filename": self.source_filename,
            "status": self.status,
            "error_details": self.error_details,
            "scenes_before": self.scenes_before,
            "scenes_after": self.scenes_after,
            "scenes_added": self.scenes_after - self.scenes_before,
            "tiles_before": self.tiles_before,
            "tiles_after": self.tiles_after,
            "tiles_added": self.tiles_after - self.tiles_before,
            "index_update_time_ms": round(self.index_update_time_ms, 2),
            "total_ingestion_time_ms": round(self.total_ingestion_time_ms, 2),
            "new_storage_bytes": self.new_storage_bytes,
            "total_storage_bytes": self.total_storage_bytes,
            "checksum_sha256": self.checksum_sha256,
            "crs": self.crs,
            "resolution_meters": self.resolution_meters,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
