#!/usr/bin/env python3
"""AstraTrace Retrieval Evaluation Benchmark CLI.

SIH 2026 | Problem ID: SIH26227
Compares Baseline vs. Semantic vs. Hybrid retrieval across Precision@K, Recall@K,
Mean Reciprocal Rank (MRR), and nDCG@K on ground-truth benchmark queries.
"""
import argparse
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from apps.backend.app.services.retrieval.evaluator import RetrievalEvaluator


def main():
    parser = argparse.ArgumentParser(
        description="AstraTrace Retrieval Evaluation Benchmark",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--top-k", "-k",
        type=int,
        default=5,
        help="Top-K cutoff for evaluation metrics",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON benchmark summary",
    )

    args = parser.parse_args()

    try:
        evaluator = RetrievalEvaluator(project_root=PROJECT_ROOT)
        print(f"[*] Running comparative evaluation on ground-truth queries (K={args.top_k})...")
        summary = evaluator.evaluate_all(k=args.top_k)

        if args.json:
            print(json.dumps(summary, indent=2))
            return

        print("=" * 80)
        print("ASTRATRACE RETRIEVAL BENCHMARK: BASELINE vs. SEMANTIC vs. HYBRID")
        print("=" * 80)
        print(f"{'Method':<12} {'Precision@K':<14} {'Recall@K':<12} {'MRR':<10} {'nDCG@K':<10} {'Latency':<10}")
        print("-" * 80)

        for mode in ["baseline", "semantic", "hybrid"]:
            m = summary[mode]
            print(
                f"{mode.upper():<12} "
                f"{m['mean_precision_at_k']:<14.4f} "
                f"{m['mean_recall_at_k']:<12.4f} "
                f"{m['mean_mrr']:<10.4f} "
                f"{m['mean_ndcg_at_k']:<10.4f} "
                f"{m['mean_latency_ms']:<8.1f}ms"
            )
        print("=" * 80)
        print(f"Queries Evaluated: {summary['queries_evaluated']}")
        print("[SUCCESS] Comparative evaluation completed without synthetic overreach.")

    except Exception as e:
        print(f"\n[ERROR] Evaluation benchmark failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
