"""Pydantic schemas for AstraTrace Provenance Graph and Integrity Verification.

SIH 2026 | Problem ID: SIH26227
Defines the Directed Acyclic Graph (DAG) structures, integrity verification
reports, and forensic evidence package exports.
"""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProvenanceNodeType(str, Enum):
    """Types of provenance lineage nodes."""
    SCENE = "SCENE"
    TILE = "TILE"
    EMBEDDING = "EMBEDDING"
    RETRIEVAL_QUERY = "RETRIEVAL_QUERY"
    CHANGE_EVENT = "CHANGE_EVENT"
    QUALITY_ASSESSMENT = "QUALITY_ASSESSMENT"
    ANALYST_REVIEW = "ANALYST_REVIEW"
    EVIDENCE_PACKAGE = "EVIDENCE_PACKAGE"


class ProvenanceEdgeType(str, Enum):
    """Types of directed relationships connecting lineage nodes."""
    DERIVED_FROM = "DERIVED_FROM"
    INDEXED_BY = "INDEXED_BY"
    EVALUATED_BY = "EVALUATED_BY"
    DETECTED_FROM = "DETECTED_FROM"
    MATCHED_BY = "MATCHED_BY"
    REVIEWED_BY = "REVIEWED_BY"
    PACKAGED_INTO = "PACKAGED_INTO"


class ProvenanceNode(BaseModel):
    """An individual entity or process node in the provenance graph."""
    id: str = Field(..., description="Unique identifier of the lineage entity")
    node_type: ProvenanceNodeType = Field(..., description="Entity category in the processing chain")
    label: str = Field(..., description="Human-readable summary label")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Detailed domain metadata")
    checksum: Optional[str] = Field(None, description="SHA-256 integrity hash where applicable")
    timestamp: Optional[str] = Field(None, description="ISO 8601 acquisition or creation timestamp")


class ProvenanceEdge(BaseModel):
    """A directed dependency or derivation relationship between two nodes."""
    source: str = Field(..., description="Originating node ID (e.g. child/derived entity)")
    target: str = Field(..., description="Target node ID (e.g. parent/source entity)")
    edge_type: ProvenanceEdgeType = Field(..., description="Nature of the dependency")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional transition attributes")


class ProvenanceGraphResponse(BaseModel):
    """Complete Directed Acyclic Graph (DAG) for an analytical target."""
    root_id: str = Field(..., description="Target entity ID requested for lineage")
    root_type: str = Field(..., description="Entity type of the requested root")
    nodes: List[ProvenanceNode] = Field(..., description="Lineage nodes in the graph")
    edges: List[ProvenanceEdge] = Field(..., description="Directed edges connecting nodes")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Aggregate summary of nodes and depth")


class VerificationStatus(str, Enum):
    """Cryptographic verification status of an artifact or entire target."""
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPERED"
    UNVERIFIED_MISSING = "UNVERIFIED_MISSING"


class ArtifactVerificationItem(BaseModel):
    """Verification result for a specific on-disk artifact."""
    artifact_id: str = Field(..., description="Unique artifact name or identifier")
    artifact_type: str = Field(..., description="Artifact category (e.g. RAW_SCENE, TILE_TIFF, MASK_PNG, MANIFEST)")
    file_path: str = Field(..., description="Relative or absolute path to the file")
    recorded_checksum: str = Field(..., description="SHA-256 checksum recorded in catalog or manifest")
    computed_checksum: Optional[str] = Field(None, description="Real-time computed SHA-256 hash")
    status: VerificationStatus = Field(..., description="Verification outcome")
    details: Optional[str] = Field(None, description="Diagnostic notes or mismatch reason")


class IntegrityVerificationRequest(BaseModel):
    """Request to verify the integrity of a target entity or specific file paths."""
    target_id: Optional[str] = Field(None, description="Tile ID, Scene ID, or Change ID to verify")
    file_paths: Optional[List[str]] = Field(None, description="Explicit file paths to check against catalog")


class IntegrityVerificationResponse(BaseModel):
    """Full cryptographic integrity report for a target and all its dependencies."""
    target_id: str = Field(..., description="Target entity verified")
    target_type: str = Field(..., description="Type of target verified")
    overall_status: VerificationStatus = Field(..., description="Aggregate status (TAMPERED > MISSING > VERIFIED)")
    total_artifacts: int = Field(..., description="Count of evaluated artifacts")
    verified_count: int = Field(..., description="Number of artifacts with matching hashes")
    tampered_count: int = Field(..., description="Number of altered or corrupted artifacts")
    missing_count: int = Field(..., description="Number of referenced artifacts missing on disk")
    artifacts: List[ArtifactVerificationItem] = Field(..., description="Detailed per-file verification records")
    verified_at: str = Field(..., description="ISO 8601 timestamp of verification execution")
    execution_ms: float = Field(..., description="Elapsed verification latency in milliseconds")


class EvidencePackageExportResponse(BaseModel):
    """Forensic evidence dossier export result."""
    export_id: str = Field(..., description="Unique export identifier")
    target_id: str = Field(..., description="Entity packaged into the dossier")
    target_type: str = Field(..., description="Entity type")
    package_path: str = Field(..., description="Relative path to the generated dossier file")
    package_checksum: str = Field(..., description="SHA-256 checksum of the entire export package")
    package_size_bytes: int = Field(..., description="Total size of the dossier file in bytes")
    exported_at: str = Field(..., description="ISO 8601 timestamp of export")
    contents_summary: Dict[str, Any] = Field(default_factory=dict, description="Summary of bundled evidence")
