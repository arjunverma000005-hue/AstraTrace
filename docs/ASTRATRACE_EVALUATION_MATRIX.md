# AstraTrace — Master Evaluation Matrix & Benchmark Protocol
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Quantitative Evaluation Specifications & Benchmark Protocol  
**Status:** APPROVED (All empirical thresholds labeled as PROPOSED EVALUATION THRESHOLD)

---

## 1. Evaluation Protocol & Integrity Standards

To satisfy the rigorous defense requirements of SIH26227, AstraTrace benchmarks every subsystem using explicit mathematical formulations, held-out evaluation datasets, and reproducible test scripts.

### Core Protocol Principles:
1. **No Data Leakage:** Training and test datasets are partitioned by disjoint geographic bounding boxes separated by a minimum 50 km buffer.
2. **Honest Baseline Comparison:** Advanced models are evaluated side-by-side with deterministic baselines (ChangeFormer vs. spectral differencing; RemoteCLIP vs. ResNet-50 keyword lookup).
3. **Transparent Threshold Labeling:** All unmeasured aspirational metrics are explicitly designated as `PROPOSED EVALUATION THRESHOLD`.
4. **Offline Evaluation Execution:** All benchmarks are executed locally via `scripts/run_evaluation.py` with network egress completely disabled.

---

## 2. Golden Evaluation Datasets Manifest

```
┌────────────────────┬──────────────────┬─────────────────────┬────────────────────────────────────────┐
│ Dataset Name       │ Sensor/Modality  │ Primary Task        │ Verification & Ground Truth Status     │
├────────────────────┼──────────────────┼─────────────────────┼────────────────────────────────────────┤
│ EuroSAT            │ Sentinel-2 L2A   │ Semantic Retrieval  │ VERIFIED (Public benchmark, 27k tiles) │
│ BigEarthNet        │ S-1 SAR & S-2 Opt│ Multisensor Baseline│ VERIFIED (Public benchmark, 590k tiles)│
│ LEVIR-CD           │ Optical Bitemp   │ Change Detection    │ VERIFIED (Public benchmark, 637 pairs) │
│ OSCD               │ Sentinel-2 Bitemp│ Urban Change        │ VERIFIED (Public benchmark, 24 scenes) │
│ AstraTrace-Nuisance│ S-1 & S-2 Staged │ False-Alarm Test    │ PLANNED (Synthetic + real clouds/drift)│
│ Golden Query Suite │ Text Queries     │ Query Parser Eval   │ PLANNED (200 curated test prompts)     │
└────────────────────┴──────────────────┴─────────────────────┴────────────────────────────────────────┘
```

---

## 3. Subsystem Evaluation Matrices

### 3.1 Natural Language Query Parsing
Evaluated across 200 curated and edge-case operational prompts:

```
┌──────────────────────────────┬──────────────────┬───────────────────────────────┬────────────────────┐
│ Metric                       │ Evaluation Type  │ Mathematical Definition       │ Evaluation Target  │
├──────────────────────────────┼──────────────────┼───────────────────────────────┼────────────────────┤
│ Schema Validity Rate         │ Deterministic    │ Valid JSON conforming to schema│ 100% (MANDATORY)   │
│ Semantic Concept Accuracy    │ Categorical      │ Target category matches truth │ ≥ 0.90 [PROPOSED]  │
│ Change Type Extraction Acc   │ Categorical      │ Appearance/Disappearance match│ ≥ 0.92 [PROPOSED]  │
│ Temporal Interval Accuracy   │ Date Bounds      │ Exact start/end date overlap  │ ≥ 0.95 [PROPOSED]  │
│ Spatial Context Accuracy     │ Geographic       │ Bounding box / AOI extracted  │ ≥ 0.90 [PROPOSED]  │
│ Ambiguity Detection Rate     │ Abstention       │ Correctly flags vague queries │ ≥ 0.85 [PROPOSED]  │
│ Parser Latency (p95, GPU)    │ System           │ Wall-clock execution time     │ < 500 ms [PROPOSED]│
│ Parser Latency (p95, CPU)    │ System           │ Wall-clock execution time     │ < 2.5 s [PROPOSED] │
└──────────────────────────────┴──────────────────┴───────────────────────────────┴────────────────────┘
```

---

### 3.2 Semantic & Multimodal Retrieval
Evaluated over held-out test scenes using RemoteCLIP (ViT-B/32) vs. ResNet-50 baseline:

