"""AstraTrace Quality Gate & False-Alarm Suppression Engine.

SIH 2026 | Problem ID: SIH26227
Decouples raw change magnitude from evidence quality, suppresses false alarms
caused by clouds, shadows, and boundary artifacts, assigns explicit uncertainty states,
and generates human-readable analyst explanations.
"""
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import time
from typing import Any, Dict, Optional, Tuple, Union
import uuid
import numpy as np
from PIL import Image

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.schemas.quality import (
    QualityDecision,
    QualityGatedChangeRequest,
    QualityGatedChangeResponse,
    QualityStatus,
    SuppressionBreakdown,
)
from apps.backend.app.services.change.detector import BaselineChangeDetector
from apps.backend.app.services.change.morphology import (
    binary_dilation,
    filter_small_components,
)
from apps.backend.app.services.quality.pair_quality import PairQualityEvaluator


class QualityGate:
    """Quality decision engine wrapping change detection and retrieval pipelines."""

    GATE_VERSION = "1.0.0"

    def __init__(
        self,
        project_root: Optional[Path] = None,
        pair_evaluator: Optional[PairQualityEvaluator] = None,
        change_detector: Optional[BaselineChangeDetector] = None,
    ):
        if project_root is None:
            current = Path(__file__).resolve()
            for parent in current.parents:
                if (parent / "data").is_dir() and (parent / "README.md").is_file():
                    self.project_root = parent
                    break
            else:
                self.project_root = current.parents[4]
        else:
            self.project_root = project_root

        self.pair_evaluator = pair_evaluator or PairQualityEvaluator()
        self.change_detector = change_detector or BaselineChangeDetector(project_root=self.project_root)

    def evaluate_change(
        self,
        t1_input: Union[Path, str, np.ndarray],
        t2_input: Union[Path, str, np.ndarray],
        request: QualityGatedChangeRequest,
        t1_acquired_at: Optional[datetime] = None,
        t2_acquired_at: Optional[datetime] = None,
        output_mask_dir: Optional[Path] = None,
    ) -> QualityGatedChangeResponse:
        """Executes quality assessment, baseline change detection, false-alarm suppression,

        and decision gating.
        """
        t0 = time.perf_counter()
        change_id = f"qchg_{uuid.uuid4().hex[:12]}"

        # 1. Evaluate temporal pair quality
        t_qual0 = time.perf_counter()
        pair_metrics, mask_bundle = self.pair_evaluator.evaluate_pair(
            t1_input=t1_input,
            t2_input=t2_input,
            t1_acquired_at=t1_acquired_at,
            t2_acquired_at=t2_acquired_at,
            t1_id=request.before_tile_id,
            t2_id=request.after_tile_id,
        )
        qual_ms = round((time.perf_counter() - t_qual0) * 1000.0, 3)

        # 2. Run baseline change detection
        t_det0 = time.perf_counter()
        raw_change_res = self.change_detector.detect_change(
            t1_path_input=t1_input,
            t2_path_input=t2_input,
            threshold=request.threshold,
            min_pixels=request.min_pixels,
            apply_morphology=request.apply_morphology,
        )
        det_ms = round((time.perf_counter() - t_det0) * 1000.0, 3)

        raw_change_mask = raw_change_res["change_mask"]
        raw_changed_pixels = int(raw_change_res["changed_pixels"])
        raw_change_score = float(raw_change_res["composite_change_score"])
        change_type = raw_change_res["change_type"]

        # 3. False-Alarm Suppression Logic
        t_gate0 = time.perf_counter()
        active_mask = raw_change_mask.copy()
        total_pixels = pair_metrics.t1_quality.total_pixels

        cloud_suppressed = 0
        shadow_suppressed = 0
        boundary_suppressed = 0
        noise_suppressed = 0

        # A. Cloud suppression
        if request.suppress_clouds:
            cloud_overlap = active_mask & (
                mask_bundle["t1_masks"]["cloud"] | mask_bundle["t2_masks"]["cloud"]
            )
            cloud_suppressed = int(np.sum(cloud_overlap))
            active_mask &= ~cloud_overlap

        # B. Shadow suppression
        if request.suppress_shadows:
            shadow_overlap = active_mask & (
                mask_bundle["t1_masks"]["shadow"] | mask_bundle["t2_masks"]["shadow"]
            )
            shadow_suppressed = int(np.sum(shadow_overlap))
            active_mask &= ~shadow_overlap

        # C. Boundary artifact suppression (within 2 pixels of nodata)
        if request.suppress_boundaries:
            nodata_all = (~mask_bundle["t1_masks"]["valid"]) | (~mask_bundle["t2_masks"]["valid"])
            if np.any(nodata_all):
                dilated_nodata = binary_dilation(nodata_all, kernel_size=5)
                boundary_overlap = active_mask & dilated_nodata
                boundary_suppressed = int(np.sum(boundary_overlap))
                active_mask &= ~boundary_overlap

        # D. Noise filtering on remaining verified components
        before_clean_count = int(np.sum(active_mask))
        if request.apply_morphology and before_clean_count > 0:
            verified_mask = filter_small_components(active_mask, min_pixels=request.min_pixels)
            noise_suppressed = before_clean_count - int(np.sum(verified_mask))
        else:
            verified_mask = active_mask

        total_suppressed = cloud_suppressed + shadow_suppressed + boundary_suppressed + noise_suppressed
        verified_changed_pixels = int(np.sum(verified_mask))
        mutual_usable = pair_metrics.mutual_usable_pixels
        verified_change_percent = (
            round((verified_changed_pixels / float(mutual_usable)) * 100.0, 4)
            if mutual_usable > 0
            else 0.0
        )

        suppression_breakdown = SuppressionBreakdown(
            cloud_suppressed_pixels=cloud_suppressed,
            shadow_suppressed_pixels=shadow_suppressed,
            boundary_suppressed_pixels=boundary_suppressed,
            noise_suppressed_pixels=noise_suppressed,
            total_suppressed_pixels=total_suppressed,
        )

        # 4. Decision Gating, Uncertainty Assignment, & Confidence Modulation
        is_uncertain = False
        final_confidence = 0.0
        decision = QualityDecision.QUALITY_PASSED
        explanation_parts: List[str] = []

        # Check for Insufficient / Uncertain condition
        if (
            pair_metrics.pair_status == QualityStatus.INSUFFICIENT
            or pair_metrics.mutual_usable_fraction < request.min_usable_fraction
        ):
            decision = QualityDecision.UNCERTAIN
            is_uncertain = True
            final_confidence = 0.0
            explanation_parts.append(
                f"Result UNCERTAIN: insufficient mutual usable area ({pair_metrics.mutual_usable_fraction * 100.0:.1f}% "
                f"< {request.min_usable_fraction * 100.0:.1f}% threshold). Observations obscured by clouds or nodata."
            )
        elif verified_changed_pixels == 0 and raw_changed_pixels > 0:
            decision = QualityDecision.QUALITY_SUPPRESSED
            is_uncertain = False
            final_confidence = 0.0
            change_type = "no_change"
            explanation_parts.append(
                f"False-alarm suppressed: all {raw_changed_pixels} raw candidate change pixels were verified as "
                f"spurious artifacts ({cloud_suppressed} cloud, {shadow_suppressed} shadow, {boundary_suppressed} boundary)."
            )
        elif pair_metrics.pair_status == QualityStatus.UNRELIABLE:
            decision = QualityDecision.QUALITY_REJECTED
            is_uncertain = True
            final_confidence = round(raw_change_score * 0.20, 4)
            explanation_parts.append(
                f"Result REJECTED as unreliable: observation pair has high contamination (pair quality score {pair_metrics.pair_quality_score:.2f})."
            )
        elif pair_metrics.pair_status == QualityStatus.DEGRADED:
            decision = QualityDecision.QUALITY_DEGRADED
            is_uncertain = False
            final_confidence = round(raw_change_score * pair_metrics.pair_quality_score, 4)
            explanation_parts.append(
                f"Result verified with DEGRADED confidence: {verified_changed_pixels} change pixels confirmed in clear area; "
                f"confidence discounted from {raw_change_score:.3f} to {final_confidence:.3f} due to partial contamination."
            )
        else:
            decision = QualityDecision.QUALITY_PASSED
            is_uncertain = False
            final_confidence = round(raw_change_score * pair_metrics.pair_quality_score, 4)
            if verified_changed_pixels > 0:
                explanation_parts.append(
                    f"Result VERIFIED with high confidence: {verified_changed_pixels} changed pixels ({change_type}) "
                    f"detected across mutually clear imagery (pair quality {pair_metrics.pair_quality_score:.2f})."
                )
            else:
                explanation_parts.append(
                    f"Result VERIFIED: zero change detected across mutually clear observations (pair quality {pair_metrics.pair_quality_score:.2f})."
                )

        if total_suppressed > 0 and decision != QualityDecision.QUALITY_SUPPRESSED:
            explanation_parts.append(f"Filtered {total_suppressed} false-alarm pixels ({cloud_suppressed} cloud, {shadow_suppressed} shadow).")

        explanation = " ".join(explanation_parts)

        # 5. Export Verified Change Mask PNG
        mask_dir = output_mask_dir or (self.project_root / "data" / "processed" / "changes")
        mask_filename = f"{change_id}_verified_mask.png"
        mask_file_path = mask_dir / mask_filename

        mask_uint8 = (verified_mask.astype(np.uint8)) * 255
        img = Image.fromarray(mask_uint8, mode="L")
        try:
            mask_dir.mkdir(parents=True, exist_ok=True)
            img.save(mask_file_path, format="PNG")
        except (OSError, PermissionError):
            tmp_dir = Path("/tmp/changes")
            tmp_dir.mkdir(parents=True, exist_ok=True)
            mask_file_path = tmp_dir / mask_filename
            img.save(mask_file_path, format="PNG")

        mask_url = f"/api/v1/change/mask/{change_id}"

        gate_ms = round((time.perf_counter() - t_gate0) * 1000.0, 3)
        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        # 6. Build Cryptographic Provenance
        provenance = {
            "quality_gate_version": self.GATE_VERSION,
            "change_detector_version": "1.0.0",
            "before_tile_id": request.before_tile_id,
            "after_tile_id": request.after_tile_id,
            "threshold_applied": raw_change_res["effective_threshold"],
            "suppression_configuration": {
                "suppress_clouds": request.suppress_clouds,
                "suppress_shadows": request.suppress_shadows,
                "suppress_boundaries": request.suppress_boundaries,
                "min_usable_fraction": request.min_usable_fraction,
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        logger.info(
            f"QualityGate change {change_id} decision={decision.value} "
            f"verified_px={verified_changed_pixels} suppressed={total_suppressed} in {total_ms}ms"
        )

        return QualityGatedChangeResponse(
            change_id=change_id,
            decision=decision,
            quality_status=pair_metrics.pair_status,
            is_uncertain=is_uncertain,
            raw_change_score=raw_change_score,
            pair_quality_score=pair_metrics.pair_quality_score,
            final_confidence=final_confidence,
            raw_changed_pixels=raw_changed_pixels,
            verified_changed_pixels=verified_changed_pixels,
            verified_change_percent=verified_change_percent,
            change_type=change_type,
            suppression_breakdown=suppression_breakdown,
            pair_quality=pair_metrics,
            explanation=explanation,
            mask_url=mask_url,
            execution_trace={
                "quality_assessment_ms": qual_ms,
                "detection_ms": det_ms,
                "gate_suppression_ms": gate_ms,
                "total_ms": total_ms,
            },
            provenance=provenance,
        )
