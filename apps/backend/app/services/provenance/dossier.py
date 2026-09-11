"""Forensic Evidence Package Dossier Service for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Generates self-contained, air-gapped forensic evidence dossiers for intelligence
briefings, operational audits, and mission verification.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, Optional
import uuid
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import get_logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.schemas.provenance import EvidencePackageExportResponse
from apps.backend.app.services.audit.service import AuditService
from apps.backend.app.services.ingestion import calculate_file_sha256
from apps.backend.app.services.provenance.service import ProvenanceService
from apps.backend.app.services.provenance.verifier import ProvenanceVerifier

logger = get_logger("astratrace.dossier")


class EvidencePackageService:
    """Service producing tamper-evident forensic intelligence dossiers."""

    def __init__(self, db: Optional[Session] = None, project_root: Optional[Path] = None):
        if project_root is None:
            current = Path(__file__).resolve()
            for parent in current.parents:
                if (parent / "data").is_dir() and (parent / "README.md").is_file():
                    self.project_root = parent
                    break
            else:
                self.project_root = current.parents[5]
        else:
            self.project_root = project_root

        if db is not None:
            self.db = db
            self._owns_db = False
        else:
            self.db = SessionLocal()
            self._owns_db = True

        self.provenance_service = ProvenanceService(db=self.db, project_root=self.project_root)
        self.verifier = ProvenanceVerifier(db=self.db, project_root=self.project_root)
        self.audit_service = AuditService(db=self.db)

    def close(self):
        """Closes internal database session if owned."""
        if self._owns_db and self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def export_dossier(
        self,
        target_id: str,
        output_path: Optional[Path] = None,
        actor: str = "analyst_dossier_exporter",
    ) -> EvidencePackageExportResponse:
        """Compiles a complete forensic dossier with lineage DAG and cryptographic proof."""
        target_id = target_id.strip()
        export_id = f"exp_{uuid.uuid4().hex[:12]}"
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()

        # 1. Reconstruct full Lineage DAG
        graph = self.provenance_service.get_provenance_graph(target_id)

        # 2. Run automated cryptographic integrity verification
        verification = self.verifier.verify_target(target_id)

        # 3. Assemble dossier structure
        dossier_data: Dict[str, Any] = {
            "export_id": export_id,
            "export_standard": "AstraTrace-SIH26227-Evidence-Dossier-v1.0",
            "exported_at": now_iso,
            "mission_profile": {
                "problem_id": "SIH26227",
                "authority": "Ministry of Defence / Indian Army DGIS",
                "air_gapped_mode": True,
                "offline_guarantee": "Zero external cloud APIs, strictly local deterministic computation",
            },
            "target": {
                "target_id": target_id,
                "target_type": graph.root_type,
            },
            "provenance_graph": graph.model_dump(),
            "integrity_verification": verification.model_dump(),
            "forensic_summary": {
                "total_lineage_nodes": len(graph.nodes),
                "total_lineage_edges": len(graph.edges),
                "verification_status": verification.overall_status.value,
                "verified_artifacts": verification.verified_count,
                "tampered_artifacts": verification.tampered_count,
                "missing_artifacts": verification.missing_count,
            },
        }

        # 4. Resolve destination path
        export_dir = self.project_root / "data" / "processed" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)

        if output_path is None:
            safe_target_id = target_id.replace("/", "_").replace("\\", "_")
            export_filename = f"dossier_{safe_target_id}_{export_id}.json"
            dest_abs = export_dir / export_filename
        else:
            dest_abs = Path(output_path)
            if not dest_abs.is_absolute():
                dest_abs = (self.project_root / dest_abs).resolve()
            dest_abs.parent.mkdir(parents=True, exist_ok=True)

        # 5. Write file and compute package SHA-256
        with open(dest_abs, "w", encoding="utf-8") as f:
            json.dump(dossier_data, f, indent=2)

        package_checksum = calculate_file_sha256(dest_abs)
        package_size_bytes = dest_abs.stat().st_size

        rel_path = (
            str(dest_abs.relative_to(self.project_root)).replace("\\", "/")
            if str(dest_abs).startswith(str(self.project_root))
            else str(dest_abs)
        )

        # 6. Log audit event
        self.audit_service.log_event(
            event_type="DOSSIER_EXPORT",
            actor=actor,
            action="GENERATE_DOSSIER",
            target_id=target_id,
            target_type=graph.root_type,
            status="SUCCESS",
            details={
                "export_id": export_id,
                "package_path": rel_path,
                "package_checksum": package_checksum,
                "package_size_bytes": package_size_bytes,
                "verification_status": verification.overall_status.value,
            },
        )

        logger.info(
            f"Evidence dossier exported {export_id} for target {target_id} -> "
            f"{rel_path} ({package_size_bytes} bytes, SHA-256: {package_checksum[:12]}...)"
        )

        return EvidencePackageExportResponse(
            export_id=export_id,
            target_id=target_id,
            target_type=graph.root_type,
            package_path=rel_path,
            package_checksum=package_checksum,
            package_size_bytes=package_size_bytes,
            exported_at=now_iso,
            contents_summary=dossier_data["forensic_summary"],
        )
