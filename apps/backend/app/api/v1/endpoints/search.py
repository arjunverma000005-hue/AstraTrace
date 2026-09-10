"""API endpoints for AstraTrace baseline retrieval search.

SIH 2026 | Problem ID: SIH26227
Provides deterministic, structured keyword and spatial/temporal tile search.
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.schemas.search import (
    BaselineSearchRequest,
    BaselineSearchResponse,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
)
from apps.backend.app.services.retrieval.service import BaselineRetrievalService
from apps.backend.app.services.search.unified_service import UnifiedSearchService

router = APIRouter(prefix="/search", tags=["search"])


@router.post(
    "/baseline",
    response_model=BaselineSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Baseline Tile Retrieval",
    description=(
        "Performs deterministic baseline retrieval by combining SQL spatial/temporal filtering, "
        "EuroSAT controlled vocabulary mapping, and multispectral feature classification. "
        "Returns ranked candidate tiles with sub-millisecond execution traces."
    ),
)
def baseline_search(
    request: BaselineSearchRequest,
    db: Session = Depends(get_db),
) -> BaselineSearchResponse:
    """Executes a multi-factor baseline search across cataloged satellite tiles."""
    service = BaselineRetrievalService(db=db)
    return service.search(request)


@router.post(
    "/unified",
    response_model=UnifiedSearchResponse,
    status_code=status.HTTP_200_OK,
    summary="Unified Multi-Modal Search",
    description=(
        "Consolidated search endpoint supporting AUTO (hybrid), SEMANTIC, KEYWORD, or CHANGE modalities. "
        "Returns Evidence-First ranked candidates with score breakdowns, optical preview links, "
        "quality indicators, and analyst triage status."
    ),
)
def unified_search(
    request: UnifiedSearchRequest,
    db: Session = Depends(get_db),
) -> UnifiedSearchResponse:
    """Executes a unified multi-modal search delivering Evidence-First candidates."""
    service = UnifiedSearchService(db=db)
    return service.search(request)

