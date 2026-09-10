"""AstraTrace Temporal Pair Quality Evaluator.

SIH 2026 | Problem ID: SIH26227
Evaluates pair-level quality across two temporal observations: mutual usable area,
spatial co-registration proxy, acquisition ordering, and composite pair status.
"""
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
import rasterio

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.schemas.quality import QualityStatus, TemporalPairQualityMetrics
from apps.backend.app.services.quality.quality_detector import TileQualityDetector


class PairQualityEvaluator:
    """Evaluates the mutual observation quality across bitemporal satellite image pairs."""

    def __init__(
        self,
        tile_detector: Optional[TileQualityDetector] = None,
        min_usable_fraction: float = 0.20,
    ):
        self.detector = tile_detector or TileQualityDetector()
        self.min_usable_fraction = float(np.clip(min_usable_fraction, 0.05, 0.90))

    def evaluate_pair(
        self,
        t1_input: Union[Path, str, np.ndarray],
        t2_input: Union[Path, str, np.ndarray],
        t1_acquired_at: Optional[datetime] = None,
        t2_acquired_at: Optional[datetime] = None,
        t1_id: Optional[str] = None,
        t2_id: Optional[str] = None,
    ) -> Tuple[TemporalPairQualityMetrics, Dict[str, Any]]:
        """Evaluates pair quality, mutual usable mask, and co-registration proxy.

        Returns:
            Tuple[TemporalPairQualityMetrics, Dict[str, Any]]:
                - Metrics Pydantic model
                - Dictionary containing masks: 'mutual_usable', 't1_masks', 't2_masks'
        """
        # 1. Georeference and metadata verification if paths are provided
        registration_score = 1.0
        reg_flags: List[str] = []

        if isinstance(t1_input, (Path, str)) and isinstance(t2_input, (Path, str)):
            p1 = Path(t1_input)
            p2 = Path(t2_input)
            if not p1.exists():
                raise NotFoundError(f"T1 raster not found: {p1}")
            if not p2.exists():
                raise NotFoundError(f"T2 raster not found: {p2}")

            with rasterio.open(p1) as s1, rasterio.open(p2) as s2:
                if s1.crs != s2.crs:
                    raise ValidationError(f"CRS mismatch: T1 '{s1.crs}' != T2 '{s2.crs}'")
                if (s1.height, s1.width) != (s2.height, s2.width):
                    raise ValidationError(
                        f"Dimension mismatch: T1 ({s1.width}x{s1.height}) != T2 ({s2.width}x{s2.height})"
                    )

                # Check geotransform resolution match
                res1 = (s1.transform.a, -s1.transform.e)
                res2 = (s2.transform.a, -s2.transform.e)
                if not (np.isclose(res1[0], res2[0], atol=1e-3) and np.isclose(res1[1], res2[1], atol=1e-3)):
                    registration_score *= 0.70
                    reg_flags.append("PIXEL_RESOLUTION_MISMATCH")

        # 2. Analyze individual tile quality
        t1_metrics, t1_masks = self.detector.analyze_raster(t1_input, tile_id=t1_id)
        t2_metrics, t2_masks = self.detector.analyze_raster(t2_input, tile_id=t2_id)

        # 3. Mutual usable intersection
        total_pixels = t1_metrics.total_pixels
        mutual_usable_mask = t1_masks["usable"] & t2_masks["usable"]
        mutual_usable_pixels = int(np.sum(mutual_usable_mask))
        mutual_usable_fraction = round(mutual_usable_pixels / float(total_pixels), 4) if total_pixels > 0 else 0.0

        # 4. Pure-NumPy Co-Registration Gradient Alignment Proxy
        # Computes edge gradient consistency in the mutual usable background
        if mutual_usable_pixels > 100:
            if isinstance(t1_input, np.ndarray) and isinstance(t2_input, np.ndarray):
                arr1, arr2 = t1_input, t2_input
            else:
                with rasterio.open(Path(t1_input)) as s1, rasterio.open(Path(t2_input)) as s2:
                    arr1 = s1.read(1).astype(np.float32)
                    arr2 = s2.read(1).astype(np.float32)

            # Gradient magnitudes on 2D slice
            a1 = arr1[0] if arr1.ndim == 3 else arr1
            a2 = arr2[0] if arr2.ndim == 3 else arr2
            gy1, gx1 = np.gradient(a1)
            gy2, gx2 = np.gradient(a2)
            grad1 = np.hypot(gx1, gy1)
            grad2 = np.hypot(gx2, gy2)

            # Normalization
            norm1 = np.std(grad1[mutual_usable_mask]) + 1e-6
            norm2 = np.std(grad2[mutual_usable_mask]) + 1e-6
            grad_diff = np.abs((grad1 - grad2) / np.maximum(norm1, norm2))
            mean_grad_diff = float(np.mean(grad_diff[mutual_usable_mask]))

            # Map edge deviation to [0.5, 1.0] registration score
            edge_penalty = min(0.5, mean_grad_diff * 0.1)
            registration_score = max(0.5, registration_score - edge_penalty)
            registration_score = round(float(registration_score), 4)

            if registration_score < 0.75:
                reg_flags.append("HIGH_EDGE_MISALIGNMENT_RISK")
        else:
            registration_score = 0.5
            reg_flags.append("INSUFFICIENT_MUTUAL_PIXELS_FOR_REGISTRATION")

        # 5. Temporal Baseline & Order Evaluation
        baseline_days = None
        temporal_flags: List[str] = []
        if t1_acquired_at and t2_acquired_at:
            delta = t2_acquired_at - t1_acquired_at
            baseline_days = round(delta.total_seconds() / 86400.0, 2)
            if baseline_days < 0:
                temporal_flags.append("TEMPORAL_ORDER_INVERTED")
            elif baseline_days == 0:
                temporal_flags.append("IDENTICAL_ACQUISITION_TIME")
            elif baseline_days > 1825:  # > 5 years
                temporal_flags.append("LONG_TEMPORAL_BASELINE")

        # 6. Composite Pair Quality Score
        min_single_quality = min(t1_metrics.quality_score, t2_metrics.quality_score)
        pair_score = (
            0.55 * min_single_quality
            + 0.35 * mutual_usable_fraction
            + 0.10 * registration_score
        )
        pair_quality_score = round(float(np.clip(pair_score, 0.0, 1.0)), 4)

        # 7. Overall Pair Quality Status & Flags
        pair_flags = reg_flags + temporal_flags
        if t1_metrics.quality_status == QualityStatus.INSUFFICIENT or t2_metrics.quality_status == QualityStatus.INSUFFICIENT:
            pair_status = QualityStatus.INSUFFICIENT
            pair_flags.append("PAIR_INSUFFICIENT_DATA")
        elif mutual_usable_fraction < self.min_usable_fraction:
            pair_status = QualityStatus.UNCERTAIN
            pair_flags.append("MUTUAL_USABLE_AREA_TOO_LOW")
        elif t1_metrics.quality_status == QualityStatus.UNRELIABLE or t2_metrics.quality_status == QualityStatus.UNRELIABLE or pair_quality_score < 0.35:
            pair_status = QualityStatus.UNRELIABLE
            pair_flags.append("PAIR_UNRELIABLE_OBSERVATION")
        elif (
            t1_metrics.quality_status == QualityStatus.DEGRADED
            or t2_metrics.quality_status == QualityStatus.DEGRADED
            or mutual_usable_fraction < 0.70
            or pair_quality_score < 0.80
        ):
            pair_status = QualityStatus.DEGRADED
            pair_flags.append("PAIR_DEGRADED_QUALITY")
        else:
            pair_status = QualityStatus.USABLE
            pair_flags.append("PAIR_USABLE_HIGH_CONFIDENCE")

        metrics = TemporalPairQualityMetrics(
            t1_quality=t1_metrics,
            t2_quality=t2_metrics,
            mutual_usable_pixels=mutual_usable_pixels,
            mutual_usable_fraction=mutual_usable_fraction,
            registration_score=registration_score,
            temporal_baseline_days=baseline_days,
            pair_quality_score=pair_quality_score,
            pair_status=pair_status,
            pair_flags=pair_flags,
        )

        mask_bundle = {
            "mutual_usable": mutual_usable_mask,
            "t1_masks": t1_masks,
            "t2_masks": t2_masks,
        }
        return metrics, mask_bundle
