#!/usr/bin/env python3
"""AstraTrace Baseline Retrieval CLI Tool.

SIH 2026 | Problem ID: SIH26227
Performs fast, deterministic baseline search directly from the terminal combining
spatial/temporal SQL filtering, EuroSAT vocabulary parsing, and multispectral scoring.

Usage Examples:
    python scripts/baseline_search.py --query "urban buildings"
    python scripts/baseline_search.py --query "roads near factories" --bbox 73.57 18.94 73.63 18.99 --top-k 5
    python scripts/baseline_search.py --query "dense forest" --json
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.schemas.search import BaselineSearchRequest
from apps.backend.app.services.retrieval.service import BaselineRetrievalService


def main():
    parser = argparse.ArgumentParser(
        description="AstraTrace Baseline Satellite Tile Search CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--query", "-q", required=True, help="Search query (e.g., 'urban buildings', 'forest')")
    parser.add_argument("--bbox", nargs=4, type=float, metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"), help="Spatial bounding box filter (EPSG:4326)")
    parser.add_argument("--point", nargs=2, type=float, metavar=("LON", "LAT"), help="Spatial point coordinate filter")
    parser.add_argument("--date-from", help="Start acquisition timestamp (ISO format, e.g., 2023-01-01)")
    parser.add_argument("--date-to", help="End acquisition timestamp (ISO format, e.g., 2025-01-01)")
    parser.add_argument("--sensor", help="Satellite sensor filter (e.g., SENTINEL-2)")
    parser.add_argument("--top-k", "-k", type=int, default=10, help="Maximum number of ranked results to return")
    parser.add_argument("--min-confidence", "-c", type=float, default=0.0, help="Minimum composite confidence threshold")
    parser.add_argument("--json", action="store_true", help="Output results as raw JSON")

    args = parser.parse_args()

    # Parse timestamps
    date_from_dt = None
    if args.date_from:
        try:
            date_from_dt = datetime.fromisoformat(args.date_from)
        except Exception as e:
            print(f"[ERROR] Invalid --date-from timestamp: {e}", file=sys.stderr)
            sys.exit(1)

    date_to_dt = None
    if args.date_to:
        try:
            date_to_dt = datetime.fromisoformat(args.date_to)
        except Exception as e:
            print(f"[ERROR] Invalid --date-to timestamp: {e}", file=sys.stderr)
            sys.exit(1)

    bbox_tuple = tuple(args.bbox) if args.bbox else None
    point_tuple = tuple(args.point) if args.point else None

    req = BaselineSearchRequest(
        query=args.query,
        bbox=bbox_tuple,
        point=point_tuple,
        date_from=date_from_dt,
        date_to=date_to_dt,
        sensor=args.sensor,
        top_k=args.top_k,
        min_confidence=args.min_confidence,
    )

    try:
        with BaselineRetrievalService(project_root=PROJECT_ROOT) as service:
            response = service.search(req)

        if args.json:
            print(response.model_dump_json(indent=2))
            sys.exit(0)

        # Pretty CLI Table Output
        print("=" * 80)
        print("ASTRATRACE BASELINE RETRIEVAL RESULTS")
        print("=" * 80)
        print(f"Query ID:        {response.query_id}")
        print(f"Query:           '{response.query}'")
        vocab_str = ", ".join(f"{k}: {v:.2f}" for k, v in response.matched_vocabulary.items())
        print(f"Matched Synsets: {vocab_str} {'(OOV Fallback)' if response.is_out_of_vocabulary else ''}")
        print(f"Candidates:      {response.total_candidates} total evaluated -> {response.returned_results} returned")
        trace = response.execution_trace
        print(f"Latency:         Total: {trace['total_ms']:.1f}ms (Parser: {trace['query_parser_ms']:.1f}ms, SQL: {trace['retrieval_ms']:.1f}ms, Scoring: {trace['scoring_ms']:.1f}ms)")
        print("-" * 80)

        if not response.results:
            print("No matching candidate tiles found satisfying the constraints.")
            print("=" * 80)
            sys.exit(0)

        print(f"{'Rank':<5} {'Score':<8} {'Tile ID':<22} {'Top Class':<16} {'Conf':<6} {'Acquired':<12} {'Sensor':<10}")
        print("-" * 80)
        for r in response.results:
            acquired_short = r.acquired_at[:10] if r.acquired_at else "N/A"
            print(
                f"{r.rank:<5} {r.baseline_score:<8.4f} {r.tile_id:<22} "
                f"{r.top_class:<16} {r.top_class_confidence:<6.2f} {acquired_short:<12} {r.sensor:<10}"
            )
            # Show score breakdown
            sb = r.score_breakdown
            print(f"      -> Factors: Class={sb['class_score']:.3f} | Spatial={sb['spatial_score']:.3f} | Temporal={sb['temporal_score']:.3f} | Matched={r.matched_classes}")

        print("=" * 80)
        sys.exit(0)

    except Exception as e:
        print(f"[ERROR] Baseline search failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
