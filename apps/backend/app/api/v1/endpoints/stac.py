"""STAC-compatible metadata API endpoints for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Implements a STAC-compatible internal representation of Collections and Items.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from apps.backend.app.core.errors import NotFoundError
from apps.backend.app.db.session import get_db
from apps.backend.app.services.catalog import CatalogService

router = APIRouter(prefix="/stac", tags=["stac"])


@router.get(
    "",
    summary="STAC Root Landing Page",
    description="Returns the root catalog landing page following the STAC specification format."
)
def stac_root() -> Dict[str, Any]:
    """Root STAC catalog definition."""
    return {
        "stac_version": "1.0.0",
        "type": "Catalog",
        "id": "astratrace-catalog",
        "title": "AstraTrace Offline Satellite Catalog",
        "description": "Offline geospatial intelligence metadata catalog for multi-temporal satellite imagery.",
        "conformsTo": [
            "https://api.stacspec.org/v1.0.0/core",
            "https://api.stacspec.org/v1.0.0/collections",
            "https://api.stacspec.org/v1.0.0/ogcapi-features",
        ],
        "links": [
            {"rel": "self", "href": "/api/v1/stac", "type": "application/json"},
            {"rel": "root", "href": "/api/v1/stac", "type": "application/json"},
            {"rel": "data", "href": "/api/v1/stac/collections", "type": "application/json"},
        ],
    }


@router.get(
    "/collections",
    summary="List STAC Collections",
    description="Returns the list of available collections in the catalog."
)
def list_stac_collections(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns available STAC collections."""
    service = CatalogService(db=db)
    collections = service.get_collections_summary()
    return {
        "collections": collections,
        "links": [
            {"rel": "self", "href": "/api/v1/stac/collections"},
            {"rel": "root", "href": "/api/v1/stac"},
        ],
    }


@router.get(
    "/collections/{collection_id}",
    summary="Get STAC Collection",
    description="Returns metadata for a specific STAC collection."
)
def get_stac_collection(collection_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns collection metadata."""
    service = CatalogService(db=db)
    collections = service.get_collections_summary()
    for col in collections:
        if col["id"] == collection_id:
            return col
    raise NotFoundError(f"STAC collection not found: {collection_id}")


@router.get(
    "/collections/{collection_id}/items",
    summary="Query STAC Items in Collection",
    description="Returns STAC Item GeoJSON Features belonging to the specified collection."
)
def get_stac_collection_items(
    collection_id: str,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Returns ItemCollection for the requested collection."""
    service = CatalogService(db=db)
    total, scenes = service.query_scenes(collection=collection_id, limit=limit, offset=offset)
    features = [s.to_stac_item() for s in scenes]
    return {
        "type": "FeatureCollection",
        "features": features,
        "numberMatched": total,
        "numberReturned": len(features),
        "links": [
            {"rel": "self", "href": f"/api/v1/stac/collections/{collection_id}/items"},
            {"rel": "collection", "href": f"/api/v1/stac/collections/{collection_id}"},
            {"rel": "root", "href": "/api/v1/stac"},
        ],
    }


@router.get(
    "/collections/{collection_id}/items/{item_id}",
    summary="Get STAC Item",
    description="Returns a single STAC Item GeoJSON Feature by its scene ID."
)
def get_stac_item(collection_id: str, item_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Returns single STAC Item."""
    service = CatalogService(db=db)
    scene = service.get_scene(item_id)
    if scene.collection != collection_id:
        raise NotFoundError(f"Item '{item_id}' not found in collection '{collection_id}'.")
    return scene.to_stac_item()
