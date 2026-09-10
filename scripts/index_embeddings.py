#!/usr/bin/env python3
"""AstraTrace Offline Vector Embedding Indexing CLI.

SIH 2026 | Problem ID: SIH26227
Batch-indexes satellite tiles from the metadata catalog into 512-dimensional
vector embeddings and persists the local vector index cache.
"""
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService


def main():
    parser = argparse.ArgumentParser(
        description="AstraTrace Vector Embedding Indexer",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--force-reindex",
        action="store_true",
        help="Recompute embeddings for tiles that already have embeddings",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON summary",
    )

    args = parser.parse_args()

    try:
        with SemanticRetrievalService(project_root=PROJECT_ROOT) as service:
            meta = service.model.model_metadata()
            print(f"[*] Initializing Embedding Model: {meta['model_name']} ({meta['dimension']}-D, {meta['operational_mode']})")
            print(f"[*] Indexing catalog tiles (force_reindex={args.force_reindex})...")

            result = service.index_catalog_tiles(force_reindex=args.force_reindex)

            if args.json:
                print(json.dumps(result, indent=2))
            else:
                print("=" * 60)
                print("ASTRATRACE VECTOR INDEXING SUMMARY")
                print("=" * 60)
                print(f" Newly Indexed Tiles : {result['indexed_count']}")
                print(f" Existing (Skipped)  : {result['skipped_count']}")
                print(f" Total Vectors in DB : {result['total_indexed']}")
                print(f" Processing Time     : {result['total_ms']:.1f} ms")
                print("=" * 60)
                print("[SUCCESS] Vector index updated and persisted.")

    except Exception as e:
        print(f"\n[ERROR] Indexing failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
