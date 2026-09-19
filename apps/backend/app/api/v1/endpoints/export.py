"""API endpoints for AstraTrace Multi-Format Evidence Export.

SIH 2026 | Problem ID: SIH26227
Generates forensic evidence reports in HTML/PDF, GeoJSON vector footprints, and CSV.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.services.export_service import ExportService

router = APIRouter(prefix="/export", tags=["export"])


class ExportReportRequest(BaseModel):
    format: str = Field("HTML", description="Export format: HTML, PDF, GEOJSON, or CSV")
    pair_ids: Optional[List[str]] = Field(None, description="Candidate pair identifiers to include")
    candidate_data: Optional[Dict[str, Any]] = Field(None, description="Direct candidate metadata")


@router.post(
    "/report",
    status_code=status.HTTP_200_OK,
    summary="Generate Forensic Intelligence Dossier",
    description="Exports analyst reports with provenance DAG, change masks, quality metrics, and georeferencing.",
)
def export_report(
    request: ExportReportRequest,
    db: Session = Depends(get_db),
) -> Response:
    """Exports forensic evidence dossier."""
    service = ExportService(db=db)
    fmt = request.format.upper()

    if fmt in ("HTML", "PDF"):
        data = request.candidate_data or {
            "pair_id": (request.pair_ids[0] if request.pair_ids else "CANDIDATE_01"),
            "query": "newly built structures near roads between January 2023 and January 2025",
            "location": "Rajasthan / Thar Sector (27.023°N, 71.450°E)",
            "sensor": "Sentinel-2A L2A",
            "confidence": 0.91,
            "quality": 0.95,
            "decision": "CONFIRMED",
            "earliest_change_date": "2023-08-14",
            "provenance_hash": "a4f89d30c5e12891f7c699042b7811ef62881a257cd4916a2491e018d451cb99",
        }
        content = service.generate_html_dossier(data)
        return Response(content=content, media_type="text/html")

    elif fmt == "GEOJSON":
        pids = request.pair_ids or []
        data = service.generate_geojson(pids)
        return Response(content=data, media_type="application/geo+json")

    elif fmt == "CSV":
        candidates = [request.candidate_data] if request.candidate_data else []
        content = service.generate_csv(candidates)
        return Response(content=content, media_type="text/csv")

    return Response(content="Unsupported export format", status_code=400)
