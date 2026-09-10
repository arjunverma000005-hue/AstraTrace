"""AstraTrace Retrieval Evaluation Engine.

SIH 2026 | Problem ID: SIH26227
Empirically benchmarks and compares Baseline Retrieval vs. Semantic Retrieval
vs. Hybrid Retrieval using information-retrieval metrics (Precision@K, Recall@K,
Mean Reciprocal Rank, and nDCG@K).
"""
import math
from pathlib import Path
import time
from typing import Any, Dict, List, Optional
import numpy as np

from apps.backend.app.schemas.search import BaselineSearchRequest
from apps.backend.app.schemas.semantic import SemanticSearchRequest
from apps.backend.app.services.retrieval.service import BaselineRetrievalService
from apps.backend.app.services.retrieval.semantic_service import SemanticRetrievalService


# Canonical ground-truth test evaluation queries mapped to actual synthetic scene concepts
EVALUATION_GROUND_TRUTH = [
    {
        "query": "industrial warehouse storage",
        "expected_tile_ids": [
            "scn_sentinel-2_20241222_7acad713_t0001",
            "scn_sentinel-2_20241222_7acad713_t0004",
        ],
        "category": "Industrial",
    },
    {
        "query": "mountain forest vegetation",
        "expected_tile_ids": [
            "scn_sentinel-2_20230115_96ed9480_t0000",
            "scn_sentinel-2_20241222_7acad713_t0000",
            "scn_sentinel-2_20230115_96ed9480_t0002",
        ],
        "category": "Forest",
    },
    {
        "query": "transportation highway road",
        "expected_tile_ids": [
            "scn_sentinel-2_20230115_96ed9480_t0003",
            "scn_sentinel-2_20241222_7acad713_t0003",
        ],
        "category": "Highway",
    },
    {
        "query": "water stream river basin",
        "expected_tile_ids": [
            "scn_sentinel-2_20230115_96ed9480_t0006",
            "scn_sentinel-2_20241222_7acad713_t0006",
        ],
        "category": "River",
    },
]


def compute_precision_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Computes Precision@K: fraction of retrieved top-k items that are relevant."""
    if k <= 0:
        return 0.0
    top_k = retrieved_ids[:k]
    rel_set = set(relevant_ids)
    hits = sum(1 for tid in top_k if tid in rel_set)
    return round(hits / float(k), 4)


def compute_recall_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Computes Recall@K: fraction of all relevant items retrieved in top-k."""
    if not relevant_ids:
        return 0.0
    top_k = retrieved_ids[:k]
    rel_set = set(relevant_ids)
    hits = sum(1 for tid in top_k if tid in rel_set)
    return round(hits / float(len(relevant_ids)), 4)


def compute_mrr(retrieved_ids: List[str], relevant_ids: List[str]) -> float:
    """Computes Mean Reciprocal Rank: 1 / rank of the first relevant result."""
    rel_set = set(relevant_ids)
    for rank, tid in enumerate(retrieved_ids, start=1):
        if tid in rel_set:
            return round(1.0 / rank, 4)
    return 0.0


def compute_ndcg_at_k(retrieved_ids: List[str], relevant_ids: List[str], k: int) -> float:
    """Computes Normalized Discounted Cumulative Gain (nDCG@K) binary relevance."""
    if k <= 0 or not relevant_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    rel_set = set(relevant_ids)

    # DCG
    dcg = 0.0
    for i, tid in enumerate(top_k):
        rel = 1.0 if tid in rel_set else 0.0
        dcg += rel / math.log2(i + 2)

    # Ideal DCG
    ideal_hits = min(k, len(relevant_ids))
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))

    if idcg <= 0.0:
        return 0.0
    return round(dcg / idcg, 4)


