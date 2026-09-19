# AstraTrace 2.0 — System Architecture Document
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Theme:** Space Technology  
**Classification:** DEFENCE UNCLASSIFIED // SOVEREIGN AIR-GAPPED DEPLOYMENT  

---

## 1. Executive System Overview

AstraTrace 2.0 is an offline-first, provenance-preserving geospatial intelligence (GeoINT) discovery and change detection platform. Built from scratch to address the demanding operational mandates of the Indian Army (DGIS) and Ministry of Defence, AstraTrace eliminates the critical bottlenecks of manual satellite archive inspection, false-alarm-prone pixel differencing, unvetted cloud dependencies, and opaque AI decision-making.

### Key Architectural Invariants:
1. **100% Air-Gapped Sovereign Operation:** Zero external network egress. No runtime dependency on CDNs, cloud inference APIs, external tile servers, or remote font/style registries.
2. **Three-Tier Storage Model:** Clean separation between immutable rasters/weights, persistent database state, and ephemeral scratch memory. The application source tree remains strictly read-only during execution.
3. **Evidence-First Change Detection:** Raw pixel differencing is never equated to meaningful tactical change. Every candidate change must pass through an automated multispectral Quality Gate (cloud, shadow, and NoData filtering) and adaptive Otsu morphological thresholding.
4. **$O(N_{\text{new}})$ Incremental Ingestion:** Adding new satellite acquisitions updates spatial catalogs and vector indices in linear time proportional to new data, without re-indexing historical archives.
5. **Cryptographic Provenance DAG:** Every derived observation, tile, change mask, and analyst adjudication is linked into an immutable SHA-256 Directed Acyclic Graph (DAG) with full tamper detection.

---

## 2. High-Level Architecture Diagram

```mermaid
flowchart TB
    subgraph UI["Analyst Presentation Layer (Apps/Frontend)"]
        NAV["Top Mission Bar<br/>Live UTC | Air-Gap Badge | Active AOI"]
        SEARCH["Search Bar<br/>Natural Language Slot Parser | Image-to-Image Sim | Mode Selector"]
        MAP["MapLibre GL Map Viewer<br/>7 Comparison Modes: Swipe, Opacity, Spyglass, Side-by-Side, Flicker, Diff, Mask"]
        TIMELINE["Temporal Scrubber<br/>T1 / T2 Pins | Earliest Change Indicator | Animation Controls"]
        INSPECT["9-Tab Evidence Inspector<br/>Overview, Scores, Before/After, Change, Similar, Clusters, Provenance, Audit, Meta"]
        BENCH_MODAL["Benchmark Dossier Modal<br/>mAP@5, nDCG@5, FARR, Latency, Air-Gap Proof"]
    end

    subgraph API["REST & Geospatial Gateway (Apps/Backend FastAPI)"]
        ROUTER["FastAPI APIRouter (/api/v1)"]
        EP_SEARCH["/search/unified, /search/similar-tiles, /search/image"]
        EP_CHANGE["/change/detect, /change/preview, /change/mask"]
        EP_QUALITY["/quality/assess, /quality/pair"]
        EP_CLUSTERS["/clusters, /clusters/{id}"]
        EP_PROV["/provenance/graph/{id}, /provenance/verify"]
        EP_REVIEW["/review/queue, /review/decision, /review/history"]
        EP_EVAL["/evaluation/summary, /evaluation/run"]
        EP_EXPORT["/export/report, /provenance/export"]
    end

    subgraph SERVICES["Core Domain Services (Apps/Backend Services)"]
        SVC_INGEST["Incremental Ingestion Engine<br/>Atomic Tiling | CRS Validation | SHA-256 Manifest"]
        SVC_RETRIEVAL["Dual-Modality Retrieval<br/>EuroSAT Baseline + 512-D Unit Embeddings"]
        SVC_FAISS["FAISS Vector Index<br/>IndexFlatIP Exact Cosine ANN Search"]
        SVC_QGATE["Multispectral Quality Gate<br/>Cloud, Shadow, NoData Masking & Usable Area"]
        SVC_CHANGE["Adaptive Change Detection<br/>Bitemporal Diff + Otsu Clamping + Morph Closing"]
        SVC_CLUSTER["Unsupervised Discovery<br/>K-Means & DBSCAN Anomaly Clusterer"]
        SVC_PROV["Forensic Provenance<br/>SHA-256 Parent-Child DAG & Tamper Verifier"]
        SVC_AUDIT["Immutable Audit Logger<br/>Append-Only Forensic Action Log"]
        SVC_EVAL["Automated Benchmark Runner<br/>mAP, NDCG, MRR, FARR, Latency Benchmarker"]
    end

    subgraph STORAGE["Three-Tier Storage Model"]
        TIER1["Tier 1: Immutable Data & Models (Read-Only)<br/>• Sentinel-2 L2A GeoTIFF Rasters<br/>• Pre-trained Model Weights<br/>• Ground-Truth Evaluation Datasets"]
        TIER2["Tier 2: Persistent State (R/W)<br/>• SQLite / PostGIS Catalog (metadata.db)<br/>• FAISS Vector Indices (embeddings/)<br/>• JSON-L Audit Chains (audit/)<br/>• Analyst Review Decisions (reviews.db)"]
        TIER3["Tier 3: Ephemeral Scratch (Temporary)<br/>• Memory Buffers<br/>• In-Flight Tiling Slices<br/>• Temporary Export Bundles"]
    end

    UI <-->|HTTP / JSON / GeoJSON| ROUTER
    ROUTER --> EP_SEARCH & EP_CHANGE & EP_QUALITY & EP_CLUSTERS & EP_PROV & EP_REVIEW & EP_EVAL & EP_EXPORT
    EP_SEARCH --> SVC_RETRIEVAL & SVC_FAISS
    EP_CHANGE --> SVC_CHANGE & SVC_QGATE
    EP_QUALITY --> SVC_QGATE
    EP_CLUSTERS --> SVC_CLUSTER
    EP_PROV --> SVC_PROV
    EP_REVIEW --> SVC_AUDIT
    EP_EVAL --> SVC_EVAL
    EP_EXPORT --> SVC_PROV & SVC_AUDIT

    SERVICES --> STORAGE
    SVC_INGEST --> TIER1 & TIER2
    SVC_RETRIEVAL & SVC_FAISS --> TIER2
    SVC_CHANGE & SVC_QGATE --> TIER1 & TIER3
    SVC_PROV & SVC_AUDIT --> TIER2
```

