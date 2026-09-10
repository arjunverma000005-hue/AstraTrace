"""AstraTrace Quality Service.

SIH 2026 | Problem ID: SIH26227
Orchestrates tile quality assessment, pair evaluation, catalog lookups,
and quality-gated change detection.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple, Union
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.schemas.quality import (
    QualityGatedChangeRequest,
    QualityGatedChangeResponse,
    TemporalPairQualityMetrics,
    TileQualityMetrics,
)
from apps.backend.app.services.catalog import CatalogService
from apps.backend.app.services.quality.pair_quality import PairQualityEvaluator
from apps.backend.app.services.quality.quality_detector import TileQualityDetector
from apps.backend.app.services.quality.quality_gate import QualityGate


class QualityService:
    """High-level service coordinating optical quality analysis and gated change detection."""

    def __init__(
        self,
        db: Optional[Session] = None,
        project_root: Optional[Path] = None,
        quality_gate: Optional[QualityGate] = None,
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

        if db is not None:
            self.db = db
            self._owns_db = False
        else:
            self.db = SessionLocal()
            self._owns_db = True

        self.catalog = CatalogService(db=self.db, project_root=self.project_root)
        self.detector = TileQualityDetector()
        self.pair_evaluator = PairQualityEvaluator(tile_detector=self.detector)
        self.gate = quality_gate or QualityGate(
            project_root=self.project_root,
            pair_evaluator=self.pair_evaluator,
        )

    def close(self):
        if self._owns_db and self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _resolve_tile_path(self, tile_id: str) -> Tuple[Path, Optional[datetime]]:
        """Resolves catalog tile ID to absolute raster path and acquisition timestamp."""
        tile = self.db.query(TileRecord).filter(TileRecord.tile_id == tile_id).first()
        if not tile:
            raise NotFoundError(f"Tile not found in catalog: {tile_id}")

        abs_path = (self.project_root / tile.path).resolve()
        if not abs_path.exists():
            raise NotFoundError(f"Raster file missing on disk for tile {tile_id}: {abs_path}")

        scene = tile.scene
        acq_at = scene.acquired_at if scene else None
        return abs_path, acq_at

    def assess_tile(
        self,
        tile_id_or_path: Union[str, Path],
    ) -> TileQualityMetrics:
        """Evaluates optical quality signals for a tile ID or local raster path."""
        target_path = None
        tid = None

        if isinstance(tile_id_or_path, (str, Path)):
            str_val = str(tile_id_or_path)
            # Check if it's a catalog tile ID
            tile = self.db.query(TileRecord).filter(TileRecord.tile_id == str_val).first()
            if tile:
                target_path = (self.project_root / tile.path).resolve()
                tid = tile.tile_id
            else:
                p = Path(str_val)
                if not p.is_absolute():
                    p = (self.project_root / p).resolve()
                if p.exists() and p.is_file():
                    target_path = p
                    tid = p.stem
                else:
                    raise NotFoundError(f"Could not resolve tile ID or file path: {tile_id_or_path}")

        metrics, _ = self.detector.analyze_raster(target_path, tile_id=tid)
        return metrics

    def assess_pair(
        self,
        t1_input: Union[str, Path],
        t2_input: Union[str, Path],
    ) -> TemporalPairQualityMetrics:
        """Evaluates pair quality, mutual usable intersection, and co-registration proxy."""
        p1, acq1 = self._resolve_input(t1_input)
        p2, acq2 = self._resolve_input(t2_input)

        tid1 = t1_input if isinstance(t1_input, str) and not t1_input.endswith(".tif") else p1.stem
        tid2 = t2_input if isinstance(t2_input, str) and not t2_input.endswith(".tif") else p2.stem

        metrics, _ = self.pair_evaluator.evaluate_pair(
            t1_input=p1,
            t2_input=p2,
            t1_acquired_at=acq1,
            t2_acquired_at=acq2,
            t1_id=tid1,
            t2_id=tid2,
        )
        return metrics

    def detect_gated_change(
        self,
        request: QualityGatedChangeRequest,
    ) -> QualityGatedChangeResponse:
        """Executes full quality-gated change detection workflow."""
        if request.before_tile_id and request.after_tile_id:
            p1, acq1 = self._resolve_tile_path(request.before_tile_id)
            p2, acq2 = self._resolve_tile_path(request.after_tile_id)
        elif request.before_tile_path and request.after_tile_path:
            p1 = Path(request.before_tile_path)
            p2 = Path(request.after_tile_path)
            if not p1.is_absolute():
                p1 = (self.project_root / p1).resolve()
            if not p2.is_absolute():
                p2 = (self.project_root / p2).resolve()
            acq1 = None
            acq2 = None
        else:
            raise ValidationError("Invalid request: specify either tile IDs or tile paths.")

        return self.gate.evaluate_change(
            t1_input=p1,
            t2_input=p2,
            request=request,
            t1_acquired_at=acq1,
            t2_acquired_at=acq2,
        )

    def _resolve_input(self, inp: Union[str, Path]) -> Tuple[Path, Optional[datetime]]:
        str_val = str(inp)
        tile = self.db.query(TileRecord).filter(TileRecord.tile_id == str_val).first()
        if tile:
            return (self.project_root / tile.path).resolve(), tile.scene.acquired_at if tile.scene else None
        p = Path(str_val)
        if not p.is_absolute():
            p = (self.project_root / p).resolve()
        if p.exists() and p.is_file():
            return p, None
        raise NotFoundError(f"Could not resolve input: {inp}")
