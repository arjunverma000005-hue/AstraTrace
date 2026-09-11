"""Analyst Review Service for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Manages human-in-the-loop analyst decisions, audit logging, evidence-first queue aggregation,
and decision persistence. Preserves immutable provenance; prohibited from retraining models.
"""
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy import desc
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import get_logger
from apps.backend.app.models.catalog import TileRecord
from apps.backend.app.models.review import AnalystReviewRecord
from apps.backend.app.schemas.review import (
    ReviewDecision,
    ReviewHistoryResponse,
    ReviewQueueItem,
    ReviewQueueResponse,
    ReviewRecordResponse,
    SubmitReviewRequest,
    TargetType,
)

logger = get_logger("astratrace.review")

# Strict regex identifier validation against path traversal
TARGET_ID_REGEX = re.compile(r"^[a-zA-Z0-9_\-\.]+$")


class AnalystReviewService:
    """Service handling analyst triage, decision persistence, and queue management."""

    def __init__(self, db: Session, project_root: Optional[Path] = None):
        self.db = db
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

    def submit_decision(self, request: SubmitReviewRequest) -> ReviewRecordResponse:
        """Records an auditable analyst review decision with an evidence snapshot."""
        # 1. Validate target identifier safety
        if not TARGET_ID_REGEX.match(request.target_id):
            raise ValidationError(f"Invalid target ID format: {request.target_id}")

        # 2. Extract confidence, quality status, and provenance snapshot
        confidence_snapshot = 0.50
        quality_status_snapshot = "USABLE"
        provenance_snapshot: Dict[str, Any] = {
            "target_id": request.target_id,
            "target_type": request.target_type.value,
            "review_timestamp": datetime.now(timezone.utc).isoformat(),
        }

        if request.target_type == TargetType.TILE:
            tile = self.db.query(TileRecord).filter(TileRecord.tile_id == request.target_id).first()
            if not tile:
                raise NotFoundError(f"Target tile '{request.target_id}' not found in catalog.")
            confidence_snapshot = round(float(1.0 - (tile.cloud_cover_percent / 100.0)), 4)
            quality_status_snapshot = "USABLE" if tile.cloud_cover_percent < 20.0 else "DEGRADED"
            provenance_snapshot.update({
                "scene_id": tile.scene_id,
                "tile_index": tile.tile_index,
                "checksum": tile.checksum,
                "cloud_cover_percent": tile.cloud_cover_percent,
                "nodata_percent": tile.nodata_percent,
            })
        else:
            # Change detection event (qchg_ or chg_)
            provenance_snapshot.update({
                "source": "baseline_or_gated_change_detection",
            })

        # 3. Create review record
        review_id = f"rev_{uuid.uuid4().hex[:12]}"
        now_dt = datetime.now(timezone.utc)
        record = AnalystReviewRecord(
            review_id=review_id,
            target_id=request.target_id,
            target_type=request.target_type.value,
            decision=request.decision.value,
            analyst_id=request.analyst_id.strip(),
            notes=request.notes.strip() if request.notes else None,
            confidence_at_review=confidence_snapshot,
            quality_status_at_review=quality_status_snapshot,
            provenance_snapshot=provenance_snapshot,
            created_at=now_dt,
            updated_at=now_dt,
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        logger.info(
            f"Analyst review recorded: {review_id} target={request.target_id} "
            f"decision={request.decision.value} analyst={request.analyst_id}"
        )

        try:
            from apps.backend.app.services.audit.service import AuditService
            audit_svc = AuditService(db=self.db)
            audit_svc.log_event(
                event_type="ANALYST_REVIEW",
                actor=request.analyst_id.strip(),
                action="SUBMIT_DECISION",
                target_id=request.target_id,
                target_type=request.target_type.value,
                status="SUCCESS",
                details={
                    "review_id": review_id,
                    "decision": request.decision.value,
                    "notes": request.notes,
                    "confidence_at_review": confidence_snapshot,
                    "quality_status_at_review": quality_status_snapshot,
                },
            )
        except Exception as e:
            logger.warning(f"Failed to record audit event for review {review_id}: {e}")

        return ReviewRecordResponse(
            review_id=record.review_id,
            target_id=record.target_id,
            target_type=record.target_type,
            decision=ReviewDecision(record.decision),
            analyst_id=record.analyst_id,
            notes=record.notes,
            confidence_at_review=record.confidence_at_review,
            quality_status_at_review=record.quality_status_at_review,
            provenance_snapshot=record.provenance_snapshot or {},
            created_at=record.created_at.isoformat(),
            updated_at=record.updated_at.isoformat(),
        )

    def get_history(self, target_id: str) -> ReviewHistoryResponse:
        """Retrieves chronological decision audit history for a given target."""
        if not TARGET_ID_REGEX.match(target_id):
            raise ValidationError(f"Invalid target ID format: {target_id}")

        records = (
            self.db.query(AnalystReviewRecord)
            .filter(AnalystReviewRecord.target_id == target_id)
            .order_by(desc(AnalystReviewRecord.created_at))
            .all()
        )

        history_items = [
            ReviewRecordResponse(
                review_id=r.review_id,
                target_id=r.target_id,
                target_type=r.target_type,
                decision=ReviewDecision(r.decision),
                analyst_id=r.analyst_id,
                notes=r.notes,
                confidence_at_review=r.confidence_at_review,
                quality_status_at_review=r.quality_status_at_review,
                provenance_snapshot=r.provenance_snapshot or {},
                created_at=r.created_at.isoformat(),
                updated_at=r.updated_at.isoformat(),
            )
            for r in records
        ]

        return ReviewHistoryResponse(
            target_id=target_id,
            total_reviews=len(history_items),
            history=history_items,
        )

    def get_queue(
        self,
        status_filter: Optional[ReviewDecision] = None,
        target_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> ReviewQueueResponse:
        """Aggregates catalog items into an Evidence-First operational review queue."""
        # Query all tiles from catalog
        tile_query = self.db.query(TileRecord).order_by(TileRecord.tile_id.asc())
        tiles: List[TileRecord] = tile_query.all()

        # Build map of latest reviews by target_id
        reviews: List[AnalystReviewRecord] = (
            self.db.query(AnalystReviewRecord)
            .order_by(AnalystReviewRecord.created_at.desc())
            .all()
        )
        latest_reviews: Dict[str, AnalystReviewRecord] = {}
        for r in reviews:
            if r.target_id not in latest_reviews:
                latest_reviews[r.target_id] = r

        queue_items: List[ReviewQueueItem] = []
        pending_count = 0
        confirmed_count = 0
        rejected_count = 0
        flagged_count = 0

        for idx, t in enumerate(tiles):
            curr_rev = latest_reviews.get(t.tile_id)
            decision = ReviewDecision(curr_rev.decision) if curr_rev else ReviewDecision.PENDING_REVIEW

            if decision == ReviewDecision.PENDING_REVIEW:
                pending_count += 1
            elif decision == ReviewDecision.CONFIRMED:
                confirmed_count += 1
            elif decision == ReviewDecision.REJECTED:
                rejected_count += 1
            elif decision == ReviewDecision.FLAGGED_FOR_INSPECTION:
                flagged_count += 1

            # Apply filter
            if status_filter and status_filter != ReviewDecision.PENDING_REVIEW:
                if decision != status_filter:
                    continue
            elif status_filter == ReviewDecision.PENDING_REVIEW:
                if decision != ReviewDecision.PENDING_REVIEW:
                    continue

            # Calculate confidence and evidence metrics
            cloud_pct = t.cloud_cover_percent or 0.0
            usable_frac = round(max(0.0, 1.0 - (cloud_pct / 100.0)), 4)
            conf = usable_frac
            qual_status = "USABLE" if cloud_pct < 10.0 else ("DEGRADED" if cloud_pct < 30.0 else "UNRELIABLE")
            flags = ["HIGH_QUALITY_CLEAR"] if cloud_pct < 5.0 else (["CLOUD_HAZE"] if cloud_pct >= 10.0 else [])

            centroid = [
                round((t.min_lon + t.max_lon) / 2.0, 6),
                round((t.min_lat + t.max_lat) / 2.0, 6),
            ]
            bbox = [t.min_lon, t.min_lat, t.max_lon, t.max_lat]
            geometry = {
                "type": "Polygon",
                "coordinates": [[
                    [t.min_lon, t.min_lat],
                    [t.max_lon, t.min_lat],
                    [t.max_lon, t.max_lat],
                    [t.min_lon, t.max_lat],
                    [t.min_lon, t.min_lat],
                ]],
            }

            serialized_rev = None
            if curr_rev:
                serialized_rev = ReviewRecordResponse(
                    review_id=curr_rev.review_id,
                    target_id=curr_rev.target_id,
                    target_type=curr_rev.target_type,
                    decision=ReviewDecision(curr_rev.decision),
                    analyst_id=curr_rev.analyst_id,
                    notes=curr_rev.notes,
                    confidence_at_review=curr_rev.confidence_at_review,
                    quality_status_at_review=curr_rev.quality_status_at_review,
                    provenance_snapshot=curr_rev.provenance_snapshot or {},
                    created_at=curr_rev.created_at.isoformat(),
                    updated_at=curr_rev.updated_at.isoformat(),
                )

            item = ReviewQueueItem(
                queue_id=f"qitem_{t.tile_id}",
                target_id=t.tile_id,
                target_type="TILE",
                what=f"Sentinel-2 Observation (Tile {t.tile_index})",
                where={
                    "bbox": bbox,
                    "centroid": centroid,
                    "geometry": geometry,
                    "coordinates": [
                        [bbox[0], bbox[3]],
                        [bbox[2], bbox[3]],
                        [bbox[2], bbox[1]],
                        [bbox[0], bbox[1]],
                    ],
                    "crs": "EPSG:32643",
                },
                when=t.scene.acquired_at.isoformat() if t.scene and t.scene.acquired_at else None,
                which={
                    "sensor": t.scene.sensor if t.scene else "SENTINEL-2",
                    "scene_id": t.scene_id,
                    "tile_id": t.tile_id,
                    "tile_index": t.tile_index,
                },
                why={
                    "confidence_score": conf,
                    "usable_area_score": usable_frac,
                    "spatial_extent": "Western Ghats, MH",
                },
                confidence=conf,
                quality_status=qual_status,
                quality_flags=flags,
                evidence={
                    "preview_url": f"/api/v1/catalog/tiles/{t.tile_id}/preview",
                    "mask_url": None,
                    "usable_fraction": usable_frac,
                    "cloud_fraction": round(cloud_pct / 100.0, 4),
                    "shadow_fraction": 0.0,
                    "scene_preview_url": f"/api/v1/catalog/scenes/{t.scene_id}/preview" if t.scene else None,
                    "scene_bbox": [t.scene.min_lon, t.scene.min_lat, t.scene.max_lon, t.scene.max_lat] if t.scene else None,
                    "scene_coordinates": [
                        [t.scene.min_lon, t.scene.max_lat],
                        [t.scene.max_lon, t.scene.max_lat],
                        [t.scene.max_lon, t.scene.min_lat],
                        [t.scene.min_lon, t.scene.min_lat],
                    ] if t.scene else None,
                },
                provenance={
                    "checksum": t.checksum,
                    "pixel_size": f"{t.width}x{t.height}",
                    "bands": 4,
                },
                review_status=decision,
                current_review=serialized_rev,
            )
            queue_items.append(item)

        total_filtered = len(queue_items)
        paginated_items = queue_items[offset : offset + limit]

        return ReviewQueueResponse(
            total=total_filtered,
            pending_count=pending_count,
            confirmed_count=confirmed_count,
            rejected_count=rejected_count,
            flagged_count=flagged_count,
            items=paginated_items,
        )
