"""AstraTrace Baseline Scoring & Multi-Factor Ranking Engine.

SIH 2026 | Problem ID: SIH26227
Combines keyword/class alignment, spatial overlap/IoU, and temporal recency
into a calibrated composite baseline retrieval score S_base in [0.0, 1.0].
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple


class BaselineScorer:
    """Computes multi-factor ranking scores for satellite tiles against search queries."""

    def __init__(
        self,
        weight_class: float = 0.60,
        weight_spatial: float = 0.25,
        weight_temporal: float = 0.15,
    ):
        total_w = weight_class + weight_spatial + weight_temporal
        self.w_class = weight_class / total_w
        self.w_spatial = weight_spatial / total_w
        self.w_temporal = weight_temporal / total_w

    def compute_class_score(
        self,
        target_weights: Dict[str, float],
        tile_probabilities: Dict[str, float],
    ) -> Tuple[float, str, float, List[str]]:
        """Computes semantic class alignment score between query targets and tile predictions.

        Returns:
            Tuple of (class_score, top_predicted_class, top_confidence, matched_classes)
        """
        # 1. Dot product alignment
        score = 0.0
        matched_classes: List[str] = []
        for cls_name, target_w in target_weights.items():
            tile_prob = tile_probabilities.get(cls_name, 0.0)
            score += target_w * tile_prob
            if tile_prob >= 0.05 and target_w > 0:
                matched_classes.append(cls_name)

        # 2. Find top predicted class
        top_cls = "Unknown"
        top_conf = 0.0
        for cls_name, prob in tile_probabilities.items():
            if prob > top_conf:
                top_conf = prob
                top_cls = cls_name

        return round(float(score), 4), top_cls, round(float(top_conf), 4), matched_classes

    def compute_spatial_score(
        self,
        tile_bbox: List[float],
        query_bbox: Optional[Tuple[float, float, float, float]] = None,
        query_point: Optional[Tuple[float, float]] = None,
    ) -> float:
        """Computes spatial overlap / intersection score between query geometry and tile bounds.

        tile_bbox: [min_lon, min_lat, max_lon, max_lat]
        query_bbox: (min_lon, min_lat, max_lon, max_lat)
        """
        t_minx, t_miny, t_maxx, t_maxy = tile_bbox

        if query_point is not None:
            px, py = query_point
            if t_minx <= px <= t_maxx and t_miny <= py <= t_maxy:
                return 1.0
            return 0.0

        if query_bbox is None:
            return 1.0

        q_minx, q_miny, q_maxx, q_maxy = query_bbox

        # 2D Intersection box
        inter_minx = max(t_minx, q_minx)
        inter_miny = max(t_miny, q_miny)
        inter_maxx = min(t_maxx, q_maxx)
        inter_maxy = min(t_maxy, q_maxy)

        if inter_minx >= inter_maxx or inter_miny >= inter_maxy:
            return 0.0

        inter_area = (inter_maxx - inter_minx) * (inter_maxy - inter_miny)
        tile_area = (t_maxx - t_minx) * (t_maxy - t_miny)
        query_area = (q_maxx - q_minx) * (q_maxy - q_miny)

        if tile_area <= 0:
            return 0.0

        # Overlap ratio relative to tile
        tile_coverage = inter_area / tile_area
        # Intersection-over-Union
        union_area = tile_area + query_area - inter_area
        iou = inter_area / union_area if union_area > 0 else 0.0

        # Blended spatial score: emphasizes coverage of candidate tile while factoring IoU
        spatial_score = 0.6 * tile_coverage + 0.4 * iou
        return round(float(min(1.0, max(0.0, spatial_score))), 4)

    def compute_temporal_score(
        self,
        acquired_at: Optional[datetime],
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
    ) -> float:
        """Computes temporal recency score within the query window."""
        if acquired_at is None:
            return 0.5

        # Normalize timezones
        if acquired_at.tzinfo is None:
            acquired_at = acquired_at.replace(tzinfo=timezone.utc)

        if date_from is not None and date_from.tzinfo is None:
            date_from = date_from.replace(tzinfo=timezone.utc)

        if date_to is not None and date_to.tzinfo is None:
            date_to = date_to.replace(tzinfo=timezone.utc)

        if date_from is not None and date_to is not None:
            total_duration = (date_to - date_from).total_seconds()
            if total_duration > 0:
                elapsed = (acquired_at - date_from).total_seconds()
                # Relative recency between 0.70 and 1.00
                progress = min(1.0, max(0.0, elapsed / total_duration))
                return round(0.70 + 0.30 * progress, 4)
            return 1.0

        return 1.0

    def compute_composite_score(
        self,
        class_score: float,
        spatial_score: float,
        temporal_score: float,
    ) -> Tuple[float, Dict[str, float]]:
        """Computes final composite baseline score and returns individual factor breakdown."""
        composite = (
            self.w_class * class_score
            + self.w_spatial * spatial_score
            + self.w_temporal * temporal_score
        )
        composite = round(min(1.0, max(0.0, composite)), 4)
        breakdown = {
            "class_score": round(class_score, 4),
            "spatial_score": round(spatial_score, 4),
            "temporal_score": round(temporal_score, 4),
            "weight_class": round(self.w_class, 4),
            "weight_spatial": round(self.w_spatial, 4),
            "weight_temporal": round(self.w_temporal, 4),
        }
        return composite, breakdown
