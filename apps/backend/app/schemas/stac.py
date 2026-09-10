"""STAC-compatible metadata models for AstraTrace.

SIH 2026 | Problem ID: SIH26227
Implements a STAC-compatible internal metadata representation for Collections and Items.
"""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class STACLink(BaseModel):
    """Link structure in STAC specification."""
    rel: str
    href: str
    type: Optional[str] = None
    title: Optional[str] = None


class STACAsset(BaseModel):
    """Asset object representing a file resource in STAC."""
    href: str
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    roles: Optional[List[str]] = None
    properties: Optional[Dict[str, Any]] = None


class STACItem(BaseModel):
    """STAC Item representation (GeoJSON Feature with STAC fields)."""
    type: str = "Feature"
    stac_version: str = "1.0.0"
    stac_extensions: List[str] = Field(
        default_factory=lambda: [
            "https://stac-extensions.github.io/eo/v1.1.0/schema.json",
            "https://stac-extensions.github.io/file/v2.1.0/schema.json",
        ]
    )
    id: str
    collection: str
    geometry: Dict[str, Any]
    bbox: List[float]
    properties: Dict[str, Any]
    assets: Dict[str, STACAsset]
    links: List[STACLink]


class STACExtentSpatial(BaseModel):
    bbox: List[List[float]]


class STACExtentTemporal(BaseModel):
    interval: List[List[Optional[str]]]


class STACExtent(BaseModel):
    spatial: STACExtentSpatial
    temporal: STACExtentTemporal


class STACCollection(BaseModel):
    """STAC Collection representation."""
    type: str = "Collection"
    stac_version: str = "1.0.0"
    id: str
    title: str
    description: str
    license: str = "proprietary"
    extent: STACExtent
    links: List[STACLink]
    summaries: Optional[Dict[str, Any]] = None


class STACCollectionList(BaseModel):
    """List of available STAC Collections."""
    collections: List[STACCollection]
    links: List[STACLink]
