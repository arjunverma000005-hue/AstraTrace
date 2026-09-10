# AstraTrace — Master Architecture Review & System Specification
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Document Type:** Architecture Audit & System Specification  
**Status:** ARCHITECTURE REVIEW COMPLETE (Scope Frozen; Pre-Implementation)

---

## 1. Executive Architecture Audit Summary

This document establishes the verified technical architecture for **AstraTrace**, an offline, provenance-preserving geospatial intelligence (GeoINT) discovery engine. The system addresses **SIH26227** by transforming satellite archive exploitation from a manual, coordinate-bound process into an automated semantic, temporal, and multisensor discovery workflow.

### Non-Negotiable Source-of-Truth Hierarchy
1. Official SIH 2026 Problem Statement (SIH26227)
2. AstraTrace Developer Guide (v1.0)
3. Approved AstraTrace Research & Architecture Documents
4. Existing Project Requirements & Schemas
5. Actual Repository State (`https://github.com/arjunverma000005-hue/AstraTrace` — verified as empty / virgin repo)
6. Official Documentation of Technologies (GDAL, PostGIS, PyTorch, OGC STAC)
7. Peer-Reviewed Research Literature
8. Reputable Open-Source Repositories
9. General Engineering Knowledge

---

## 2. Verified Repository State Audit

- **Repository Inspected:** `https://github.com/arjunverma000005-hue/AstraTrace`
- **Audit Method:** `git ls-remote` query against the designated repository URL.
- **Audit Finding:** The remote repository contains **zero refs, zero branches, and zero commits**. It is an uninitialized, virgin repository.
- **Architectural Consequence:** No legacy code exists to preserve or refactor. The architecture defined herein serves as the clean, definitive blueprint for Milestone 1. No implementation features, performance metrics, or screenshots are claimed as pre-existing.

---

## 3. Canonical End-to-End System Architecture

The AstraTrace architecture is strictly partitioned into two decoupled loops:
1. **The Operational Core Pipeline (Critical Path):** Fully deterministic, fast, offline, and observable.
2. **The Controlled Self-Improvement Loop (Offline Path):** Asynchronous, decoupled, gated by human review.

```
===================================================================================================
                                1. OPERATIONAL INFERENCE PIPELINE
===================================================================================================

[Satellite Scene Ingestion (GeoTIFF / COG)]
                  │
                  ▼
      [STAC Metadata Validation]  ──► (Extracts timestamp, sensor, CRS, bbox, bands)
                  │
                  ▼
   [Raster Preprocessing & Masking]
   ├── Coordinate Reference System (CRS) Reprojection (UTM / EPSG:3857)
   ├── Sub-Pixel Co-Registration (ORB/RANSAC ≤ 0.5 px residual)
   ├── Quality Mask Generation (Cloud, Haze, Shadow, NoData via SCL/Bands)
   └── Radiometric Normalization & SAR Speckle Filtering (Lee Filter)
                  │
                  ▼
          [Tiling Engine]  ──► (Fixed 256x256 tiles with 10% overlap + SHA-256 hash)
                  │
                  ├──► [Optical Encoder (RemoteCLIP ViT-B/32)] ──┐
                  │                                             ├──► [Joint Geospatial Embedding]
                  ├──► [SAR Encoder (Sentinel-1 Backscatter)] ──┘               │
                  │                                                             ▼
                  │                                             [Vector Index (pgvector HNSW / FAISS)]
                  │
                  └──► [Temporal Pair Builder]
                                │
                                ▼
                   [Temporal Change Engine]
                   ├── Tier 1: Spectral / NDVI / NDWI Difference (Baseline)
                   └── Tier 2: Bitemporal Siamese Transformer (ChangeFormer-lite)
                                │
                                ▼
                    [Change Evidence Store]
                                │
[Analyst Query (Text / Image / AOI)]                           │
                  │                                            │
                  ▼                                            │
          [Query Parser]                                       │
   (Grammar-Constrained Local SLM: Target, Change, Spatial, Time)│
                  │                                            │
                  ▼                                            │
      [Hybrid Retrieval Engine] ◄──────────────────────────────┘
   (Vector Cosine Distance + PostGIS Spatial R-Tree + Temporal Date Range SQL)
                  │
                  ▼
       [Quality Gate Evaluation]
   (Suppresses Cloud Contamination, Seasonal Shifts, Registration Jitter)
   (Labels: confirmed_change | probable_change | uncertain | likely_artifact | insufficient_quality)
                  │
                  ▼
     [Multisensor Agreement Scoring]
   (Optical Difference Corroborated with SAR Backscatter Shift)
                  │
                  ▼
        [Candidate Ranking]
   (Score = 0.30*Semantic + 0.25*Change + 0.15*Agreement + 0.10*Spatial + 0.10*Quality + 0.10*Feedback)
                  │
                  ▼
       [Evidence Composition]
   (Generates Bitemporal Visual Diffs, Probability Mask Overlays, Provenance Traces)
                  │
                  ▼
[FastAPI Service ──► React + MapLibre GL JS Analyst UI]
                  │
                  ├──► [Analyst Review Queue: Confirm / Reject / Annotate]
                  │                 │
                  │                 ▼
                  │     [Immutable Audit Trail]
                  │     (Append-Only PostgreSQL with Cryptographic Hash Chaining)
                  │
                  └──► [Provenance-Preserving Export (PDF / GeoJSON Dossier)]

===================================================================================================
                        2. CONTROLLED SELF-IMPROVEMENT LOOP (OFFLINE ONLY)
===================================================================================================

[Analyst Adjudication (Confirm / Reject)]
                  │
                  ▼
       [Feedback & Review Store]  ──► (Accumulates Hard Positives & Hard Negatives)
                  │
                  ▼
        [Critic & Reflector]      ──► (Analyzes Systematic Failures & Proposes Rerank/Prompt Deltas)
                  │
                  ▼
      [Candidate Improvement]     ──► (Generates Proposed Weight Tuning or Prompt Variant)
                  │
                  ▼
    [Automated Offline Evaluation]──► (Benchmarks against Golden Set: LEVIR-CD, EuroSAT, Nuisance Set)
                  │
                  ▼
   [Security & Red-Team Gate]     ──► (Runs Adversarial Test Matrix RT-SEC-01 through 18)
                  │
                  ▼
     [Regression Testing Gate]    ──► (Verifies No Performance Degradation on Legacy Benchmarks)
                  │
                  ▼
     [Human Approval Promotion]   ──► (Lead Engineer / Analyst Signs Off on Release)
                  │
                  ▼
   [Versioned Model / Config Release]
```

