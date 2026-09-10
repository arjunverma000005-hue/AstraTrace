"""Unified Search Service for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Orchestrates multi-modal retrieval (EuroSAT keywords, 512-D semantic vectors, spatial/temporal,
and quality filters) into a consolidated, Evidence-First intelligence format.
"""
import math
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from apps.backend.app.core.logging import get_logger
from apps.backend.app.models.catalog import TileRecord
from apps.backend.app.models.review import AnalystReviewRecord
from apps.backend.app.schemas.search import (
    BaselineSearchRequest,
    EvidenceFirstCandidate,
    SearchMode,
    UnifiedSearchRequest,
    UnifiedSearchResponse,
)
from apps.backend.app.schemas.semantic import SemanticSearchRequest
from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService
from apps.backend.app.services.retrieval.service import BaselineRetrievalService

logger = get_logger("astratrace.unified_search")


class UnifiedSearchService:
    """Consolidated search service delivering Evidence-First candidate rankings."""

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

    def search(self, request: UnifiedSearchRequest) -> UnifiedSearchResponse:
        """Executes a unified search request and returns structured Evidence-First candidates."""
        t0 = time.perf_counter()
        query_id = f"unif_{uuid.uuid4().hex[:12]}"

        # 1. Fetch latest analyst reviews for status overlay
        reviews: List[AnalystReviewRecord] = (
            self.db.query(AnalystReviewRecord)
            .order_by(AnalystReviewRecord.created_at.desc())
            .all()
        )
        review_map: Dict[str, str] = {}
        for r in reviews:
            if r.target_id not in review_map:
                review_map[r.target_id] = r.decision

        candidates: List[EvidenceFirstCandidate] = []

        # 2. Route by search modality
        query_text = (request.query or "").strip()

        if request.search_mode == SearchMode.KEYWORD and query_text:
            # Baseline EuroSAT keyword classifier route
            b_service = BaselineRetrievalService(db=self.db)
            b_req = BaselineSearchRequest(
                query=query_text,
                bbox=request.bbox,
                point=request.point,
                date_from=request.date_from,
                date_to=request.date_to,
                sensor=request.sensor,
                top_k=request.top_k,
                min_confidence=request.min_confidence,
            )
            b_res = b_service.search(b_req)
            for idx, r in enumerate(b_res.results):
                centroid = [
                    round((r.bounds_wgs84[0] + r.bounds_wgs84[2]) / 2.0, 6),
                    round((r.bounds_wgs84[1] + r.bounds_wgs84[3]) / 2.0, 6),
                ]
                cloud_pct = r.cloud_cover_percent
                usable_frac = round(max(0.0, 1.0 - (cloud_pct / 100.0)), 4)
                qual_status = "USABLE" if cloud_pct < 10.0 else ("DEGRADED" if cloud_pct < 30.0 else "UNRELIABLE")

                candidates.append(
                    EvidenceFirstCandidate(
                        candidate_id=f"cand_{r.tile_id}",
                        target_id=r.tile_id,
                        target_type="TILE",
                        rank=idx + 1,
                        what=f"{r.top_class} (Confidence: {r.top_class_confidence:.1%})",
                        where={
                            "bbox": r.bounds_wgs84,
                            "centroid": centroid,
                            "geometry": r.geometry,
                            "crs": "EPSG:32643",
                        },
                        when=r.acquired_at,
                        which={
                            "sensor": r.sensor,
                            "scene_id": r.scene_id,
                            "tile_id": r.tile_id,
                        },
                        why=r.score_breakdown,
                        confidence=round(r.baseline_score, 4),
                        quality_status=qual_status,
                        quality_flags=["LOW_CLOUD_COVER"] if cloud_pct < 5.0 else [],
                        evidence={
                            "preview_url": f"/api/v1/catalog/tiles/{r.tile_id}/preview",
                            "mask_url": None,
                            "usable_fraction": usable_frac,
                            "cloud_fraction": round(cloud_pct / 100.0, 4),
                            "shadow_fraction": 0.0,
                        },
                        provenance={
                            "checksum": r.checksum,
                            "algorithm": "EuroSAT-Baseline-Scorer",
                        },
                        review_status=review_map.get(r.tile_id, "PENDING_REVIEW"),
                    )
                )

        elif (request.search_mode in (SearchMode.AUTO, SearchMode.HYBRID, SearchMode.SEMANTIC)) and query_text:
            # Semantic vector or hybrid route
            alpha = 1.0 if request.search_mode == SearchMode.SEMANTIC else 0.65
            with SemanticRetrievalService(project_root=self.project_root) as s_service:
                s_req = SemanticSearchRequest(
                    query=query_text,
                    top_k=request.top_k,
                    hybrid_weight=alpha,
                    min_confidence=request.min_confidence,
                    bbox=request.bbox,
                    point=request.point,
                    date_from=request.date_from,
                    date_to=request.date_to,
                    sensor=request.sensor,
                )
                s_res = s_service.search_semantic(s_req)

                for idx, r in enumerate(s_res.results):
                    # Fetch database tile for full geometry and metadata
                    tile_db = self.db.query(TileRecord).filter(TileRecord.tile_id == r.tile_id).first()
                    centroid = [
                        round((r.bounds_wgs84[0] + r.bounds_wgs84[2]) / 2.0, 6),
                        round((r.bounds_wgs84[1] + r.bounds_wgs84[3]) / 2.0, 6),
                    ]
                    cloud_pct = tile_db.cloud_cover_percent if tile_db else 0.0
                    usable_frac = round(max(0.0, 1.0 - (cloud_pct / 100.0)), 4)
                    qual_status = "USABLE" if cloud_pct < 10.0 else ("DEGRADED" if cloud_pct < 30.0 else "UNRELIABLE")

                    geometry = tile_db.to_geojson_geometry() if tile_db else {
                        "type": "Polygon",
                        "coordinates": [[
                            [r.bounds_wgs84[0], r.bounds_wgs84[1]],
                            [r.bounds_wgs84[2], r.bounds_wgs84[1]],
                            [r.bounds_wgs84[2], r.bounds_wgs84[3]],
                            [r.bounds_wgs84[0], r.bounds_wgs84[3]],
                            [r.bounds_wgs84[0], r.bounds_wgs84[1]],
                        ]],
                    }

                    candidates.append(
                        EvidenceFirstCandidate(
                            candidate_id=f"cand_{r.tile_id}",
                            target_id=r.tile_id,
                            target_type="TILE",
                            rank=idx + 1,
                            what=f"Target Semantic Match (Sim: {r.cosine_sim:.3f})",
                            where={
                                "bbox": r.bounds_wgs84,
                                "centroid": centroid,
                                "geometry": geometry,
                                "crs": "EPSG:32643",
                            },
                            when=tile_db.scene.acquired_at.isoformat() if tile_db and tile_db.scene and tile_db.scene.acquired_at else None,
                            which={
                                "sensor": r.sensor,
                                "scene_id": r.scene_id,
                                "tile_id": r.tile_id,
                            },
                            why={
                                "semantic_score": r.semantic_score,
                                "cosine_sim": r.cosine_sim,
                                "baseline_score": r.baseline_score or 0.0,
                                "hybrid_score": r.hybrid_score,
                            },
                            confidence=round(r.hybrid_score, 4),
                            quality_status=qual_status,
                            quality_flags=["SEMANTIC_ALIGNED"] if r.cosine_sim > 0.1 else [],
                            evidence={
                                "preview_url": f"/api/v1/catalog/tiles/{r.tile_id}/preview",
                                "mask_url": None,
                                "usable_fraction": usable_frac,
                                "cloud_fraction": round(cloud_pct / 100.0, 4),
                                "shadow_fraction": 0.0,
                            },
                            provenance={
                                "checksum": r.checksum,
                                "model_name": s_res.model_info.get("model_name", "RemoteCLIP-ResNet50") if isinstance(s_res.model_info, dict) else getattr(s_res.model_info, "model_name", "RemoteCLIP-ResNet50"),
                                "dimension": s_res.model_info.get("dimension", 512) if isinstance(s_res.model_info, dict) else getattr(s_res.model_info, "dimension", 512),
                            },
                            review_status=review_map.get(r.tile_id, "PENDING_REVIEW"),
                        )
                    )

        else:
            # Spatial/temporal catalog lookup route (empty query or spatial browse)
            tile_query = self.db.query(TileRecord)
            if request.bbox:
                min_lon, min_lat, max_lon, max_lat = request.bbox
                tile_query = tile_query.filter(
                    TileRecord.min_lon <= max_lon,
                    TileRecord.max_lon >= min_lon,
                    TileRecord.min_lat <= max_lat,
                    TileRecord.max_lat >= min_lat,
                )
            tiles = tile_query.limit(request.top_k).all()

            for idx, t in enumerate(tiles):
                centroid = [
                    round((t.min_lon + t.max_lon) / 2.0, 6),
                    round((t.min_lat + t.max_lat) / 2.0, 6),
                ]
                cloud_pct = t.cloud_cover_percent or 0.0
                usable_frac = round(max(0.0, 1.0 - (cloud_pct / 100.0)), 4)
                qual_status = "USABLE" if cloud_pct < 10.0 else ("DEGRADED" if cloud_pct < 30.0 else "UNRELIABLE")

                candidates.append(
                    EvidenceFirstCandidate(
                        candidate_id=f"cand_{t.tile_id}",
                        target_id=t.tile_id,
                        target_type="TILE",
                        rank=idx + 1,
                        what=f"Sentinel-2 Tile Observation ({t.tile_index})",
                        where={
                            "bbox": [t.min_lon, t.min_lat, t.max_lon, t.max_lat],
                            "centroid": centroid,
                            "geometry": t.to_geojson_geometry(),
                            "crs": "EPSG:32643",
                        },
                        when=t.scene.acquired_at.isoformat() if t.scene and t.scene.acquired_at else None,
                        which={
                            "sensor": t.scene.sensor if t.scene else "SENTINEL-2",
                            "scene_id": t.scene_id,
                            "tile_id": t.tile_id,
                        },
                        why={
                            "spatial_score": 1.0,
                            "quality_score": usable_frac,
                        },
                        confidence=usable_frac,
                        quality_status=qual_status,
                        quality_flags=["SPATIAL_INTERSECT"],
                        evidence={
                            "preview_url": f"/api/v1/catalog/tiles/{t.tile_id}/preview",
                            "mask_url": None,
                            "usable_fraction": usable_frac,
                            "cloud_fraction": round(cloud_pct / 100.0, 4),
                            "shadow_fraction": 0.0,
                        },
                        provenance={
                            "checksum": t.checksum,
                            "source": "Catalog-Spatial-Index",
                        },
                        review_status=review_map.get(t.tile_id, "PENDING_REVIEW"),
                    )
                )

        # 3. Filter by quality status if requested
        if request.allowed_quality_statuses:
            allowed_upper = {s.upper() for s in request.allowed_quality_statuses}
            candidates = [c for c in candidates if c.quality_status.upper() in allowed_upper]

        # 4. Filter by minimum confidence
        if request.min_confidence > 0.0:
            candidates = [c for c in candidates if c.confidence >= request.min_confidence]

        # 5. Pagination
        total_candidates = len(candidates)
        page_size = max(1, request.page_size)
        total_pages = max(1, math.ceil(total_candidates / page_size))
        start_idx = (request.page - 1) * page_size
        paginated_candidates = candidates[start_idx : start_idx + page_size]

        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return UnifiedSearchResponse(
            query_id=query_id,
            query=request.query,
            search_mode=request.search_mode,
            total_candidates=total_candidates,
            page=request.page,
            page_size=page_size,
            total_pages=total_pages,
            results=paginated_candidates,
            execution_trace={"total_ms": total_ms},
        )
