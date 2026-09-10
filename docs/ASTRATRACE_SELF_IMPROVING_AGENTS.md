# AstraTrace — Self-Improving AI Systems & Agent Architecture
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Domain:** Agentic Systems / Reflective AI / Continual Learning / Safe Autonomy  
**Status:** APPROVED ARCHITECTURE SPECIFICATION (Pre-Implementation)

---

## 1. Motivation & Foundational Distinction

In operational geospatial intelligence, static systems quickly become brittle when exposed to diverse geographic terrains, novel sensor artifacts, and nuanced analyst vocabulary. However, allowing an AI agent to autonomously modify its own code or neural network weights in production introduces catastrophic risks: goal drift, hallucination loops, reward hacking, and security degradation.

To resolve this tension, AstraTrace enforces a fundamental engineering boundary:

```
┌────────────────────────────────────────┬────────────────────────────────────────┐
│ MODEL SELF-IMPROVEMENT                 │ AGENT SCAFFOLD SELF-IMPROVEMENT        │
├────────────────────────────────────────┼────────────────────────────────────────┤
│ • Unsupervised online weight updates.  │ • Systematic prompt template tuning.   │
│ • Catastrophic forgetting risk.        │ • Retrieval reranking weight tuning.   │
│ • Opaque mathematical drift.           │ • Tool invocation recipe optimization. │
│ • Prohibited in production AstraTrace. │ • Curated episodic & procedural memory.│
│ • Permitted ONLY via offline gates.    │ • Primary AstraTrace improvement axis. │
└────────────────────────────────────────┴────────────────────────────────────────┘
```

AstraTrace focuses strictly on **Scaffold-Level Improvement** during active operation, restricting neural weight updates to rigorous, offline-evaluated training cycles.

---

## 2. AstraTrace Self-Improvement Closed-Loop Architecture

The self-improvement lifecycle operates through an isolated, gated pipeline:

```
[Analyst / User]
       │
       ▼
   [Task Input]
       │
       ▼
[Worker Execution Engine]
       │
       ▼
[Observable Execution Trace] ──► [Structured Telemetry & Latency Logs]
       │
       ▼
[Evaluator / Critic Agent] ────► [Computes Correctness, Grounding, Safety]
       │
       ▼
[Experience Store] ────────────► [Partitioned: Episodic / Procedural / Feedback]
       │
       ▼
[Reflector Module] ────────────► [Answers: What failed? Why? What should change?]
       │
       ▼
[Candidate Improvement] ───────► [Generates: Proposed Prompt / Rerank Weight]
       │
       ▼
[Offline Evaluation Suite] ────► [Benchmarks Candidate against 200+ Golden Cases]
       │
       ▼
[Security & Red-Team Suite] ───► [Verifies Zero Guardrail Degradation]
       │
       ▼
[Regression Test Gate] ────────► [Ensures No Metric Drops on Legacy Baselines]
       │
       ▼
[Human-in-the-Loop Approval] ──► [Lead Engineer / Analyst Reviews Diff & Metrics]
       │
       ▼
[Versioned Production Release]
```

### Non-Negotiable Rule:
Under no circumstances may an agent perform:
`EXECUTION ──► AUTONOMOUS SELF-MODIFICATION ──► PRODUCTION`
Every modification must pass offline regression testing and human promotion approval.

---

## 3. Worker, Critic & Reflector Triad

The system splits operational reasoning into three specialized, decoupled agents:

