"""AstraTrace Benchmark Evaluation Schemas.

SIH 2026 | Problem ID: SIH26227
Pydantic schemas representing quantitative evaluation metrics across retrieval,
change detection, quality gate false-alarm suppression, provenance verification,
and system latency / air-gap isolation.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class RetrievalMethodMetrics(BaseModel):
    """Evaluation metrics for a single retrieval modality."""
    mean_precision_at_k: float = Field(..., ge=0.0, le=1.0, description="Mean Precision@K across queries")
    mean_recall_at_k: float = Field(..., ge=0.0, le=1.0, description="Mean Recall@K across queries")
    mean_mrr: float = Field(..., ge=0.0, le=1.0, description="Mean Reciprocal Rank")
    mean_ndcg_at_k: float = Field(..., ge=0.0, le=1.0, description="Mean Normalized Discounted Cumulative Gain at K")
    mean_latency_ms: float = Field(..., ge=0.0, description="Average query execution latency in milliseconds")


class RetrievalBenchmarkSummary(BaseModel):
    """Comparative retrieval benchmark summary across modalities."""
    queries_evaluated: int = Field(..., ge=1, description="Total ground-truth queries evaluated")
    top_k: int = Field(..., ge=1, description="Top-K cutoff applied")
    baseline: RetrievalMethodMetrics = Field(..., description="Baseline keyword + spectral classifier metrics")
    semantic: RetrievalMethodMetrics = Field(..., description="512-D semantic cosine vector search metrics")
    hybrid: RetrievalMethodMetrics = Field(..., description="Hybrid blended search metrics")


class ChangeScenarioMetric(BaseModel):
    """Evaluation metrics for a single change detection scenario."""
    scenario_name: str = Field(..., description="Descriptive scenario name")
    baseline_changed_pixels: int = Field(..., ge=0, description="Changed pixels detected by baseline detector")
    gated_changed_pixels: int = Field(..., ge=0, description="Changed pixels detected by quality-gated detector")
    suppressed_pixels: int = Field(..., ge=0, description="Pixels suppressed by quality gate")
    decision: str = Field(..., description="Quality gate decision (e.g. QUALITY_PASSED, QUALITY_SUPPRESSED, UNCERTAIN)")
    gated_confidence: float = Field(..., ge=0.0, le=1.0, description="Calibrated gated confidence score")
    false_alarm_reduction_rate: float = Field(..., ge=0.0, le=100.0, description="False Alarm Reduction Rate percentage")


class ChangeBenchmarkSummary(BaseModel):
    """Change detection and false-alarm suppression benchmark summary."""
    scenarios: List[ChangeScenarioMetric] = Field(..., description="Per-scenario evaluation metrics")
    true_positive_preservation_pct: float = Field(..., ge=0.0, le=100.0, description="Percentage of true change preserved")
    false_alarm_suppression_pct: float = Field(..., ge=0.0, le=100.0, description="Percentage of environmental false alarms suppressed")
    otsu_stability_passed: bool = Field(..., description="Whether adaptive Otsu thresholds remained within [0.15, 0.65]")


class QualityGateBenchmarkSummary(BaseModel):
    """Quality gate operational metrics."""
    cloud_rejection_accuracy: float = Field(..., ge=0.0, le=1.0, description="Accuracy in suppressing cloud artifacts")
    shadow_rejection_accuracy: float = Field(..., ge=0.0, le=1.0, description="Accuracy in suppressing shadow artifacts")
    nodata_abstention_accuracy: float = Field(..., ge=0.0, le=1.0, description="Accuracy in abstaining on severe NoData")


class ProvenanceBenchmarkSummary(BaseModel):
    """Cryptographic provenance and audit verification metrics."""
    verified_artifacts: int = Field(..., ge=0, description="Count of cryptographically verified artifacts")
    tampered_artifacts_detected: int = Field(..., ge=0, description="Count of tampered artifacts successfully flagged")
    missing_artifacts: int = Field(..., ge=0, description="Count of missing catalog references detected")
    mean_verification_latency_ms: float = Field(..., ge=0.0, description="Mean SHA-256 streaming verification latency in ms")
    dag_node_count: int = Field(..., ge=1, description="Nodes in reference lineage DAG")
    dag_edge_count: int = Field(..., ge=0, description="Edges in reference lineage DAG")
    dossier_export_valid: bool = Field(..., description="Whether forensic evidence dossier generated with valid SHA-256 seal")


class SystemLatencyBenchmarkSummary(BaseModel):
    """System-level throughput and security invariant metrics."""
    mean_query_latency_ms: float = Field(..., ge=0.0, description="Mean unified search latency in ms")
    p95_query_latency_ms: float = Field(..., ge=0.0, description="p95 unified search latency in ms")
    evidence_first_completeness_pct: float = Field(..., ge=0.0, le=100.0, description="Percentage of candidates possessing all 8 intelligence dimensions")
    airgap_isolation_verified: bool = Field(..., description="Whether strict 0 outbound network egress was confirmed")


class BenchmarkRunReport(BaseModel):
    """Top-level benchmark evaluation report."""
    report_id: str = Field(..., description="Unique benchmark execution report identifier")
    timestamp: datetime = Field(..., description="UTC execution timestamp")
    duration_seconds: float = Field(..., ge=0.0, description="Total evaluation run duration in seconds")
    platform: str = Field(..., description="Execution host platform information")
    offline_mode: bool = Field(..., description="Air-gapped offline mode status")
    retrieval: RetrievalBenchmarkSummary = Field(..., description="Information retrieval benchmarks")
    change_detection: ChangeBenchmarkSummary = Field(..., description="Change detection & false-alarm benchmarks")
    quality_gate: QualityGateBenchmarkSummary = Field(..., description="Quality gate operational benchmarks")
    provenance: ProvenanceBenchmarkSummary = Field(..., description="Provenance & cryptographic benchmarks")
    system: SystemLatencyBenchmarkSummary = Field(..., description="System throughput & air-gap benchmarks")
    all_benchmarks_passed: bool = Field(..., description="Overall mission evaluation pass status")
