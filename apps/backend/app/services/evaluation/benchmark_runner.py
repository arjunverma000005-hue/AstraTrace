"""AstraTrace Benchmark Evaluation Runner Service.

SIH 2026 | Problem ID: SIH26227
Orchestrates automated, reproducible quantitative evaluation across all core subsystems:
1. Retrieval (Baseline vs. Semantic vs. Hybrid)
2. Bitemporal Change Detection & Quality Gate False-Alarm Suppression
3. Cryptographic Provenance & Lineage DAG Integrity
4. System Latency & Air-Gapped Network Isolation
"""
import math
import os
from pathlib import Path
import platform
import socket
import sys
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import uuid

import numpy as np
import rasterio

from apps.backend.app.config import settings
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
from apps.backend.app.schemas.quality import QualityGatedChangeRequest
from apps.backend.app.schemas.search import UnifiedSearchRequest, SearchMode
from apps.backend.app.services.change.detector import BaselineChangeDetector
from apps.backend.app.services.quality.service import QualityService
from apps.backend.app.services.retrieval.evaluator import RetrievalEvaluator
from apps.backend.app.services.provenance.service import ProvenanceService
from apps.backend.app.services.provenance.verifier import ProvenanceVerifier
from apps.backend.app.services.provenance.dossier import EvidencePackageService
from apps.backend.app.services.ingestion import calculate_file_sha256
from apps.backend.app.services.search.unified_service import UnifiedSearchService
from apps.backend.app.db.session import SessionLocal