```
┌──────────────────────────────┬──────────────────────────────────────────────┬────────────────────────┐
│ Metric                       │ Mathematical Formulation                     │ Proposed Target        │
├──────────────────────────────┼──────────────────────────────────────────────┼────────────────────────┤
│ Recall@1                     │ Relevant in top 1 / Total relevant           │ ≥ 0.35 [PROPOSED]      │
│ Recall@5                     │ Relevant in top 5 / Total relevant           │ ≥ 0.55 [PROPOSED]      │
│ Recall@10                    │ Relevant in top 10 / Total relevant          │ ≥ 0.70 [PROPOSED]      │
│ Recall@20                    │ Relevant in top 20 / Total relevant          │ ≥ 0.82 [PROPOSED]      │
│ Precision@10                 │ Relevant in top 10 / 10                      │ ≥ 0.60 [PROPOSED]      │
│ Mean Reciprocal Rank (MRR)   │ Mean of 1 / rank of first relevant result    │ ≥ 0.65 [PROPOSED]      │
│ nDCG@10                      │ Normalized Discounted Cumulative Gain at 10  │ ≥ 0.72 [PROPOSED]      │
│ Retrieval Latency (p95)      │ pgvector HNSW search duration                │ < 1.5 s [PROPOSED]     │
└──────────────────────────────┴──────────────────────────────────────────────┴────────────────────────┘
```

---

### 3.3 Bitemporal Change Detection
Evaluated on LEVIR-CD and OSCD test splits comparing ChangeFormer-lite against raw spectral differencing:

```
┌──────────────────────────────┬──────────────────────────────────────────────┬────────────────────────┐
│ Metric                       │ Mathematical Formulation                     │ Proposed Target        │
├──────────────────────────────┼──────────────────────────────────────────────┼────────────────────────┤
│ Intersection-over-Union(IoU) │ TP / (TP + FP + FN)                          │ ≥ 0.65 [PROPOSED]      │
│ Change F1-Score              │ 2*TP / (2*TP + FP + FN)                      │ ≥ 0.70 [PROPOSED]      │
│ Change Precision             │ TP / (TP + FP)                               │ ≥ 0.72 [PROPOSED]      │
│ Change Recall                │ TP / (TP + FN)                               │ ≥ 0.68 [PROPOSED]      │
│ False Positive Rate (FPR)    │ FP / (FP + TN)                               │ ≤ 0.05 [PROPOSED]      │
│ Earliest Obs Error (Days)    │ |Estimated Date - True Date|                 │ ≤ 15 days [PROPOSED]   │
│ Single-Tile Inference (GPU)  │ Wall-clock forward pass (256x256 bitemporal) │ < 5.0 s [PROPOSED]     │
│ Single-Tile Inference (CPU)  │ Wall-clock forward pass (256x256 bitemporal) │ < 20.0 s [PROPOSED]    │
└──────────────────────────────┴──────────────────────────────────────────────┴────────────────────────┘
```

---

### 3.4 Quality Gate & False-Alarm Suppression
Evaluated specifically on the AstraTrace Nuisance Challenge Set (severe clouds, shadows, registration shifts, seasonal drying; zero actual construction):

```
┌──────────────────────────────┬──────────────────────────────────────────────┬────────────────────────┐
│ Metric                       │ Mathematical Formulation                     │ Proposed Target        │
├──────────────────────────────┼──────────────────────────────────────────────┼────────────────────────┤
│ False-Alarm Reduction Rate   │ (FP_baseline - FP_gated) / FP_baseline * 100%│ ≥ 25% [PROPOSED]       │
│ Expected Calibration Error   │ Weighted sum of |accuracy - confidence|      │ ≤ 0.08 [PROPOSED]      │
│ Cloud Rejection Accuracy     │ Correct rejection of tiles with >15% cloud   │ ≥ 0.95 [PROPOSED]      │
│ Registration Warning Recall  │ Detection of pairs with >1.0 px shift        │ ≥ 0.90 [PROPOSED]      │
└──────────────────────────────┴──────────────────────────────────────────────┴────────────────────────┘
```

---

### 3.5 Groundedness & Provenance Integrity

```
┌──────────────────────────────┬──────────────────────────────────────────────┬────────────────────────┐
│ Metric                       │ Evaluation Method                            │ Target                 │
├──────────────────────────────┼──────────────────────────────────────────────┼────────────────────────┤
│ Context Groundedness Score   │ Supported Claims / Total Claims Generated    │ 1.00 (MANDATORY)       │
│ Unsupported Claim Rate (UCR) │ 1.0 - Groundedness Score                     │ 0.00 (MANDATORY)       │
│ Scene ID Attribution Accuracy│ Real existing catalog ID in database         │ 100% (MANDATORY)       │
│ Provenance Completeness      │ Result records linked to valid SHA-256 hash  │ 100% (MANDATORY)       │
│ External Network Leakage     │ Packets captured attempting outbound egress  │ STRICTLY ZERO          │
└──────────────────────────────┴──────────────────────────────────────────────┴────────────────────────┘
```

---

## 4. Automated Benchmark Script (`scripts/run_evaluation.py`)

AstraTrace encapsulates the full evaluation protocol into a single reproducible CLI tool:
```bash
python scripts/run_evaluation.py \
  --datasets-dir /data/benchmarks \
  --models-dir /models \
  --output-report docs/evaluation_report.json \
  --device cuda \
  --verify-provenance
```
This script executes all benchmark splits, generates reliability diagrams, computes IoU/F1 and Recall@K curves, and outputs the official SIH evaluation dossier.
