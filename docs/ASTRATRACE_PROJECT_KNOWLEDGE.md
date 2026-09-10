# AstraTrace — Master Project Knowledge & Blueprint
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Problem Title:** Semantic Retrieval and Multi-Temporal Change Analysis of Satellite Imagery  
**Organization / Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Theme:** Space Technology  
**Category:** Software  
**Status:** LEARNING & RESEARCH ONLY (Pre-Implementation)  
**Current Codebase State:** NOT INITIALIZED (Repository is empty; zero implementation code currently committed)

---

## 1. Executive Summary & Operational Context

Defence and geospatial analysts face an overwhelming influx of multi-temporal, multi-sensor satellite imagery. Conventional exploitation systems suffer from a severe architectural limitation: an analyst must know the exact geographic coordinates, bounding boxes, or calendar acquisition dates before they can search or analyze imagery. When tasked with broad-area monitoring, strategic reconnaissance, or infrastructure assessment, this manual coordinate-driven lookup fails.

**AstraTrace** is an offline, provenance-preserving geospatial intelligence (GeoINT) discovery engine designed to solve this operational bottleneck. It enables intelligence analysts to:
1. Search satellite archives by natural language semantics (e.g., *"Find newly built structures near roads between January 2023 and January 2025"*).
2. Discover visually and semantically similar sites across expansive geographical regions (*Find Similar Sites*).
3. Detect and classify true structural changes over time while suppressing environmental and sensor artifacts (clouds, seasonal shifts, shadows, misregistration).
4. Cross-verify observations using multisensor evidence (combining Optical and Synthetic Aperture Radar / SAR).
5. Interrogate results with complete end-to-end provenance, auditable lineage, and human-in-the-loop analyst review.
6. Operate in sovereign, strictly air-gapped, network-disabled environments.

AstraTrace is **not** a generic conversational chatbot, **not** an ungrounded RAG demo, and **not** an autonomous agent with open-ended execution privileges. It is a mission-critical analytical workbench engineered for precision, evidence attribution, and mathematical reproducibility.

---

## 2. Official SIH26227 Requirements & Constraints

### 2.1 Official Mandatory Capabilities
According to the official SIH26227 problem statement and the approved AstraTrace Developer Guide, the system must deliver:

1. **Semantic and Multimodal Retrieval:**
   - Free-text semantic search over indexed satellite tiles.
   - Image-to-image similarity retrieval (querying using an image patch or map bounding box).
   - Rank-ordered candidate returns based on relevance.
   - Deterministic filtering by Area-of-Interest (AOI polygon/bbox), date range, and sensor type.

2. **Multi-Temporal Change Analysis:**
   - Identify visual and structural evolution: appearance, disappearance, expansion, and contraction.
   - Classify detected changes into concrete functional categories: construction, clearance, water variation, and road development.
   - Estimate the earliest supported observation date confirming a change event.

3. **Quality-Aware False-Alarm Suppression:**
   - Suppress nuisance changes driven by seasonal vegetation shifts, illumination/sun-angle disparities, cloud shadows, haze, snow, radiometric differences, and minor co-registration errors.
   - Generate per-pixel quality and confidence masks.
   - Prioritize high precision over indiscriminate, noisy recall.

4. **Discovery and Spatial Clustering:**
   - Group similar geographical sites across wide regional areas.
   - Support interactive discovery of analogous infrastructure.

5. **Analyst Workflow and Provenance:**
   - Ranked review queue prioritized by composite confidence.
   - Visual before/after comparison with overlaid change masks.
   - Complete metadata display: acquisition timestamp, sensor platform, resolution, coordinate reference system (CRS), processing history.
   - Structured analyst adjudication: `Confirm`, `Reject`, or `Annotate`.
   - Immutable audit logging and provenance-preserving export packages.

6. **Scale, Incremental Ingestion, and Sovereignty:**
   - Efficient vector and spatial indexing (PostGIS + pgvector / FAISS).
   - Incremental ingestion of newly acquired scenes without full index recomputation.
   - 100% on-premises, air-gapped operation with network egress disabled during evaluation.
   - Native support for Cloud Optimized GeoTIFFs (COG) and STAC metadata.

