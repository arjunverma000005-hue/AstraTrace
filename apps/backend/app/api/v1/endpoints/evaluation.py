"""AstraTrace Benchmark Evaluation REST Endpoints.

SIH 2026 | Problem ID: SIH26227
Provides operational endpoints for inspecting live or cached quantitative
evaluation metrics across all AstraTrace subsystems.
"""
from fastapi import APIRouter, HTTPException, Query, status
from apps.backend.app.schemas.evaluation import BenchmarkRunReport
from apps.backend.app.services.evaluation.benchmark_runner import BenchmarkRunnerService

router = APIRouter(prefix="/evaluation", tags=["Automated Evaluation & Benchmarks"])


@router.get(
    "/summary",
    response_model=BenchmarkRunReport,
    summary="Get Evaluation Benchmark Summary",
    description="Retrieves the latest quantitative benchmark evaluation summary report across retrieval, change detection, quality gate, and provenance subsystems."
)
async def get_evaluation_summary(
    force_refresh: bool = Query(False, description="If True, triggers a fresh benchmark run rather than reading cache")
) -> BenchmarkRunReport:
    """Returns the latest quantitative evaluation report."""
    try:
        service = BenchmarkRunnerService()
        if force_refresh:
            return service.run_full_benchmark()
        return service.get_latest_report(run_if_missing=True)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve evaluation summary: {str(e)}",
        )


@router.post(
    "/run",
    response_model=BenchmarkRunReport,
    status_code=status.HTTP_201_CREATED,
    summary="Trigger Automated Benchmark Run",
    description="Executes a complete quantitative benchmark across all subsystems and caches the results."
)
async def trigger_benchmark_run(
    top_k: int = Query(5, ge=1, le=20, description="Top-K cutoff for retrieval metrics")
) -> BenchmarkRunReport:
    """Executes a full benchmark run and returns the structured evaluation report."""
    try:
        service = BenchmarkRunnerService()
        return service.run_full_benchmark(top_k=top_k)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Benchmark execution failed: {str(e)}",
        )
