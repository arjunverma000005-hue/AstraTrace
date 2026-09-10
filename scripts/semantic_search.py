#!/usr/bin/env python3
"""AstraTrace Semantic Vector Search CLI.

SIH 2026 | Problem ID: SIH26227
Queries the offline vector store via natural language text or image-to-image similarity.
"""
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.schemas.semantic import SemanticSearchRequest, SimilarTilesRequest
from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService


def main():
    parser = argparse.ArgumentParser(
        description="AstraTrace Semantic Vector Search CLI",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Natural language semantic search query (e.g. 'industrial warehouse')",
    )
    parser.add_argument(
        "--reference-tile",
        type=str,
        help="Catalog Tile ID for image-to-image similarity search ('Find Similar Sites')",
    )
    parser.add_argument(
        "--reference-path",
        type=str,
        help="Direct path to satellite GeoTIFF raster for similarity search",
    )
    parser.add_argument(
        "--bbox",
        nargs=4,
        type=float,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        help="Spatial bounding box filter in WGS-84 coordinates",
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Maximum ranked results to return",
    )
    parser.add_argument(
        "--hybrid-weight", "-w",
        type=float,
        default=0.65,
        help="Alpha weighting (1.0 = pure semantic, 0.0 = pure baseline)",
    )
    parser.add_argument(
        "--min-confidence", "-c",
        type=float,
        default=0.0,
        help="Minimum confidence cutoff [0.0 - 1.0]",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON response",
    )

    args = parser.parse_args()

    if not args.query and not args.reference_tile and not args.reference_path:
        print("\n[ERROR] Must provide either --query or --reference-tile or --reference-path.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    try:
        with SemanticRetrievalService(project_root=PROJECT_ROOT) as service:
            if args.query:
                req = SemanticSearchRequest(
                    query=args.query,
                    bbox=tuple(args.bbox) if args.bbox else None,
                    top_k=args.top_k,
                    hybrid_weight=args.hybrid_weight,
                    min_confidence=args.min_confidence,
                )
                response = service.search_semantic(req)
            else:
                req_sim = SimilarTilesRequest(
                    reference_tile_id=args.reference_tile,
                    reference_raster_path=args.reference_path,
                    bbox=tuple(args.bbox) if args.bbox else None,
                    top_k=args.top_k,
                    min_confidence=args.min_confidence,
                )
                response = service.search_similar_tiles(req_sim)

            if args.json:
                print(response.model_dump_json(indent=2))
                return

            print("=" * 80)
            print(f"ASTRATRACE SEMANTIC RETRIEVAL RESULTS [Mode: {response.search_mode}]")
            print(f"Query ID  : {response.query_id}")
            print(f"Model     : {response.model_info['model_name']} ({response.model_info['dimension']}-D)")
            print(f"Total Hits: {response.returned_results} (from {response.total_indexed} indexed vectors)")
            print(f"Latency   : {response.execution_trace['total_ms']:.1f} ms "
                  f"(Encode: {response.execution_trace['encode_ms']:.1f}ms, ANN: {response.execution_trace['ann_ms']:.1f}ms)")
            print("=" * 80)

            if not response.results:
                print("No matching satellite tiles found exceeding confidence threshold.")
                return

            header = f"{'Rank':<5} {'Tile ID':<42} {'Hybrid':<8} {'Semantic':<9} {'Base':<8} {'Sensor':<10}"
            print(header)
            print("-" * 80)
            for res in response.results:
                base_str = f"{res.baseline_score:.4f}" if res.baseline_score is not None else "N/A"
                print(
                    f"{res.rank:<5} "
                    f"{res.tile_id:<42} "
                    f"{res.hybrid_score:<8.4f} "
                    f"{res.semantic_score:<9.4f} "
                    f"{base_str:<8} "
                    f"{res.sensor:<10}"
                )
            print("=" * 80)

    except Exception as e:
        print(f"\n[ERROR] Semantic search failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