class RetrievalEvaluator:
    """Evaluates and compares Baseline, Semantic, and Hybrid retrieval methods."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()

    def evaluate_all(self, k: int = 5) -> Dict[str, Any]:
        """Runs comparative evaluation suite across all benchmark queries."""
        baseline_results: List[Dict[str, Any]] = []
        semantic_results: List[Dict[str, Any]] = []
        hybrid_results: List[Dict[str, Any]] = []

        with (
            BaselineRetrievalService(project_root=self.project_root) as base_service,
            SemanticRetrievalService(project_root=self.project_root) as sem_service,
        ):
            # Ensure index is built
            sem_service.index_catalog_tiles()

            for item in EVALUATION_GROUND_TRUTH:
                q = item["query"]
                relevant = item["expected_tile_ids"]

                # 1. Evaluate Baseline
                t_b0 = time.perf_counter()
                b_resp = base_service.search(BaselineSearchRequest(query=q, top_k=k))
                b_lat = round((time.perf_counter() - t_b0) * 1000.0, 2)
                b_ids = [r.tile_id for r in b_resp.results]

                baseline_results.append({
                    "query": q,
                    "precision_at_k": compute_precision_at_k(b_ids, relevant, k),
                    "recall_at_k": compute_recall_at_k(b_ids, relevant, k),
                    "mrr": compute_mrr(b_ids, relevant),
                    "ndcg_at_k": compute_ndcg_at_k(b_ids, relevant, k),
                    "latency_ms": b_lat,
                    "top_retrieved": b_ids[:3],
                })

                # 2. Evaluate Pure Semantic (hybrid_weight=1.0)
                t_s0 = time.perf_counter()
                s_resp = sem_service.search_semantic(
                    SemanticSearchRequest(query=q, top_k=k, hybrid_weight=1.0)
                )
                s_lat = round((time.perf_counter() - t_s0) * 1000.0, 2)
                s_ids = [r.tile_id for r in s_resp.results]

                semantic_results.append({
                    "query": q,
                    "precision_at_k": compute_precision_at_k(s_ids, relevant, k),
                    "recall_at_k": compute_recall_at_k(s_ids, relevant, k),
                    "mrr": compute_mrr(s_ids, relevant),
                    "ndcg_at_k": compute_ndcg_at_k(s_ids, relevant, k),
                    "latency_ms": s_lat,
                    "top_retrieved": s_ids[:3],
                })

                # 3. Evaluate Hybrid (hybrid_weight=0.65)
                t_h0 = time.perf_counter()
                h_resp = sem_service.search_semantic(
                    SemanticSearchRequest(query=q, top_k=k, hybrid_weight=0.65)
                )
                h_lat = round((time.perf_counter() - t_h0) * 1000.0, 2)
                h_ids = [r.tile_id for r in h_resp.results]

                hybrid_results.append({
                    "query": q,
                    "precision_at_k": compute_precision_at_k(h_ids, relevant, k),
                    "recall_at_k": compute_recall_at_k(h_ids, relevant, k),
                    "mrr": compute_mrr(h_ids, relevant),
                    "ndcg_at_k": compute_ndcg_at_k(h_ids, relevant, k),
                    "latency_ms": h_lat,
                    "top_retrieved": h_ids[:3],
                })

        # Macro averages
        def macro_avg(metric_key: str, data: List[Dict[str, Any]]) -> float:
            return round(float(np.mean([d[metric_key] for d in data])), 4)

        summary = {
            "evaluation_k": k,
            "queries_evaluated": len(EVALUATION_GROUND_TRUTH),
            "baseline": {
                "mean_precision_at_k": macro_avg("precision_at_k", baseline_results),
                "mean_recall_at_k": macro_avg("recall_at_k", baseline_results),
                "mean_mrr": macro_avg("mrr", baseline_results),
                "mean_ndcg_at_k": macro_avg("ndcg_at_k", baseline_results),
                "mean_latency_ms": macro_avg("latency_ms", baseline_results),
            },
            "semantic": {
                "mean_precision_at_k": macro_avg("precision_at_k", semantic_results),
                "mean_recall_at_k": macro_avg("recall_at_k", semantic_results),
                "mean_mrr": macro_avg("mrr", semantic_results),
                "mean_ndcg_at_k": macro_avg("ndcg_at_k", semantic_results),
                "mean_latency_ms": macro_avg("latency_ms", semantic_results),
            },
            "hybrid": {
                "mean_precision_at_k": macro_avg("precision_at_k", hybrid_results),
                "mean_recall_at_k": macro_avg("recall_at_k", hybrid_results),
                "mean_mrr": macro_avg("mrr", hybrid_results),
                "mean_ndcg_at_k": macro_avg("ndcg_at_k", hybrid_results),
                "mean_latency_ms": macro_avg("latency_ms", hybrid_results),
            },
            "detailed_queries": {
                "baseline": baseline_results,
                "semantic": semantic_results,
                "hybrid": hybrid_results,
            },
        }

        return summary
