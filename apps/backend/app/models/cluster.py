"""SQLAlchemy Declarative Models for AstraTrace Discovery & Clustering.

SIH 2026 | Problem ID: SIH26227
Tracks unsupervised semantic & spatial clusters across satellite tile embeddings,
identifying representative scenes, geographic envelopes, and dominant semantic tags.
"""
from datetime import datetime, timezone
import json
from typing import Any, Dict, List, Optional
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


class ClusterRecord(Base):
    """Discovery cluster record grouping similar sites across the archive."""
    __tablename__ = "clusters"

    cluster_id = Column(String(64), primary_key=True, index=True)
    cluster_label = Column(String(128), nullable=False)
    algorithm = Column(String(32), nullable=False, default="HDBSCAN")  # KMEANS, HDBSCAN, SPATIAL_SEMANTIC
    n_samples = Column(Integer, nullable=False, default=0)
    representative_tile_id = Column(String(160), nullable=False, index=True)
    representative_scene_id = Column(String(128), nullable=False)
    geographic_bounds = Column(Text, nullable=False)  # GeoJSON bbox or convex hull
    dominant_semantics = Column(Text, nullable=False, default="[]")  # JSON list of top semantic tags
    similarity_score = Column(Float, nullable=False, default=0.85)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("idx_clusters_algorithm", "algorithm"),
        Index("idx_clusters_rep_tile", "representative_tile_id"),
    )

    def get_dominant_semantics(self) -> List[str]:
        """Returns deserialized list of dominant semantic feature tags."""
        try:
            return json.loads(self.dominant_semantics)
        except Exception:
            return []

    def set_dominant_semantics(self, tags: List[str]) -> None:
        """Serializes list of dominant semantic feature tags."""
        self.dominant_semantics = json.dumps(tags)

    def to_dict(self) -> Dict[str, Any]:
        """Converts cluster record to dictionary."""
        try:
            geom = json.loads(self.geographic_bounds)
        except Exception:
            geom = None

        return {
            "cluster_id": self.cluster_id,
            "cluster_label": self.cluster_label,
            "algorithm": self.algorithm,
            "n_samples": self.n_samples,
            "representative_tile_id": self.representative_tile_id,
            "representative_scene_id": self.representative_scene_id,
            "geographic_bounds": geom,
            "dominant_semantics": self.get_dominant_semantics(),
            "similarity_score": round(self.similarity_score, 4),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
