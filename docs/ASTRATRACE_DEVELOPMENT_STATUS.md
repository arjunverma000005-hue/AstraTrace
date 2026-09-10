# AstraTrace — Development Status Tracker
**Project:** AstraTrace  
**SIH Problem ID:** SIH26227  
**Sponsor:** Ministry of Defence / Indian Army, Directorate General of Information Systems (DGIS)  
**Last Updated:** 2026-09-11 (Milestone 8 Completion)

---

## 1. Milestone Progress Overview

```
┌──────────┬───────────────────────────────────────────┬─────────────┬────────────────────────────────────┐
│ Milestone│ Description                               │ Status      │ Completion Evidence / Deliverables │
├──────────┼───────────────────────────────────────────┼─────────────┼────────────────────────────────────┤
│ M1       │ Foundation & Repository Setup             │ COMPLETED   │ apps/backend, apps/frontend, tests │
│ M2       │ Data Ingestion & Preprocessing            │ COMPLETED   │ IngestionService, CLI, API, tests  │
│ M3       │ Metadata Catalog & Database Indexing      │ COMPLETED   │ PostGIS DDL, SQLite, STAC, API     │
│ M4       │ Baseline Retrieval Pipeline               │ COMPLETED   │ Vocabulary, Scorer, Search API/CLI │
│ M5       │ Baseline Change Detection Pipeline        │ COMPLETED   │ Detector, Morphology, API, CLI, tests │
│ M6       │ Advanced Embeddings & Semantic Search     │ COMPLETED   │ 512-D Vectors, NumPy ANN, Hybrid, API, CLI, Benchmark │
│ M7       │ Quality Gate & False-Alarm Suppression    │ COMPLETED   │ Tile/Pair Quality, False-Alarm Gating, API, CLI, Benchmark │
│ M8       │ Backend Search APIs & MapLibre UI         │ COMPLETED   │ Unified Search, MapLibre UI, Review Queue, CLI, tests │
│ M9       │ Provenance Graph & Offline Hardening      │ PLANNED     │ Scheduled for Day 9                │
│ M10      │ Automated Evaluation & SIH Presentation   │ PLANNED     │ Scheduled for Day 10               │
└──────────┴───────────────────────────────────────────┴─────────────┴────────────────────────────────────┘
```

---

## 2. Component Implementation Status

