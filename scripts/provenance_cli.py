#!/usr/bin/env python3
"""AstraTrace Provenance & Offline Integrity CLI.

SIH 2026 | Problem ID: SIH26227
Command-line utility for inspecting the provenance Directed Acyclic Graph (DAG),
verifying cryptographic file integrity, generating forensic evidence dossiers,
and querying the append-oriented operational audit log.
"""
import argparse
import json
from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.db.session import SessionLocal
from apps.backend.app.services.audit.service import AuditService
from apps.backend.app.services.provenance.dossier import EvidencePackageService
from apps.backend.app.services.provenance.service import ProvenanceService
from apps.backend.app.services.provenance.verifier import ProvenanceVerifier


def parse_args():
    parser = argparse.ArgumentParser(
        description="AstraTrace Provenance Graph & Cryptographic Integrity CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--graph", type=str, metavar="TARGET_ID", help="Inspect provenance lineage DAG for target ID")
    action_group.add_argument("--verify", type=str, metavar="TARGET_ID", help="Verify cryptographic SHA-256 integrity for target ID")
    action_group.add_argument("--export", type=str, metavar="TARGET_ID", help="Export forensic evidence dossier for target ID")
    action_group.add_argument("--audit", action="store_true", help="Query structured operational audit log")

    # Options for --export
    parser.add_argument("--output", type=str, default=None, help="Custom file path for exported dossier JSON")
    parser.add_argument("--actor", type=str, default="analyst_terminal", help="Actor identity for audit records")

    # Options for --audit
    parser.add_argument("--type", type=str, default=None, help="Filter audit events by event type (e.g. REVIEW, VERIFY, CHANGE)")
    parser.add_argument("--status", type=str, default=None, help="Filter audit events by status (SUCCESS, TAMPERED, etc.)")
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of records to display")
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset")

    # General
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON payload")

    return parser.parse_args()


def handle_graph(target_id: str, as_json: bool):
    with SessionLocal() as db:
        service = ProvenanceService(db=db, project_root=PROJECT_ROOT)
        graph = service.get_provenance_graph(target_id)

    if as_json:
        print(graph.model_dump_json(indent=2))
        return

    print("=" * 80)
    print(f"ASTRATRACE PROVENANCE GRAPH: {graph.root_id} ({graph.root_type})")
    print("=" * 80)
    print(f"Total Nodes: {len(graph.nodes)} | Total Edges: {len(graph.edges)}")
    print("-" * 80)
    print("NODES:")
    for n in graph.nodes:
        chk = f" [SHA-256: {n.checksum[:10]}...]" if n.checksum else ""
        print(f"  • [{n.node_type.value:18}] {n.id:<45} {n.label}{chk}")

    print("\nEDGES (Dependency & Derivation):")
    for e in graph.edges:
        meta_str = f" ({e.metadata})" if e.metadata else ""
        print(f"  • {e.source} --[{e.edge_type.value}]--> {e.target}{meta_str}")
    print("=" * 80)


def handle_verify(target_id: str, as_json: bool):
    with SessionLocal() as db:
        verifier = ProvenanceVerifier(db=db, project_root=PROJECT_ROOT)
        report = verifier.verify_target(target_id)

    if as_json:
        print(report.model_dump_json(indent=2))
        return

    status_color = "\033[92m" if report.overall_status.value == "VERIFIED" else "\033[91m"
    reset_color = "\033[0m"

    print("=" * 85)
    print(f"ASTRATRACE CRYPTOGRAPHIC INTEGRITY REPORT: {report.target_id} ({report.target_type})")
    print("=" * 85)
    print(
        f"Overall Status: {status_color}{report.overall_status.value}{reset_color} | "
        f"Verified: {report.verified_count}/{report.total_artifacts} | "
        f"Tampered: {report.tampered_count} | Missing: {report.missing_count} | "
        f"Latency: {report.execution_ms:.1f}ms"
    )
    print("-" * 85)
    print(f"{'Artifact ID':<35} {'Type':<22} {'Status':<12} {'Details'}")
    print("-" * 85)
    for a in report.artifacts:
        col = "\033[92m" if a.status.value == "VERIFIED" else "\033[91m"
        print(f"{a.artifact_id:<35} {a.artifact_type:<22} {col}{a.status.value:<12}{reset_color} {a.details or ''}")
    print("=" * 85)


def handle_export(target_id: str, output_path: Optional[str], actor: str, as_json: bool):
    with SessionLocal() as db:
        service = EvidencePackageService(db=db, project_root=PROJECT_ROOT)
        out_p = Path(output_path) if output_path else None
        res = service.export_dossier(target_id, output_path=out_p, actor=actor)

    if as_json:
        print(res.model_dump_json(indent=2))
        return

    print("=" * 80)
    print("ASTRATRACE FORENSIC EVIDENCE DOSSIER EXPORTED")
    print("=" * 80)
    print(f"Export ID:     {res.export_id}")
    print(f"Target Entity: {res.target_id} ({res.target_type})")
    print(f"Package Path:  {res.package_path}")
    print(f"Package Size:  {res.package_size_bytes} bytes")
    print(f"SHA-256 Hash:  {res.package_checksum}")
    print(f"Timestamp:     {res.exported_at}")
    print(f"Summary:       {res.contents_summary}")
    print("=" * 80)


def handle_audit(event_type: Optional[str], status: Optional[str], limit: int, offset: int, as_json: bool):
    with SessionLocal() as db:
        service = AuditService(db=db)
        total, events = service.query_events(
            event_type=event_type,
            status=status,
            limit=limit,
            offset=offset,
        )

    if as_json:
        payload = {
            "total": total,
            "limit": limit,
            "offset": offset,
            "events": [e.to_dict() for e in events],
        }
        print(json.dumps(payload, indent=2))
        return

    print("=" * 95)
    print(f"ASTRATRACE OPERATIONAL AUDIT LOG (Total: {total}, Showing: {len(events)})")
    print("=" * 95)
    print(f"{'Event ID':<18} {'Type':<18} {'Actor':<18} {'Target ID':<25} {'Status':<10} {'Created'}")
    print("-" * 95)
    for e in events:
        col = "\033[92m" if e.status == "SUCCESS" else ("\033[91m" if e.status == "TAMPERED" else "\033[93m")
        reset = "\033[0m"
        dt_str = e.created_at.strftime("%Y-%m-%d %H:%M:%S") if e.created_at else "N/A"
        print(f"{e.event_id:<18} {e.event_type:<18} {e.actor:<18} {e.target_id:<25} {col}{e.status:<10}{reset} {dt_str}")
    print("=" * 95)


def main():
    args = parse_args()
    if args.graph:
        handle_graph(args.graph, args.json)
    elif args.verify:
        handle_verify(args.verify, args.json)
    elif args.export:
        handle_export(args.export, args.output, args.actor, args.json)
    elif args.audit:
        handle_audit(args.type, args.status, args.limit, args.offset, args.json)


if __name__ == "__main__":
    main()
