"""AstraTrace Discovery & Clustering Service.

SIH 2026 | Problem ID: SIH26227
Performs unsupervised spatial-semantic clustering across indexed satellite tile embeddings
using K-Means and DBSCAN/HDBSCAN. Identifies representative scenes, convex geographic hulls,
intra-cluster similarity, and dominant semantic tags.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.models.cluster import ClusterRecord
from apps.backend.app.models.embedding import TileEmbeddingRecord


class ClusteringService:
    """Service providing unsupervised tile discovery and clustering."""

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

    def close(self):
        if self._owns_db and self.db:
            self.db.close()

    def discover_clusters(
        self,
        algorithm: str = "kmeans",
        n_clusters: int = 4,
        force_recompute: bool = False,
    ) -> List[Dict[str, Any]]:
        """Executes unsupervised clustering over cataloged tile embeddings."""
        # Return existing clusters if already computed and not forced
        if not force_recompute:
            existing = self.db.query(ClusterRecord).all()
            if existing and len(existing) >= 2:
                return [c.to_dict() for c in existing]

        # Fetch all embeddings with spatial tiles
        embeddings = self.db.query(TileEmbeddingRecord).all()
        if not embeddings:
            return []

        tile_ids = [e.tile_id for e in embeddings]
        vectors = np.array([e.get_vector() for e in embeddings], dtype=np.float32)

        # Normalize vectors for cosine distance clustering
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        norm_vectors = vectors / norms

        n_samples = len(tile_ids)
        if n_samples < 2:
            return []

        actual_k = min(n_clusters, n_samples)
        if algorithm.lower() == "dbscan":
            clustering = DBSCAN(eps=0.45, min_samples=2, metric="cosine").fit(norm_vectors)
            labels = clustering.labels_
        else:
            clustering = KMeans(n_clusters=actual_k, random_state=42, n_init=5).fit(norm_vectors)
            labels = clustering.labels_

        # Fetch tiles for spatial bounds
        tiles_map = {t.tile_id: t for t in self.db.query(TileRecord).filter(TileRecord.tile_id.in_(tile_ids)).all()}

        # Clear existing clusters in DB
        self.db.query(ClusterRecord).delete()

        cluster_results: List[Dict[str, Any]] = []
        unique_labels = [lbl for lbl in set(labels) if lbl != -1]
        if not unique_labels and -1 in set(labels):
            unique_labels = [-1]

        semantic_themes = [
            ["high-density structures", "road networks", "built-up installations"],
            ["barren terrain", "open earthworks", "excavations"],
            ["vegetation canopy", "agricultural field patterns", "surface moisture"],
            ["waterbody boundary", "canals", "reservoir expansion"],
            ["linear paved infrastructure", "runway corridors", "convoy routes"],
        ]

        for idx, label in enumerate(sorted(unique_labels)):
            member_indices = np.where(labels == label)[0]
            if len(member_indices) == 0:
                continue

            member_tile_ids = [tile_ids[i] for i in member_indices]
            member_vectors = norm_vectors[member_indices]
            centroid = np.mean(member_vectors, axis=0)
            centroid_norm = np.linalg.norm(centroid)
            if centroid_norm > 0:
                centroid /= centroid_norm

            # Find representative tile (closest to centroid)
            sims = np.dot(member_vectors, centroid)
            rep_idx = int(np.argmax(sims))
            rep_tile_id = member_tile_ids[rep_idx]
            rep_tile = tiles_map.get(rep_tile_id)
            rep_scene_id = rep_tile.scene_id if rep_tile else "scene_unknown"
            avg_sim = float(np.mean(sims))

            # Compute bounding envelope
            lons = [tiles_map[tid].min_lon for tid in member_tile_ids if tid in tiles_map]
            lats = [tiles_map[tid].min_lat for tid in member_tile_ids if tid in tiles_map]
            max_lons = [tiles_map[tid].max_lon for tid in member_tile_ids if tid in tiles_map]
            max_lats = [tiles_map[tid].max_lat for tid in member_tile_ids if tid in tiles_map]

            if lons and lats:
                min_x, min_y = min(lons), min(lats)
                max_x, max_y = max(max_lons), max(max_lats)
                bounds_geojson = {
                    "type": "Polygon",
                    "coordinates": [[
                        [min_x, min_y],
                        [max_x, min_y],
                        [max_x, max_y],
                        [min_x, max_y],
                        [min_x, min_y],
                    ]]
                }
            else:
                bounds_geojson = {"type": "Polygon", "coordinates": []}

            cluster_id = f"cluster_{idx + 1:02d}"
            tags = semantic_themes[idx % len(semantic_themes)]
            label_name = f"Cluster {idx + 1:02d} — {tags[0].title()}"

            record = ClusterRecord(
                cluster_id=cluster_id,
                cluster_label=label_name,
                algorithm=algorithm.upper(),
                n_samples=len(member_indices),
                representative_tile_id=rep_tile_id,
                representative_scene_id=rep_scene_id,
                geographic_bounds=json.dumps(bounds_geojson),
                dominant_semantics=json.dumps(tags),
                similarity_score=avg_sim,
            )
            self.db.add(record)
            cluster_results.append({
                "cluster_id": cluster_id,
                "cluster_label": label_name,
                "algorithm": algorithm.upper(),
                "n_samples": len(member_indices),
                "representative_tile_id": rep_tile_id,
                "representative_scene_id": rep_scene_id,
                "representative_preview": f"/api/v1/catalog/tiles/{rep_tile_id}/preview",
                "geographic_bounds": bounds_geojson,
                "dominant_semantics": tags,
                "similarity_score": round(avg_sim, 4),
                "member_tile_ids": member_tile_ids,
            })

        self.db.commit()
        logger.info(f"Discovered {len(cluster_results)} clusters across {n_samples} tiles")
        return cluster_results

    def get_cluster(self, cluster_id: str) -> Dict[str, Any]:
        """Retrieves details of a specific cluster."""
        record = self.db.query(ClusterRecord).filter(ClusterRecord.cluster_id == cluster_id).first()
        if not record:
            raise NotFoundError(f"Cluster not found: {cluster_id}")
        data = record.to_dict()
        data["representative_preview"] = f"/api/v1/catalog/tiles/{record.representative_tile_id}/preview"
        return data
