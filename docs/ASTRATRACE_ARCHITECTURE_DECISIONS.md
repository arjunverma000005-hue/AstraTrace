# AstraTrace — Architecture Decision Records (ADRs)
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Document Type:** Formal Architecture Decision Records (ADR-001 through ADR-010)  
**Status:** APPROVED & LOCKED

---

## ADR-001: Offline-First Air-Gapped Architecture
- **Status:** APPROVED
- **Context:** SIH26227 evaluation strictly mandates that the platform operate with network access disabled after staging. No external cloud APIs, hosted databases, or remote endpoints may be invoked at runtime.
- **Options Considered:**
  1. *Cloud-Native Deployment with Local Mocking:* Fast development, but high failure risk when internet is cut.
  2. *Hybrid Deployment (Cloud vector DB + local frontend):* Disqualified by SIH constraints.
  3. *100% Self-Contained Docker Compose Deployment:* All databases, model weights, raster files, and inference engines reside on local loopback.
- **Decision:** Adopt Option 3: A completely self-contained Docker Compose stack with network isolation (`internal: true`) for final evaluation.
- **Consequences:** Eliminates external latency and cloud egress costs; requires pre-staging all container images and model weights.
- **Risks:** High initial disk storage footprint (~20 GB for Docker images, dependencies, and model weights).
- **Verification Method:** Execute `docker compose -f infrastructure/offline-compose.yml up -d` with host physical network interface unplugged or disabled. Verify complete search and change detection execution.

---

## ADR-002: Semantic Retrieval Model Selection
- **Status:** APPROVED
- **Context:** Analysts need to search satellite imagery via natural language concepts (e.g. "storage depots", "runways", "deforested areas") without manual labeling.
- **Options Considered:**
  1. *Generic OpenAI CLIP (ViT-B/32):* Trained on internet photos; poor performance on nadir satellite overhead views and multispectral bands.
  2. *Prithvi-EO-2.0 (NASA/IBM):* Powerful 300M parameter model, but lacks native free-text embedding alignment and requires extreme GPU VRAM.
  3. *RemoteCLIP (ViT-B/32):* Contrastively trained on 824,000 domain-specific remote-sensing image-text pairs; MIT license.
- **Decision:** Standardize on **RemoteCLIP (ViT-B/32)** as the primary semantic search model, paired with a standard **ResNet-50** keyword-matching baseline.
- **Consequences:** Provides native text-to-satellite-image embedding alignment out of the box with reasonable inference latency (<80ms GPU, <450ms CPU).
- **Risks:** RemoteCLIP is trained primarily on RGB; spectral bands (NIR, SWIR) must be normalized or projected into 3-channel representations for retrieval.
- **Verification Method:** Benchmark zero-shot Recall@10 on held-out EuroSAT and RSICD validation splits.

---

## ADR-003: Temporal Change Detection Architecture
- **Status:** APPROVED
- **Context:** The system must detect visual and structural appearance, disappearance, expansion, and contraction between bitemporal satellite observations.
- **Options Considered:**
  1. *Pixel Differencing & NDVI Thresholding Only:* Fast and deterministic, but generates unacceptable false alarms on seasonal vegetation and sun-angle shifts.
  2. *Heavy Diffusion-Based Change Synthesis:* High risk of hallucination and slow inference.
  3. *Two-Tier Progression (Deterministic Baseline + ChangeFormer-lite):* Combine spectral difference baseline with a Siamese hierarchical transformer (ChangeFormer-lite) that outputs pixel-level change segmentation masks.
- **Decision:** Adopt Option 3.
- **Consequences:** Gives the team a solid baseline on Day 5 and an advanced transformer on Day 6, ensuring defensibility and fallbacks.
- **Risks:** ChangeFormer requires paired bitemporal training data; model weights must be pre-staged.
- **Verification Method:** Evaluate pixel-level IoU and F1 on LEVIR-CD and OSCD benchmark datasets.

---

