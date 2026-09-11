"""Automated Test Suite for AstraTrace Milestone 9: Provenance Graph + Offline Hardening.

SIH 2026 | Problem ID: SIH26227
Validates processing lineage DAG reconstruction, real-time SHA-256 integrity verification,
tamper detection, forensic evidence dossier export, structured audit logging,
air-gapped network isolation, and security input sanitization.
"""
import json
from pathlib import Path
import shutil
import socket
import tempfile
import pytest
from fastapi.testclient import TestClient

from apps.backend.app.core.errors import NotFoundError, ValidationError
from apps.backend.app.db.session import SessionLocal, init_db
from apps.backend.app.main import create_app
from apps.backend.app.models.audit import AuditEventRecord
from apps.backend.app.models.catalog import SceneRecord, TileRecord
from apps.backend.app.schemas.provenance import (
    ProvenanceNodeType,
    VerificationStatus,
)
from apps.backend.app.schemas.review import SubmitReviewRequest, TargetType, ReviewDecision
from apps.backend.app.services.audit.service import AuditService
from apps.backend.app.services.ingestion import calculate_file_sha256
from apps.backend.app.services.provenance.dossier import EvidencePackageService
from apps.backend.app.services.provenance.service import ProvenanceService
from apps.backend.app.services.provenance.verifier import ProvenanceVerifier
from apps.backend.app.services.review.service import AnalystReviewService