### 2.2 Explicit Constraints
- **Network Sovereignty:** Evaluation runs with network access completely disabled after staging. No external SaaS APIs (OpenAI, Google Cloud, external STAC endpoints) are permitted at runtime.
- **Model Provenance:** All pretrained weights must be declared with verifiable origin, licensing, and SHA-256 checksums, and must be packaged locally.
- **Public Data Compliance:** Development and evaluation utilize public satellite data (Copernicus Sentinel-1/Sentinel-2, USGS Landsat, open benchmarks) and organizer-provided evaluation sets. No classified data is used.
- **Engineering Metrics:** The evaluation requires reporting indexed surface area, scene/tile counts, index build duration, storage footprint, query latency (p95), and hardware specifications.

---

## 3. End-to-End System Architecture

The AstraTrace pipeline follows a strictly ordered, observable workflow where every step produces auditable data artifacts:

```
[Satellite Scene Ingestion (GeoTIFF / COG)]
                  │
                  ▼
      [STAC Metadata Validation]
                  │
                  ▼
   [Raster Preprocessing & Masking]
   ├── CRS Reprojection & Alignment
   ├── Cloud / Haze / Shadow / NoData Masks
   └── Radiometric Normalization
                  │
                  ▼
          [Tiling Engine]
                  │
                  ├──► [Optical Encoder] ──┐
                  │                        ├──► [Multimodal Fusion] ──► [Vector Index (pgvector/FAISS)]
                  ├──► [SAR Encoder] ──────┘
                  │
                  └──► [Temporal Pair Builder] ──► [Temporal Change Model] ──► [Change Evidence Store]
                                                                                      │
[Analyst Query (Text / Image / AOI)]                                                 │
                  │                                                                   │
                  ▼                                                                   │
          [Query Parser]                                                              │
   (Extracts Target, Change, Spatial, Time)                                           │
                  │                                                                   │
                  ▼                                                                   │
     [Hybrid Retrieval Engine] ◄──────────────────────────────────────────────────────┘
   (Combines Vector Search + PostGIS Spatial/Temporal Filters + Change Evidence)
                  │
                  ▼
       [Quality Gate Evaluation]
   (Filters Cloud Contamination, Seasonal Artifacts, Misregistration)
                  │
                  ▼
     [Multisensor Agreement Scoring]
   (Cross-verifies Optical and SAR Evidence)
                  │
                  ▼
        [Candidate Ranking]
   (Composite Score: Semantic + Change + Agreement + Spatial + Quality + Feedback)
                  │
                  ▼
       [Evidence Composition]
                  │
                  ▼
[FastAPI Backend ──► React + MapLibre UI]
                  │
                  ├──► [Analyst Adjudication (Confirm / Reject)]
                  │                 │
                  │                 ▼
                  │      [Immutable Audit Trail]
                  │                 │
                  │                 ▼
                  │   [Offline Feedback Store & Reranking Queue]
                  │
                  └──► [Provenance-Preserving Export (PDF / GeoJSON)]
```

---

## 4. The Five Core AstraTrace Innovations

| Innovation | What Competitors Do | AstraTrace Technical Differentiator |
| :--- | :--- | :--- |
| **1. Temporal-Semantic Retrieval** | Text-to-image search returning static snapshots without temporal context. | Parses natural-language temporal queries (e.g., *"newly built structures near roads between 2023 and 2025"*) and simultaneously evaluates semantic concept embeddings against bi-temporal change vectors. |
| **2. Quality-Gated Change Intelligence** | Naive pixel differencing or uncalibrated change models that flag every cloud, shadow, and seasonal crop shift as a change alert. | Employs an explicit quality filter analyzing cloud masks, illumination angles, seasonal NDVI/NDWI baselines, and co-registration residuals to classify alerts into granular states (`confirmed_change`, `probable_change`, `uncertain`, `likely_artifact`, `insufficient_quality`). |
| **3. Multisensor Agreement Scoring** | Relies exclusively on optical imagery, blinding the system during cloud cover, or treats SAR as an isolated afterthought. | Computes co-registered Optical (Sentinel-2) and SAR (Sentinel-1) structural changes. Modalities that corroborate each other boost candidate confidence; contradictions depress confidence and trigger uncertainty flags. Missing modalities fall back gracefully with explicit indicators. |
| **4. Provenance-As-Data** | Opaque black-box outputs with a single similarity percentage. | Every query result is anchored in an immutable directed acyclic graph (DAG) capturing raw scene IDs, band resolutions, preprocessing hashes, model checkpoint SHA-256, inference parameters, and quality metrics. Results are fully reproducible. |
| **5. Incremental Offline Index** | Monolithic vector databases requiring total archive re-indexing upon ingestion of each new satellite pass. | Modular tiling and append-only spatial/vector indexes allow incoming scenes to be ingested, tiled, embedded, and indexed incrementally without taking the platform offline or rebuilding historical tables. |

