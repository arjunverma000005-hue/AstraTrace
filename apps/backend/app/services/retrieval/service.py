"""AstraTrace Baseline Retrieval Service.

SIH 2026 | Problem ID: SIH26227
Orchestrates spatial/temporal database queries, controlled vocabulary mapping,
multispectral feature classification, multi-factor ranking, and execution tracing.
"""
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Union
import uuid

from sqlalchemy.orm import Session

from apps.backend.app.core.logging import logger
from apps.backend.app.models.catalog import bbox_to_geojson_polygon
from apps.backend.app.schemas.catalog import TileSearchRequest
from apps.backend.app.schemas.search import (
    BaselineSearchRequest,
    BaselineSearchResponse,
    BaselineTileResult,
)
from apps.backend.app.services.catalog import CatalogService
from apps.backend.app.services.retrieval.baseline_classifier import TileFeatureClassifier
from apps.backend.app.services.retrieval.baseline_scorer import BaselineScorer
from apps.backend.app.services.retrieval.vocabulary import ControlledVocabulary


class BaselineRetrievalService:
    """End-to-end service for baseline search across cataloged satellite tiles."""

    def __init__(
        self,
        db: Optional[Session] = None,
        project_root: Optional[Path] = None,
        catalog_service: Optional[CatalogService] = None,
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

        if catalog_service is not None:
            self.catalog = catalog_service
            self._owns_catalog = False
        else:
            self.catalog = CatalogService(db=db, project_root=self.project_root)
            self._owns_catalog = True

        self.vocabulary = ControlledVocabulary()
        self.classifier = TileFeatureClassifier(project_root=self.project_root)
        self.scorer = BaselineScorer()

    def close(self):
        """Closes internal database session if owned."""
        if self._owns_catalog and self.catalog:
            self.catalog.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def search(self, request: BaselineSearchRequest) -> BaselineSearchResponse:
        """Executes a complete baseline search."""
        start_time = time.perf_counter()
        query_id = f"qry_{uuid.uuid4().hex[:12]}"

        # 1. Parse natural language query with Controlled Vocabulary
        t0 = time.perf_counter()
        target_weights, is_oov = self.vocabulary.parse_query(request.query)
        t1 = time.perf_counter()
        query_parser_ms = round((t1 - t0) * 1000.0, 3)

        # 2. Query candidate tiles from SQL Database using spatial and temporal bounds
        # We request up to 200 candidates to rank
        catalog_req = TileSearchRequest(
            bbox=list(request.bbox) if request.bbox else None,
            point=list(request.point) if request.point else None,
            date_from=request.date_from,
            date_to=request.date_to,
            sensor=request.sensor,
            limit=200,
            offset=0,
        )
        total_candidates, candidate_tiles = self.catalog.query_tiles(catalog_req)
        t2 = time.perf_counter()
        retrieval_ms = round((t2 - t1) * 1000.0, 3)

        # 3. Classify and score each candidate tile
        scored_candidates = []
        for tile in candidate_tiles:
            tile_path_raw = tile["path"]
            tile_path = Path(tile_path_raw)
            if not tile_path.is_absolute():
                tile_path = (self.project_root / tile_path).resolve()

            # Classify tile into EuroSAT probabilities
            try:
                tile_probs = self.classifier.classify_tile(tile_path)
            except Exception as e:
                logger.warning(f"Feature classification failed for tile {tile['tile_id']}: {e}")
                # Fallback to uniform distribution
                tile_probs = {c: 0.1 for c in target_weights.keys()}

            # A. Semantic class alignment score
            class_score, top_cls, top_conf, matched_classes = self.scorer.compute_class_score(
                target_weights, tile_probs
            )

            # B. Spatial overlap score
            spatial_score = self.scorer.compute_spatial_score(
                tile_bbox=tile["bounds_wgs84"],
                query_bbox=request.bbox,
                query_point=request.point,
            )

            # C. Temporal recency score
            acquired_dt = None
            if tile.get("acquired_at"):
                try:
                    acquired_dt = datetime.fromisoformat(tile["acquired_at"].replace("Z", "+00:00"))
                except Exception:
                    pass

            temporal_score = self.scorer.compute_temporal_score(
                acquired_at=acquired_dt,
                date_from=request.date_from,
                date_to=request.date_to,
            )

            # D. Composite score
            composite_score, breakdown = self.scorer.compute_composite_score(
                class_score=class_score,
                spatial_score=spatial_score,
                temporal_score=temporal_score,
            )

            if composite_score >= request.min_confidence:
                scored_candidates.append({
                    "tile": tile,
                    "composite_score": composite_score,
                    "breakdown": breakdown,
                    "top_class": top_cls,
                    "top_class_confidence": top_conf,
                    "matched_classes": matched_classes,
                })

        # 4. Rank candidates by composite score descending, then acquired_at descending
        scored_candidates.sort(
            key=lambda x: (x["composite_score"], x["tile"].get("acquired_at") or ""),
            reverse=True,
        )

        # Slice to top_k
        top_results = scored_candidates[: request.top_k]

        # 5. Format results into response models
        ranked_tile_results: List[BaselineTileResult] = []
        for idx, item in enumerate(top_results, start=1):
            tile_data = item["tile"]
            bounds = tile_data["bounds_wgs84"]
            geo_poly = bbox_to_geojson_polygon(bounds[0], bounds[1], bounds[2], bounds[3])

            result_item = BaselineTileResult(
                rank=idx,
                tile_id=tile_data["tile_id"],
                scene_id=tile_data["scene_id"],
                tile_index=tile_data["tile_index"],
                baseline_score=item["composite_score"],
                score_breakdown=item["breakdown"],
                top_class=item["top_class"],
                top_class_confidence=item["top_class_confidence"],
                matched_classes=item["matched_classes"],
                bounds_wgs84=bounds,
                geometry=geo_poly,
                acquired_at=tile_data.get("acquired_at"),
                sensor=tile_data.get("sensor", "UNKNOWN"),
                checksum=tile_data["checksum"],
                cloud_cover_percent=tile_data.get("cloud_cover_percent", 0.0),
                nodata_percent=tile_data.get("nodata_percent", 0.0),
            )
            ranked_tile_results.append(result_item)

        t3 = time.perf_counter()
        scoring_ms = round((t3 - t2) * 1000.0, 3)
        total_ms = round((t3 - start_time) * 1000.0, 3)

        execution_trace = {
            "query_parser_ms": query_parser_ms,
            "retrieval_ms": retrieval_ms,
            "scoring_ms": scoring_ms,
            "total_ms": total_ms,
        }

        logger.info(
            f"Baseline search executed query='{request.query}' candidates={total_candidates} "
            f"returned={len(ranked_tile_results)} latency={total_ms}ms"
        )

        return BaselineSearchResponse(
            query_id=query_id,
            query=request.query,
            matched_vocabulary=target_weights,
            is_out_of_vocabulary=is_oov,
            total_candidates=total_candidates,
            returned_results=len(ranked_tile_results),
            results=ranked_tile_results,
            execution_trace=execution_trace,
        )