## ADR-004: Unified Database & Vector Retrieval Architecture
- **Status:** APPROVED
- **Context:** AstraTrace requires simultaneous spatial bounding box filtering, temporal date range selection, metadata filtering, and vector similarity search.
- **Options Considered:**
  1. *Separate Vector DB (Milvus/Qdrant) + Separate Spatial DB (PostGIS):* Introduces two-phase query synchronization overhead and dual-service maintenance complexity.
  2. *SQLite with Custom Vector Extensions:* Inadequate spatial query performance for large multi-scene catalogs.
  3. *PostgreSQL 16 with PostGIS 3.4 and pgvector 0.7+ (with FAISS fast-path):* Single ACID database handling spatial geometries, timestamps, metadata, and high-dimensional vectors.
- **Decision:** Standardize on **PostgreSQL + PostGIS + pgvector** as the unified system catalog, using in-memory **FAISS** strictly for batch similarity clustering during "Find Similar Sites".
- **Consequences:** Simplifies deployment to a single primary database container; enables expressive hybrid SQL queries in a single round-trip.
- **Risks:** Building HNSW indexes on large tables requires memory allocation tuning in PostgreSQL (`maintenance_work_mem`).
- **Verification Method:** Execute hybrid spatial-temporal-vector queries over 10,000 synthetic tile vectors; verify p95 latency < 1.5 seconds.

---

## ADR-005: Quality-Aware False-Alarm Suppression Gate
- **Status:** APPROVED
- **Context:** Raw image differencing flags clouds, shadows, seasonal crop variations, and misregistration jitter as "changes," inundating analysts with false alerts.
- **Options Considered:**
  1. *Black-Box End-to-End Deep Net:* Hope the neural network learns to ignore clouds implicitly. (Consistently fails under out-of-distribution weather).
  2. *Explicit Multi-Rule Quality Gate:* Programmatic analysis of cloud/haze masks (Sentinel-2 Scene Classification Layer), shadow projections, co-registration error bounds, and seasonal NDVI variance.
- **Decision:** Implement an **Explicit Quality Gate** assigning 5 categorical states: `confirmed_change`, `probable_change`, `uncertain`, `likely_artifact`, `insufficient_quality`.
- **Consequences:** Transparent, rule-grounded suppression of false alerts; directly defensible to military intelligence jury members.
- **Risks:** Overly conservative thresholds might suppress subtle, genuine ground transformations.
- **Verification Method:** Evaluate False-Alarm Reduction Rate on a dedicated Nuisance Evaluation Set containing heavy cloud and seasonal shifts with zero real ground construction. Target: $\ge 25\%$ reduction vs. baseline differencing.

---

## 6. ADR-006: Multisensor Optical & SAR Agreement Scoring
- **Status:** APPROVED
- **Context:** Optical sensors are blind at night and obscured by clouds. Synthetic Aperture Radar (SAR) penetrates weather and measures surface geometry and roughness.
- **Options Considered:**
  1. *Optical-Only Pipeline:* Inadequate for sovereign defence monitoring; fails under persistent monsoon cloud cover.
  2. *End-to-End Joint Multimodal Transformer:* Extremely data-hungry; high risk of training failure during a 10-day hackathon sprint.
  3. *Decoupled Modality Scoring with Cross-Agreement Metric:* Independent optical and SAR feature evaluation combined via a mathematical agreement index ($A_{opt, sar} = 1.0 - |S_{opt} - S_{sar}|$).
- **Decision:** Adopt Option 3 for the MVP/Should-Have tier. Support optical-only, SAR-only, and joint cross-verified modes with explicit missing-modality indicators.
- **Consequences:** Modular implementation; failure or absence of one sensor does not crash the operational pipeline.
- **Risks:** SAR imagery contains inherent speckle noise requiring adaptive Lee filtering.
- **Verification Method:** Test paired Sentinel-1 / Sentinel-2 scenes over known construction sites; verify that SAR double-bounce corroboration increases candidate confidence score.

---

## ADR-007: Grammar-Constrained Local SLM Query Parsing
- **Status:** APPROVED
- **Context:** Free-text analyst queries must be parsed into structured spatial, temporal, and semantic constraints without sending data to external cloud APIs.
- **Options Considered:**
  1. *Handcrafted Regex & Heuristic Rule Parser:* Fragile; fails on colloquial language variations.
  2. *Unconstrained Local LLM Text Output:* Prone to formatting errors, markdown hallucination, and invalid JSON syntax.
  3. *Grammar-Constrained Local SLM (Qwen2.5-7B-Instruct / Llama-3.1-8B via GGUF/llama.cpp):* Enforces strict GBNF context-free grammars matching Pydantic JSON schemas.