---

## 3. The Clean Three-Tier Storage Architecture

A major vulnerability of traditional geospatial pipelines is writing temporary outputs or index files directly into the source code repository or raster ingestion folders. AstraTrace enforces strict boundary separation across three tiers:

| Storage Tier | Storage Path | Access Mode | Contents & Lifespan | Invariants Enforced |
| :--- | :--- | :---: | :--- | :--- |
| **Tier 1: Immutable Assets** | `data/raw/`, `models/weights/` | `RO` (Read-Only) | Raw Sentinel-2 / Sentinel-1 GeoTIFF rasters, pre-trained model weights, held-out ground truth files. | Byte-for-byte immutable. Mountable as `:ro` in Docker. SHA-256 checked on load. |
| **Tier 2: Persistent State** | `data/processed/` | `RW` (Read/Write) | `metadata.db` (Spatial Catalog & Reviews), `embeddings/` (FAISS vector index), `audit/` (Audit trails). | Persists across container restarts. Append-only logs with cryptographic hash-chaining. |
| **Tier 3: Ephemeral Scratch** | `/tmp` or OS tempdir | `RW` (Transient) | Tile slicing buffers, temporary unzipped export bundles, in-flight difference rasters. | Flushed automatically. Never referenced in persistent DAG chains. |

---

## 4. Subsystem Deep Dive

### 4.1 Incremental Raster Ingestion & Tiling Engine
- **Module:** `apps.backend.app.services.ingestion_incremental.IncrementalIngestor`
- **Tiling Spec:** Fixed grid subdivision ($256 \times 256$ pixels, $10\text{m}$ GSD per pixel for Sentinel-2 bands B02, B03, B04, B08).
- **Coordinate Transformations:** Validates EPSG:4326 (WGS84) geographic and EPSG:3857 (Web Mercator) projection metadata via GDAL/Rasterio.
- **Complexity:** $O(N_{\text{new}})$ — new scenes are sliced and their vectors computed without reprocessing prior scenes.
- **Failure Recovery:** Atomic staging. If a tile generation or database insert fails, the staging directory is cleaned and the transaction rolled back.

### 4.2 Dual-Modality Retrieval Engine
- **Baseline Keyword Scorer:** Maps analyst queries against EuroSAT's 10 Land Use Land Cover (LULC) canonical classes (AnnualCrop, Forest, HerbaceousVegetation, Highway, Industrial, Pasture, PermanentCrop, Residential, River, SeaLake) with lexical filtering.
- **Semantic Vector Engine:** 512-dimensional orthogonal unit-sphere embeddings ($||\mathbf{v}||_2 = 1$). Fast similarity calculation using FAISS `IndexFlatIP`.
- **Hybrid Retrieval Formulator:**
  $$S_{\text{hybrid}}(q, t) = \alpha \cdot S_{\text{semantic}}(q, t) + (1 - \alpha) \cdot S_{\text{baseline}}(q, t)$$
  Empirically calibrated to $\alpha = 0.65$, yielding balanced precision across high-level operational concepts and strict land-cover definitions.

### 4.3 Multispectral Quality Gate & False-Alarm Suppression
- **Module:** `apps.backend.app.services.quality.quality_gate.QualityGateService`
- **Nuisance Mitigation:**
  - **Cloud Mask:** High-reflectance optical thresholding with band ratio verification.
  - **Shadow Mask:** Low-illumination near-infrared absorption scoring.
  - **NoData Mask:** Border black-fill and missing sensor swath detection.
  - **Usable Area Verification:** Requires $> 80\%$ cloud/shadow-free overlap between $T_1$ and $T_2$ before allowing change classification.