---

## 4. Subsystem Audits & Technical Specifications

### 4.1 Ingestion & Geospatial Preprocessing
- **Technologies:** GDAL 3.8+, Rasterio 1.3+, Shapely 2.0+, GeoPandas.
- **Input Formats:** GeoTIFF, Cloud Optimized GeoTIFF (COG), STAC JSON catalogs.
- **CRS Handling:** Native preservation of projected coordinate systems; automatic reprojection to local UTM zones or EPSG:3857 for consistent pixel-to-meter distance calculations.
- **Windowed Raster Reads:** Uses Rasterio windowed reads to process large $10,000 \times 10,000$ scenes in memory-efficient blocks, avoiding Out-Of-Memory (OOM) crashes.
- **Co-Registration Bounds:** Bitemporal observations undergo sub-pixel feature matching (ORB/RANSAC). If registration residual exceeds $1.0\text{ pixel}$, the pair is flagged with `registration_warning` and down-weighted in the quality gate.

### 4.2 Metadata & Cataloging
- **Database Engine:** PostgreSQL 16 with PostGIS 3.4.
- **Catalog Model:** STAC (SpatioTemporal Asset Catalog) v1.0.0 compatible schema.
- **Spatial Indexing:** 2D R-Tree indexes (`GiST`) on scene bounding boxes and tile footprints (`ST_Intersects`, `ST_Contains`, `ST_DWithin`).
- **Temporal Indexing:** B-Tree index on `scenes.acquired_at` and composite index on `(sensor, acquired_at)`.

### 4.3 Storage Subsystem
- **Object Storage:** MinIO (local S3-compatible object store) deployed inside Docker, with fallback to local POSIX filesystem mounts (`data/tiles/`, `data/raw/`).
- **Intermediate Formats:** Cloud Optimized GeoTIFF for raster tiles; Parquet for precomputed tabular metadata and feature summaries.

