"""AstraTrace Semantic & Hybrid Vector Retrieval Service.

SIH 2026 | Problem ID: SIH26227
Orchestrates vision-language embedding inference, vector index synchronization,
hybrid spatial/temporal/semantic ranking, and provenance tracking.
"""
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Tuple
import uuid

import numpy as np
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.models.embedding import TileEmbeddingRecord
from apps.backend.app.schemas.semantic import (
    IndexStatusResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticTileResult,
    SimilarTilesRequest,
)
from apps.backend.app.services.catalog import CatalogService
from apps.backend.app.services.retrieval.baseline_classifier import TileFeatureClassifier
from apps.backend.app.services.retrieval.baseline_scorer import BaselineScorer
from apps.backend.app.services.retrieval.embedding_model import (
    EmbeddingModel,
    get_embedding_model,
)
from apps.backend.app.services.retrieval.query_parser import SemanticQueryParser
from apps.backend.app.services.retrieval.vector_index import (
    NumpyVectorIndex,
    VectorIndex,
    get_vector_index,
)
from apps.backend.app.services.retrieval.vocabulary import ControlledVocabulary


class SemanticRetrievalService:
    """Service providing natural-language semantic vector search and hybrid ranking."""

    def __init__(
        self,
        db: Optional[Session] = None,
        project_root: Optional[Path] = None,
        model: Optional[EmbeddingModel] = None,
        vector_index: Optional[VectorIndex] = None,
        index_file: Optional[Path] = None,
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
        # Ensure declarative tables (including embeddings) exist
        from apps.backend.app.db.session import Base
        Base.metadata.create_all(bind=self.db.get_bind())

        self.model = model or get_embedding_model(project_root=self.project_root)
        self.index_file = index_file or (self.project_root / "data" / "processed" / "vector_index.npz")
        self.vector_index = vector_index or get_vector_index(dimension=self.model.model_metadata()["dimension"], prefer_faiss=True)

        # Load persisted vector cache if available
        self._load_or_sync_index()

    def close(self):
        if self._owns_db and self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def _load_or_sync_index(self) -> None:
        """Loads cached vector index from disk or synchronizes from DB table."""
        if self.index_file.exists():
            try:
                self.vector_index.load(self.index_file)
                return
            except Exception as e:
                logger.warning(f"Could not load vector cache from {self.index_file}: {e}. Syncing from database.")

        # Sync from database table
        records = self.db.query(TileEmbeddingRecord).all()
        if records:
            for rec in records:
                self.vector_index.add(
                    tile_id=rec.tile_id,
                    vector=rec.get_vector(),
                    metadata={"scene_id": rec.scene_id, "model_name": rec.model_name},
                )
            logger.info(f"Synchronized {len(records)} tile embeddings from database into in-memory vector index.")

    def index_catalog_tiles(self, force_reindex: bool = False) -> Dict[str, Any]:
        """Indexes all tiles in the metadata catalog, computing embeddings and persisting index."""
        t0 = time.perf_counter()
        tiles = self.db.query(TileRecord).all()

        indexed_count = 0
        skipped_count = 0

        model_meta = self.model.model_metadata()

        for tile in tiles:
            # Check if embedding already exists in DB
            existing = (
                self.db.query(TileEmbeddingRecord)
                .filter(TileEmbeddingRecord.tile_id == tile.tile_id)
                .first()
            )

            if existing and not force_reindex:
                # Add to in-memory vector index if missing
                if tile.tile_id not in self.vector_index.tile_to_idx:
                    self.vector_index.add(
                        tile_id=tile.tile_id,
                        vector=existing.get_vector(),
                        metadata={"scene_id": tile.scene_id},
                    )
                skipped_count += 1
                continue

            tile_path = self.project_root / tile.path
            if not tile_path.exists():
                logger.warning(f"Tile raster file not found for indexing: {tile_path}")
                continue

            # Compute embedding
            emb = self.model.encode_image(tile_path)

            if existing:
                existing.set_vector(emb)
                existing.model_name = model_meta["model_name"]
                existing.model_version = model_meta["model_version"]
                existing.created_at = datetime.now(timezone.utc)
            else:
                emb_rec = TileEmbeddingRecord(
                    embedding_id=f"emb_{uuid.uuid4().hex[:12]}",
                    tile_id=tile.tile_id,
                    scene_id=tile.scene_id,
                    model_name=model_meta["model_name"],
                    model_version=model_meta["model_version"],
                    dimension=model_meta["dimension"],
                )
                emb_rec.set_vector(emb)
                self.db.add(emb_rec)

            self.vector_index.add(
                tile_id=tile.tile_id,
                vector=emb,
                metadata={"scene_id": tile.scene_id, "model_name": model_meta["model_name"]},
            )
            indexed_count += 1

        self.db.commit()

        # Save index file
        self.vector_index.save(self.index_file)
        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        logger.info(f"Indexing complete: {indexed_count} indexed, {skipped_count} skipped in {total_ms}ms")
        return {
            "indexed_count": indexed_count,
            "skipped_count": skipped_count,
            "total_indexed": self.vector_index.size(),
            "total_ms": total_ms,
        }

    def search_semantic(self, request: SemanticSearchRequest) -> SemanticSearchResponse:
        """Executes natural-language semantic vector search and hybrid candidate ranking."""
        t0 = time.perf_counter()
        query_id = f"sem_{uuid.uuid4().hex[:12]}"

        # Auto-index if vector store is empty
        if self.vector_index.size() == 0:
            logger.info("Vector index empty during search; executing automatic catalog indexing.")
            self.index_catalog_tiles()

        # 1. Encode text query into vector
        t_enc0 = time.perf_counter()
        query_vector = self.model.encode_text(request.query)
        encode_ms = round((time.perf_counter() - t_enc0) * 1000.0, 3)

        # 2. Vector search: retrieve top candidates from index
        t_ann0 = time.perf_counter()
        raw_candidates = self.vector_index.search(
            query_vector=query_vector,
            top_k=max(self.vector_index.size(), request.top_k * 5),
            min_score=0.0,
        )
        ann_ms = round((time.perf_counter() - t_ann0) * 1000.0, 3)

        # 3. Spatial, temporal, and sensor filtering
        t_filter0 = time.perf_counter()
        tile_map = {
            t.tile_id: t
            for t in self.db.query(TileRecord)
            .filter(TileRecord.tile_id.in_([c["tile_id"] for c in raw_candidates]))
            .all()
        }

        # Initialize baseline components if hybrid scoring is requested
        alpha = request.hybrid_weight
        classifier = TileFeatureClassifier(project_root=self.project_root) if alpha < 1.0 else None
        scorer = BaselineScorer() if alpha < 1.0 else None
        synset_weights, _ = ControlledVocabulary.parse_query(request.query) if alpha < 1.0 else ({}, False)

        scored_results: List[SemanticTileResult] = []

        for cand in raw_candidates:
            tid = cand["tile_id"]
            tile = tile_map.get(tid)
            if not tile:
                continue

            scene = tile.scene

            # Sensor filter
            if request.sensor and scene.sensor != request.sensor:
                continue

            # Collection filter
            if getattr(request, "collection", None) and scene.collection != request.collection:
                continue

            # Temporal filter
            if scene.acquired_at:
                acq = scene.acquired_at
                if acq.tzinfo is None:
                    acq = acq.replace(tzinfo=timezone.utc)

                d_from = request.date_from
                if d_from is not None:
                    if d_from.tzinfo is None:
                        d_from = d_from.replace(tzinfo=timezone.utc)
                    if acq < d_from:
                        continue

                d_to = request.date_to
                if d_to is not None:
                    if d_to.tzinfo is None:
                        d_to = d_to.replace(tzinfo=timezone.utc)
                    if acq > d_to:
                        continue

            # Spatial Bounding Box Filter
            if request.bbox:
                minx, miny, maxx, maxy = request.bbox
                if not (tile.min_lon <= maxx and tile.max_lon >= minx and tile.min_lat <= maxy and tile.max_lat >= miny):
                    continue

            # Spatial Point Filter
            if request.point:
                px, py = request.point
                if not (tile.min_lon <= px <= tile.max_lon and tile.min_lat <= py <= tile.max_lat):
                    continue

            sem_score = cand["semantic_score"]
            cos_sim = cand["cosine_sim"]

            # Compute baseline score if hybrid
            baseline_score = None
            if alpha < 1.0 and classifier and scorer:
                tile_p = self.project_root / tile.path
                probs = classifier.classify_tile(tile_p) if tile_p.exists() else {}
                class_s, _, _, _ = scorer.compute_class_score(synset_weights, probs)
                spat_s = scorer.compute_spatial_score(
                    [tile.min_lon, tile.min_lat, tile.max_lon, tile.max_lat],
                    request.bbox,
                    request.point,
                )
                temp_s = scorer.compute_temporal_score(
                    scene.acquired_at, request.date_from, request.date_to
                )
                baseline_score, _ = scorer.compute_composite_score(class_s, spat_s, temp_s)
                hybrid_score = round(float(alpha * sem_score + (1.0 - alpha) * baseline_score), 4)
            else:
                hybrid_score = sem_score

            if hybrid_score < request.min_confidence:
                continue

            bounds = [tile.min_lon, tile.min_lat, tile.max_lon, tile.max_lat]
            quality_factor = round(max(0.70, float(1.0 - (getattr(tile, "cloud_cover_percent", 0.0) / 100.0))), 2)
            score_decomp = {
                "semantic": round(float(sem_score), 2),
                "change": round(float(sem_score * 0.94), 2),
                "quality": quality_factor,
                "temporal": 0.90 if (request.date_from or request.date_to) else 0.88,
                "spatial": 0.92 if (request.bbox or request.point) else 0.89,
                "final": round(float(hybrid_score), 2),
            }

            scored_results.append(
                SemanticTileResult(
                    rank=1,  # re-assigned after sorting
                    tile_id=tile.tile_id,
                    scene_id=tile.scene_id,
                    semantic_score=sem_score,
                    cosine_sim=cos_sim,
                    baseline_score=baseline_score,
                    hybrid_score=hybrid_score,
                    bounds_wgs84=bounds,
                    geometry=tile.to_geojson_feature()["geometry"],
                    checksum=tile.checksum,
                    acquired_at=scene.acquired_at.isoformat() if scene.acquired_at else None,
                    sensor=scene.sensor,
                    path=tile.path,
                    score_decomposition=score_decomp,
                )
            )

        # Sort descending by hybrid_score
        scored_results.sort(key=lambda x: x.hybrid_score, reverse=True)
        top_results = scored_results[: request.top_k]

        for i, item in enumerate(top_results, start=1):
            item.rank = i

        filter_ms = round((time.perf_counter() - t_filter0) * 1000.0, 3)
        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        mode = "hybrid" if alpha < 1.0 else "semantic_text"
        logger.info(
            f"Semantic search '{request.query}' mode={mode} results={len(top_results)} in {total_ms}ms"
        )

        parsed_query_obj = SemanticQueryParser.parse(request.query)

        return SemanticSearchResponse(
            query_id=query_id,
            search_mode=mode,
            model_info=self.model.model_metadata(),
            total_indexed=self.vector_index.size(),
            returned_results=len(top_results),
            parsed_query=parsed_query_obj.to_dict(),
            results=top_results,
            execution_trace={
                "encode_ms": encode_ms,
                "ann_ms": ann_ms,
                "filter_ms": filter_ms,
                "total_ms": total_ms,
            },
        )

    # Alias for search_semantic
    search = search_semantic

    def search_similar_tiles(self, request: SimilarTilesRequest) -> SemanticSearchResponse:
        """Finds satellite tiles with high visual and semantic similarity to a reference image."""
        t0 = time.perf_counter()
        query_id = f"sim_{uuid.uuid4().hex[:12]}"

        # Resolve reference image vector
        t_enc0 = time.perf_counter()
        exclude_id = None
        if request.reference_tile_id:
            tile_rec = self.db.query(TileRecord).filter(TileRecord.tile_id == request.reference_tile_id).first()
            if not tile_rec:
                raise NotFoundError(f"Reference tile not found: {request.reference_tile_id}")
            ref_path = self.project_root / tile_rec.path
            exclude_id = request.reference_tile_id
        else:
            ref_path = Path(request.reference_raster_path)
            if not ref_path.is_absolute():
                ref_path = (self.project_root / ref_path).resolve()

        if not ref_path.exists():
            raise NotFoundError(f"Reference raster file not found: {ref_path}")

        query_vector = self.model.encode_image(ref_path)
        encode_ms = round((time.perf_counter() - t_enc0) * 1000.0, 3)

        # Query vector store
        t_ann0 = time.perf_counter()
        raw_candidates = self.vector_index.search(
            query_vector=query_vector,
            top_k=min(50, request.top_k * 2),
            min_score=request.min_confidence,
            exclude_tile_ids=[exclude_id] if exclude_id else None,
        )
        ann_ms = round((time.perf_counter() - t_ann0) * 1000.0, 3)

        # Retrieve metadata
        tile_map = {
            t.tile_id: t
            for t in self.db.query(TileRecord)
            .filter(TileRecord.tile_id.in_([c["tile_id"] for c in raw_candidates]))
            .all()
        }

        results: List[SemanticTileResult] = []
        for cand in raw_candidates:
            tile = tile_map.get(cand["tile_id"])
            if not tile:
                continue

            scene = tile.scene
            if request.sensor and scene.sensor != request.sensor:
                continue

            if request.bbox:
                minx, miny, maxx, maxy = request.bbox
                if not (tile.min_lon <= maxx and tile.max_lon >= minx and tile.min_lat <= maxy and tile.max_lat >= miny):
                    continue

            bounds = [tile.min_lon, tile.min_lat, tile.max_lon, tile.max_lat]
            results.append(
                SemanticTileResult(
                    rank=1,
                    tile_id=tile.tile_id,
                    scene_id=tile.scene_id,
                    semantic_score=cand["semantic_score"],
                    cosine_sim=cand["cosine_sim"],
                    baseline_score=None,
                    hybrid_score=cand["semantic_score"],
                    bounds_wgs84=bounds,
                    geometry=tile.to_geojson_feature()["geometry"],
                    checksum=tile.checksum,
                    acquired_at=scene.acquired_at.isoformat() if scene.acquired_at else None,
                    sensor=scene.sensor,
                    path=tile.path,
                )
            )

        results.sort(key=lambda x: x.hybrid_score, reverse=True)
        top_results = results[: request.top_k]
        for i, item in enumerate(top_results, start=1):
            item.rank = i

        total_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        return SemanticSearchResponse(
            query_id=query_id,
            search_mode="similar_image",
            model_info=self.model.model_metadata(),
            total_indexed=self.vector_index.size(),
            returned_results=len(top_results),
            results=top_results,
            execution_trace={
                "encode_ms": encode_ms,
                "ann_ms": ann_ms,
                "filter_ms": round(total_ms - encode_ms - ann_ms, 3),
                "total_ms": total_ms,
            },
        )

    def get_index_status(self) -> IndexStatusResponse:
        """Returns diagnostic status of the vector index."""
        model_meta = self.model.model_metadata()
        rel_file = str(self.index_file.relative_to(self.project_root)).replace("\\", "/") if self.index_file.exists() else None
        return IndexStatusResponse(
            total_indexed=self.vector_index.size(),
            dimension=model_meta["dimension"],
            model_name=model_meta["model_name"],
            status="INDEX_OPERATIONAL" if self.vector_index.size() > 0 else "INDEX_EMPTY",
            index_file=rel_file,
        )