---

## 5. Scope Boundary (MVP vs. Future)

To prevent feature creep and guarantee delivery within hackathon constraints, AstraTrace enforces strict boundary tiers:

### MUST HAVE (MVP Boundary)
- Local satellite archive storage (MinIO / local filesystem).
- GeoTIFF and Cloud Optimized GeoTIFF (COG) ingestion pipeline.
- STAC-compliant metadata catalog in PostgreSQL / PostGIS.
- Semantic free-text query parsing and embedding retrieval.
- Image-to-image similarity retrieval.
- Bi-temporal change detection engine (before/after comparison).
- Quality-aware cloud, haze, shadow, and NoData filtering.
- Ranked candidate review list with visual before/after evidence and change masks.
- Calibrated confidence and uncertainty scores.
- End-to-end provenance tracking attached to each candidate.
- Analyst confirmation/rejection review action with audit logging.
- Standalone Docker Compose offline deployment profile with network egress disabled.

### SHOULD HAVE (Post-MVP High Priority)
- Sentinel-1 (SAR) and Sentinel-2 (Optical) cross-modal fusion.
- Multi-class change categorization (construction, clearance, road extension, water variation).
- Earliest supported observation date estimation via temporal scene stacks.
- Incremental index update scripts for new scene ingestion.
- Exportable formal intelligence evidence dossiers (PDF + GeoJSON).
- Observable query execution trace detailing latency and component contributions.

### NICE TO HAVE (Bonus / Differentiation)
- Active learning feedback loop to adjust reranking weights based on analyst confirmations.
- Proximity-based filtering using pre-indexed OpenStreetMap (OSM) road vector layers.
- Local multilingual query support (e.g., Hindi query parsing via local small language models).
- Hardware execution toggle (CPU fallback benchmark vs. GPU acceleration).

### FUTURE (Explicitly Excluded from Hackathon Scope)
- Ingestion adapters for classified or military-restricted proprietary satellite formats.
- Distributed multi-node Kubernetes clustering and multi-agency federation.
- Real-time airborne / drone telemetry stream ingestion.
- Autonomous online model weight retraining directly inside production containers.
- Underground, subterranean, or concealed activity detection.

---

## 6. Data and Sensor Strategy

### 6.1 Satellite Constellations
1. **Sentinel-2 L2A (Copernicus):**
   - *Modality:* Optical Multispectral (Bands: Blue B2, Green B3, Red B4, NIR B8 at 10m; RedEdge B5-B7, SWIR B11-B12 at 20m).
   - *Role:* Primary source for land-use semantics, vegetation indices (NDVI), water indices (NDWI/MNDWI), and spectral change analysis.
2. **Sentinel-1 GRD (Copernicus):**
   - *Modality:* C-Band Synthetic Aperture Radar (SAR), Ground Range Detected, Dual-polarization (VV + VH) at 10m.
   - *Role:* Cloud-penetrating structural and dielectric change verification, building corner-reflector detection, and seasonal vegetation penetration.
3. **Landsat 8/9 Collection 2 (USGS):**
   - *Modality:* Optical and Thermal Infrared (30m multispectral, 15m panchromatic).
   - *Role:* Long-term historical baseline comparison and multi-decadal context.