### 4.4 Embedding & Hybrid Vector Retrieval
- **Primary Vector Store:** PostgreSQL `pgvector` 0.7+ using HNSW (Hierarchical Navigable Small World) index with cosine distance operator (`<=>`).
- **Fast-Path Batch Index:** FAISS (`IndexFlatIP`) utilized for ultra-fast in-memory batch clustering during the "Find Similar Sites" analyst workflow.
- **Hybrid Query Execution:** Combines spatial polygon filters, temporal date ranges, sensor types, and vector cosine similarity within a single SQL statement.

### 4.5 Query Understanding & Language Subsystem
- **Runtime:** Local Small Language Model (SLM) executing via `llama.cpp` / `llama-cpp-python` with GGUF 4-bit quantization.
- **Models:** Qwen2.5-7B-Instruct or Llama-3.1-8B-Instruct.
- **Grammar-Constrained Decoding:** Uses GBNF grammars to guarantee 100% syntactically valid Pydantic JSON output. The model is mathematically incapable of generating unstructured conversational fluff.
- **Strict Boundary:** The SLM has zero tool execution privileges, zero shell access, and zero authority to generate spatial coordinates or scene IDs.

### 4.6 Temporal Change Detection Subsystem
- **Tier 1 (Deterministic Baseline):**
  - NDVI delta ($\Delta NDVI = NDVI_{after} - NDVI_{before}$)
  - NDWI delta ($\Delta NDWI = NDWI_{after} - NDWI_{before}$)
  - Spectral angle difference and absolute RGB/NIR difference.
  - Morphological opening/closing and minimum connected component size filter ($>10\text{ pixels}$).
- **Tier 2 (Advanced ML Model):**
  - ChangeFormer-lite: Siamese hierarchical transformer encoder with lightweight MLP decoder processing co-registered $T_1$ and $T_2$ tiles.
  - Outputs binary change probability maps and multi-class logits (construction, clearance, water, road).

### 4.7 Quality Gate & False-Alarm Suppression
- Evaluates 6 nuisance dimensions before allowing a change candidate to enter the ranked queue:
  1. *Cloud & Haze Contamination:* Rejects tiles with $>15\%$ cloud cover in the region of change.
  2. *Shadow Interference:* Cloud shadow masking prevents false structural appearance detections.
  3. *NoData Boundaries:* Border and nodata pixels are masked out of change calculations.
  4. *Seasonal Phenology:* Compares acquisition calendar month; seasonal vegetation shifts are flagged via NDVI baseline drift rather than structural change.
  5. *Sun-Angle & Illumination Discrepancies:* Azimuth/elevation delta checks prevent solar angle shifts from being labeled as structural changes.
  6. *Co-registration Jitter:* High-frequency edge differences along high-contrast boundaries are filtered.
- **Categorical States Assigned:** `confirmed_change`, `probable_change`, `uncertain`, `likely_artifact`, `insufficient_quality`.

### 4.8 Multisensor Agreement Engine
- Fuses Optical (Sentinel-2) and SAR (Sentinel-1) observations:
  - Optical captures spectral reflectance and land-cover signatures.
  - SAR captures structural roughness, dielectric properties, and double-bounce corner reflectors.
- **Agreement Metric:**
  $$A_{opt, sar} = 1.0 - |S_{opt} - S_{sar}|$$
- Corroborating optical/SAR evidence inflates ranking; contradiction depresses score and assigns `uncertain` state. Missing SAR data triggers fallback to optical-only mode with an explicit `modality_missing: SAR` tag.

### 4.9 Provenance & Forensic Audit
- Every candidate result is backed by a verifiable provenance graph storing:
  - `source_scene_ids`, `acquisition_timestamps`, `sensor_platforms`
  - `coordinate_reference_system`, `spatial_bounds`
  - `preprocessing_pipeline_version`, `model_checkpoint_sha256`
  - `quality_gate_metrics`, `confidence_score`, `uncertainty_score`
  - `analyst_id`, `review_decision`, `review_timestamp`
- Stored in an append-only PostgreSQL table (`audit_events`) with Merkle-style hash chaining.

---

## 5. Anti-Complexity & Hardening Directives

To guarantee delivery and defense in the SIH 10-day window:
1. **NO Kubernetes:** Strictly Docker Compose. No Helm charts, no distributed ingress controllers.
2. **NO Cloud Dependencies at Runtime:** Zero external API calls. All weights, data, and packages are local.
3. **NO Generative Image Synthesis:** No diffusion models, GANs, or hallucinated imagery.
4. **NO Autonomous Code Modification:** Self-improvement is restricted to prompt tuning and reranker coefficients; zero autonomous code or model commits.