```
┌────────────────────────────────────────────────────────────────────────┐
│ 1. WORKER AGENT                                                        │
│ • Objective: Execute the user's operational query.                     │
│ • Responsibilities: Parse query, extract constraints, call hybrid      │
│   retrieval, trigger change detection, and compose evidence.           │
│ • Constraints: Strictly deterministic tool calls; zero code generation.│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 2. CRITIC AGENT                                                        │
│ • Objective: Grade execution fidelity and evidence grounding.          │
│ • Checks: Did the Worker cite real Scene IDs? Were quality flags       │
│   respected? Did confidence match empirical calibration? Did the       │
│   Worker attempt unauthorized tools?                                   │
│ • Output: Structured Scorecard {groundedness, latency_score, error_flag}│
└──────────────────────────────────┬─────────────────────────────────────┘
                                   │
                                   ▼
┌────────────────────────────────────────────────────────────────────────┐
│ 3. REFLECTOR AGENT                                                     │
│ • Objective: Post-mortem failure analysis & strategy recommendation.   │
│ • Core Questions:                                                      │
│   1. What happened during this query execution?                        │
│   2. Why did retrieval return false positives or miss true targets?   │
│   3. What systematic prompt ambiguity caused the parser failure?       │
│   4. What concrete configuration adjustment would fix this?            │
│ • Output: Versioned Candidate Recommendation (NOT direct commit).      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Multi-Tiered Self-Improving Memory Architecture

AstraTrace employs three distinct memory stores with strict metadata hygiene:

### 4.1 Episodic Memory
- **Content:** Exact execution traces of complex, ambiguous, or multi-step queries (query text, extracted JSON, returned candidate IDs, analyst confirmation/rejection status).
- **Retention & Decay:** Traces are retained with an exponential half-life (e.g. 90 days). Stale or unreviewed episodes are automatically compressed into statistical aggregates.
- **Entry Schema:**
  ```json
  {
    "memory_id": "mem_ep_0891",
    "timestamp": "2026-09-10T18:22:00Z",
    "source": "analyst_session",
    "user_id": "usr_analyst_04",
    "query": "Find newly built structures near roads",
    "parsed_constraints": {"target": "built structures", "context": "near roads"},
    "retrieved_tiles": ["tile_0042", "tile_0098"],
    "analyst_action": "confirmed",
    "validation_status": "verified_ground_truth"
  }
  ```

### 4.2 Semantic Memory
- **Content:** Domain vocabulary mappings, sensor-specific radiometric rules, regional geographic terminology, and satellite band combinations.
- **Update Mechanism:** Consolidated periodically from analyst annotations and validated domain taxonomies.

### 4.3 Procedural Memory
- **Content:** Optimal execution recipes and tool routing policies (e.g., *"When query mentions road expansion, prioritize Sentinel-2 Band 8 NIR edge differencing followed by Sentinel-1 VV backscatter cross-check"*).

### 4.4 Memory Poisoning & Conflict Defense
- Memories derived from unverified sources receive a low initial confidence score ($<0.30$).
- When two episodic memories conflict (e.g., analyst A confirms a tile, analyst B rejects the identical tile), the system does not average the scores; it tags the case as `CONTESTED` and alerts the lead reviewer.

---

## 5. Self-Improving Retrieval & Reranking

When analysts review search results, their decisions become structured feedback:

```
[Analyst Click: "Confirm"] ──► Hard Positive Example (Query <-> Tile Pair)
[Analyst Click: "Reject"]  ──► Hard Negative Example (Query <-> Tile Pair)
```

### Reranking Update Pipeline:
1. **Feedback Staging:** Confirmations and rejections are accumulated in the `reviews` table.
2. **Batch Training Queue:** Once a threshold of validated reviews is reached ($\ge 100$ balanced pairs), an offline training job fits a lightweight reranker (e.g., cross-encoder or logistic ranking layer).
3. **Evaluation Check:** The candidate reranker is evaluated against the golden evaluation set. It must demonstrate an improvement in Recall@10 ($\Delta \ge +0.02$) without increasing latency by $>100\text{ ms}$.
4. **Promotion:** Upon passing automated regression and human review, the new reranker weights are promoted to production.

---

## 6. Safety Guardrails Against Self-Improvement Failure Modes

```
┌─────────────────────────┬────────────────────────────────────────────────────────────────────────┐
│ Failure Mode            │ AstraTrace Architectural Defense                                       │
├─────────────────────────┼────────────────────────────────────────────────────────────────────────┤
│ Reward Hacking          │ Evaluators use deterministic multi-metric rubrics (IoU, F1, Latency); │
│                         │ the agent cannot optimize one metric by destroying others.             │
│ Evaluator Gaming        │ The Critic Agent code and golden evaluation test cases are stored in a │
│                         │ read-only, cryptographically hashed volume inaccessible to workers.    │
│ Memory Poisoning        │ Rate limiting on analyst review submissions; multi-analyst quorum      │
│                         │ required before feedback is admitted to the training store.            │
│ Goal & Prompt Drift     │ Core system instructions are frozen; only user-facing few-shot examples│
│                         │ and grammar parameters can be proposed for tuning.                     │
│ Provenance Falsification│ Audit records are append-only; agents have zero SQL `UPDATE` privileges│
│                         │ on history tables.                                                     │
└─────────────────────────┴────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Levels of Safe Autonomy in AstraTrace

AstraTrace maps system autonomy against seven recognized levels:

- **Level 0 (No Self-Improvement):** Static code, static prompts, static model weights.
- **Level 1 (Memory Accumulation):** Logs traces, records analyst confirmations/rejections in structured database.
- **Level 2 (Reflective Diagnostics):** Reflector agent analyzes failures and generates post-mortem diagnostic reports.
- **Level 3 (Candidate Proposal Generation):** Proposes revised prompt formulations or reranking coefficients.
- **Level 4 (Automated Offline Benchmarking):** Automatically executes full regression test suite against proposed candidates.
- **Level 5 (Human-Gated Promotion):** System presents benchmark delta to human engineer who explicitly approves deployment.
- **Level 6 (Autonomous Low-Risk Promotion):** System autonomously adjusts bounded hyper-parameters within strict guardrail limits.
- **Level 7 (Full Autonomous Modification):** System modifies its own source code, tools, or models without human review.

### AstraTrace Operational Target:
**AstraTrace operates strictly at LEVEL 1 through LEVEL 5.**  
Levels 6 and 7 are **STRICTLY PROHIBITED** and require explicit high-level architectural and security re-authorization.
