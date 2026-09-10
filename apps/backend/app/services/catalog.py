"""AstraTrace Catalog and Geospatial Database Service.

SIH 2026 | Problem ID: SIH26227
Provides transaction-safe, idempotent ingestion from Milestone 2 manifests,
spatial bounding box queries, temporal range filtering, and STAC-compatible metadata serialization.
"""
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.models.catalog import SceneRecord, TileRecord, bbox_to_wkt
from apps.backend.app.schemas.catalog import CatalogIngestResponse, TileSearchRequest


class CatalogService:
    """Service for cataloging satellite scenes and performing spatial/temporal indexing."""

    def __init__(self, db: Optional[Session] = None, project_root: Optional[Path] = None):
        self._db_external = db is not None
        self.db = db if db is not None else SessionLocal()

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

    def close(self):
        """Closes the session if it was internally created."""
        if not self._db_external and self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def register_manifest(self, manifest_input: Union[str, Path, Dict[str, Any]]) -> CatalogIngestResponse:
        """Registers a Milestone 2 ingestion manifest into the catalog.

        Guarantees idempotency: re-registering an unchanged manifest returns SKIPPED_DUPLICATE
        without throwing a database error.
        """
        # 1. Load manifest data
        if isinstance(manifest_input, (str, Path)):
            manifest_path = Path(manifest_input)
            if not manifest_path.is_absolute():
                manifest_path = (self.project_root / manifest_path).resolve()

            if not manifest_path.exists() or not manifest_path.is_file():
                raise NotFoundError(f"Manifest file not found: {manifest_input}")

            with open(manifest_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            rel_manifest_path = str(manifest_path.relative_to(self.project_root)).replace("\\", "/")
        elif isinstance(manifest_input, dict):
            data = manifest_input
            rel_manifest_path = data.get("manifest_path", "")
        else:
            raise ValidationError("manifest_input must be a filepath string, Path, or dictionary.")

        # 2. Validate essential manifest fields
        required_fields = ["scene_id", "sensor", "collection", "acquired_at", "crs", "dimensions", "bbox_wgs84", "scene_checksum", "tiles"]
        for field in required_fields:
            if field not in data:
                raise ValidationError(f"Invalid manifest: missing required field '{field}'.")

        scene_id = data["scene_id"]
        sensor = data["sensor"]
        collection = data["collection"]
        checksum = data["scene_checksum"]
        bbox = data["bbox_wgs84"]

        if len(bbox) != 4:
            raise ValidationError(f"Invalid bbox_wgs84: expected 4 floats, got {bbox}")

        min_lon, min_lat, max_lon, max_lat = bbox

        # Parse acquisition date
        try:
            acquired_dt = datetime.fromisoformat(data["acquired_at"].replace("Z", "+00:00"))
        except Exception as e:
            raise ValidationError(f"Invalid acquired_at timestamp '{data['acquired_at']}': {e}")

        # 3. Check for existing record (Idempotency check)
        existing_scene = self.db.query(SceneRecord).filter(SceneRecord.scene_id == scene_id).first()
        if existing_scene:
            if existing_scene.checksum == checksum:
                logger.info(f"Scene {scene_id} already registered with matching checksum. Skipping duplicate.")
                return CatalogIngestResponse(
                    scene_id=scene_id,
                    sensor=sensor,
                    collection=collection,
                    tiles_registered=len(existing_scene.tiles),
                    status="SKIPPED_DUPLICATE",
                    message="Scene is already registered in the catalog with matching SHA-256 checksum.",
                )
            else:
                logger.info(f"Scene {scene_id} exists with modified checksum. Updating records.")
                # Delete existing tiles to cleanly refresh
                self.db.delete(existing_scene)
                self.db.flush()

        # 4. Insert SceneRecord and TileRecords in single atomic transaction
        try:
            geom_wkt = bbox_to_wkt(min_lon, min_lat, max_lon, max_lat)
            width, height, bands = data["dimensions"]

            scene_record = SceneRecord(
                scene_id=scene_id,
                source_uri=data.get("source_uri", ""),
                sensor=sensor,
                collection=collection,
                acquired_at=acquired_dt,
                crs=data["crs"],
                width=width,
                height=height,
                bands=bands,
                resolution_meters=10.0,
                min_lon=min_lon,
                min_lat=min_lat,
                max_lon=max_lon,
                max_lat=max_lat,
                geom=geom_wkt,
                checksum=checksum,
                manifest_path=rel_manifest_path,
                tiles_count=len(data["tiles"]),
                tile_size=data.get("tile_size", 256),
                overlap=data.get("overlap", 25),
                status="INDEXED",
            )
            self.db.add(scene_record)
            self.db.flush()

            # Insert tiles
            tiles_data = data["tiles"]
            for t in tiles_data:
                t_bbox = t["bounds_wgs84"]
                t_min_lon, t_min_lat, t_max_lon, t_max_lat = t_bbox
                t_geom_wkt = bbox_to_wkt(t_min_lon, t_min_lat, t_max_lon, t_max_lat)
                pixel_win = t["pixel_window"]

                tile_record = TileRecord(
                    tile_id=t["tile_id"],
                    scene_id=scene_id,
                    tile_index=t["tile_index"],
                    path=t["path"],
                    min_lon=t_min_lon,
                    min_lat=t_min_lat,
                    max_lon=t_max_lon,
                    max_lat=t_max_lat,
                    geom=t_geom_wkt,
                    col_off=pixel_win[0],
                    row_off=pixel_win[1],
                    width=pixel_win[2],
                    height=pixel_win[3],
                    cloud_cover_percent=t.get("cloud_cover_percent", 0.0),
                    nodata_percent=t.get("nodata_percent", 0.0),
                    checksum=t["checksum"],
                )
                self.db.add(tile_record)

            self.db.commit()
            logger.info(f"Successfully cataloged scene {scene_id} with {len(tiles_data)} tiles.")

            return CatalogIngestResponse(
                scene_id=scene_id,
                sensor=sensor,
                collection=collection,
                tiles_registered=len(tiles_data),
                status="REGISTERED",
                message=f"Successfully registered scene and {len(tiles_data)} tiles into catalog.",
            )
        except Exception as e:
            self.db.rollback()
            logger.error(f"Catalog ingestion failed for {scene_id}: {e}", exc_info=True)
            raise ValidationError(f"Failed to catalog scene: {str(e)}")

    def query_scenes(
        self,
        sensor: Optional[str] = None,
        collection: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        bbox: Optional[List[float]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> Tuple[int, List[SceneRecord]]:
        """Queries scenes by sensor, collection, temporal range, and spatial bounding box."""
        query = self.db.query(SceneRecord)

        if sensor:
            query = query.filter(SceneRecord.sensor == sensor.upper())
        if collection:
            query = query.filter(SceneRecord.collection == collection)
        if date_from:
            query = query.filter(SceneRecord.acquired_at >= date_from)
        if date_to:
            query = query.filter(SceneRecord.acquired_at <= date_to)

        # Spatial 2D Bounding Box intersection filter:
        # scene.max_lon >= q.min_lon AND scene.min_lon <= q.max_lon AND
        # scene.max_lat >= q.min_lat AND scene.min_lat <= q.max_lat
        if bbox:
            q_minx, q_miny, q_maxx, q_maxy = bbox
            query = query.filter(
                and_(
                    SceneRecord.max_lon >= q_minx,
                    SceneRecord.min_lon <= q_maxx,
                    SceneRecord.max_lat >= q_miny,
                    SceneRecord.min_lat <= q_maxy,
                )
            )

        total = query.count()
        scenes = query.order_by(SceneRecord.acquired_at.desc()).offset(offset).limit(limit).all()
        return total, scenes

    def query_tiles(self, request: TileSearchRequest) -> Tuple[int, List[Dict[str, Any]]]:
        """Searches catalog tiles with combined spatial, temporal, and quality constraints."""
        query = self.db.query(TileRecord).join(SceneRecord, TileRecord.scene_id == SceneRecord.scene_id)

        # Spatial Filtering
        if request.bbox:
            q_minx, q_miny, q_maxx, q_maxy = request.bbox
            query = query.filter(
                and_(
                    TileRecord.max_lon >= q_minx,
                    TileRecord.min_lon <= q_maxx,
                    TileRecord.max_lat >= q_miny,
                    TileRecord.min_lat <= q_maxy,
                )
            )
        elif request.point:
            lon, lat = request.point
            query = query.filter(
                and_(
                    TileRecord.min_lon <= lon,
                    TileRecord.max_lon >= lon,
                    TileRecord.min_lat <= lat,
                    TileRecord.max_lat >= lat,
                )
            )

        # Temporal Filtering (applied via parent SceneRecord)
        if request.date_from:
            query = query.filter(SceneRecord.acquired_at >= request.date_from)
        if request.date_to:
            query = query.filter(SceneRecord.acquired_at <= request.date_to)

        # Sensor Filtering
        if request.sensor:
            query = query.filter(SceneRecord.sensor == request.sensor.upper())

        # Quality Filtering
        if request.max_cloud_cover is not None:
            query = query.filter(TileRecord.cloud_cover_percent <= request.max_cloud_cover)

        total = query.count()
        tiles = (
            query.order_by(SceneRecord.acquired_at.desc(), TileRecord.tile_index.asc())
            .offset(request.offset)
            .limit(request.limit)
            .all()
        )

        results = []
        for t in tiles:
            tile_dict = t.to_dict()
            tile_dict["sensor"] = t.scene.sensor
            tile_dict["acquired_at"] = t.scene.acquired_at.isoformat()
            tile_dict["collection"] = t.scene.collection
            results.append(tile_dict)

        return total, results

    def get_scene(self, scene_id: str) -> SceneRecord:
        """Retrieves a single scene record by ID."""
        scene = self.db.query(SceneRecord).filter(SceneRecord.scene_id == scene_id).first()
        if not scene:
            raise NotFoundError(f"Scene not found in catalog: {scene_id}")
        return scene

    def get_stac_item(self, scene_id: str) -> Dict[str, Any]:
        """Returns the STAC Item representation for a scene."""
        scene = self.get_scene(scene_id)
        return scene.to_stac_item()

    def get_collections_summary(self) -> List[Dict[str, Any]]:
        """Returns a list of all distinct collections with spatial and temporal extents."""
        collections_query = (
            self.db.query(
                SceneRecord.collection,
                func.min(SceneRecord.min_lon).label("min_lon"),
                func.min(SceneRecord.min_lat).label("min_lat"),
                func.max(SceneRecord.max_lon).label("max_lon"),
                func.max(SceneRecord.max_lat).label("max_lat"),
                func.min(SceneRecord.acquired_at).label("min_date"),
                func.max(SceneRecord.acquired_at).label("max_date"),
                func.count(SceneRecord.scene_id).label("scene_count"),
            )
            .group_by(SceneRecord.collection)
            .all()
        )

        result = []
        for col in collections_query:
            result.append({
                "type": "Collection",
                "stac_version": "1.0.0",
                "id": col.collection,
                "title": f"AstraTrace Collection: {col.collection}",
                "description": f"Offline satellite observations for {col.collection} ({col.scene_count} scenes).",
                "license": "proprietary",
                "extent": {
                    "spatial": {
                        "bbox": [[col.min_lon, col.min_lat, col.max_lon, col.max_lat]] if col.min_lon is not None else [[-180, -90, 180, 90]]
                    },
                    "temporal": {
                        "interval": [[
                            col.min_date.isoformat() if col.min_date else None,
                            col.max_date.isoformat() if col.max_date else None,
                        ]]
                    },
                },
                "links": [
                    {"rel": "self", "href": f"/api/v1/stac/collections/{col.collection}"},
                    {"rel": "items", "href": f"/api/v1/stac/collections/{col.collection}/items"},
                    {"rel": "root", "href": "/api/v1/stac"},
                ],
            })
        return result
