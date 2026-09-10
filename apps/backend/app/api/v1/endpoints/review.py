"""API endpoints for AstraTrace Analyst Review Queue and Decision Persistence.

SIH 2026 | Problem ID: SIH26227
Provides operational endpoints for human-in-the-loop triage, audit trails, and decision logging.
"""
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.schemas.review import (
    ReviewDecision,
    ReviewHistoryResponse,
    ReviewQueueResponse,
    ReviewRecordResponse,
    SubmitReviewRequest,
)
from apps.backend.app.services.review.service import AnalystReviewService

router = APIRouter(prefix="/review", tags=["review"])


@router.post(
    "/decision",
    response_model=ReviewRecordResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit Analyst Decision",
    description=(
        "Records an auditable analyst review decision (CONFIRMED, REJECTED, or FLAGGED_FOR_INSPECTION) "
        "along with an immutable snapshot of evidence confidence and provenance."
    ),
)
def submit_analyst_decision(
    request: SubmitReviewRequest,
    db: Session = Depends(get_db),
) -> ReviewRecordResponse:
    """Persists a human-in-the-loop review decision into the catalog database."""
    service = AnalystReviewService(db=db)
    return service.submit_decision(request)


@router.get(
    "/queue",
    response_model=ReviewQueueResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Analyst Review Queue",
    description=(
        "Retrieves a paginated, Evidence-First review queue of observation targets "
        "filterable by review status (PENDING_REVIEW, CONFIRMED, REJECTED, FLAGGED)."
    ),
)
def get_review_queue(
    status: Optional[ReviewDecision] = Query(
        None,
        description="Filter by decision state: PENDING_REVIEW, CONFIRMED, REJECTED, FLAGGED_FOR_INSPECTION",
    ),
    target_type: Optional[str] = Query(
        None,
        description="Filter by target type: TILE or CHANGE",
    ),
    limit: int = Query(50, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: Session = Depends(get_db),
) -> ReviewQueueResponse:
    """Returns items in the operational analyst queue."""
    service = AnalystReviewService(db=db)
    return service.get_queue(
        status_filter=status,
        target_type=target_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/history/{target_id}",
    response_model=ReviewHistoryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Target Review History",
    description="Returns the full chronological audit trail of analyst decisions for a specific target.",
)
def get_target_review_history(
    target_id: str,
    db: Session = Depends(get_db),
) -> ReviewHistoryResponse:
    """Returns decision history for auditability and provenance."""
    service = AnalystReviewService(db=db)
    return service.get_history(target_id)