class BenchmarkRunnerService:
    """Service providing programmatic and API-driven execution of AstraTrace benchmarks."""

    _cached_report: Optional[BenchmarkRunReport] = None

    def __init__(self, project_root: Optional[Path] = None):
        if project_root is None:
            current = Path(__file__).resolve()
            for parent in current.parents:
                if (parent / "data").is_dir() and (parent / "README.md").is_file():
                    self.project_root = parent
                    break
            else:
                self.project_root = current.parents[5]
        else:
            self.project_root = project_root

    def get_latest_report(self, run_if_missing: bool = True) -> BenchmarkRunReport:
        """Retrieves the latest cached benchmark report or triggers a new run."""
        if self._cached_report is not None:
            return self._cached_report

        # Check on-disk cache
        report_file = self.project_root / "data" / "processed" / "evaluation" / "benchmark_report.json"
        if report_file.exists():
            try:
                import json
                with open(report_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    report = BenchmarkRunReport(**data)
                    self._cached_report = report
                    return report
            except Exception:
                pass

        if run_if_missing:
            return self.run_full_benchmark()
        raise RuntimeError("No cached benchmark report available")

    def run_full_benchmark(self, top_k: int = 5) -> BenchmarkRunReport:
        """Executes the complete end-to-end benchmark suite across all subsystems."""
        start_time = time.perf_counter()
        run_id = f"bench_{uuid.uuid4().hex[:12]}"
        timestamp = datetime.now(timezone.utc)

        # 1. Retrieval Benchmark
        retrieval_summary = self._run_retrieval_benchmark(top_k=top_k)

        # 2. Change Detection & False-Alarm Suppression Benchmark
        change_summary, quality_summary = self._run_change_and_quality_benchmark()

        # 3. Provenance & Cryptographic Verification Benchmark
        provenance_summary = self._run_provenance_benchmark()

        # 4. System Latency, Evidence-First Completeness & Air-Gap Benchmark
        system_summary = self._run_system_and_airgap_benchmark()

        duration = round(time.perf_counter() - start_time, 3)

        # Overall Mission Success Check
        all_passed = (
            retrieval_summary.semantic.mean_mrr >= retrieval_summary.baseline.mean_mrr
            and change_summary.true_positive_preservation_pct >= 95.0
            and change_summary.false_alarm_suppression_pct >= 95.0
            and change_summary.otsu_stability_passed is True
            and provenance_summary.tampered_artifacts_detected >= 1
            and provenance_summary.dossier_export_valid is True
            and system_summary.evidence_first_completeness_pct == 100.0
            and system_summary.airgap_isolation_verified is True
        )

        report = BenchmarkRunReport(
            report_id=run_id,
            timestamp=timestamp,
            duration_seconds=duration,
            platform=f"{platform.system()} {platform.release()} ({platform.machine()})",
            offline_mode=settings.offline_mode,
            retrieval=retrieval_summary,
            change_detection=change_summary,
            quality_gate=quality_summary,
            provenance=provenance_summary,
            system=system_summary,
            all_benchmarks_passed=all_passed,
        )

        # Cache in memory
        self._cached_report = report

        # Persist to disk
        out_dir = self.project_root / "data" / "processed" / "evaluation"
        out_dir.mkdir(parents=True, exist_ok=True)
        report_file = out_dir / "benchmark_report.json"
        with open(report_file, "w", encoding="utf-8") as f:
            f.write(report.model_dump_json(indent=2))

        return report

    def _run_retrieval_benchmark(self, top_k: int) -> RetrievalBenchmarkSummary:
        """Runs the comparative retrieval benchmark."""
        evaluator = RetrievalEvaluator(project_root=self.project_root)
        raw = evaluator.evaluate_all(k=top_k)

        return RetrievalBenchmarkSummary(
            queries_evaluated=raw["queries_evaluated"],
            top_k=top_k,
            baseline=RetrievalMethodMetrics(**raw["baseline"]),
            semantic=RetrievalMethodMetrics(**raw["semantic"]),
            hybrid=RetrievalMethodMetrics(**raw["hybrid"]),
        )

    def _run_change_and_quality_benchmark(self) -> tuple[ChangeBenchmarkSummary, QualityGateBenchmarkSummary]:
        """Runs change detection and false-alarm suppression challenge scenarios."""
        t1_path = self.project_root / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0001.tif"
        t2_path = self.project_root / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0001.tif"
        t0_before = self.project_root / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif"
        t0_after = self.project_root / "data" / "processed" / "scn_sentinel-2_20241222_7acad713" / "tile_0000.tif"

        bench_dir = self.project_root / "data" / "processed" / "benchmark_challenges"
        bench_dir.mkdir(parents=True, exist_ok=True)

        with rasterio.open(t0_after) as src:
            meta = src.meta.copy()
            clean_arr = src.read()

        # Cloud Challenge
        cloud_arr = clean_arr.copy().astype(np.float32)
        cloud_arr[:, 50:130, 50:130] = 5500.0
        cloud_path = bench_dir / "tile_cloud_challenge.tif"
        with rasterio.open(cloud_path, "w", **meta) as dst:
            dst.write(cloud_arr.astype(meta["dtype"]))

        # Shadow Challenge
        shadow_arr = clean_arr.copy().astype(np.float32)
        shadow_arr[:, 140:200, 140:200] = 300.0
        shadow_path = bench_dir / "tile_shadow_challenge.tif"
        with rasterio.open(shadow_path, "w", **meta) as dst:
            dst.write(shadow_arr.astype(meta["dtype"]))

        # NoData Challenge
        nodata_arr = clean_arr.copy()
        nodata_arr[:, :, :220] = 0
        nodata_path = bench_dir / "tile_nodata_challenge.tif"
        with rasterio.open(nodata_path, "w", **meta) as dst:
            dst.write(nodata_arr)

        scenarios = [
            {"name": "True Construction Change", "p1": t1_path, "p2": t2_path, "is_real_change": True},
            {"name": "Clean Negative Control", "p1": t0_before, "p2": t0_after, "is_real_change": False},
            {"name": "Cloud Contamination Challenge", "p1": t0_before, "p2": cloud_path, "is_real_change": False},
            {"name": "Cloud Shadow Challenge", "p1": t0_before, "p2": shadow_path, "is_real_change": False},
            {"name": "Severe NoData Challenge", "p1": t0_before, "p2": nodata_path, "is_real_change": False},
        ]

        baseline_detector = BaselineChangeDetector(project_root=self.project_root)
        quality_service = QualityService(project_root=self.project_root)

        scenario_metrics: List[ChangeScenarioMetric] = []
        true_positive_pixels_baseline = 0
        true_positive_pixels_gated = 0
        nuisance_pixels_baseline = 0
        nuisance_pixels_gated = 0
        otsu_stability = True

        cloud_suppressed = 0
        shadow_suppressed = 0
        nodata_abstained = 0

        with QualityService(project_root=self.project_root) as quality_service:
            for sc in scenarios:
                base_res = baseline_detector.detect_change(
                    t1_path_input=sc["p1"],
                    t2_path_input=sc["p2"],
                    threshold=0.15,
                    min_pixels=10,
                )
                gated_req = QualityGatedChangeRequest(
                    before_tile_path=str(sc["p1"]),
                    after_tile_path=str(sc["p2"]),
                    threshold=0.15,
                    min_pixels=10,
                )
                gated_res = quality_service.detect_gated_change(gated_req)

                base_px = base_res["changed_pixels"]
                gated_px = gated_res.verified_changed_pixels
                suppressed = max(0, base_px - gated_px)

                farr = 0.0
                if base_px > 0:
                    farr = round(((base_px - gated_px) / base_px) * 100.0, 2)

                metric = ChangeScenarioMetric(
                    scenario_name=sc["name"],
                    baseline_changed_pixels=base_px,
                    gated_changed_pixels=gated_px,
                    suppressed_pixels=suppressed,
                    decision=gated_res.decision.value,
                    gated_confidence=gated_res.final_confidence,
                    false_alarm_reduction_rate=farr,
                )
                scenario_metrics.append(metric)

                # Accumulate true vs nuisance metrics
                if sc["is_real_change"]:
                    true_positive_pixels_baseline += base_px
                    true_positive_pixels_gated += gated_px
                else:
                    nuisance_pixels_baseline += base_px
                    nuisance_pixels_gated += gated_px

                # Check Otsu range [0.15, 0.65]
                th = base_res["effective_threshold"]
                if not (0.15 <= th <= 0.65):
                    otsu_stability = False

                # Specific Challenge Checks
                if "Cloud Contamination" in sc["name"] and gated_res.decision.value == "QUALITY_SUPPRESSED":
                    cloud_suppressed = 1
                if "Cloud Shadow" in sc["name"] and gated_res.decision.value == "QUALITY_SUPPRESSED":
                    shadow_suppressed = 1
                if "Severe NoData" in sc["name"] and gated_res.decision.value == "UNCERTAIN":
                    nodata_abstained = 1

        true_pos_pct = 100.0
        if true_positive_pixels_baseline > 0:
            true_pos_pct = round((true_positive_pixels_gated / true_positive_pixels_baseline) * 100.0, 2)

        false_alarm_suppression_pct = 100.0
        if nuisance_pixels_baseline > 0:
            suppressed_total = max(0, nuisance_pixels_baseline - nuisance_pixels_gated)
            false_alarm_suppression_pct = round((suppressed_total / nuisance_pixels_baseline) * 100.0, 2)

        change_summary = ChangeBenchmarkSummary(
            scenarios=scenario_metrics,
            true_positive_preservation_pct=true_pos_pct,
            false_alarm_suppression_pct=false_alarm_suppression_pct,
            otsu_stability_passed=otsu_stability,
        )

        quality_summary = QualityGateBenchmarkSummary(
            cloud_rejection_accuracy=float(cloud_suppressed),
            shadow_rejection_accuracy=float(shadow_suppressed),
            nodata_abstention_accuracy=float(nodata_abstained),
        )

        return change_summary, quality_summary

    def _run_provenance_benchmark(self) -> ProvenanceBenchmarkSummary:
        """Runs the cryptographic provenance and tamper verification benchmark."""
        sample_tile_id = "scn_sentinel-2_20230115_96ed9480_t0000"

        with SessionLocal() as db:
            verifier = ProvenanceVerifier(db=db, project_root=self.project_root)
            ver_report = verifier.verify_target(sample_tile_id)

            # Tamper detection verification
            tamper_file = self.project_root / "data" / "processed" / "benchmark_challenges" / "tamper_test.tif"
            with open(self.project_root / "data" / "processed" / "scn_sentinel-2_20230115_96ed9480" / "tile_0000.tif", "rb") as f:
                content = bytearray(f.read())
            # Corrupt 4 bytes
            content[100:104] = b"\xff\xff\xff\xff"
            with open(tamper_file, "wb") as f:
                f.write(content)

            tamper_detected = 0
            computed_hash = calculate_file_sha256(tamper_file)
            expected_hash = ver_report.artifacts[0].recorded_checksum if ver_report.artifacts else ""
            if computed_hash != expected_hash:
                tamper_detected = 1

            # Lineage DAG inspection
            prov_service = ProvenanceService(db=db, project_root=self.project_root)
            dag = prov_service.get_provenance_graph(sample_tile_id)

            # Dossier export inspection
            dossier_svc = EvidencePackageService(db=db, project_root=self.project_root)
            dossier = dossier_svc.export_dossier(sample_tile_id, actor="eval_benchmark")

        return ProvenanceBenchmarkSummary(
            verified_artifacts=ver_report.verified_count,
            tampered_artifacts_detected=tamper_detected,
            missing_artifacts=ver_report.missing_count,
            mean_verification_latency_ms=ver_report.execution_ms,
            dag_node_count=len(dag.nodes),
            dag_edge_count=len(dag.edges),
            dossier_export_valid=bool(dossier.package_checksum and len(dossier.package_checksum) == 64),
        )

    def _run_system_and_airgap_benchmark(self) -> SystemLatencyBenchmarkSummary:
        """Runs the system query throughput, Evidence-First dimension validation, and air-gap test."""
        latencies = []
        evidence_first_ok = True

        test_queries = [
            ("industrial warehouse logistics", SearchMode.AUTO),
            ("forest mountain vegetation", SearchMode.SEMANTIC),
            ("transportation highway road", SearchMode.HYBRID),
            ("water stream river basin", SearchMode.KEYWORD),
        ]

        with SessionLocal() as db:
            unified_service = UnifiedSearchService(db=db, project_root=self.project_root)

            for q_text, mod in test_queries:
                t0 = time.perf_counter()
                req = UnifiedSearchRequest(
                    query=q_text,
                    search_mode=mod,
                    top_k=5,
                    min_confidence=0.0,
                )
                res = unified_service.search(req)
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                latencies.append(elapsed_ms)

                # Validate 8 Dimensions on top candidates
                for cand in res.results:
                    if not (
                        cand.what
                        and cand.where
                        and cand.which
                        and cand.why
                        and (0.0 <= cand.confidence <= 1.0)
                        and cand.evidence
                        and cand.provenance
                    ):
                        evidence_first_ok = False

        mean_lat = round(float(np.mean(latencies)), 2)
        p95_lat = round(float(np.percentile(latencies, 95)), 2)

        # Air-gap verification via socket monkey patch
        orig_connect = socket.socket.connect
        airgap_passed = False

        def block_external(sock_self, address):
            host = address[0]
            if str(host) in ("127.0.0.1", "localhost", "::1"):
                return orig_connect(sock_self, address)
            raise RuntimeError(f"Air-gap violation: outbound socket to {host}")

        try:
            socket.socket.connect = block_external
            with SessionLocal() as db:
                airgap_service = UnifiedSearchService(db=db, project_root=self.project_root)
                # Execute one complete search under strict air-gap trap
                req_airgap = UnifiedSearchRequest(
                    query="airgap verification query",
                    search_mode=SearchMode.AUTO,
                    top_k=3,
                )
                airgap_service.search(req_airgap)
                airgap_passed = True
        except Exception:
            airgap_passed = False
        finally:
            socket.socket.connect = orig_connect

        return SystemLatencyBenchmarkSummary(
            mean_query_latency_ms=mean_lat,
            p95_query_latency_ms=p95_lat,
            evidence_first_completeness_pct=100.0 if evidence_first_ok else 0.0,
            airgap_isolation_verified=airgap_passed,
        )
