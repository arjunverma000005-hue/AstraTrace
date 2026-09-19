"""AstraTrace Atomic Incremental Ingestion Engine.

SIH 2026 | Problem ID: SIH26227
Processes newly added GeoTIFF/COG scenes on the fly:
VALIDATE -> EXTRACT METADATA -> GEOREFERENCE CHECK -> TILE -> QUALITY -> EMBEDDING -> INDEX UPDATE -> CATALOG UPDATE.
Atomically updates the vector index without rebuilding the complete store.
"""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import uuid

import numpy as np
import rasterio
from rasterio.warp import transform_bounds
from rasterio.windows import Window
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.models.catalog import SceneRecord, TileRecord, bbox_to_wkt
from apps.backend.app.models.embedding import TileEmbeddingRecord
from apps.backend.app.models.ingestion import IngestionHistoryRecord
from apps.backend.app.services.retrieval.embedding_model import get_embedding_model
from apps.backend.app.services.retrieval.vector_index import get_vector_index


def compute_file_sha256(filepath: Path) -> str:
    """Computes streaming SHA-256 hash of a file."""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


class IncrementalIngestionService:
    """Performs atomic incremental scene ingestion and index delta commits."""

    def __init__(self, db: Optional[Session] = None, project_root: Optional[Path] = None):
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

        self.processed_dir = self.project_root / "data" / "processed"
        self.scratch_dir = self.project_root / "data" / "scratch"
        for d in [self.processed_dir, self.scratch_dir]:
            try:
                d.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                pass

        self.model = get_embedding_model(project_root=self.project_root)
        self.vector_index = get_vector_index(dimension=self.model.model_metadata()["dimension"], prefer_faiss=True)
        # Load existing index cache if available
        index_file = self.processed_dir / "vector_index.npz"
        if index_file.exists():
            try:
                self.vector_index.load(index_file)
            except Exception as e:
                logger.warning(f"Could not load vector index cache in incremental service: {e}")

    def close(self):
        if self._owns_db and self.db:
            self.db.close()

    def ingest_new_scene(
        self,
        raster_path: Path,
        scene_id: Optional[str] = None,
        sensor: str = "SENTINEL-2",
        collection: str = "archive",
        data_type: str = "CONTROLLED_DEMO",
        tile_size: int = 256,
        overlap: int = 24,
    ) -> Dict[str, Any]:
        """Validates, tiles, embeds, and incrementally indexes a single GeoTIFF/COG scene."""
        t0 = time.perf_counter()
        batch_id = f"batch_{uuid.uuid4().hex[:10]}"

        # 1. Validation & Pre-flight
        if not raster_path.exists() or not raster_path.is_file():
            raise NotFoundError(f"Raster file not found: {raster_path}")

        file_size = raster_path.stat().st_size
        if file_size > 2 * 1024 * 1024 * 1024:
            raise ValidationError("File size exceeds 2 GB limit")

        # 2. Georeference Check
        try:
            with rasterio.open(raster_path) as src:
                crs = src.crs
                if not crs or not src.transform:
                    raise ValidationError("ERR_GEOREF_INVALID: Raster missing valid CRS or georeferencing transform.")
                crs_str = crs.to_string()
                bounds = src.bounds
                width, height, bands = src.width, src.height, src.count

                # Transform bounds to WGS84
                if crs_str != "EPSG:4326":
                    min_lon, min_lat, max_lon, max_lat = transform_bounds(
                        crs, "EPSG:4326", bounds.left, bounds.bottom, bounds.right, bounds.top
                    )
                else:
                    min_lon, min_lat, max_lon, max_lat = bounds.left, bounds.bottom, bounds.right, bounds.top

                res_meters = float(abs(src.transform.a))
        except rasterio.errors.RasterioError as e:
            raise ValidationError(f"ERR_GEOREF_INVALID: Corrupt or unreadable GeoTIFF: {e}")

        # Check existing baseline counts
        scenes_before = self.db.query(SceneRecord).count()
        tiles_before = self.db.query(TileRecord).count()

        actual_scene_id = scene_id or raster_path.stem
        checksum = compute_file_sha256(raster_path)

        # Check if already ingested
        existing_scene = self.db.query(SceneRecord).filter(SceneRecord.scene_id == actual_scene_id).first()
        if existing_scene:
            logger.info(f"Scene {actual_scene_id} already indexed. Skipping.")
            return {
                "status": "ALREADY_INDEXED",
                "batch_id": batch_id,
                "scene_id": actual_scene_id,
                "scenes_before": scenes_before,
                "scenes_after": scenes_before,
                "tiles_before": tiles_before,
                "tiles_after": tiles_before,
                "index_update_time_ms": 0.0,
                "total_ingestion_time_ms": 0.0,
                "new_storage_bytes": 0,
                "checksum_sha256": checksum,
            }

        # 3. Create Scene Record
        rel_path = str(raster_path.relative_to(self.project_root)) if str(raster_path).startswith(str(self.project_root)) else str(raster_path)
        scene_rec = SceneRecord(
            scene_id=actual_scene_id,
            source_uri=rel_path,
            sensor=sensor,
            collection=collection,
            acquired_at=datetime.now(timezone.utc),
            crs=crs_str,
            width=width,
            height=height,
            bands=bands,
            resolution_meters=res_meters,
            min_lon=min_lon,
            min_lat=min_lat,
            max_lon=max_lon,
            max_lat=max_lat,
            geom=bbox_to_wkt(min_lon, min_lat, max_lon, max_lat),
            checksum=checksum,
            manifest_path=f"data/manifests/{actual_scene_id}.json",
            tiles_count=0,
            tile_size=tile_size,
            overlap=overlap,
            status="INDEXED",
        )
        self.db.add(scene_rec)
        self.db.flush()

        # 4. Tiling & Quality Analysis
        step = tile_size - overlap
        created_tiles: List[TileRecord] = []
        new_embeddings_to_add: List[Tuple[str, np.ndarray, Dict[str, Any]]] = []

        with rasterio.open(raster_path) as src:
            tile_idx = 0
            for r in range(0, height, step):
                for c in range(0, width, step):
                    w = min(tile_size, width - c)
                    h = min(tile_size, height - r)
                    if w < tile_size // 2 or h < tile_size // 2:
                        continue

                    window = Window(col_off=c, row_off=r, width=w, height=h)
                    data = src.read(window=window)
                    w_bounds = rasterio.windows.bounds(window, src.transform)
                    if crs_str != "EPSG:4326":
                        t_minx, t_miny, t_maxx, t_maxy = transform_bounds(crs, "EPSG:4326", *w_bounds)
                    else:
                        t_minx, t_miny, t_maxx, t_maxy = w_bounds

                    tile_id = f"{actual_scene_id}_t{tile_idx:04d}"
                    tile_file = self.processed_dir / f"{tile_id}.tif"

                    # Save tile raster
                    t_profile = src.profile.copy()
                    t_profile.pop("blockxsize", None)
                    t_profile.pop("blockysize", None)
                    t_profile.pop("tiled", None)
                    t_profile.update({
                        "height": h,
                        "width": w,
                        "transform": rasterio.windows.transform(window, src.transform),
                    })
                    with rasterio.open(tile_file, "w", **t_profile) as dst:
                        dst.write(data)

                    tile_checksum = compute_file_sha256(tile_file)
                    tile_rel = str(tile_file.relative_to(self.project_root)) if str(tile_file).startswith(str(self.project_root)) else str(tile_file)

                    # Simple cloud metric proxy
                    nodata_pct = float(np.mean(data == 0) * 100.0)
                    cloud_pct = float(np.mean(data > 240) * 10.0)

                    t_rec = TileRecord(
                        tile_id=tile_id,
                        scene_id=actual_scene_id,
                        tile_index=tile_idx,
                        path=tile_rel,
                        min_lon=t_minx,
                        min_lat=t_miny,
                        max_lon=t_maxx,
                        max_lat=t_maxy,
                        geom=bbox_to_wkt(t_minx, t_miny, t_maxx, t_maxy),
                        col_off=c,
                        row_off=r,
                        width=w,
                        height=h,
                        cloud_cover_percent=cloud_pct,
                        nodata_percent=nodata_pct,
                        checksum=tile_checksum,
                    )
                    created_tiles.append(t_rec)
                    self.db.add(t_rec)

                    # 5. Compute embedding for tile
                    emb_vec = self.model.encode_image(tile_file)
                    m_meta = self.model.model_metadata()
                    emb_rec = TileEmbeddingRecord(
                        embedding_id=f"emb_{tile_id}",
                        tile_id=tile_id,
                        scene_id=actual_scene_id,
                        model_name=m_meta.get("model_name", "RemoteCLIP-ViT-B-32"),
                        model_version=m_meta.get("model_version", m_meta.get("version", "1.0.0")),
                        dimension=len(emb_vec),
                        checksum=hashlib.sha256(emb_vec.tobytes()).hexdigest(),
                    )
                    emb_rec.set_vector(emb_vec)
                    self.db.add(emb_rec)

                    new_embeddings_to_add.append((
                        tile_id,
                        emb_vec,
                        {
                            "scene_id": actual_scene_id,
                            "sensor": sensor,
                            "bounds": [t_minx, t_miny, t_maxx, t_maxy],
                        },
                    ))
                    tile_idx += 1

        scene_rec.tiles_count = len(created_tiles)
        self.db.commit()

        # 6. ATOMIC VECTOR INDEX UPDATE (O(N_new) without rebuilding old index!)
        t_idx0 = time.perf_counter()
        for tid, vec, meta in new_embeddings_to_add:
            self.vector_index.add(tile_id=tid, vector=vec, metadata=meta)
        index_update_time_ms = round((time.perf_counter() - t_idx0) * 1000.0, 3)

        # Persist updated vector cache
        try:
            self.vector_index.save(self.processed_dir / "vector_index.npz")
        except Exception as e:
            logger.warning(f"Could not persist vector cache: {e}")

        # Compute storage delta
        total_ingestion_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        storage_delta = sum(
            (self.project_root / t.path).stat().st_size
            for t in created_tiles
            if (self.project_root / t.path).exists()
        )
        scenes_after = self.db.query(SceneRecord).count()
        tiles_after = self.db.query(TileRecord).count()

        # 7. Record in Ingestion History Ledger
        history = IngestionHistoryRecord(
            batch_id=batch_id,
            scene_id=actual_scene_id,
            source_filename=raster_path.name,
            status="SUCCESS",
            scenes_before=scenes_before,
            scenes_after=scenes_after,
            tiles_before=tiles_before,
            tiles_after=tiles_after,
            index_update_time_ms=index_update_time_ms,
            total_ingestion_time_ms=total_ingestion_time_ms,
            new_storage_bytes=storage_delta,
            total_storage_bytes=storage_delta + file_size,
            checksum_sha256=checksum,
            crs=crs_str,
            resolution_meters=res_meters,
        )
        self.db.add(history)
        self.db.commit()

        logger.info(
            f"Atomic incremental ingestion complete for {actual_scene_id}: "
            f"+{len(created_tiles)} tiles, index updated in {index_update_time_ms}ms"
        )

        return history.to_dict()

    def get_ingestion_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Returns the ingestion history ledger."""
        records = (
            self.db.query(IngestionHistoryRecord)
            .order_by(IngestionHistoryRecord.created_at.desc())
            .limit(limit)
            .all()
        )
        return [r.to_dict() for r in records]
