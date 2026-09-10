# AstraTrace — AI Evaluation & Benchmark Plan
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Domain:** Quantitative Evaluation / Machine Learning Benchmarking / Groundedness / Calibration  
**Status:** APPROVED EVALUATION SPECIFICATION (Pre-Implementation)

---

## 1. Evaluation Objectives & Philosophy

In high-stakes defence and intelligence applications, algorithmic transparency, calibrated confidence, and empirical reproducibility take precedence over ungrounded claims. AstraTrace rejects opaque "black-box" demonstrations. Every component—from query parsing and vector retrieval to change detection, quality gating, and evidence synthesis—is subjected to rigorous quantitative benchmarking.

### Core Evaluation Tenets:
1. **Honest Baselines First:** Every advanced transformer or foundation model must demonstrate a statistically significant performance delta over a classical baseline (e.g., ChangeFormer vs. raw differencing with morphological cleanup; RemoteCLIP vs. ResNet-50 keyword matching).
2. **Separation of Failure Modes:** When an analytical output is erroneous, the evaluation harness must isolate whether it was caused by **Retrieval Failure** (relevant scene/tile was not surfaced) or **Inference/Generation Failure** (tile was retrieved but change/semantics were misclassified).
3. **Calibrated Confidence:** An algorithm that reports 95% confidence on an ambiguous cloud shadow is operationally dangerous. Predicted probabilities must reflect true empirical error rates.
4. **Geographic & Temporal Partitioning:** Splits must be geographically disjoint (non-overlapping spatial bounding boxes) and temporally held out to prevent spatial-autocorrelation leakage.

---

## 2. Golden Datasets & Ground Truth Specifications

```
┌─────────────────┬──────────────────────┬──────────────────────┬───────────────────────────────┐
│ Dataset Name    │ Modality / Sensor    │ Primary Task         │ Annotation Type               │
├─────────────────┼──────────────────────┼──────────────────────┼───────────────────────────────┤
│ EuroSAT         │ Sentinel-2 (Optical) │ Semantic Retrieval   │ 10 Land-Cover Classes         │
│ BigEarthNet     │ Sentinel-1 & S-2     │ Multisensor Baseline │ 19 Land-Cover Multi-labels    │
│ LEVIR-CD        │ Optical Bitemporal   │ Change Detection     │ Pixel-level Building Masks    │
│ OSCD            │ Sentinel-2 Bitemp    │ Change Detection     │ Urban Change Binary Masks     │
│ S2Looking       │ Optical Bitemporal   │ Rural Building CD    │ Multi-temporal Polygons       │
│ AstraTrace-Syn  │ S-1 & S-2 (Public)   │ Nuisance Ablation    │ Controlled Synthetic Changes  │
│ Golden Queries  │ Natural Language     │ Query Parser Eval    │ Structured JSON Ground Truth  │
└─────────────────┴──────────────────────┴──────────────────────┴───────────────────────────────┘
```

### 2.1 Geographic Split Strategy
- **Training AOI:** 70% of spatial tiles.
- **Validation AOI:** 15% of spatial tiles (disjoint administrative zone/grid).
- **Held-Out Test AOI:** 15% of spatial tiles (minimum 50 km buffer separation to prevent spatial leakage).

---

## 3. Detailed Metric Formulations

### 3.1 Semantic & Multimodal Retrieval
Evaluated over $N$ golden query scenarios against ground-truth relevant tiles $R_q$:

- **Recall@K:** Proportion of relevant tiles successfully retrieved within top $K$ results:
  $$\text{Recall@K} = \frac{1}{|Q|} \sum_{q \in Q} \frac{|R_q \cap \text{Top}_K(q)|}{|R_q|}$$
  *Evaluated at $K \in \{1, 5, 10, 20\}$.* Target: $\ge 0.70$ for $K=10$.
- **Precision@K:** Fraction of retrieved top $K$ tiles that are genuinely relevant:
  $$\text{Precision@K} = \frac{1}{|Q|} \sum_{q \in Q} \frac{|R_q \cap \text{Top}_K(q)|}{K}$$
- **Mean Reciprocal Rank (MRR):** Measures the ranking position of the first relevant candidate:
  $$\text{MRR} = \frac{1}{|Q|} \sum_{q \in Q} \frac{1}{\text{rank}_q}$$
- **Normalized Discounted Cumulative Gain (nDCG@K):** Evaluates graded relevance:
  $$\text{DCG@K} = \sum_{i=1}^K \frac{2^{rel_i} - 1}{\log_2(i + 1)}, \quad \text{nDCG@K} = \frac{\text{DCG@K}}{\text{IDCG@K}}$$
- **Retrieval Latency:** p50, p95, p99 search duration in milliseconds. Target: $\text{p95} < 1500\text{ ms}$.

---

### 3.2 Multi-Temporal Change Detection
Evaluated against pixel-level binary and multi-class ground-truth masks:

- **Intersection-over-Union (IoU / Jaccard Index):**
  $$\text{IoU} = \frac{|Y_{true} \cap Y_{pred}|}{|Y_{true} \cup Y_{pred}|} = \frac{TP}{TP + FP + FN}$$
  Target: $\ge 0.65$ on held-out change benchmarks.