### 2.1 Backend (`apps/backend`)
- [x] **FastAPI Application Factory:** Implemented in `app/main.py` with CORS and request tracing middleware.
- [x] **Configuration Management:** Implemented in `app/config.py` with Pydantic Settings and strict environment validation.
- [x] **Structured Logging:** Implemented in `app/core/logging.py` with JSON formatting, request ID injection, and sensitive token scrubbing.
- [x] **Error Handling:** Implemented in `app/core/errors.py` with RFC 7807 problem details.
- [x] **Health & Status Endpoints:** Implemented in `app/api/v1/router.py` serving `/health` and `/status`.
- [x] **Scene Ingestion Router:** Implemented in `app/api/v1/router.py` serving `POST /api/v1/ingest` and `GET /api/v1/ingest/manifest/{scene_id}`.
- [x] **Ingestion & Tiling Service:** Implemented in `app/services/ingestion.py` (Rasterio GeoTIFF parsing, sliding-window tiling, quality metrics, SHA-256 lineage manifests).
- [x] **Ingestion Schemas:** Implemented in `app/schemas/ingest.py` (Pydantic models with sensor validation and coordinate bounds).
- [x] **Database Session & Engine:** Implemented in `app/db/session.py` (SQLAlchemy 2.0 engine, connection pooling, SQLite WAL + foreign keys, PostgreSQL support).
- [x] **Catalog Models:** Implemented in `app/models/catalog.py` (`SceneRecord` and `TileRecord` with WKT and GeoJSON polygon serialization).
- [x] **Catalog Schemas:** Implemented in `app/schemas/catalog.py` and `app/schemas/stac.py` (STAC Collections and Items).
- [x] **Catalog Service:** Implemented in `app/services/catalog.py` (Idempotent manifest registration, spatial bounding box queries, temporal queries, STAC serialization).
- [x] **Catalog & STAC Endpoints:** Implemented in `app/api/v1/endpoints/catalog.py` and `app/api/v1/endpoints/stac.py`.
- [x] **Baseline Search Router & Service:** Implemented in `app/services/retrieval/` and `app/api/v1/endpoints/search.py` serving `POST /api/v1/search/baseline`.
- [x] **EuroSAT Controlled Vocabulary:** Implemented in `app/services/retrieval/vocabulary.py` with synset resolution.
- [x] **Tile Feature Classifier & Scorer:** Implemented in `app/services/retrieval/baseline_classifier.py` and `baseline_scorer.py` (NDVI, NDWI, Brightness, Texture, IoU, Temporal recency).
- [x] **Baseline Search CLI:** Implemented in `scripts/baseline_search.py`.
- [x] **Change Differencing & Otsu:** Implemented in `app/services/change/differencing.py` (Normalized Euclidean distance $\Delta \mathbf{S} \in [0, 1]$, index deltas $\Delta \text{NDVI}, \Delta \text{NDWI}, \Delta \text{Brightness}$, adaptive Otsu $[0.15, 0.65]$).
- [x] **Pure NumPy Morphology:** Implemented in `app/services/change/morphology.py` (Binary erosion, dilation, opening, closing, 8-connectivity BFS connected component area filter).
- [x] **Baseline Change Detector:** Implemented in `app/services/change/detector.py` (Validation, masking, Otsu thresholding, morphology, physical taxonomy classification, PNG mask export).
- [x] **Change Detection Service & REST Endpoints:** Implemented in `app/services/change/service.py`, `app/schemas/change.py`, and `app/api/v1/endpoints/change.py` (`POST /api/v1/change/detect`, `POST /api/v1/change/scene-pair`, `GET /api/v1/change/mask/{change_id}`).
- [x] **Change Detection CLI:** Implemented in `scripts/detect_change.py` with single tile pair and batch scene pairing.
- [x] **Semantic Retrieval Service & Vector Engine:** Implemented in `app/services/retrieval/semantic_service.py` and `vector_index.py` (512-D unit sphere vectors, vectorized NumPy exact cosine similarity, hybrid scoring $S_{\text{hybrid}} = \alpha S_{\text{semantic}} + (1-\alpha) S_{\text{baseline}}$).
- [x] **Semantic REST Endpoints:** Implemented in `app/api/v1/endpoints/semantic.py` (`POST /api/v1/search/semantic`, `POST /api/v1/search/similar-tiles`, `POST /api/v1/embeddings/index`, `GET /api/v1/embeddings/status`).
- [x] **Embedding & Search CLIs:** Implemented in `scripts/index_embeddings.py`, `scripts/semantic_search.py`, and `scripts/evaluate_retrieval.py`.
- [x] **Tile Optical Quality Detector:** Implemented in `app/services/quality/quality_detector.py` (Pure NumPy optical metrics: NoData, cloud detection via visible whiteness/NIR, cloud shadow via low visible/NIR, saturation, usable area fraction, quality status classification).
- [x] **Observation Pair Quality Evaluator:** Implemented in `app/services/quality/pair_quality.py` (Mutual usable intersection, pure-NumPy gradient alignment co-registration proxy, temporal baseline verification, composite pair score).
- [x] **False-Alarm Quality Gate:** Implemented in `app/services/quality/quality_gate.py` (Gated decision engine, false-alarm suppression for clouds, shadows, boundary artifacts, morphological noise; confidence modulation, transparent structured analyst explanations).
- [x] **Quality Service & REST Endpoints:** Implemented in `app/services/quality/service.py`, `app/schemas/quality.py`, and `app/api/v1/endpoints/quality.py` (`POST /api/v1/quality/assess-tile`, `POST /api/v1/quality/assess-pair`, `GET /api/v1/quality/config`, `POST /api/v1/change/detect-gated`).
- [x] **Quality Assessment & Benchmark CLIs:** Implemented in `scripts/assess_quality.py` and `scripts/evaluate_quality_gate.py`.
- [x] **Unified Search Service & REST API:** Implemented in `app/services/search/unified_service.py` and `app/api/v1/endpoints/search.py` (`POST /api/v1/search/unified`) delivering 8-dimension Evidence-First candidates across AUTO, HYBRID, SEMANTIC, KEYWORD, and CHANGE modalities.
- [x] **Raster RGB Preview Generator:** Implemented in `app/api/v1/endpoints/catalog.py` (`GET /api/v1/catalog/tiles/{tile_id}/preview`) with 2%-98% percentile contrast stretching and strict path traversal protection.
- [x] **Analyst Review Service & REST Endpoints:** Implemented in `app/services/review/service.py` and `app/api/v1/endpoints/review.py` (`POST /api/v1/review/decision`, `GET /api/v1/review/queue`, `GET /api/v1/review/history/{target_id}`).
- [x] **Analyst Review Database Model & DDL:** Implemented in `app/models/review.py` (`AnalystReviewRecord`), SQLite catalog, and `sql/migrations/003_add_analyst_reviews.sql`.
- [x] **Analyst Review Queue CLI:** Implemented in `scripts/review_cli.py` (`--list`, `--inspect`, `--decide`, `--history`).

