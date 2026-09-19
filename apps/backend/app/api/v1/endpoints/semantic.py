"""API endpoints for AstraTrace semantic vector retrieval and embedding indexing.

SIH 2026 | Problem ID: SIH26227
Provides natural-language satellite search, image-to-image similarity, and index status.
"""
from typing import Any, Dict
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.schemas.semantic import (
    IndexStatusResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SimilarTilesRequest,
)
from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService

router = APIRouter(tags=["semantic-search"])


@router.post(
    "/search/semantic",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Natural Language Semantic Satellite Search",
    description=(
        "Encodes an unconstrained natural-language query into a 512-dimensional vector embedding, "
        "executes exact cosine similarity search over indexed satellite tiles, applies spatial/temporal filters, "
        "and blends with baseline keyword/spectral scoring in hybrid mode."
    ),
)
def search_semantic(
    request: SemanticSearchRequest,
    db: Session = Depends(get_db),
) -> SemanticSearchResponse:
    """Executes natural-language semantic vector retrieval and hybrid ranking."""
    service = SemanticRetrievalService(db=db)
    return service.search_semantic(request)


@router.post(
    "/search/similar-tiles",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Image-to-Image Satellite Tile Similarity",
    description=(
        "Given a reference catalog tile ID or raster file, extracts its 512-dimensional embedding and retrieves "
        "the most semantically and visually similar satellite tiles across the catalog ('Find Similar Sites')."
    ),
)
@router.post(
    "/search/image",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Image-to-Image Similarity Search",
    description="Finds similar satellite locations from a selected tile ID, crop, or reference image.",
)
def search_similar_tiles(
    request: SimilarTilesRequest,
    db: Session = Depends(get_db),
) -> SemanticSearchResponse:
    """Finds visually and semantically similar satellite tiles given a reference image."""
    service = SemanticRetrievalService(db=db)
    return service.search_similar_tiles(request)


@router.get(
    "/similar/{tile_id}",
    response_model=SemanticSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Find Similar Sites by Tile ID",
    description="Convenience endpoint returning top similar sites for an analyst-selected tile.",
)
def get_similar_by_tile_id(
    tile_id: str,
    top_k: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
) -> SemanticSearchResponse:
    """Finds similar sites by tile ID."""
    service = SemanticRetrievalService(db=db)
    req = SimilarTilesRequest(reference_tile_id=tile_id, top_k=top_k)
    return service.search_similar_tiles(req)


@router.post(
    "/embeddings/index",
    status_code=status.HTTP_200_OK,
    summary="Index All Catalog Tiles Into Vector Store",
    description="Batch-computes vision embeddings for all cataloged tiles and persists the vector index.",
)
def index_embeddings(
    force_reindex: bool = Query(False, description="Whether to recompute existing embeddings"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Generates embeddings for all catalog tiles and saves vector cache."""
    service = SemanticRetrievalService(db=db)
    return service.index_catalog_tiles(force_reindex=force_reindex)


@router.get(
    "/embeddings/status",
    response_model=IndexStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Vector Index Status",
    description="Returns total indexed embeddings, vector dimension, model architecture, and cache status.",
)
def get_embeddings_status(
    db: Session = Depends(get_db),
) -> IndexStatusResponse:
    """Returns vector store health and indexing diagnostics."""
    service = SemanticRetrievalService(db=db)
    return service.get_index_status()
