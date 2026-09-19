"""SQLAlchemy Declarative Models for AstraTrace Change Detection & Verification.

SIH 2026 | Problem ID: SIH26227
Tracks bitemporal change candidate pairs, quality gate verdicts, false-alarm
suppression rationales, earliest supported change dates, and vectorized footprints.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, Optional
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    Index,
)

from apps.backend.app.db.session import Base


class ChangePairRecord(Base):
    """Bitemporal change candidate record evaluated by the Quality Gate."""
    __tablename__ = "change_pairs"

    pair_id = Column(String(64), primary_key=True, index=True)
    t1_scene_id = Column(String(128), nullable=False, index=True)
    t2_scene_id = Column(String(128), nullable=False, index=True)
    t1_tile_id = Column(String(160), nullable=False, index=True)
    t2_tile_id = Column(String(160), nullable=False, index=True)

    baseline_date = Column(DateTime(timezone=True), nullable=True, index=True)
    target_date = Column(DateTime(timezone=True), nullable=True, index=True)

    # Scores
    change_score = Column(Float, nullable=False, default=0.0)
    quality_score = Column(Float, nullable=False, default=1.0)
    confidence_score = Column(Float, nullable=False, default=0.0)

    # Classification & Quality Gate
    change_type = Column(String(64), nullable=False, default="CONSTRUCTION")  # CONSTRUCTION, CLEARANCE, etc.
    quality_gate_status = Column(String(16), nullable=False, default="PASS")  # PASS, REJECT
    quality_gate_reason = Column(Text, nullable=False, default="PASSED_VERIFICATION")
    earliest_change_date = Column(DateTime(timezone=True), nullable=True)

    # Artifacts & Footprint
    mask_file_path = Column(String(512), nullable=True)
    vector_geojson = Column(Text, nullable=True)  # GeoJSON polygon or MultiPolygon of change
    changed_pixels = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_change_pairs_gate_status", "quality_gate_status"),
        Index("idx_change_pairs_type", "change_type"),
        Index("idx_change_pairs_dates", "baseline_date", "target_date"),
    )

    def to_dict(self) -> Dict[str, Any]:
        """Converts record to dictionary."""
        try:
            footprint = json.loads(self.vector_geojson) if self.vector_geojson else None
        except Exception:
            footprint = None

        return {
            "pair_id": self.pair_id,
            "t1_scene_id": self.t1_scene_id,
            "t2_scene_id": self.t2_scene_id,
            "t1_tile_id": self.t1_tile_id,
            "t2_tile_id": self.t2_tile_id,
            "baseline_date": self.baseline_date.isoformat() if self.baseline_date else None,
            "target_date": self.target_date.isoformat() if self.target_date else None,
            "change_score": round(self.change_score, 4),
            "quality_score": round(self.quality_score, 4),
            "confidence_score": round(self.confidence_score, 4),
            "change_type": self.change_type,
            "quality_gate_status": self.quality_gate_status,
            "quality_gate_reason": self.quality_gate_reason,
            "earliest_change_date": self.earliest_change_date.isoformat() if self.earliest_change_date else None,
            "mask_file_path": self.mask_file_path,
            "changed_pixels": self.changed_pixels,
            "vector_geojson": footprint,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
