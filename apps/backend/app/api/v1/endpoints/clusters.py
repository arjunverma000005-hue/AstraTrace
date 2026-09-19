"""API endpoints for AstraTrace Unsupervised Discovery & Clustering.

SIH 2026 | Problem ID: SIH26227
Provides discovery clustering, representative scene identification, and semantic tagging.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.backend.app.db.session import get_db
from apps.backend.app.services.clustering.service import ClusteringService

router = APIRouter(prefix="/clusters", tags=["clusters"])


@router.get(
    "",
    response_model=List[Dict[str, Any]],
    status_code=status.HTTP_200_OK,
    summary="List Discovery Clusters",
    description="Returns unsupervised semantic clusters with representative scenes, geographic bounds, and dominant tags.",
)
def list_clusters(
    algorithm: str = Query("kmeans", description="Clustering algorithm ('kmeans' or 'dbscan')"),
    n_clusters: int = Query(4, ge=2, le=10, description="Target cluster count"),
    force_recompute: bool = Query(False, description="Whether to recompute clusters"),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Lists or computes discovery clusters."""
    service = ClusteringService(db=db)
    return service.discover_clusters(algorithm=algorithm, n_clusters=n_clusters, force_recompute=force_recompute)


@router.get(
    "/{cluster_id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Get Cluster Details",
    description="Returns metadata, representative tile, and geographic bounds of a specific cluster.",
)
def get_cluster(
    cluster_id: str,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Retrieves metadata for a specific cluster."""
    service = ClusteringService(db=db)
    return service.get_cluster(cluster_id)