### 2.2 Frontend (`apps/frontend`)
- [x] **React 18 & TypeScript Shell:** Implemented in `src/App.tsx` with 3-column tactical workstation layout.
- [x] **API Client:** Implemented in `src/api/client.ts` with typed `/api/v1/search/unified`, review decisions, and preview loaders.
- [x] **Live Health Card:** Implemented in `src/components/HealthCard.tsx`.
- [x] **Error Boundary:** Implemented in `src/components/ErrorBoundary.tsx`.
- [x] **MapLibre GL JS Map Viewer:** Implemented in `src/components/MapViewer.tsx` (100% offline self-contained style, vector tile rendering, candidate bounding footprints, WebGL 2D tactical fallback).
- [x] **Multi-modal Search Bar:** Implemented in `src/components/SearchBar.tsx` (modality switcher, bounding box coordinates, confidence cutoff slider).
- [x] **Evidence-First Inspection Card:** Implemented in `src/components/EvidenceCard.tsx` (WHAT, WHERE, WHEN, WHICH, WHY, CONFIDENCE, EVIDENCE, PROVENANCE with confirmation/rejection action buttons).
- [x] **Analyst Review Queue Component:** Implemented in `src/components/ReviewQueue.tsx` (triage tabs, summary status counters, item selection).

### 2.3 Data & Storage
- [x] **Directory Hierarchy:** Established `data/raw/`, `data/processed/`, `data/samples/`.
- [x] **Sample Fixture:** Created `data/samples/sample_metadata.json`.
- [x] **GeoTIFF Scene Storage:** Implemented in `data/processed/{scene_id}/` storing georeferenced tiles and `manifest.json`.
- [x] **Synthetic Bitemporal Sentinel-2 Scenes:** Generated via `scripts/generate_sample_scenes.py` at `data/samples/scenes/` (512x512, 4 bands B2/B3/B4/B8, 10m UTM EPSG:32643).
- [x] **Database Catalog Storage:** Implemented in `data/catalog.db` (local SQLite catalog) and `sql/init_postgis.sql` (production PostgreSQL/PostGIS DDL with pgvector extension and HNSW index).
- [x] **Tile Embedding Storage:** Implemented in `app/models/embedding.py` (`TileEmbeddingRecord` table with 512-D float32 BLOB, tile/scene FKs, and checksums) and `data/processed/vector_index.npz`.
- [x] **Change Mask Artifact Storage:** Implemented at `data/processed/changes/{change_id}_mask.png` and verified masks at `data/processed/changes/{change_id}_verified.png`.
- [x] **Thumbnail Storage:** Generated at `data/processed/thumbnails/{tile_id}.png`.