@pytest.fixture(scope="module")
def project_root():
    """Resolves project root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "data").is_dir() and (parent / "README.md").is_file():
            return parent
    return current.parents[2]


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    """Initializes all registered database tables."""
    init_db()


@pytest.fixture(scope="module")
def client():
    """FastAPI TestClient with initialized database."""
    init_db()
    app = create_app()
    return TestClient(app)


@pytest.fixture(scope="module")
def sample_tile_id(project_root):
    """Retrieves an existing sample tile ID from database."""
    with SessionLocal() as db:
        tile = db.query(TileRecord).first()
        assert tile is not None, "At least one tile must exist in catalog for verification."
        return tile.tile_id


# ==============================================================================
# 1. PROVENANCE GRAPH (DAG) TESTS
# ==============================================================================

def test_provenance_graph_tile_dag(project_root, sample_tile_id):
    """Verifies that a Tile target produces an upstream Scene and downstream quality/embedding nodes."""
    with SessionLocal() as db:
        service = ProvenanceService(db=db, project_root=project_root)
        graph = service.get_provenance_graph(sample_tile_id)

    assert graph.root_id == sample_tile_id
    assert graph.root_type == "TILE"
    assert len(graph.nodes) >= 3  # TILE, SCENE, QUALITY_ASSESSMENT (and EMBEDDING if present)
    assert len(graph.edges) >= 2

    node_types = {n.node_type for n in graph.nodes}
    assert ProvenanceNodeType.TILE in node_types
    assert ProvenanceNodeType.SCENE in node_types
    assert ProvenanceNodeType.QUALITY_ASSESSMENT in node_types

    edge_types = {e.edge_type.value for e in graph.edges}
    assert "DERIVED_FROM" in edge_types
    assert "EVALUATED_BY" in edge_types


def test_provenance_graph_scene_dag(project_root):
    """Verifies that a Scene target produces a DAG containing all its child tiles."""
    with SessionLocal() as db:
        scene = db.query(SceneRecord).first()
        assert scene is not None

        service = ProvenanceService(db=db, project_root=project_root)
        graph = service.get_provenance_graph(scene.scene_id)

    assert graph.root_id == scene.scene_id
    assert graph.root_type == "SCENE"
    assert len(graph.nodes) >= 1 + len(scene.tiles)
    assert graph.summary["total_nodes"] == len(graph.nodes)


def test_provenance_graph_review_lineage(project_root, sample_tile_id):
    """Verifies that an Analyst Review produces a DAG connecting review to target tile and scene."""
    with SessionLocal() as db:
        review_service = AnalystReviewService(db=db, project_root=project_root)
        rev_resp = review_service.submit_decision(
            SubmitReviewRequest(
                target_id=sample_tile_id,
                target_type=TargetType.TILE,
                decision=ReviewDecision.CONFIRMED,
                analyst_id="analyst_provenance_tester",
                notes="Verified clear sector for tactical reconnaissance",
            )
        )

        prov_service = ProvenanceService(db=db, project_root=project_root)
        graph = prov_service.get_provenance_graph(rev_resp.review_id)

    assert graph.root_id == rev_resp.review_id
    assert graph.root_type == "ANALYST_REVIEW"
    node_ids = {n.id for n in graph.nodes}
    assert rev_resp.review_id in node_ids
    assert sample_tile_id in node_ids


def test_provenance_graph_not_found(project_root):
    """Verifies that querying a non-existent entity raises NotFoundError."""
    with SessionLocal() as db:
        service = ProvenanceService(db=db, project_root=project_root)
        with pytest.raises(NotFoundError):
            service.get_provenance_graph("nonexistent_entity_id_99999")


# ==============================================================================
# 2. CRYPTOGRAPHIC INTEGRITY & TAMPER DETECTION TESTS
# ==============================================================================

def test_integrity_verification_verified(project_root, sample_tile_id):
    """Verifies that unaltered on-disk artifacts pass cryptographic verification with status VERIFIED."""
    with SessionLocal() as db:
        verifier = ProvenanceVerifier(db=db, project_root=project_root)
        report = verifier.verify_target(sample_tile_id)

    assert report.target_id == sample_tile_id
    assert report.target_type == "TILE"
    assert report.overall_status == VerificationStatus.VERIFIED
    assert report.verified_count > 0
    assert report.tampered_count == 0
    assert report.missing_count == 0
    assert report.execution_ms > 0


def test_integrity_verification_tamper_detection(project_root):
    """CRITICAL TEST: Deliberately alters an artifact and verifies that ProvenanceVerifier detects TAMPERED."""
    test_tampered_id = "scn_test_tampered_tile_t9999"
    with SessionLocal() as db:
        # Pre-cleanup
        db.query(TileRecord).filter(TileRecord.tile_id == test_tampered_id).delete()
        db.commit()

        # Create a temporary clone tile record to test tampering safely
        original_tile = db.query(TileRecord).first()
        assert original_tile is not None

        # Create temporary file with altered bytes
        orig_file = (project_root / original_tile.path).resolve()
        assert orig_file.exists()

        temp_dir = Path(tempfile.mkdtemp())
        try:
            tampered_file = temp_dir / "tampered_tile.tif"
            shutil.copyfile(orig_file, tampered_file)

            # Modify 4 bytes in the file
            with open(tampered_file, "r+b") as f:
                f.seek(10)
                f.write(b"\xFF\xFE\xFD\xFC")

            # Check with a dummy TileRecord pointing to tampered file but expecting original checksum
            fake_tile = TileRecord(
                tile_id=test_tampered_id,
                scene_id=original_tile.scene_id,
                tile_index=9999,
                path=str(tampered_file.relative_to(project_root)).replace("\\", "/") if str(tampered_file).startswith(str(project_root)) else str(tampered_file),
                min_lon=original_tile.min_lon,
                min_lat=original_tile.min_lat,
                max_lon=original_tile.max_lon,
                max_lat=original_tile.max_lat,
                geom=original_tile.geom,
                col_off=0,
                row_off=0,
                width=256,
                height=256,
                cloud_cover_percent=0.0,
                nodata_percent=0.0,
                checksum=original_tile.checksum,  # Expects original checksum, but file was altered!
            )
            db.add(fake_tile)
            db.commit()

            verifier = ProvenanceVerifier(db=db, project_root=project_root)
            report = verifier.verify_target(test_tampered_id)

            assert report.overall_status == VerificationStatus.TAMPERED
            assert report.tampered_count >= 1
        finally:
            with SessionLocal() as cleanup_db:
                cleanup_db.query(TileRecord).filter(TileRecord.tile_id == test_tampered_id).delete()
                cleanup_db.commit()
            shutil.rmtree(temp_dir, ignore_errors=True)


def test_integrity_verification_missing_artifact(project_root):
    """Verifies that an artifact pointing to a non-existent file reports UNVERIFIED_MISSING."""
    with SessionLocal() as db:
        verifier = ProvenanceVerifier(db=db, project_root=project_root)

        # 1. Test missing change mask file
        report_chg = verifier.verify_target("chg_test_missing_mask_9999")
        assert report_chg.overall_status == VerificationStatus.UNVERIFIED_MISSING
        assert report_chg.missing_count >= 1

        # 2. Test missing tile raster file
        test_missing_id = "scn_test_missing_tile_t8888"
        db.query(TileRecord).filter(TileRecord.tile_id == test_missing_id).delete()
        db.commit()

        try:
            fake_tile = TileRecord(
                tile_id=test_missing_id,
                scene_id=db.query(SceneRecord).first().scene_id,
                tile_index=8888,
                path="data/processed/nonexistent_directory/missing_tile.tif",
                min_lon=73.0,
                min_lat=18.0,
                max_lon=73.1,
                max_lat=18.1,
                geom="POLYGON((73 18, 73.1 18, 73.1 18.1, 73 18.1, 73 18))",
                col_off=0,
                row_off=0,
                width=256,
                height=256,
                cloud_cover_percent=0.0,
                nodata_percent=0.0,
                checksum="0000000000000000000000000000000000000000000000000000000000000000",
            )
            db.add(fake_tile)
            db.commit()

            report_tile = verifier.verify_target(test_missing_id)
            assert report_tile.missing_count >= 1
            missing_items = [a for a in report_tile.artifacts if a.status == VerificationStatus.UNVERIFIED_MISSING]
            assert len(missing_items) >= 1
            assert missing_items[0].artifact_type == "TILE_GEOTIFF"
        finally:
            with SessionLocal() as cleanup_db:
                cleanup_db.query(TileRecord).filter(TileRecord.tile_id == test_missing_id).delete()
                cleanup_db.commit()


# ==============================================================================
# 3. FORENSIC EVIDENCE DOSSIER EXPORT TESTS
# ==============================================================================

def test_evidence_dossier_export(project_root, sample_tile_id):
    """Verifies that EvidencePackageService compiles a tamper-proof forensic JSON dossier."""
    with SessionLocal() as db:
        service = EvidencePackageService(db=db, project_root=project_root)
        export_res = service.export_dossier(sample_tile_id, actor="analyst_test_lead")

    assert export_res.export_id.startswith("exp_")
    assert export_res.target_id == sample_tile_id
    assert export_res.package_size_bytes > 0
    assert len(export_res.package_checksum) == 64

    # Verify exported file exists and SHA-256 matches
    export_file = (project_root / export_res.package_path).resolve()
    assert export_file.exists()
    computed_sha = calculate_file_sha256(export_file)
    assert computed_sha == export_res.package_checksum

    # Validate dossier contents
    with open(export_file, "r", encoding="utf-8") as f:
        dossier = json.load(f)

    assert dossier["mission_profile"]["air_gapped_mode"] is True
    assert dossier["mission_profile"]["problem_id"] == "SIH26227"
    assert "provenance_graph" in dossier
    assert "integrity_verification" in dossier
    assert dossier["integrity_verification"]["overall_status"] == "VERIFIED"


# ==============================================================================
# 4. STRUCTURED AUDIT LOGGING TESTS
# ==============================================================================

def test_structured_audit_logging():
    """Verifies append-oriented event logging, filtering, and retrieval."""
    with SessionLocal() as db:
        service = AuditService(db=db)
        rec = service.log_event(
            event_type="TEST_EVENT",
            actor="analyst_unit_tester",
            action="EXECUTE_SECURITY_SCAN",
            target_id="test_target_alpha",
            target_type="TILE",
            status="SUCCESS",
            details={"scan_parameters": "strict_mode"},
        )

        assert rec.event_id.startswith("evt_")
        assert rec.event_type == "TEST_EVENT"

        # Query back
        total, events = service.query_events(
            event_type="TEST_EVENT",
            actor="analyst_unit_tester",
            limit=10,
        )
        assert total >= 1
        found = any(e.event_id == rec.event_id for e in events)
        assert found is True


# ==============================================================================
# 5. REST API ENDPOINT TESTS
# ==============================================================================

def test_api_get_provenance_graph(client, sample_tile_id):
    """Verifies GET /api/v1/provenance/graph/{target_id}."""
    resp = client.get(f"/api/v1/provenance/graph/{sample_tile_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["root_id"] == sample_tile_id
    assert len(data["nodes"]) > 0
    assert len(data["edges"]) > 0


def test_api_post_verify_integrity(client, sample_tile_id):
    """Verifies POST /api/v1/provenance/verify."""
    resp = client.post(
        "/api/v1/provenance/verify",
        json={"target_id": sample_tile_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["overall_status"] == "VERIFIED"
    assert data["verified_count"] > 0


def test_api_get_export_dossier(client, sample_tile_id):
    """Verifies GET /api/v1/provenance/export/{target_id}."""
    resp = client.get(f"/api/v1/provenance/export/{sample_tile_id}")
    assert resp.status_code == 201
    data = resp.json()
    assert "export_id" in data
    assert "package_checksum" in data
    assert data["package_size_bytes"] > 0


def test_api_query_audit_log(client):
    """Verifies GET /api/v1/provenance/audit-log."""
    resp = client.get("/api/v1/provenance/audit-log?limit=5")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "events" in data
    assert isinstance(data["events"], list)


def test_api_security_path_traversal_rejection(client):
    """Verifies that path traversal attacks on provenance endpoints are rejected with 400, 404, or 422."""
    resp = client.get("/api/v1/provenance/graph/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code in [400, 404, 422]

    resp_verify = client.post(
        "/api/v1/provenance/verify",
        json={"target_id": "../../etc/shadow"},
    )
    assert resp_verify.status_code in [400, 404, 422]


# ==============================================================================
# 6. AIR-GAPPED NETWORK ISOLATION TEST (STRICT ZERO REMOTE SOCKET CALLS)
# ==============================================================================

def test_airgap_network_isolation(monkeypatch, client, sample_tile_id):
    """CRITICAL DEFENCE INVARIANT: Blocks all outbound socket connections and ensures
    full pipeline functions in 100% air-gapped isolation without external network calls.
    """
    original_connect = socket.socket.connect

    def blocked_connect(self, address):
        host, port = address[0], address[1]
        # Allow loopback/localhost only if needed by in-process testclient
        if str(host) in ("127.0.0.1", "localhost", "::1"):
            return original_connect(self, address)
        raise RuntimeError(
            f"AIR-GAP VIOLATION: AstraTrace attempted outbound network call to {host}:{port} "
            f"in offline mode! All external connections are strictly forbidden."
        )

    monkeypatch.setattr(socket.socket, "connect", blocked_connect)

    # 1. Test Ingestion Manifest Check
    manifest_res = client.get(f"/api/v1/ingest/manifest/scn_sentinel-2_20230115_96ed9480")
    assert manifest_res.status_code == 200

    # 2. Test Baseline Keyword Search
    kw_res = client.post(
        "/api/v1/search/unified",
        json={"query": "forest vegetation", "search_mode": "KEYWORD", "top_k": 3},
    )
    assert kw_res.status_code == 200

    # 3. Test Semantic Vector Search (Deterministic Offline Embedding)
    sem_res = client.post(
        "/api/v1/search/unified",
        json={"query": "industrial facility", "search_mode": "SEMANTIC", "top_k": 3},
    )
    assert sem_res.status_code == 200

    # 4. Test Provenance Graph Retrieval
    prov_res = client.get(f"/api/v1/provenance/graph/{sample_tile_id}")
    assert prov_res.status_code == 200

    # 5. Test Cryptographic Verification
    verify_res = client.post(
        "/api/v1/provenance/verify",
        json={"target_id": sample_tile_id},
    )
    assert verify_res.status_code == 200

    # 6. Test Dossier Export
    export_res = client.get(f"/api/v1/provenance/export/{sample_tile_id}")
    assert export_res.status_code == 201

    # 7. Test Audit Log Query
    audit_res = client.get("/api/v1/provenance/audit-log?limit=5")
    assert audit_res.status_code == 200

    # If this test passed with the monkeypatch in place, zero outbound network calls were made!
