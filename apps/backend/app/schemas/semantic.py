"""Pydantic v2 Schemas for Semantic Retrieval and Vector Indexing.

SIH 2026 | Problem ID: SIH26227
Defines request contracts, hybrid scoring payloads, and response models.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field, model_validator


class SemanticSearchRequest(BaseModel):
    """Request contract for natural-language satellite semantic search."""
    query: str = Field(..., min_length=1, max_length=500, description="Natural language semantic concept")
    bbox: Optional[Tuple[float, float, float, float]] = Field(
        None, description="Optional bounding box [min_lon, min_lat, max_lon, max_lat]"
    )
    point: Optional[Tuple[float, float]] = Field(
        None, description="Optional point coordinates [lon, lat]"
    )
    date_from: Optional[datetime] = Field(None, description="Earliest observation timestamp")
    date_to: Optional[datetime] = Field(None, description="Latest observation timestamp")
    sensor: Optional[str] = Field(None, description="Satellite sensor filter (e.g. SENTINEL-2)")
    collection: Optional[str] = Field(None, description="Catalog collection name filter")
    top_k: int = Field(10, ge=1, le=50, description="Maximum results to return")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Minimum confidence cutoff")
    hybrid_weight: float = Field(
        0.65, ge=0.0, le=1.0, description="Weight alpha: score = alpha * S_semantic + (1-alpha) * S_baseline"
    )


class SimilarTilesRequest(BaseModel):
    """Request contract for image-to-image similarity search ('Find Similar Sites')."""
    reference_tile_id: Optional[str] = Field(None, description="Catalog tile ID of reference image")
    reference_raster_path: Optional[str] = Field(None, description="Direct file path to reference raster")
    bbox: Optional[Tuple[float, float, float, float]] = Field(None, description="Optional spatial bounding box")
    sensor: Optional[str] = Field(None, description="Sensor filter")
    top_k: int = Field(10, ge=1, le=50, description="Maximum similar tiles to return")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Minimum confidence cutoff")

    @model_validator(mode="after")
    def validate_reference(self):
        if not self.reference_tile_id and not self.reference_raster_path:
            raise ValueError("Must provide either reference_tile_id or reference_raster_path.")
        return self


class SemanticTileResult(BaseModel):
    """Individual ranked tile result with semantic, baseline, and hybrid scores."""
    rank: int = Field(..., description="1-indexed rank")
    tile_id: str = Field(..., description="Unique tile identifier")
    scene_id: str = Field(..., description="Parent scene identifier")
    semantic_score: float = Field(..., description="Normalized semantic score in [0.0, 1.0]")
    cosine_sim: float = Field(..., description="Raw cosine similarity in [-1.0, 1.0]")
    baseline_score: Optional[float] = Field(None, description="Baseline keyword/spatial/temporal score")
    hybrid_score: float = Field(..., description="Blended hybrid ranking score")
    bounds_wgs84: List[float] = Field(..., description="[min_lon, min_lat, max_lon, max_lat]")
    geometry: Dict[str, Any] = Field(..., description="GeoJSON polygon geometry")
    checksum: str = Field(..., description="SHA-256 tile hash")
    acquired_at: Optional[str] = Field(None, description="Observation timestamp")
    sensor: str = Field(..., description="Satellite sensor name")
    path: str = Field(..., description="Relative raster path")


class SemanticSearchResponse(BaseModel):
    """Complete response payload for semantic and hybrid vector retrieval."""
    query_id: str = Field(..., description="Unique execution query ID")
    search_mode: str = Field(..., description="'semantic_text', 'similar_image', or 'hybrid'")
    model_info: Dict[str, Any] = Field(..., description="Vision-language model metadata")
    total_indexed: int = Field(..., description="Total tiles indexed in vector store")
    returned_results: int = Field(..., description="Number of results returned")
    results: List[SemanticTileResult] = Field(..., description="Ranked tile candidates")
    execution_trace: Dict[str, float] = Field(..., description="Timing breakdown in milliseconds")


class IndexStatusResponse(BaseModel):
    """Health and status metadata for the local vector index."""
    total_indexed: int = Field(..., description="Total vector embeddings indexed")
    dimension: int = Field(..., description="Vector embedding dimension (512)")
    model_name: str = Field(..., description="Active embedding model name")
    status: str = Field(..., description="Vector index operational status")
    index_file: Optional[str] = Field(None, description="Path to persisted index cache")
