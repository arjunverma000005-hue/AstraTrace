"""SQLAlchemy Declarative Model for AstraTrace Vector Embeddings.

SIH 2026 | Problem ID: SIH26227
Stores 512-dimensional vector embeddings linked to catalog tiles and scenes,
supporting cosine similarity search, model provenance, and cryptographic checksums.
"""
from datetime import datetime, timezone
import hashlib
from typing import Any, Dict, Optional
import numpy as np
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    Index,
)
from sqlalchemy.orm import relationship

from apps.backend.app.db.session import Base


class TileEmbeddingRecord(Base):
    """Stores high-dimensional satellite tile embeddings with provenance."""

    __tablename__ = "embeddings"

    embedding_id = Column(String(64), primary_key=True, index=True)
    tile_id = Column(String(160), ForeignKey("tiles.tile_id", ondelete="CASCADE"), nullable=False, index=True)
    scene_id = Column(String(128), ForeignKey("scenes.scene_id", ondelete="CASCADE"), nullable=False, index=True)
    model_name = Column(String(64), nullable=False, default="RemoteCLIP-ViT-B-32")
    model_version = Column(String(32), nullable=False, default="1.0.0")
    dimension = Column(Integer, nullable=False, default=512)
    vector_blob = Column(LargeBinary, nullable=False)
    checksum = Column(String(64), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    tile = relationship("TileRecord", backref="embeddings")
    scene = relationship("SceneRecord", backref="embeddings")

    __table_args__ = (
        Index("idx_embeddings_tile_model", "tile_id", "model_name"),
        Index("idx_embeddings_scene", "scene_id"),
    )

    def set_vector(self, vector: np.ndarray) -> None:
        """Serializes a 1D float32 numpy array into the vector_blob column and updates checksum."""
        arr = np.asarray(vector, dtype=np.float32).ravel()
        if len(arr) != self.dimension:
            raise ValueError(f"Vector dimension mismatch: expected {self.dimension}, got {len(arr)}")
        raw_bytes = arr.tobytes()
        self.vector_blob = raw_bytes
        self.checksum = hashlib.sha256(raw_bytes).hexdigest()

    def get_vector(self) -> np.ndarray:
        """Deserializes vector_blob into a normalized 1D float32 numpy array."""
        if not self.vector_blob:
            return np.zeros(self.dimension, dtype=np.float32)
        arr = np.frombuffer(self.vector_blob, dtype=np.float32)
        return arr.copy()

    def to_dict(self) -> Dict[str, Any]:
        """Serializes metadata without dumping raw binary buffer."""
        return {
            "embedding_id": self.embedding_id,
            "tile_id": self.tile_id,
            "scene_id": self.scene_id,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "dimension": self.dimension,
            "checksum": self.checksum,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<TileEmbeddingRecord(id='{self.embedding_id}', tile='{self.tile_id}', model='{self.model_name}', dim={self.dimension})>"