- **False Alarm Reduction Rate (FARR):**
  $$\text{FARR} = \frac{\Delta_{\text{raw}} - \Delta_{\text{gated}}}{\Delta_{\text{raw}}} \times 100\%$$
  Empirically measured at **100.0%** rejection on cloud and shadow perturbation challenges.

### 4.4 Bitemporal Change Detection Pipeline
- **Module:** `apps.backend.app.services.change.detector.ChangeDetectorService`
- **Spectral Differencing:** Multi-channel normalized Euclidean distance $\Delta \mathbf{S}(x, y) = ||\mathbf{S}_{T_2}(x, y) - \mathbf{S}_{T_1}(x, y)||_2$.
- **Adaptive Otsu Clamping:** Automatically calculates optimal binarization threshold $T^*$, clamped strictly to the range $[0.15, 0.65]$ to prevent under-segmentation in low-contrast environments.
- **Morphological Post-Processing:** Applies mathematical closing ($3 \times 3$ structuring element) to bridge disconnected building footprints, followed by opening to eliminate single-pixel sensor speckle.

### 4.5 Unsupervised Discovery & Clustering
- **Module:** `apps.backend.app.services.clustering.service.ClusteringService`
- **Algorithms:** K-Means clustering for macro-scale pattern partitioning, and DBSCAN for dense anomaly discovery in unindexed frontier sectors.
- **Operational Utility:** Enables analysts to discover anomalous clusters of infrastructure expansion without needing pre-existing labels.

### 4.6 Cryptographic Provenance DAG
- **Module:** `apps.backend.app.services.provenance.service.ProvenanceService`
- **Graph Topology:** Directed Acyclic Graph tracing every entity:
  $$\text{Raw Scene} \longrightarrow \text{Ingestion Task} \longrightarrow \text{Tile} \longrightarrow \text{Embedding} \longrightarrow \text{Change Detection} \longrightarrow \text{Analyst Adjudication}$$
- **Verification Engine:** Cryptographic verifier traverses the parent-child hash chain ($H_{\text{child}} = \text{SHA-256}(H_{\text{parent}} \mathbin{\Vert} \text{Payload})$). Any byte modification immediately triggers a `TAMPER_DETECTED` state.

### 4.7 NASA Worldview-Inspired Analyst Interface
- **Technology:** React 18, TypeScript 5, MapLibre GL JS 6.9, Tailwind CSS.
- **7 Bitemporal Comparison Modes:** Single, Swipe (draggable split curtain), Opacity (cross-fade slider), Spyglass (circular magnifying loupe), Side-by-Side (synchronized dual viewports), Flicker (rapid alternation), Difference (CSS contrast difference blend), and Change Mask overlay.
- **9-Tab Evidence Inspector:** Deep inspection across Overview, Scores, Before/After, Change, Similar, Clusters, Provenance, Audit, and Metadata.
- **Timeline Scrubber:** Synchronized temporal exploration with T1/T2 epoch pins and automated playback.

---

## 5. Security & Air-Gap Enforcement

- **Socket-Level Interception Test:** Automated test suite `tests/backend/test_airgap_no_outbound_network.py` wraps Python `socket.socket.connect` to verify that no network requests leave the machine.
- **No External Font or Tile Requests:** MapLibre GL JS operates with pre-cached local raster tile layers and local vector fonts.
- **Container Isolation:** Multi-container deployment uses Docker `bridge` network configured with `internal: true`, which disables the default gateway and drops all outbound routing.
- **Non-Root Execution:** Backend executes under dedicated non-privileged user `astrauser:astragroup` (UID/GID 1000).

---

## 6. Architecture Traceability Matrix

| SIH26227 Requirement | System Component | Implementation File | Pass Criteria |
| :--- | :--- | :--- | :---: |
| Semantic Satellite Search | Semantic Retrieval Service | `apps/backend/app/services/retrieval/semantic_service.py` | Top-5 Precision > Baseline, Latency < 1500 ms |
| False-Alarm Suppression | Multispectral Quality Gate | `apps/backend/app/services/quality/quality_gate.py` | 100% Cloud & Shadow Rejection |
| Change Detection | Adaptive Otsu Detector | `apps/backend/app/services/change/detector.py` | Clamped Otsu [0.15, 0.65], Morphology Closing |
| Air-Gap Security | Socket Monitor & Nginx | `tests/backend/test_airgap_no_outbound_network.py` | Zero network egress |
| Forensic Lineage | Provenance DAG & Verifier | `apps/backend/app/services/provenance/` | SHA-256 Hash Chain Integrity Verified |
| Analyst Interface | NASA Worldview UI | `apps/frontend/src/components/MapViewer.tsx` | 7 Comparison Modes, 9-Tab Inspector |
