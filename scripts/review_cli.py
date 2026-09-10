#!/usr/bin/env python3
"""AstraTrace Analyst Review Queue CLI.

SIH 2026 | Problem ID: SIH26227
Command-line utility for operational analysts to inspect the review queue,
examine evidence-first candidate dossiers, and record auditable review decisions.
All decisions are recorded immutably without triggering model fine-tuning or retraining.
"""
import argparse
import json
from pathlib import Path
import sys
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.db.session import SessionLocal
from apps.backend.app.schemas.review import (
    ReviewDecision,
    SubmitReviewRequest,
    TargetType,
)
from apps.backend.app.services.review.service import AnalystReviewService


def parse_args():
    parser = argparse.ArgumentParser(
        description="AstraTrace Analyst Review Queue & Triage CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    action_group = parser.add_mutually_exclusive_group(required=True)
    action_group.add_argument("--list", action="store_true", help="List items in the review queue")
    action_group.add_argument("--inspect", type=str, metavar="TARGET_ID", help="Inspect evidence for target ID")
    action_group.add_argument("--decide", type=str, metavar="TARGET_ID", help="Submit a review decision for target ID")
    action_group.add_argument("--history", type=str, metavar="TARGET_ID", help="View decision history for target ID")

    # Options for --list
    parser.add_argument(
        "--status",
        type=str,
        choices=["PENDING_REVIEW", "CONFIRMED", "REJECTED", "FLAGGED_FOR_INSPECTION"],
        default=None,
        help="Filter queue items by decision status",
    )
    parser.add_argument("--limit", type=int, default=20, help="Maximum number of items to display")
    parser.add_argument("--offset", type=int, default=0, help="Pagination offset")

    # Options for --decide
    parser.add_argument(
        "--decision",
        type=str,
        choices=["CONFIRMED", "REJECTED", "FLAGGED_FOR_INSPECTION"],
        help="Decision to record (required with --decide)",
    )
    parser.add_argument("--analyst", type=str, default="analyst_terminal", help="Analyst identifier")
    parser.add_argument("--notes", type=str, default="", help="Operational rationale or observations")
    parser.add_argument(
        "--target-type",
        type=str,
        choices=["TILE", "CHANGE_EVENT"],
        default="TILE",
        help="Type of target being reviewed",
    )

    # General
    parser.add_argument("--json", action="store_true", help="Output machine-readable JSON payload")

    return parser.parse_args()


def handle_list(service: AnalystReviewService, status: Optional[str], limit: int, offset: int, as_json: bool):
    status_filter = ReviewDecision(status) if status else None
    queue = service.get_queue(status_filter=status_filter, limit=limit, offset=offset)

    if as_json:
        print(queue.model_dump_json(indent=2))
        return

    print("=" * 80)
    print("ASTRATRACE ANALYST REVIEW QUEUE")
    print(f"Summary: Pending={queue.pending_count} | Confirmed={queue.confirmed_count} | "
          f"Rejected={queue.rejected_count} | Flagged={queue.flagged_count} | Total={queue.total}")
    print("=" * 80)
    print(f"{'TARGET ID':<26} {'STATUS':<24} {'CONF':<7} {'ACQUIRED':<16} {'WHAT'}")
    print("-" * 80)

    for item in queue.items:
        stat = item.review_status.value
        conf_str = f"{item.confidence:.2f}"
        when_str = item.when[:10] if item.when else "N/A"
        what_str = item.what[:28] if item.what else "Observation"
        print(f"{item.target_id:<26} {stat:<24} {conf_str:<7} {when_str:<16} {what_str}")

    print("=" * 80)


def handle_inspect(service: AnalystReviewService, target_id: str, as_json: bool):
    queue = service.get_queue(limit=500)
    matched_item = next((it for it in queue.items if it.target_id == target_id), None)
    history = service.get_history(target_id)

    if as_json:
        payload = {
            "queue_item": matched_item.model_dump() if matched_item else None,
            "history": history.model_dump(),
        }
        print(json.dumps(payload, indent=2))
        return

    if not matched_item:
        print(f"[-] Target '{target_id}' not found in current queue.")
        return

    print("=" * 70)
    print(f"EVIDENCE DOSSIER: {matched_item.target_id}")
    print("=" * 70)
    print(f"WHAT:            {matched_item.what}")
    print(f"WHERE (CRS):     {matched_item.where.get('crs', 'N/A')}")
    print(f"WHERE (BBOX):    {matched_item.where.get('bbox')}")
    print(f"WHEN:            {matched_item.when}")
    print(f"CONFIDENCE:      {matched_item.confidence:.4f}")
    print(f"QUALITY STATUS:  {matched_item.quality_status}")
    print(f"QUALITY FLAGS:   {', '.join(matched_item.quality_flags) if matched_item.quality_flags else 'None'}")
    print(f"LATEST DECISION: {matched_item.review_status.value}")

    print("\nPROVENANCE:")
    for k, v in matched_item.provenance.items():
        print(f"  - {k}: {v}")

    print("\nAUDIT HISTORY:")
    if not history.history:
        print("  (No reviews recorded yet)")
    else:
        for rev in history.history:
            print(f"  [{rev.created_at}] {rev.decision.value} by {rev.analyst_id} - Notes: {rev.notes or 'None'}")
    print("=" * 70)


def handle_decide(service: AnalystReviewService, target_id: str, decision_str: Optional[str],
                  analyst_id: str, notes: str, target_type_str: str, as_json: bool):
    if not decision_str:
        print("[-] Error: --decision is required when using --decide")
        sys.exit(1)

    req = SubmitReviewRequest(
        target_id=target_id,
        target_type=TargetType(target_type_str),
        decision=ReviewDecision(decision_str),
        analyst_id=analyst_id,
        notes=notes if notes else None,
    )
    result = service.submit_decision(req)

    if as_json:
        print(result.model_dump_json(indent=2))
        return

    print("=" * 60)
    print("ANALYST DECISION RECORDED SUCCESSFULLY")
    print("=" * 60)
    print(f"Review ID:       {result.review_id}")
    print(f"Target ID:       {result.target_id}")
    print(f"Decision:        {result.decision.value}")
    print(f"Analyst:         {result.analyst_id}")
    print(f"Timestamp:       {result.created_at}")
    print(f"Confidence Snap: {result.confidence_at_review}")
    print(f"Quality Snap:    {result.quality_status_at_review}")
    print(f"Notes:           {result.notes or 'None'}")
    print("=" * 60)


def handle_history(service: AnalystReviewService, target_id: str, as_json: bool):
    history = service.get_history(target_id)
    if as_json:
        print(history.model_dump_json(indent=2))
        return

    print("=" * 70)
    print(f"DECISION AUDIT TRAIL: {target_id} (Total: {history.total_reviews})")
    print("=" * 70)
    for rev in history.history:
        print(f"[{rev.created_at}] Review {rev.review_id}: {rev.decision.value} by {rev.analyst_id}")
        if rev.notes:
            print(f"  Notes: {rev.notes}")
        print(f"  Confidence at review: {rev.confidence_at_review} | Quality: {rev.quality_status_at_review}")
    print("=" * 70)


def main():
    args = parse_args()

    db = SessionLocal()
    try:
        service = AnalystReviewService(db=db, project_root=PROJECT_ROOT)

        if args.list:
            handle_list(service, args.status, args.limit, args.offset, args.json)
        elif args.inspect:
            handle_inspect(service, args.inspect, args.json)
        elif args.decide:
            handle_decide(service, args.decide, args.decision, args.analyst, args.notes, args.target_type, args.json)
        elif args.history:
            handle_history(service, args.history, args.json)
    finally:
        db.close()


if __name__ == "__main__":
    main()
