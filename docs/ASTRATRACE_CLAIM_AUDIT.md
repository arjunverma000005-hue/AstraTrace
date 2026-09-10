# AstraTrace — Master Technical Claim Audit & Verification
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Rigorous Scientific & Engineering Claim Audit  
**Status:** AUDIT COMPLETED & BASELINED

---

## 1. Audit Taxonomy & Evaluation Criteria

To prevent academic dishonesty, exaggerated capability assertions, and misleading benchmark claims, every numerical metric, hardware requirement, model classification, and system feature referenced in AstraTrace documentation is audited against five explicit categories:

- **[A] Published Result from Original Cited Source:** External empirical benchmark achieved by the original researchers in peer-reviewed literature or official technical reports on standard benchmark datasets. *(Under no circumstances may this be claimed as an AstraTrace measurement).*
- **[B] Independently Verified AstraTrace Benchmark:** Empirically measured by the AstraTrace engineering team on local hardware using reproducible test scripts and held-out validation sets.
- **[C] Engineering Estimate:** Calculated feasibility projection derived from architectural analysis, computational complexity, memory bandwidth, and operational constraints.
- **[D] Planned Target:** Aspirational operational requirement or design objective to be experimentally evaluated and verified during Milestone 12 benchmarking.
- **[E] Unsupported / Must Remove or Rephrase:** Unverified, misleading, ungrounded, or premature assertion that must be corrected or excised from official project materials.

---

## 2. Comprehensive Claim Audit Table

```
┌────┬─────────────────────────────────────────────────┬──────┬────────────────────────────────────────────────────────┐
│ ID │ Claim / Stated Metric                           │ Cat  │ Audit Determination & Rephrasing Guidance              │
├────┼─────────────────────────────────────────────────┼──────┼────────────────────────────────────────────────────────┤
│ 01 │ ChangeFormer achieves 90.4% F1                  │ [A]  │ Published result from Bandara & Patel (IGARSS 2022) on │
│    │                                                 │      │ LEVIR-CD benchmark. NOT an AstraTrace measurement.     │
│ 02 │ RemoteCLIP zero-shot retrieval accuracy         │ [A]  │ Published result from Chen et al. (IEEE TGRS 2024) on  │
│    │                                                 │      │ RSICD/RSITMD datasets. NOT an AstraTrace measurement.  │
│ 03 │ EuroSAT contains 27,000 Sentinel-2 patches      │ [A]  │ Published specification of the public EuroSAT dataset. │
│ 04 │ BigEarthNet contains 590,326 bimodal patches    │ [A]  │ Published specification of the BigEarthNet benchmark.  │
│ 05 │ Metadata query p95 latency < 300 ms             │ [D]  │ Planned engineering target for PostgreSQL/PostGIS.     │
│ 06 │ Vector search p95 latency < 1.5 seconds         │ [D]  │ Planned engineering target for pgvector HNSW index.    │
│ 07 │ Single-tile change inference < 5s on GPU        │ [C]  │ Engineering estimate based on ChangeFormer FLOPs.      │
│ 08 │ Single-tile change inference < 20s on CPU       │ [C]  │ Engineering estimate based on PyTorch x86 CPU run.     │
│ 09 │ Incremental tile indexing < 10s per tile (GPU)  │ [C]  │ Engineering estimate covering tiling + embedding.      │
│ 10 │ Offline startup time < 60 seconds               │ [D]  │ Planned target for Docker Compose container init.      │
│ 11 │ Retrieval Recall@10 ≥ 0.70                      │ [D]  │ Planned target on AstraTrace held-out evaluation set.  │
│ 12 │ Change detection F1 ≥ 0.70                      │ [D]  │ Planned target on held-out public/synthetic set.       │
│ 13 │ False-alarm reduction ≥ 25% vs baseline diff    │ [D]  │ Planned target on curated Nuisance Challenge Set.      │
│ 14 │ Provenance completeness = 100%                  │ [D]  │ Planned target; mandatory architectural invariant.     │
│ 15 │ Offline external network requests = ZERO        │ [D]  │ Planned target; enforced via Docker network isolation. │
│ 16 │ Demonstration archive size = 1,000–10,000 tiles │ [D]  │ Planned target for hackathon demonstration dataset.    │
│ 17 │ Minimum hardware: 16 GB RAM                     │ [C]  │ Engineering estimate for host OS + Docker + Postgres.  │
│ 18 │ Minimum GPU VRAM: 4 GB (optional, recommended)  │ [C]  │ Engineering estimate to host RemoteCLIP ViT-B/32.       │
│ 19 │ Local SLM query parser latency < 500 ms (GPU)   │ [C]  │ Engineering estimate for Qwen2.5-7B GGUF Q4_K_M.       │
│ 20 │ Expected Calibration Error (ECE) ≤ 0.08         │ [D]  │ Planned target for reliability calibration.            │
│ 21 │ "AstraTrace is a production-ready enterprise"   │ [E]  │ UNSUPPORTED. Rephrased to: "AstraTrace is an           │
│    │                                                 │      │ operational prototype architecture for SIH 2026."     │
│ 22 │ "AstraTrace detects underground activities"     │ [E]  │ UNSUPPORTED / FALSE. Satellite sensors observe surface │
│    │                                                 │      │ features only. Explicitly denied in documentation.     │
│ 23 │ "AstraTrace autonomously retrains in production"│ [E]  │ UNSUPPORTED / PROHIBITED. Self-improvement is strictly │
│    │                                                 │      │ offline, gated, and requires human approval.           │
└────┴─────────────────────────────────────────────────┴──────┴────────────────────────────────────────────────────────┘
```

---

## 3. Mandatory Presentation & Defense Language Rules

1. **Rule on External Benchmarks:**
   - *Forbidden:* "AstraTrace delivers 90.4% change detection accuracy."
   - *Mandatory Phrasing:* "AstraTrace integrates ChangeFormer, which achieved 90.4% F1 on the public LEVIR-CD benchmark in published literature. Our local AstraTrace prototype targets an F1 score $\ge 0.70$ on our held-out test scenes."

2. **Rule on Semantic Retrieval:**
   - *Forbidden:* "Our retrieval model has proven 100% zero-shot recall on Indian terrain."
   - *Mandatory Phrasing:* "AstraTrace utilizes RemoteCLIP, a foundation model pretrained on 824k remote-sensing pairs. We evaluate its retrieval performance locally targeting Recall@10 $\ge 0.70$."

3. **Rule on False-Alarm Suppression:**
   - *Forbidden:* "AstraTrace completely eliminates all false alarms from clouds."
   - *Mandatory Phrasing:* "AstraTrace introduces a quality-gated suppression layer targeting a 25% or greater reduction in false-positive change alerts compared to raw spectral differencing across nuisance scenes."

4. **Rule on System Status:**
   - *Forbidden:* "The platform is fully deployed and running in the cloud."
   - *Mandatory Phrasing:* "AstraTrace is an offline-first, sovereign architecture packaged via Docker Compose, validated locally with network egress disabled."