- **Decision:** Adopt Option 3.
- **Consequences:** 100% syntactically valid JSON output guaranteed at the decoding level; zero token waste; zero risk of arbitrary shell command generation.
- **Risks:** Requires ~4.5 GB RAM/VRAM to host the 4-bit quantized SLM locally.
- **Verification Method:** Execute 200 automated query parsing tests; verify 100% schema validity and zero runtime deserialization crashes.

---

## ADR-008: Immutable Provenance-as-Data & Hash-Chained Audit Trail
- **Status:** APPROVED
- **Context:** Defence intelligence requires verifiable chain-of-custody. Every detection must show exactly which raw scenes, models, parameters, and analyst actions produced it.
- **Options Considered:**
  1. *Standard Ephemeral Application Logs:* Prone to rotation, truncation, and retroactive alteration.
  2. *Public Blockchain:* Massive unnecessary complexity and latency; inappropriate for classified/air-gapped systems.
  3. *Append-Only PostgreSQL Table with Merkle Hash Chaining:* Every record stores a cryptographic hash of its payload combined with the preceding record's hash (`prev_hash`).
- **Decision:** Adopt Option 3. Revoke SQL `UPDATE` and `DELETE` permissions on audit tables.
- **Consequences:** Delivers forensic auditability and tamper-detection using standard relational database technology.
- **Risks:** Database backup and restore procedures must preserve sequence integrity.
- **Verification Method:** Attempt programmatic SQL `UPDATE` queries on audit tables; verify permission rejection. Verify hash-chain integrity via automated audit verification script.

---

## ADR-009: Human-in-the-Loop Analyst Adjudication & Decoupled Feedback Store
- **Status:** APPROVED
- **Context:** Automated AI predictions cannot be treated as actionable intelligence without human verification. Furthermore, analyst decisions should inform future ranking improvements.
- **Options Considered:**
  1. *Autonomous Confirmation:* System flags and acts on changes automatically (unacceptable operational risk).
  2. *Direct Online Retraining:* Analyst click triggers real-time weight gradient updates (high risk of catastrophic forgetting and feedback poisoning).
  3. *Structured Review Queue with Decoupled Feedback Store:* Analyst confirms or rejects candidates; decisions are logged as hard positives/negatives into a separate staging table for offline reranker training.
- **Decision:** Adopt Option 3.
- **Consequences:** Protects production models from instant poisoning; maintains human authority over operational intelligence.
- **Risks:** Requires analyst time to review and label candidates.
- **Verification Method:** Submit review decisions via UI; verify immediate appearance in `reviews` table and subsequent offline reranker training dataset export.

---

## ADR-010: Gated Scaffold-Level Self-Improvement & Strict Autonomy Boundary
- **Status:** APPROVED
- **Context:** Self-improving agentic systems risk goal drift, reward hacking, and security degradation if permitted to modify their own code or weights autonomously.
- **Options Considered:**
  1. *Unrestricted Agent Autonomy (Level 7):* Agent autonomously modifies code, evaluator, and weights (STRICTLY PROHIBITED).
  2. *Static System with Zero Learning (Level 0):* Cannot adapt to new analyst vocabulary or regional environments.
  3. *Gated Scaffold-Level Improvement (Level 1 to Level 5):* Worker-Critic-Reflector triad proposes prompt or reranking adjustments; proposals must pass offline regression benchmarks and human sign-off before deployment.
- **Decision:** Adopt Option 3. Restrict AstraTrace operational autonomy strictly to Levels 1 through 5.
- **Consequences:** Enables structured adaptation while enforcing strict human oversight and zero production drift.
- **Risks:** Improvement cycle requires manual engineering review.
- **Verification Method:** Simulate an adversarial prompt proposal; verify that the automated regression and security test suite rejects the proposal prior to promotion.