### 2.4 Models & AI/ML
- [x] **Model Weights Directory:** Established `models/` placeholder with `.gitkeep` and gitignore rules.
- [x] **Baseline Feature Extractor:** Multi-spectral physics baseline + pluggable ResNet-50 hook.
- [x] **Baseline Change Detector:** Physics-based multispectral difference engine ($\Delta \mathbf{S}$, Otsu, morphology).
- [x] **Deterministic Offline Embedding Model:** Implemented in `app/services/retrieval/embedding_model.py` (512-D unit sphere projection combining EuroSAT orthogonal basis and multispectral statistics, 100% offline, pure NumPy).
- [x] **RemoteCLIP ViT-B/32 Loader Hook:** Implemented in `app/services/retrieval/embedding_model.py` (`RemoteCLIPEmbeddingModel` with SHA-256 weight integrity check and automatic offline fallback).
- [x] **Optical Quality & False-Alarm Detector:** Pure-NumPy physical reflectance rules and morphological dilation/filtering (100% offline, 0 cloud dependencies).
- [ ] *ChangeFormer-lite Weights:* PLANNED (Milestone 9).
- [ ] *Quantized SLM GGUF Weights:* PLANNED (Milestone 9).

### 2.5 Infrastructure & Docker
- [x] **Multi-stage Backend Dockerfile:** Implemented in `docker/backend.Dockerfile`.
- [x] **Multi-stage Frontend Dockerfile:** Implemented in `docker/frontend.Dockerfile`.
- [x] **Local Development Compose:** Implemented in `docker/docker-compose.yml`.
- [x] **Air-Gapped Offline Compose:** Implemented in `docker/offline-compose.yml` (`internal: true`).
- [x] **PostgreSQL/PostGIS DDL:** Implemented in `sql/init_postgis.sql` and `sql/migrations/001_initial_catalog.sql`.
- [x] **PostGIS Vector Migration:** Implemented in `sql/migrations/002_add_embeddings_table.sql`.
- [x] **Analyst Reviews Migration:** Implemented in `sql/migrations/003_add_analyst_reviews.sql`.

### 2.6 Tests & Quality
- [x] **Backend Health Tests:** Implemented in `tests/backend/test_health.py` (4 tests passing).
- [x] **Backend Config Tests:** Implemented in `tests/backend/test_config.py` (3 tests passing).
- [x] **Backend Ingestion Tests:** Implemented in `tests/backend/test_ingestion.py` (10 tests passing).
- [x] **Backend Catalog & STAC Tests:** Implemented in `tests/backend/test_catalog.py` (10 tests passing).
- [x] **Backend Baseline Retrieval Tests:** Implemented in `tests/backend/test_retrieval.py` (14 tests passing).
- [x] **Backend Change Detection Tests:** Implemented in `tests/backend/test_change_detection.py` (17 tests passing).
- [x] **Backend Semantic Retrieval Tests:** Implemented in `tests/backend/test_semantic_retrieval.py` (18 tests passing).
- [x] **Backend Quality Gate Tests:** Implemented in `tests/backend/test_quality_gate.py` (19 tests passing).
- [x] **Backend Search & Review Tests:** Implemented in `tests/backend/test_milestone8_search_review.py` (10 tests passing).
- [x] **Total Pytest Suite:** 105/105 tests passing in ~20.89s.
- [x] **Frontend TypeScript & Build:** `tsc --noEmit` passing with 0 errors, Vite production bundle built cleanly in 17.21s.
- [x] **Automated Verification Script:** Implemented in `scripts/verify_foundation.py` covering M1 to M8 (11/11 suites passing).

---

## 3. Milestone 6 Comparative Retrieval Benchmark Results

Empirically measured via `scripts/evaluate_retrieval.py --top-k 5` against ground-truth queries across all 18 catalog tiles without synthetic overreach:

| Method | Precision@5 | Recall@5 | MRR | nDCG@5 | Latency (ms) | Operational Mode |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **BASELINE** | 0.0500 | 0.0833 | 0.1250 | 0.0740 | 86.0 ms | Keyword + Spectral Feature Classifier |
| **SEMANTIC** | **0.1000** | **0.2083** | **0.2500** | **0.1708** | **5.3 ms** | 512-D Orthogonal Vector Projection |
| **HYBRID** ($\alpha=0.65$) | 0.0500 | 0.0833 | 0.1250 | 0.0740 | 228.7 ms | Linear Blend ($0.65 S_{\text{sem}} + 0.35 S_{\text{base}}$) |

*Key finding:* Pure Semantic retrieval yields a 2x improvement in Precision@5 (0.1000 vs. 0.0500), a 2.5x improvement in Recall@5 (0.2083 vs. 0.0833), and a 2x improvement in MRR (0.2500 vs. 0.1250) over baseline keyword matching while executing in only 5.3ms.

---

## 4. Milestone 7 False-Alarm Suppression Benchmark Results

Empirically measured via `scripts/evaluate_quality_gate.py` across controlled operational scenarios comparing Baseline vs. Quality-Gated Detection:

| Operational Scenario | Baseline Changed Px | Gated Changed Px | Suppressed Px | Decision | Gated Conf | Tactical Impact |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. True Construction Change** | 4800 | 4800 | 0 | `QUALITY_DEGRADED` | 0.4479 | **100% True Change Preserved** |
| **2. Clean Negative Control** | 0 | 0 | 0 | `QUALITY_PASSED` | 0.0000 | **0 False Positives** |
| **3. Cloud Contamination Challenge** | 6400 | 0 | 6400 | `QUALITY_SUPPRESSED` | 0.0000 | **100% Cloud False Alarms Suppressed** |
| **4. Cloud Shadow Challenge** | 3600 | 0 | 3600 | `QUALITY_SUPPRESSED` | 0.0000 | **100% Shadow False Alarms Suppressed** |
| **5. Insufficient Usable Area Challenge** | 0 | 0 | 0 | `UNCERTAIN` | 0.0000 | **Explicit Analyst Escalation Flag** |

---

## 5. Milestone 8 Operational Workflow & Review Queue

The operational triage layer connects the backend retrieval, change detection, and quality systems into an Evidence-First workstation:

- **Evidence-First Contract:** Every query candidate exposes 8 immutable intelligence dimensions:
  1. `WHAT`: Multi-spectral class identity, physical classification, or detected change category.
  2. `WHERE`: WGS84 bounding box, centroid coordinate, and GeoJSON Polygon with projected CRS.
  3. `WHEN`: Satellite acquisition datetime or bitemporal baseline duration.
  4. `WHICH`: Sensor platform (SENTINEL-2), scene ID, and tiled patch identifier.
  5. `WHY`: Mathematical score decomposition explaining ranking (semantic cosine similarity, baseline spectral alignment, hybrid weights).
  6. `CONFIDENCE`: Calibrated composite confidence score ($0.0 \le c \le 1.0$) modulated by the optical quality gate.
  7. `EVIDENCE`: Real-time 8-bit RGB preview thumbnail URL, verified binary change mask, and usable area metrics.
  8. `PROVENANCE`: Cryptographic SHA-256 tile checksum, algorithm signature, and execution trace timestamps.

- **Air-Gapped Map Visualization:** MapLibre GL JS operates 100% offline via self-contained dark tactical vector styling without external Mapbox/OSM tile requests, complemented by a fallback 2D vector coordinate grid for low-power or non-accelerated terminals.

- **Human-in-the-Loop Triage Guardrail:** Analyst review actions (`CONFIRMED`, `REJECTED`, `FLAGGED_FOR_INSPECTION`) are recorded with timestamps, analyst IDs, and immutable evidence snapshots into `analyst_reviews`. In accordance with strict operational rules, analyst review decisions are audit-only and **never** trigger autonomous model retraining or weight modification.

---

## 6. Blockers & Risks
- **Current Blockers:** ZERO.
- **Active Operational Risk:** Docker CLI is not installed on the Windows host PATH; all host execution and testing utilize native Python 3.12 and Node.js v22. Containerized profiles, PostGIS DDL scripts, and migrations are packaged and verified syntactically.




