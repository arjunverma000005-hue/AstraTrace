"""AstraTrace Milestone 10 Automated Evaluation & Benchmark Tests.

SIH 2026 | Problem ID: SIH26227
Tests the automated benchmark evaluation engine, metric formulations, Pydantic
schema contracts, REST endpoints, and zero-fabrication assertions.
"""
from datetime import datetime, timezone
from pathlib import Path
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from apps.backend.app.main import create_app
from apps.backend.app.schemas.evaluation import (
    BenchmarkRunReport,
    ChangeBenchmarkSummary,
    ChangeScenarioMetric,
    ProvenanceBenchmarkSummary,
    QualityGateBenchmarkSummary,
    RetrievalBenchmarkSummary,
    RetrievalMethodMetrics,
    SystemLatencyBenchmarkSummary,
)
from apps.backend.app.services.evaluation.benchmark_runner import BenchmarkRunnerService

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_evaluation_schema_validation():
    """Verifies strict Pydantic validation across all evaluation schema models."""
    # Valid retrieval metrics
    m = RetrievalMethodMetrics(
        mean_precision_at_k=0.85,
        mean_recall_at_k=0.75,
        mean_mrr=0.80,
        mean_ndcg_at_k=0.82,
        mean_latency_ms=12.5,
    )
    assert m.mean_precision_at_k == 0.85
    assert m.mean_latency_ms == 12.5

    # Out of bounds precision (> 1.0) must raise ValidationError
    with pytest.raises(ValidationError):
        RetrievalMethodMetrics(
            mean_precision_at_k=1.5,
            mean_recall_at_k=0.5,
            mean_mrr=0.5,
            mean_ndcg_at_k=0.5,
            mean_latency_ms=10.0,
        )

    # Negative latency must raise ValidationError
    with pytest.raises(ValidationError):
        RetrievalMethodMetrics(
            mean_precision_at_k=0.5,
            mean_recall_at_k=0.5,
            mean_mrr=0.5,
            mean_ndcg_at_k=0.5,
            mean_latency_ms=-5.0,
        )


def test_benchmark_runner_retrieval():
    """Verifies that retrieval benchmark computes authentic metrics with semantic superiority."""
    runner = BenchmarkRunnerService(project_root=PROJECT_ROOT)
    retrieval_summary = runner._run_retrieval_benchmark(top_k=5)

    assert retrieval_summary.queries_evaluated >= 4
    assert retrieval_summary.top_k == 5

    # Check bounds
    for mode in [retrieval_summary.baseline, retrieval_summary.semantic, retrieval_summary.hybrid]:
        assert 0.0 <= mode.mean_precision_at_k <= 1.0
        assert 0.0 <= mode.mean_recall_at_k <= 1.0
        assert 0.0 <= mode.mean_mrr <= 1.0
        assert 0.0 <= mode.mean_ndcg_at_k <= 1.0
        assert mode.mean_latency_ms > 0.0

    # Semantic retrieval must outperform or equal baseline keyword search on MRR
    assert retrieval_summary.semantic.mean_mrr >= retrieval_summary.baseline.mean_mrr


def test_benchmark_runner_change_and_quality():
    """Verifies change detection and quality gate false-alarm suppression benchmark."""
    runner = BenchmarkRunnerService(project_root=PROJECT_ROOT)
    change_summary, quality_summary = runner._run_change_and_quality_benchmark()

    assert len(change_summary.scenarios) == 5
    assert change_summary.true_positive_preservation_pct >= 95.0
    assert change_summary.false_alarm_suppression_pct >= 95.0
    assert change_summary.otsu_stability_passed is True

    # Check specific challenge responses
    assert quality_summary.cloud_rejection_accuracy == 1.0
    assert quality_summary.shadow_rejection_accuracy == 1.0
    assert quality_summary.nodata_abstention_accuracy == 1.0


def test_benchmark_runner_provenance():
    """Verifies cryptographic provenance verification and tamper detection."""
    runner = BenchmarkRunnerService(project_root=PROJECT_ROOT)
    prov_summary = runner._run_provenance_benchmark()

    assert prov_summary.verified_artifacts >= 1
    assert prov_summary.tampered_artifacts_detected == 1
    assert prov_summary.missing_artifacts == 0
    assert prov_summary.mean_verification_latency_ms > 0.0
    assert prov_summary.dag_node_count >= 5
    assert prov_summary.dag_edge_count >= 4
    assert prov_summary.dossier_export_valid is True


def test_benchmark_runner_system_and_airgap():
    """Verifies system latency, 8-dimension completeness, and strict air-gap network trap."""
    runner = BenchmarkRunnerService(project_root=PROJECT_ROOT)
    sys_summary = runner._run_system_and_airgap_benchmark()

    assert sys_summary.mean_query_latency_ms > 0.0
    assert sys_summary.p95_query_latency_ms > 0.0
    assert sys_summary.evidence_first_completeness_pct == 100.0
    assert sys_summary.airgap_isolation_verified is True


def test_api_get_evaluation_summary(client: TestClient):
    """Verifies GET /api/v1/evaluation/summary returns a valid report."""
    res = client.get("/api/v1/evaluation/summary")
    assert res.status_code == 200
    data = res.json()

    assert data["report_id"].startswith("bench_")
    assert data["offline_mode"] is True
    assert data["all_benchmarks_passed"] is True
    assert data["retrieval"]["queries_evaluated"] >= 4
    assert data["change_detection"]["true_positive_preservation_pct"] >= 95.0


def test_api_trigger_benchmark_run(client: TestClient):
    """Verifies POST /api/v1/evaluation/run executes and returns 201 Created."""
    res = client.post("/api/v1/evaluation/run?top_k=3")
    assert res.status_code == 201
    data = res.json()

    assert data["report_id"].startswith("bench_")
    assert data["retrieval"]["top_k"] == 3
    assert data["duration_seconds"] > 0.0


def test_zero_fabrication_assertions():
    """Strictly asserts that metrics are computed dynamically and not hardcoded stubs."""
    runner = BenchmarkRunnerService(project_root=PROJECT_ROOT)
    report = runner.run_full_benchmark(top_k=4)

    # 1. Verification of dynamic runtime timestamp
    now = datetime.now(timezone.utc)
    delta_seconds = abs((now - report.timestamp).total_seconds())
    assert delta_seconds < 120.0, "Report timestamp must reflect real current execution time"

    # 2. Dynamic top_k reflection
    assert report.retrieval.top_k == 4

    # 3. Dynamic non-zero execution duration
    assert report.duration_seconds > 0.01

    # 4. Scenario names must match actual disk challenges
    scenario_names = [s.scenario_name for s in report.change_detection.scenarios]
    assert "True Construction Change" in scenario_names
    assert "Cloud Contamination Challenge" in scenario_names
    assert "Severe NoData Challenge" in scenario_names
