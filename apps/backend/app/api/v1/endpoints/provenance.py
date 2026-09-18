"""FastAPI router for AstraTrace Provenance Graph, Integrity Verification, and Audit Logging.

SIH 2026 | Problem ID: SIH26227
Provides REST interfaces for lineage DAG retrieval, cryptographic file verification,
forensic evidence dossier generation, and append-oriented audit logs.
"""
import re
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import ValidationError
from apps.backend.app.db.session import get_db, get_state_db
from apps.backend.app.schemas.audit import AuditEventResponse, AuditLogResponse
from apps.backend.app.schemas.provenance import (
    EvidencePackageExportResponse,
    IntegrityVerificationRequest,
    IntegrityVerificationResponse,
    ProvenanceGraphResponse,
)
from apps.backend.app.services.audit.service import AuditService
from apps.backend.app.services.provenance.dossier import EvidencePackageService
from apps.backend.app.services.provenance.service import ProvenanceService
from apps.backend.app.services.provenance.verifier import ProvenanceVerifier

router = APIRouter(prefix="/provenance", tags=["provenance"])

# Strict regex identifier validation against path traversal
TARGET_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


def validate_target_id(target_id: str) -> str:
    """Validates alphanumeric and safe character format of identifiers."""
    clean_id = target_id.strip()
    if not clean_id or not TARGET_ID_REGEX.match(clean_id) or ".." in clean_id:
        raise ValidationError(f"Invalid target identifier format: '{target_id}'")
    return clean_id


@router.get(
    "/graph/{target_id}",
    response_model=ProvenanceGraphResponse,
    summary="Get Provenance Graph (DAG)",
    description="Constructs and returns the full Directed Acyclic Graph (DAG) representing the complete lineage of an analytical entity.",
)
async def get_provenance_graph(
    target_id: str,
    db: Session = Depends(get_db),
) -> ProvenanceGraphResponse:
    """Returns nodes and directed edges tracing processing history."""
    clean_id = validate_target_id(target_id)
    with ProvenanceService(db=db) as service:
        return service.get_provenance_graph(clean_id)


@router.post(
    "/verify",
    response_model=IntegrityVerificationResponse,
    summary="Verify Artifact Integrity",
    description="Recomputes streaming SHA-256 hashes of on-disk analytical artifacts and verifies against catalog checksums.",
)
async def verify_integrity(
    request: IntegrityVerificationRequest,
    db: Session = Depends(get_db),
) -> IntegrityVerificationResponse:
    """Performs real-time cryptographic verification and detects tampered or missing files."""
    if not request.target_id:
        raise ValidationError("Field 'target_id' is required for integrity verification.")
    clean_id = validate_target_id(request.target_id)

    with ProvenanceVerifier(db=db) as verifier:
        return verifier.verify_target(clean_id)


@router.get(
    "/export/{target_id}",
    response_model=EvidencePackageExportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Export Forensic Evidence Dossier",
    description="Generates an offline, air-gapped forensic evidence dossier containing lineage DAG, integrity proof, and mission metadata.",
)
async def export_evidence_dossier(
    target_id: str,
    db: Session = Depends(get_db),
) -> EvidencePackageExportResponse:
    """Compiles and exports a self-contained intelligence dossier."""
    clean_id = validate_target_id(target_id)
    with EvidencePackageService(db=db) as service:
        return service.export_dossier(clean_id)


@router.get(
    "/audit-log",
    response_model=AuditLogResponse,
    summary="Query Structured Audit Log",
    description="Queries the append-oriented audit log for tracking system events, verifications, and analyst triage history.",
)
async def query_audit_log(
    event_type: Optional[str] = Query(None, description="Filter by event category"),
    actor: Optional[str] = Query(None, description="Filter by actor ID"),
    target_id: Optional[str] = Query(None, description="Filter by target identifier"),
    status: Optional[str] = Query(None, description="Filter by execution status"),
    limit: int = Query(50, ge=1, le=500, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
    state_db: Session = Depends(get_state_db),
) -> AuditLogResponse:
    """Returns filtered, chronologically ordered audit records."""
    clean_target = validate_target_id(target_id) if target_id else None

    with AuditService(db=state_db) as service:
        total, records = service.query_events(
            event_type=event_type,
            actor=actor,
            target_id=clean_target,
            status=status,
            limit=limit,
            offset=offset,
        )

        serialized = [
            AuditEventResponse(
                event_id=r.event_id,
                event_type=r.event_type,
                actor=r.actor,
                action=r.action,
                target_id=r.target_id,
                target_type=r.target_type,
                status=r.status,
                details=r.details or {},
                created_at=r.created_at.isoformat() if r.created_at else "",
            )
            for r in records
        ]

        return AuditLogResponse(
            total=total,
            limit=limit,
            offset=offset,
            events=serialized,
        )
