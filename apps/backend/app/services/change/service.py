"""AstraTrace Change Detection Service.

SIH 2026 | Problem ID: SIH26227
Orchestrates bitemporal tile pairing from the catalog, executes spectral differencing
and morphology, stores mask artifacts, and records forensic provenance.
"""
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.schemas.change import (
    ChangeDetectionRequest,
    ChangeDetectionResponse,
    ChangeMetrics,
    ScenePairChangeRequest,
    ScenePairChangeResponse,
    TileProvenance,
)
from apps.backend.app.services.catalog import CatalogService
from apps.backend.app.services.change.detector import BaselineChangeDetector
from apps.backend.app.services.ingestion import calculate_file_sha256


class ChangeDetectionService:
    """Service coordinating catalog-aware bitemporal change detection."""

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

        self.detector = BaselineChangeDetector(project_root=self.project_root)

    def close(self):
        """Closes internal database session if owned."""
        if self._owns_catalog and self.catalog:
            self.catalog.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _resolve_tile_provenance(
        self,
        tile_id: Optional[str] = None,
        raster_path: Optional[str] = None,
    ) -> TileProvenance:
        """Resolves tile metadata and provenance from catalog or raster file."""
        if tile_id:
            tile_rec = (
                self.catalog.db.query(TileRecord)
                .filter(TileRecord.tile_id == tile_id)
                .first()
            )
            if not tile_rec:
                raise NotFoundError(f"Tile not found in catalog: {tile_id}")

            return TileProvenance(
                tile_id=tile_rec.tile_id,
                scene_id=tile_rec.scene_id,
                tile_index=tile_rec.tile_index,
                path=tile_rec.path,
                acquired_at=tile_rec.scene.acquired_at.isoformat() if tile_rec.scene.acquired_at else None,
                sensor=tile_rec.scene.sensor,
                checksum=tile_rec.checksum,
                bounds_wgs84=[tile_rec.min_lon, tile_rec.min_lat, tile_rec.max_lon, tile_rec.max_lat],
            )
        elif raster_path:
            p = Path(raster_path)
            if not p.is_absolute():
                p = (self.project_root / p).resolve()
            if not p.exists():
                raise NotFoundError(f"Raster file not found: {raster_path}")

            checksum = calculate_file_sha256(p)
            rel_path = str(p.relative_to(self.project_root)).replace("\\", "/") if str(p).startswith(str(self.project_root)) else str(p)

            # Try to get raster bounds from header
            import rasterio
            with rasterio.open(p) as src:
                bounds = [src.bounds.left, src.bounds.bottom, src.bounds.right, src.bounds.top]

            return TileProvenance(
                tile_id=None,
                scene_id=None,
                tile_index=None,
                path=rel_path,
                acquired_at=None,
                sensor="UNKNOWN",
                checksum=checksum,
                bounds_wgs84=bounds,
            )
        else:
            raise ValidationError("Either tile_id or raster_path must be provided.")

    def detect_tile_pair(self, request: ChangeDetectionRequest) -> ChangeDetectionResponse:
        """Compares two observations and produces a change detection report with mask."""
        t_start = time.perf_counter()
        change_id = f"chg_{uuid.uuid4().hex[:12]}"

        # 1. Resolve provenance for before and after
        prov_before = self._resolve_tile_provenance(
            tile_id=request.before_tile_id,
            raster_path=request.before_raster_path,
        )
        prov_after = self._resolve_tile_provenance(
            tile_id=request.after_tile_id,
            raster_path=request.after_raster_path,
        )

        # 2. Setup mask output destination
        mask_out_rel = None
        mask_out_abs = None
        if request.generate_mask:
            mask_out_rel = f"data/processed/changes/{change_id}.png"
            mask_out_abs = self.project_root / mask_out_rel

        # 3. Execute change detector
        result = self.detector.detect_change(
            t1_path_input=prov_before.path,
            t2_path_input=prov_after.path,
            threshold=request.threshold,
            min_pixels=request.min_component_pixels,
            apply_morphology=request.apply_morphology,
            output_mask_path=mask_out_abs,
        )

        # 4. Construct response
        metrics = ChangeMetrics(
            total_pixels=result["total_pixels"],
            valid_pixels=result["valid_pixels"],
            changed_pixels=result["changed_pixels"],
            change_percent=result["change_percent"],
            mean_magnitude=result["mean_magnitude"],
            composite_change_score=result["composite_change_score"],
            change_type=result["change_type"],
            effective_threshold=result["effective_threshold"],
            applied_morphology=result["applied_morphology"],
            min_component_pixels=result["min_component_pixels"],
            index_deltas_mean=result["index_deltas_mean"],
        )

        mask_url = f"/api/v1/change/mask/{change_id}" if mask_out_rel else None

        logger.info(
            f"Change detection executed {change_id}: {result['change_type']} "
            f"({result['changed_pixels']} changed px, score={result['composite_change_score']}) "
            f"in {result['execution_trace']['total_ms']}ms"
        )

        return ChangeDetectionResponse(
            change_id=change_id,
            before=prov_before,
            after=prov_after,
            metrics=metrics,
            mask_path=mask_out_rel,
            mask_url=mask_url,
            execution_trace=result["execution_trace"],
        )

    def detect_scene_pair(self, request: ScenePairChangeRequest) -> ScenePairChangeResponse:
        """Performs batch bitemporal change detection between all matching tiles of two scenes."""
        t0 = time.perf_counter()

        scene1 = self.catalog.get_scene(request.scene_id_t1)
        scene2 = self.catalog.get_scene(request.scene_id_t2)

        if not scene1 or not scene2:
            raise NotFoundError(f"Scenes '{request.scene_id_t1}' or '{request.scene_id_t2}' not found.")

        # Temporal ordering: ensure t1 is earlier than or equal to t2
        if scene1.acquired_at > scene2.acquired_at:
            logger.info("Re-ordering scene pair to maintain chronological T1 (before) -> T2 (after).")
            scene1, scene2 = scene2, scene1

        # Match tiles by grid index
        tiles_t1 = {t.tile_index: t for t in scene1.tiles}
        tiles_t2 = {t.tile_index: t for t in scene2.tiles}

        common_indices = sorted(set(tiles_t1.keys()).intersection(tiles_t2.keys()))
        if not common_indices:
            raise ValidationError("No co-located tile pairs found between the two scenes.")

        # Limit to max_tiles
        eval_indices = common_indices[: request.max_tiles]
        responses: List[ChangeDetectionResponse] = []
        changes_detected = 0

        for idx in eval_indices:
            t1_rec = tiles_t1[idx]
            t2_rec = tiles_t2[idx]

            pair_req = ChangeDetectionRequest(
                before_tile_id=t1_rec.tile_id,
                after_tile_id=t2_rec.tile_id,
                threshold=request.threshold,
                min_component_pixels=request.min_component_pixels,
                apply_morphology=True,
                generate_mask=True,
            )
            resp = self.detect_tile_pair(pair_req)
            responses.append(resp)
            if resp.metrics.changed_pixels > 0:
                changes_detected += 1

        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return ScenePairChangeResponse(
            scene_id_t1=scene1.scene_id,
            scene_id_t2=scene2.scene_id,
            pairs_evaluated=len(responses),
            changes_detected=changes_detected,
            results=responses,
            total_execution_ms=total_ms,
        )
