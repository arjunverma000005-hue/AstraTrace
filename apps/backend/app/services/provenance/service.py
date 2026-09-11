"""Provenance Service for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Constructs and traverses the Directed Acyclic Graph (DAG) of processing lineage
across scenes, tiles, vector embeddings, change detection, quality evaluations,
and human-in-the-loop analyst triage decisions.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.core.logging import get_logger
from apps.backend.app.db.session import SessionLocal
from apps.backend.app.models.audit import AuditEventRecord
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.models.embedding import TileEmbeddingRecord
from apps.backend.app.models.review import AnalystReviewRecord
from apps.backend.app.schemas.provenance import (
    ProvenanceEdge,
    ProvenanceEdgeType,
    ProvenanceGraphResponse,
    ProvenanceNode,
    ProvenanceNodeType,
)

logger = get_logger("astratrace.provenance")


class ProvenanceService:
    """Service reconstructing lineage DAGs across all analytical artifacts."""

    def __init__(self, db: Optional[Session] = None, project_root: Optional[Path] = None):
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

        if db is not None:
            self.db = db
            self._owns_db = False
        else:
            self.db = SessionLocal()
            self._owns_db = True

    def close(self):
        """Closes internal database session if owned."""
        if self._owns_db and self.db:
            self.db.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def get_provenance_graph(self, target_id: str) -> ProvenanceGraphResponse:
        """Constructs the complete lineage DAG for a given target identifier."""
        target_id = target_id.strip()
        nodes: Dict[str, ProvenanceNode] = {}
        edges: List[ProvenanceEdge] = []
        visited_ids: Set[str] = set()

        root_type = "UNKNOWN"

        # 1. Identify target category
        if target_id.startswith("rev_"):
            root_type = "ANALYST_REVIEW"
            self._build_review_lineage(target_id, nodes, edges, visited_ids)
        elif target_id.startswith("chg_") or target_id.startswith("qchg_"):
            root_type = "CHANGE_EVENT"
            self._build_change_lineage(target_id, nodes, edges, visited_ids)
        elif target_id.startswith("scn_") and ("_t" in target_id or "_tile" in target_id):
            root_type = "TILE"
            self._build_tile_lineage(target_id, nodes, edges, visited_ids)
        elif target_id.startswith("scn_"):
            # Check if it's a tile or scene in DB
            tile = self.db.query(TileRecord).filter(TileRecord.tile_id == target_id).first()
            if tile:
                root_type = "TILE"
                self._build_tile_lineage(target_id, nodes, edges, visited_ids)
            else:
                scene = self.db.query(SceneRecord).filter(SceneRecord.scene_id == target_id).first()
                if scene:
                    root_type = "SCENE"
                    self._build_scene_lineage(scene, nodes, edges, visited_ids)
                else:
                    raise NotFoundError(f"Target entity '{target_id}' not found in catalog.")
        else:
            # Fallback search in tiles, reviews, or audit events
            tile = self.db.query(TileRecord).filter(TileRecord.tile_id == target_id).first()
            if tile:
                root_type = "TILE"
                self._build_tile_lineage(target_id, nodes, edges, visited_ids)
            else:
                rev = self.db.query(AnalystReviewRecord).filter(AnalystReviewRecord.review_id == target_id).first()
                if rev:
                    root_type = "ANALYST_REVIEW"
                    self._build_review_lineage(target_id, nodes, edges, visited_ids)
                else:
                    raise NotFoundError(f"Target entity '{target_id}' not found in catalog or provenance graph.")

        summary = {
            "root_id": target_id,
            "root_type": root_type,
            "total_nodes": len(nodes),
            "total_edges": len(edges),
            "node_types": {t.value: sum(1 for n in nodes.values() if n.node_type == t) for t in ProvenanceNodeType},
        }

        return ProvenanceGraphResponse(
            root_id=target_id,
            root_type=root_type,
            nodes=list(nodes.values()),
            edges=edges,
            summary=summary,
        )

    def _build_tile_lineage(
        self,
        tile_id: str,
        nodes: Dict[str, ProvenanceNode],
        edges: List[ProvenanceEdge],
        visited_ids: Set[str],
    ):
        """Constructs upstream and downstream lineage for a specific tile."""
        if tile_id in visited_ids:
            return
        visited_ids.add(tile_id)

        tile = self.db.query(TileRecord).filter(TileRecord.tile_id == tile_id).first()
        if not tile:
            raise NotFoundError(f"Tile '{tile_id}' not found in catalog.")

        # A. Current Tile Node
        cloud_pct = tile.cloud_cover_percent or 0.0
        usable_frac = round(max(0.0, 1.0 - (cloud_pct / 100.0)), 4)
        nodes[tile_id] = ProvenanceNode(
            id=tile_id,
            node_type=ProvenanceNodeType.TILE,
            label=f"Tile {tile.tile_index} ({tile_id})",
            metadata={
                "scene_id": tile.scene_id,
                "tile_index": tile.tile_index,
                "pixel_window": [tile.col_off, tile.row_off, tile.width, tile.height],
                "cloud_cover_percent": cloud_pct,
                "nodata_percent": tile.nodata_percent or 0.0,
                "usable_fraction": usable_frac,
                "path": tile.path,
                "bounds_wgs84": [tile.min_lon, tile.min_lat, tile.max_lon, tile.max_lat],
            },
            checksum=tile.checksum,
            timestamp=tile.created_at.isoformat() if tile.created_at else None,
        )

        # B. Upstream: Scene Node
        scene = tile.scene
        if scene and scene.scene_id not in visited_ids:
            visited_ids.add(scene.scene_id)
            nodes[scene.scene_id] = ProvenanceNode(
                id=scene.scene_id,
                node_type=ProvenanceNodeType.SCENE,
                label=f"Scene {scene.scene_id} ({scene.sensor})",
                metadata={
                    "sensor": scene.sensor,
                    "collection": scene.collection,
                    "crs": scene.crs,
                    "dimensions": [scene.width, scene.height, scene.bands],
                    "resolution_meters": scene.resolution_meters,
                    "bbox_wgs84": [scene.min_lon, scene.min_lat, scene.max_lon, scene.max_lat],
                    "source_uri": scene.source_uri,
                    "manifest_path": scene.manifest_path,
                    "tiles_count": scene.tiles_count,
                    "status": scene.status,
                },
                checksum=scene.checksum,
                timestamp=scene.acquired_at.isoformat() if scene.acquired_at else None,
            )
            edges.append(
                ProvenanceEdge(
                    source=tile_id,
                    target=scene.scene_id,
                    edge_type=ProvenanceEdgeType.DERIVED_FROM,
                    metadata={"operation": "georeferenced_tiling", "overlap": scene.overlap},
                )
            )

        # C. Downstream: Vector Embeddings
        embs = self.db.query(TileEmbeddingRecord).filter(TileEmbeddingRecord.tile_id == tile_id).all()
        for emb in embs:
            emb_id = emb.embedding_id
            if emb_id not in visited_ids:
                visited_ids.add(emb_id)
                nodes[emb_id] = ProvenanceNode(
                    id=emb_id,
                    node_type=ProvenanceNodeType.EMBEDDING,
                    label=f"Embedding: {emb.model_name}",
                    metadata={
                        "model_name": emb.model_name,
                        "model_version": emb.model_version,
                        "dimension": emb.dimension,
                    },
                    checksum=emb.checksum,
                    timestamp=emb.created_at.isoformat() if emb.created_at else None,
                )
                edges.append(
                    ProvenanceEdge(
                        source=emb_id,
                        target=tile_id,
                        edge_type=ProvenanceEdgeType.INDEXED_BY,
                    )
                )

        # D. Quality Assessment Node
        qual_id = f"qual_{tile_id}"
        if qual_id not in visited_ids:
            visited_ids.add(qual_id)
            qual_status = "USABLE" if cloud_pct < 10.0 else ("DEGRADED" if cloud_pct < 30.0 else "UNRELIABLE")
            nodes[qual_id] = ProvenanceNode(
                id=qual_id,
                node_type=ProvenanceNodeType.QUALITY_ASSESSMENT,
                label=f"Optical Quality: {qual_status}",
                metadata={
                    "cloud_fraction": round(cloud_pct / 100.0, 4),
                    "usable_fraction": usable_frac,
                    "status": qual_status,
                    "quality_flags": ["CLEAR"] if cloud_pct < 5.0 else (["HAZE_OR_CLOUD"] if cloud_pct >= 10.0 else []),
                },
                timestamp=tile.created_at.isoformat() if tile.created_at else None,
            )
            edges.append(
                ProvenanceEdge(
                    source=qual_id,
                    target=tile_id,
                    edge_type=ProvenanceEdgeType.EVALUATED_BY,
                )
            )

        # E. Downstream: Analyst Reviews
        reviews = self.db.query(AnalystReviewRecord).filter(AnalystReviewRecord.target_id == tile_id).all()
        for rev in reviews:
            rev_id = rev.review_id
            if rev_id not in visited_ids:
                visited_ids.add(rev_id)
                nodes[rev_id] = ProvenanceNode(
                    id=rev_id,
                    node_type=ProvenanceNodeType.ANALYST_REVIEW,
                    label=f"Review: {rev.decision} ({rev.analyst_id})",
                    metadata={
                        "decision": rev.decision,
                        "analyst_id": rev.analyst_id,
                        "notes": rev.notes,
                        "confidence_at_review": rev.confidence_at_review,
                        "quality_status_at_review": rev.quality_status_at_review,
                        "provenance_snapshot": rev.provenance_snapshot,
                    },
                    timestamp=rev.created_at.isoformat() if rev.created_at else None,
                )
                edges.append(
                    ProvenanceEdge(
                        source=rev_id,
                        target=tile_id,
                        edge_type=ProvenanceEdgeType.REVIEWED_BY,
                    )
                )

    def _build_scene_lineage(
        self,
        scene: SceneRecord,
        nodes: Dict[str, ProvenanceNode],
        edges: List[ProvenanceEdge],
        visited_ids: Set[str],
    ):
        """Constructs lineage for a complete scene and its derived tiles."""
        if scene.scene_id in visited_ids:
            return
        visited_ids.add(scene.scene_id)

        nodes[scene.scene_id] = ProvenanceNode(
            id=scene.scene_id,
            node_type=ProvenanceNodeType.SCENE,
            label=f"Scene {scene.scene_id} ({scene.sensor})",
            metadata={
                "sensor": scene.sensor,
                "collection": scene.collection,
                "crs": scene.crs,
                "dimensions": [scene.width, scene.height, scene.bands],
                "resolution_meters": scene.resolution_meters,
                "bbox_wgs84": [scene.min_lon, scene.min_lat, scene.max_lon, scene.max_lat],
                "source_uri": scene.source_uri,
                "manifest_path": scene.manifest_path,
                "tiles_count": scene.tiles_count,
                "status": scene.status,
            },
            checksum=scene.checksum,
            timestamp=scene.acquired_at.isoformat() if scene.acquired_at else None,
        )

        for tile in scene.tiles:
            self._build_tile_lineage(tile.tile_id, nodes, edges, visited_ids)

    def _build_change_lineage(
        self,
        change_id: str,
        nodes: Dict[str, ProvenanceNode],
        edges: List[ProvenanceEdge],
        visited_ids: Set[str],
    ):
        """Constructs lineage for a change event, linking before/after tiles and reviews."""
        if change_id in visited_ids:
            return
        visited_ids.add(change_id)

        # Check for change mask on disk
        mask_rel = f"data/processed/changes/{change_id}.png"
        mask_alt = f"data/processed/changes/{change_id}_mask.png"
        mask_p = self.project_root / mask_rel
        if not mask_p.exists():
            mask_p = self.project_root / mask_alt
            if mask_p.exists():
                mask_rel = mask_alt

        from apps.backend.app.services.ingestion import calculate_file_sha256
        mask_checksum = calculate_file_sha256(mask_p) if mask_p.exists() else None

        # Check audit events for change metadata
        audit_rec = (
            self.db.query(AuditEventRecord)
            .filter(AuditEventRecord.target_id == change_id)
            .first()
        )
        details = audit_rec.details if audit_rec else {}
        before_tile_id = details.get("before_tile_id")
        after_tile_id = details.get("after_tile_id")

        # Check reviews for this change
        review_recs = (
            self.db.query(AnalystReviewRecord)
            .filter(AnalystReviewRecord.target_id == change_id)
            .all()
        )
        if not before_tile_id and review_recs:
            for r in review_recs:
                snap = r.provenance_snapshot or {}
                if "before_tile_id" in snap:
                    before_tile_id = snap["before_tile_id"]
                    after_tile_id = snap.get("after_tile_id")
                    break

        nodes[change_id] = ProvenanceNode(
            id=change_id,
            node_type=ProvenanceNodeType.CHANGE_EVENT,
            label=f"Change Detection: {change_id}",
            metadata={
                "before_tile_id": before_tile_id,
                "after_tile_id": after_tile_id,
                "mask_path": mask_rel if mask_p.exists() else None,
                "change_metrics": details.get("metrics", {}),
            },
            checksum=mask_checksum,
            timestamp=audit_rec.created_at.isoformat() if audit_rec else datetime.now(timezone.utc).isoformat(),
        )

        # Connect before and after tiles
        if before_tile_id and self.db.query(TileRecord).filter(TileRecord.tile_id == before_tile_id).first():
            self._build_tile_lineage(before_tile_id, nodes, edges, visited_ids)
            edges.append(
                ProvenanceEdge(
                    source=change_id,
                    target=before_tile_id,
                    edge_type=ProvenanceEdgeType.DETECTED_FROM,
                    metadata={"role": "before_t1"},
                )
            )
        if after_tile_id and self.db.query(TileRecord).filter(TileRecord.tile_id == after_tile_id).first():
            self._build_tile_lineage(after_tile_id, nodes, edges, visited_ids)
            edges.append(
                ProvenanceEdge(
                    source=change_id,
                    target=after_tile_id,
                    edge_type=ProvenanceEdgeType.DETECTED_FROM,
                    metadata={"role": "after_t2"},
                )
            )

        # Connect reviews
        for rev in review_recs:
            rev_id = rev.review_id
            if rev_id not in visited_ids:
                visited_ids.add(rev_id)
                nodes[rev_id] = ProvenanceNode(
                    id=rev_id,
                    node_type=ProvenanceNodeType.ANALYST_REVIEW,
                    label=f"Review: {rev.decision} ({rev.analyst_id})",
                    metadata={
                        "decision": rev.decision,
                        "analyst_id": rev.analyst_id,
                        "notes": rev.notes,
                        "confidence_at_review": rev.confidence_at_review,
                        "quality_status_at_review": rev.quality_status_at_review,
                    },
                    timestamp=rev.created_at.isoformat() if rev.created_at else None,
                )
                edges.append(
                    ProvenanceEdge(
                        source=rev_id,
                        target=change_id,
                        edge_type=ProvenanceEdgeType.REVIEWED_BY,
                    )
                )

    def _build_review_lineage(
        self,
        review_id: str,
        nodes: Dict[str, ProvenanceNode],
        edges: List[ProvenanceEdge],
        visited_ids: Set[str],
    ):
        """Constructs lineage originating from an analyst review decision."""
        if review_id in visited_ids:
            return
        visited_ids.add(review_id)

        rev = self.db.query(AnalystReviewRecord).filter(AnalystReviewRecord.review_id == review_id).first()
        if not rev:
            raise NotFoundError(f"Analyst review '{review_id}' not found.")

        nodes[review_id] = ProvenanceNode(
            id=review_id,
            node_type=ProvenanceNodeType.ANALYST_REVIEW,
            label=f"Review: {rev.decision} ({rev.analyst_id})",
            metadata={
                "decision": rev.decision,
                "analyst_id": rev.analyst_id,
                "notes": rev.notes,
                "target_id": rev.target_id,
                "target_type": rev.target_type,
                "confidence_at_review": rev.confidence_at_review,
                "quality_status_at_review": rev.quality_status_at_review,
                "provenance_snapshot": rev.provenance_snapshot,
            },
            timestamp=rev.created_at.isoformat() if rev.created_at else None,
        )

        target_id = rev.target_id
        if rev.target_type == "TILE" or target_id.startswith("scn_"):
            self._build_tile_lineage(target_id, nodes, edges, visited_ids)
            edges.append(
                ProvenanceEdge(
                    source=review_id,
                    target=target_id,
                    edge_type=ProvenanceEdgeType.REVIEWED_BY,
                )
            )
        elif rev.target_type == "CHANGE" or target_id.startswith("chg_") or target_id.startswith("qchg_"):
            self._build_change_lineage(target_id, nodes, edges, visited_ids)
            edges.append(
                ProvenanceEdge(
                    source=review_id,
                    target=target_id,
                    edge_type=ProvenanceEdgeType.REVIEWED_BY,
                )
            )