### 6.2 Public Benchmark & Training Datasets
- **EuroSAT:** 27,000 georeferenced Sentinel-2 image patches across 10 land-cover classes. Used for semantic retrieval baseline benchmarking.
- **BigEarthNet (Sentinel-1 & Sentinel-2):** 590,326 multi-label Sentinel-2 tiles paired with Sentinel-1 dual-pol SAR patches. Used for multisensor representation validation.
- **LEVIR-CD / S2Looking / OSCD:** Standard bitemporal remote sensing change detection benchmark datasets for building construction, urban expansion, and land clearance.

### 6.3 Synthetic Data Injection Strategy
To evaluate false-alarm suppression under rigorous, controlled conditions where ground-truth change dates are precisely known:
- Public base scenes are augmented with synthetic vector footprints (simulating newly erected warehouses, graded access tracks, cleared canopy).
- Controlled nuisance perturbations are programmatically injected into temporal pairs: seasonal color shifts, illumination variations, synthetic cloud/shadow overlays, and spatial misregistrations (0.5 to 2.0 pixel sub-pixel shifts).
- All synthetic test sets are strictly tagged as `dataset_type: synthetic` in metadata to maintain scientific honesty.

---

## 7. Operational Workflow & Analyst Interaction

1. **Dashboard Initialization:** Analyst opens the AstraTrace web interface. The system displays indexed geographical boundaries, available scene dates, sensor coverage, and system operational mode (`OFFLINE_MODE: TRUE`).
2. **Query Input:** Analyst submits a natural-language query: *"Find newly built structures near roads between January 2023 and January 2025"*, optionally drawing a bounding polygon on the map.
3. **Deterministic Query Interpretation:** The local Query Parser decomposes the query into typed filters (target: `built structures`, change: `appearance`, context: `near roads`, temporal range: `2023-01-01` to `2025-01-01`).
4. **Candidate Retrieval & Ranking:** The hybrid retrieval engine filters candidate tiles via spatial and temporal metadata, ranks tiles via semantic embedding similarity, and computes change masks between the earliest and latest usable observations.
5. **Quality Gating:** The quality gate suppresses false alarms caused by cloud coverage, shadows, or misregistration, rejecting noisy tiles and assigning quality state tags.
6. **Analyst Review Queue:** The UI presents a sorted queue of candidate detections. For each candidate, the analyst inspects:
   - Synchronized before/after image viewer.
   - Overlayable change probability mask.
   - Corroborating optical and SAR evidence panels.
   - Composite confidence score, uncertainty metric, and quality flags.
   - Complete data lineage (scene IDs, timestamps, model checksums).
7. **Adjudication & Feedback:** Analyst marks the detection as `Confirmed` or `Rejected`, optionally providing categorical notes. The decision is recorded in an immutable PostgreSQL audit log.
8. **Discovery:** Analyst clicks *"Find Similar Sites"* on a confirmed target. The engine computes vector cosine similarity against the target tile's embedding across the entire archive, surfacing analog infrastructure.
9. **Dossier Export:** Analyst exports a cryptographically verifiable intelligence report (PDF summary + GeoJSON boundary layers with embedded provenance hashes).
10. **Air-Gap Verification:** Outbound network interfaces are disconnected; the entire search, retrieval, inference, and review cycle continues to operate with zero degradation.

---

## 8. Non-Negotiable Source-of-Truth Rules
1. **Never claim implementation that does not exist:** The codebase is currently uninitialized. All components described herein represent approved architectural targets and research specifications.
2. **Never claim unmeasured accuracy:** Performance benchmarks, F1 scores, and latency metrics must cite concrete experimental runs once implemented.
3. **Strict Language Status Labeling:**
   - Feature planned in specifications: **PLANNED**
   - Feature deferred to future phases: **FUTURE**
   - Candidate model/technology discovered in research: **RESEARCH CANDIDATE**
   - Unverified or absent specification: **INFORMATION NOT PROVIDED**
4. **Prohibition on Hallucinated Intelligence:** Under no circumstances may an AI component generate fictional coordinates, false scene timestamps, ungrounded change vectors, or synthetic intelligence claims. If evidence is lacking, the system must return `INSUFFICIENT EVIDENCE`.