- **F1-Score:** Harmonic mean of precision and recall:
  $$F1 = \frac{2 \cdot TP}{2 \cdot TP + FP + FN}$$
  Target: $\ge 0.70$ on held-out public/synthetic benchmark.
- **False Positive Rate (FPR) & False Negative Rate (FNR):**
  $$\text{FPR} = \frac{FP}{FP + TN}, \quad \text{FNR} = \frac{FN}{TP + FN}$$
- **Earliest Supported Observation Error:** Temporal discrepancy (in calendar days) between the algorithmically deduced earliest observation confirming a change and the ground-truth date $T_{true}$:
  $$\Delta T = |T_{pred} - T_{true}| \quad \text{(days)}$$

---

### 3.3 Quality Gate & False-Alarm Suppression
Evaluated specifically on a "Nuisance Challenge Set" containing severe environmental shifts with zero actual construction/demolition:

- **False-Alarm Reduction Rate:** Percent reduction in false alerts generated by the quality-gated pipeline compared to raw spectral differencing:
  $$\text{FARR} = \frac{FP_{baseline} - FP_{gated}}{FP_{baseline}} \times 100\%$$
  Target: $\ge 25\%$ reduction on nuisance benchmark.
- **Expected Calibration Error (ECE):** Partitions model probability predictions into $M$ equal bins $B_m$ and computes weighted difference between confidence and accuracy:
  $$\text{ECE} = \sum_{m=1}^M \frac{|B_m|}{N} \left| \text{acc}(B_m) - \text{conf}(B_m) \right|$$
  Target: $\text{ECE} \le 0.08$ (indicates reliable confidence estimation).
- **Reliability Diagrams:** Plots observed accuracy against predicted confidence intervals to visualize over-confidence or under-confidence.

---

### 3.4 Query Parsing & Natural Language Understanding
Evaluated against 200 synthetically constructed and analyst-curated golden prompts:

- **Field Extraction Accuracy:** Independent accuracy for `semantic_concept`, `change_type`, `spatial_context`, `temporal_range`, `sensors`.
- **Exact Match (EM):** Percent of queries where all extracted fields precisely match ground truth.
- **Schema Validity:** Strict 100% pass rate requirement. Every parsed output must conform to Pydantic JSON schema without syntax or typing exceptions.
- **Ambiguity Detection Rate:** System must correctly identify underspecified queries (e.g. "show changes") and request clarification rather than hallucinating parameters.

---

### 3.5 RAG Faithfulness & Hallucination Prevention
Evaluated on natural language analytical summaries generated for analysts:

- **Context Groundedness:** Proportion of sentences in the generated summary directly supported by structured metadata and model evidence:
  $$\text{Groundedness} = \frac{\text{Supported Claims}}{\text{Total Claims Made}}$$
  Target: $1.00$ (Zero tolerance for unsupported claims).
- **Unsupported Claim Rate (UCR):**
  $$\text{UCR} = 1.0 - \text{Groundedness}$$
  Target: $0.00$.
- **Citation Attribution Accuracy:** Verifies that cited Scene IDs, timestamps, and coordinates match real indexed catalog records.

---

### 3.6 LLM-as-Judge Protocol (Guardrailed Usage)
If an LLM is used as an auxiliary evaluator for text summarization:
- **Defined Metric Rubric:** 5-point scale measuring (1) Factual Grounding, (2) Completeness, (3) Conciseness, (4) Absence of Hallucination.
- **Bias Mitigation:** Randomized presentation order (eliminates position bias); length normalization (eliminates verbosity bias); temperature set to 0.0 for deterministic scoring.
- **Human Calibration:** LLM scores must be calibrated against at least 50 human analyst annotations, requiring Pearson $r \ge 0.85$.
- **Authority Constraint:** An LLM judge is **never** the sole authority; deterministic unit tests and metric computations override LLM judgments.

---

## 4. Engineering & System Targets

```
┌─────────────────────────────────┬──────────────────────┬──────────────────────┐
│ Metric                          │ Baseline Target      │ Advanced Target      │
├─────────────────────────────────┼──────────────────────┼──────────────────────┤
│ Metadata Query p95 Latency      │ < 500 ms             │ < 300 ms             │
│ Vector Search p95 Latency       │ < 2.5 s              │ < 1.5 s              │
│ Single-Tile Change (GPU)        │ < 10.0 s             │ < 5.0 s              │
│ Single-Tile Change (CPU)        │ < 40.0 s             │ < 20.0 s             │
│ Incremental Tile Ingestion      │ < 20.0 s / tile      │ < 10.0 s / tile      │
│ Offline Cold Start Time         │ < 120 s              │ < 60 s               │
│ Provenance Completeness         │ 100%                 │ 100%                 │
│ External Network Calls          │ STRICTLY ZERO        │ STRICTLY ZERO        │
│ Demonstration Archive Size      │ 1,000 tiles          │ 10,000 tiles         │
└─────────────────────────────────┴──────────────────────┴──────────────────────┘
```
*(Note: Performance thresholds marked as targets represent engineering goals for the MVP; empirical values will be recorded during Milestone 12 benchmarking).*
